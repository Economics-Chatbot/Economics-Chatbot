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


class _DelimiterStripper:
    markers = ("\n<<<EASY>>>", "\n<<<EXAMPLE>>>")

    def __init__(self) -> None:
        self.pending = ""

    def feed(self, chunk: str) -> str:
        self.pending += chunk
        return self._flush_complete()

    def finish(self) -> str:
        visible = self.pending
        self.pending = ""
        for marker in self.markers:
            visible = visible.replace(marker, "")
        return visible

    def _flush_complete(self) -> str:
        visible = self.pending
        for marker in self.markers:
            visible = visible.replace(marker, "")
        keep = 0
        for marker in self.markers:
            for size in range(1, min(len(marker), len(visible)) + 1):
                if visible.endswith(marker[:size]):
                    keep = max(keep, size)
        self.pending = visible[-keep:] if keep else ""
        return visible[:-keep] if keep else visible


async def _stream_term(
    *,
    query: str,
    index: int,
    term: TermDocument,
    llm_client: LLMClient,
) -> AsyncIterator[str]:
    yield sse("answer_start", AnswerStartData(index=index, term=term.term_name))
    chunks: list[str] = []
    delimiter_stripper = _DelimiterStripper()
    try:
        retrieval_result = RetrievalResult(status="matched", terms=[term])
        async for chunk in llm_client.stream_answer(
            user_query=query,
            retrieval_result=retrieval_result,
        ):
            chunks.append(chunk)
            visible = delimiter_stripper.feed(chunk)
            if visible:
                yield sse("delta", DeltaData(index=index, text=visible))
        visible = delimiter_stripper.finish()
        if visible:
            yield sse("delta", DeltaData(index=index, text=visible))
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
