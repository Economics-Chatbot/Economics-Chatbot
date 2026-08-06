import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi.concurrency import run_in_threadpool
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.models.schemas import (
    Answer,
    AnswerDoneData,
    AnswerStartData,
    DeltaData,
    DoneData,
    ErrorData,
    FailureData,
    Source,
    Suggestion,
    SuggestionsData,
)
from app.services.retrieval import TermDocument, retrieve

SOURCE_TITLE = "한국은행 경제금융용어 800선"
EASY_DELIMITER = "\n<<<EASY>>>\n"
EXAMPLE_DELIMITER = "\n<<<EXAMPLE>>>\n"

SYSTEM_PROMPT = (
    "당신은 한국은행 경제금융용어 공식 정의를 바탕으로 쉬운 설명을 만드는 도우미입니다. "
    "제공된 공식 정의에 있는 내용만 사용하고, 정의에 없는 사실을 추가하지 마세요. "
    "마크다운이나 다른 설명 없이 아래 형식을 정확히 지켜서 답하세요.\n\n"
    "{한 줄 정의}\n"
    "<<<EASY>>>\n"
    "{쉬운 설명}\n"
    "<<<EXAMPLE>>>\n"
    "{생활 속 예시}"
)


def sse(event: str, data: Any) -> str:
    payload = data.model_dump() if hasattr(data, "model_dump") else data
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def extract_terms(query: str) -> list[str]:
    terms = [part.strip(" .,?!") for part in re.split(r"\s*(?:,|와|과|및|그리고)\s*", query)]
    return [term for term in terms if term]


def _parse_answer(term: str, related_keywords: list[str], raw_text: str) -> Answer:
    one_line, _, remainder = raw_text.partition(EASY_DELIMITER)
    easy_explanation, _, example = remainder.partition(EXAMPLE_DELIMITER)

    return Answer(
        term=term,
        one_line_definition=one_line.strip(),
        easy_explanation=easy_explanation.strip(),
        example=example.strip(),
        related_keywords=related_keywords,
        sources=[Source(title=SOURCE_TITLE)],
    )


class _DelimiterStripper:
    """Buffers streamed text so the raw delimiters never leak into client text."""

    def __init__(self, delimiters: list[str]) -> None:
        self._delimiters = delimiters
        self._pending = ""
        self._max_delimiter_len = max((len(d) for d in delimiters), default=0)

    def feed(self, chunk: str) -> str:
        combined = self._pending + chunk
        emit = ""

        while True:
            earliest_index = None
            matched_delimiter = ""
            for delimiter in self._delimiters:
                index = combined.find(delimiter)
                if index != -1 and (earliest_index is None or index < earliest_index):
                    earliest_index = index
                    matched_delimiter = delimiter
            if earliest_index is None:
                break
            emit += combined[:earliest_index]
            combined = combined[earliest_index + len(matched_delimiter) :]

        hold_back = 0
        for length in range(min(len(combined), self._max_delimiter_len - 1), 0, -1):
            suffix = combined[-length:]
            if any(delimiter.startswith(suffix) for delimiter in self._delimiters):
                hold_back = length
                break

        if hold_back:
            emit += combined[:-hold_back]
            self._pending = combined[-hold_back:]
        else:
            emit += combined
            self._pending = ""
        return emit

    def flush(self) -> str:
        remainder, self._pending = self._pending, ""
        return remainder


class AnswerGeneration:
    """Streams a term's LLM-written explanation and exposes the parsed Answer once done."""

    def __init__(self, term_document: TermDocument) -> None:
        self.term_document = term_document
        self.raw_text = ""

    async def stream_chunks(self) -> AsyncIterator[str]:
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        stripper = _DelimiterStripper([EASY_DELIMITER, EXAMPLE_DELIMITER])

        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"용어명: {self.term_document.term_name}\n"
                        f"공식 정의: {self.term_document.official_definition}"
                    ),
                },
            ],
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            self.raw_text += delta
            cleaned = stripper.feed(delta)
            if cleaned:
                yield cleaned

        remainder = stripper.flush()
        if remainder:
            yield remainder

    def build_answer(self) -> Answer:
        return _parse_answer(
            self.term_document.term_name,
            self.term_document.related_terms,
            self.raw_text,
        )


async def stream_events(query: str) -> AsyncIterator[str]:
    terms = extract_terms(query) or [query.strip()]
    completed: list[int] = []
    failed: list[int] = []
    errors: list[int] = []
    suggested = False

    for index, term in enumerate(terms):
        try:
            result = await run_in_threadpool(retrieve, term)
        except asyncio.CancelledError:
            raise
        except Exception:
            errors.append(index)
            yield sse(
                "error",
                ErrorData(index=index, code="search_failed", message="검색 처리 중 오류가 발생했습니다."),
            )
            continue

        matched_document = result.terms[0] if result.status == "matched" and result.terms else None
        if matched_document is not None and not matched_document.official_definition:
            matched_document = None

        if matched_document is not None:
            try:
                completed.append(index)
                yield sse("answer_start", AnswerStartData(index=index, term=matched_document.term_name))
                generation = AnswerGeneration(matched_document)
                async for text in generation.stream_chunks():
                    yield sse("delta", DeltaData(index=index, text=text))
                yield sse("answer_done", AnswerDoneData(index=index, answer=generation.build_answer()))
            except asyncio.CancelledError:
                raise
            except Exception:
                if index in completed:
                    completed.remove(index)
                errors.append(index)
                yield sse(
                    "error",
                    ErrorData(index=index, code="answer_generation_failed", message="답변 생성 중 오류가 발생했습니다."),
                )
            continue

        if result.status == "candidates" and result.candidates:
            suggested = True
            yield sse(
                "suggestions",
                SuggestionsData(
                    index=index,
                    term=term,
                    suggestions=[Suggestion(term=candidate.term_name) for candidate in result.candidates],
                ),
            )
            continue

        failed.append(index)
        yield sse(
            "failure",
            FailureData(index=index, term=term, reason="not_found", message="관련된 경제 용어를 찾지 못했습니다."),
        )

    if not completed and errors:
        yield sse("done", DoneData(status="error", failed_indices=errors))
    elif completed and errors:
        yield sse("done", DoneData(status="partial", completed_indices=completed, failed_indices=errors))
    elif not completed and suggested and not failed:
        yield sse("done", DoneData(status="suggestions"))
    elif not completed and failed:
        yield sse("done", DoneData(status="failed", failed_indices=failed))
    elif failed:
        yield sse("done", DoneData(status="partial", completed_indices=completed, failed_indices=failed))
    else:
        yield sse("done", DoneData(status="completed", completed_indices=completed))
