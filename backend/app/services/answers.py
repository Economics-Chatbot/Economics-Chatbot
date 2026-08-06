from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Callable
from typing import Any

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
from app.services.llm import LLMClient, LLMError, LLMTimeoutError
from app.services.retrieval import RetrievalResult, TermDocument

DELTA_CHUNK_SIZE = 32


def sse(event: str, data: Any) -> str:
    payload = data.model_dump() if hasattr(data, "model_dump") else data
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def extract_terms(query: str) -> list[str]:
    terms = [part.strip(" .,?？！") for part in re.split(r"\s*(?:,|，|및|그리고)\s*", query)]
    return [term for term in terms if term]


def _parse_answer(term: str, text: str, related_keywords: list[str]) -> Answer:
    easy_marker = "\n<<<EASY>>>"
    example_marker = "\n<<<EXAMPLE>>>"
    definition, separator, rest = text.partition(easy_marker)
    easy, separator2, example = rest.partition(example_marker)
    if not separator or not separator2 or not all((definition.strip(), easy.strip(), example.strip())):
        raise ValueError("invalid answer format")
    return Answer(
        term=term,
        one_line_definition=definition.strip(),
        easy_explanation=easy.strip(),
        example=example.strip(),
        related_keywords=related_keywords,
        sources=[Source(title="한국은행 경제금융용어 800선")],
    )


class _SectionStreamer:
    markers = (
        ("\n<<<EASY>>>", "easy_explanation"),
        ("\n<<<EXAMPLE>>>", "example"),
    )

    def __init__(self) -> None:
        self.pending = ""
        self.section = "one_line_definition"

    def feed(self, chunk: str) -> list[tuple[str, str]]:
        self.pending += chunk
        return self._flush_complete(False)

    def finish(self) -> list[tuple[str, str]]:
        visible = self.pending
        self.pending = ""
        return [(self.section, visible)] if visible else []

    def _flush_complete(self, final: bool) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        while True:
            matches = [(self.pending.find(marker), marker, section) for marker, section in self.markers]
            matches = [match for match in matches if match[0] >= 0]
            if matches:
                position, marker, section = min(matches, key=lambda item: item[0])
                if position:
                    result.append((self.section, self.pending[:position]))
                self.pending = self.pending[position + len(marker):]
                self.section = section
                continue
            if final:
                if self.pending:
                    result.append((self.section, self.pending))
                    self.pending = ""
                return result
            keep = 0
            for marker, _ in self.markers:
                for size in range(1, min(len(marker), len(self.pending)) + 1):
                    if self.pending.endswith(marker[:size]):
                        keep = max(keep, size)
            if len(self.pending) > keep:
                result.append((self.section, self.pending[:-keep] if keep else self.pending))
                self.pending = self.pending[-keep:] if keep else ""
            return result


class _DeltaBatcher:
    def __init__(self, chunk_size: int = DELTA_CHUNK_SIZE) -> None:
        self.chunk_size = chunk_size
        self.section: str | None = None
        self.pending = ""

    def feed(self, section: str, text: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        if self.section != section:
            result.extend(self.finish())
            self.section = section
        self.pending += text
        while len(self.pending) >= self.chunk_size:
            result.append((section, self.pending[:self.chunk_size]))
            self.pending = self.pending[self.chunk_size:]
        return result

    def finish(self) -> list[tuple[str, str]]:
        if self.section is None or not self.pending:
            return []
        result = [(self.section, self.pending)]
        self.pending = ""
        return result


async def _stream_term(
    *,
    query: str,
    index: int,
    term: TermDocument,
    llm_client: LLMClient,
) -> AsyncIterator[str]:
    yield sse(
        "answer_start",
        AnswerStartData(index=index, term=term.term_name, related_keywords=term.related_terms),
    )
    chunks: list[str] = []
    section_streamer = _SectionStreamer()
    delta_batcher = _DeltaBatcher()
    try:
        retrieval_result = RetrievalResult(status="matched", terms=[term])
        async for chunk in llm_client.stream_answer(
            user_query=query,
            retrieval_result=retrieval_result,
        ):
            chunks.append(chunk)
            for section, visible in section_streamer.feed(chunk):
                for batched_section, text in delta_batcher.feed(section, visible):
                    yield sse("delta", DeltaData(index=index, section=batched_section, text=text))
        for section, visible in section_streamer.finish():
            for batched_section, text in delta_batcher.feed(section, visible):
                yield sse("delta", DeltaData(index=index, section=batched_section, text=text))
        for section, text in delta_batcher.finish():
            yield sse("delta", DeltaData(index=index, section=section, text=text))
        answer = _parse_answer(term.term_name, "".join(chunks), term.related_terms)
    except asyncio.CancelledError:
        raise
    except LLMTimeoutError:
        yield sse("error", ErrorData(index=index, code="llm_timeout", message="답변 생성 시간이 초과되었습니다.", retryable=True))
        return
    except LLMError:
        yield sse("error", ErrorData(index=index, code="llm_error", message="답변 생성 중 오류가 발생했습니다.", retryable=True))
        return
    except ValueError:
        yield sse("error", ErrorData(index=index, code="answer_generation_failed", message="답변 형식이 올바르지 않습니다."))
        return
    except Exception:
        yield sse("error", ErrorData(index=index, code="answer_generation_failed", message="답변 생성 중 오류가 발생했습니다."))
        return

    yield sse("answer_done", AnswerDoneData(index=index, answer=answer))


async def stream_events(
    query: str,
    retrieve_fn: Callable[..., RetrievalResult],
    llm_client_factory: Callable[[], LLMClient],
) -> AsyncIterator[str]:
    terms = extract_terms(query)
    completed: list[int] = []
    failed: list[int] = []
    errors: list[int] = []
    suggested = False

    for index, term_text in enumerate(terms):
        try:
            result = await asyncio.to_thread(retrieve_fn, term_text)
        except asyncio.CancelledError:
            raise
        except Exception:
            errors.append(index)
            yield sse("error", ErrorData(index=index, code="retrieval_failed", message="검색 처리 중 오류가 발생했습니다."))
            continue

        if result.status == "candidates":
            suggested = True
            suggestions = [Suggestion(term=item.term_name) for item in result.candidates]
            yield sse("suggestions", SuggestionsData(index=index, term=term_text, suggestions=suggestions))
            continue

        if result.status != "matched" or not result.terms or not result.terms[0].official_definition:
            failed.append(index)
            yield sse("failure", FailureData(index=index, term=term_text, reason="not_found", message="일치하는 경제용어를 찾지 못했습니다."))
            continue

        before_errors = len(errors)
        async for event in _stream_term(
            query=query,
            index=index,
            term=result.terms[0],
            llm_client=llm_client_factory(),
        ):
            yield event
            if event.startswith("event: error"):
                errors.append(index)
        if len(errors) == before_errors:
            completed.append(index)

    if completed and (failed or errors):
        status = "partial"
    elif completed:
        status = "completed"
    elif errors:
        status = "error"
    elif suggested:
        status = "suggestions"
    else:
        status = "failed"
    yield sse("done", DoneData(status=status, completed_indices=completed, failed_indices=failed + errors))
