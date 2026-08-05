import asyncio
import json
import re
from collections.abc import AsyncIterator, Iterator
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


def sse(event: str, data: Any) -> str:
    payload = data.model_dump() if hasattr(data, "model_dump") else data
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def extract_terms(query: str) -> list[str]:
    terms = [part.strip(" .,?？！") for part in re.split(r"\s*(?:,|，|및|그리고)\s*", query)]
    return [term for term in terms if term]


_ANSWERS = {
    "인플레이션": Answer(
        term="인플레이션",
        one_line_definition="상품과 서비스의 전반적인 가격 수준이 지속해서 오르는 현상입니다.",
        easy_explanation="같은 돈으로 살 수 있는 물건의 양이 줄어드는 것을 뜻합니다.",
        example="예전에는 1,000원이던 간식이 1,200원이 되는 경우입니다.",
        related_keywords=["물가", "구매력", "디플레이션"],
        sources=[Source(title="한국은행 경제금융용어 800선")],
    ),
    "디플레이션": Answer(
        term="디플레이션",
        one_line_definition="상품과 서비스의 전반적인 가격 수준이 지속해서 하락하는 현상입니다.",
        easy_explanation="물가는 내려가지만 소비와 생산도 함께 위축될 수 있습니다.",
        example="기업 매출과 임금이 줄어 사람들이 소비를 미루는 상황입니다.",
        related_keywords=["물가", "소비", "인플레이션"],
        sources=[Source(title="한국은행 경제금융용어 800선")],
    ),
}

_SUGGESTIONS = {
    "물가상승": [Suggestion(term="인플레이션", reason="물가가 오르는 현상")],
    "물가 상승": [Suggestion(term="인플레이션", reason="물가가 오르는 현상")],
}


def _answer_text(answer: Answer) -> str:
    return "\n".join(
        [
            answer.one_line_definition,
            answer.easy_explanation,
            f"예시: {answer.example}",
        ]
    )


def build_events(query: str) -> Iterator[str]:
    terms = extract_terms(query)
    completed: list[int] = []
    failed: list[int] = []
    errors: list[int] = []
    suggested = False

    for index, term in enumerate(terms):
        answer = _ANSWERS.get(term)
        if answer is None:
            candidates = _SUGGESTIONS.get(term)
            if candidates:
                suggested = True
                yield sse(
                    "suggestions",
                    SuggestionsData(index=index, term=term, suggestions=candidates),
                )
                continue
            failed.append(index)
            yield sse(
                "failure",
                FailureData(
                    index=index,
                    term=term,
                    reason="not_found",
                    message="일치하는 경제용어를 찾지 못했습니다.",
                ),
            )
            continue

        try:
            completed.append(index)
            yield sse("answer_start", AnswerStartData(index=index, term=term))
            for chunk in re.findall(r".{1,24}(?:\s+|$)", _answer_text(answer)):
                yield sse("delta", DeltaData(index=index, text=chunk))
            yield sse("answer_done", AnswerDoneData(index=index, answer=answer))
        except Exception:
            if index in completed:
                completed.remove(index)
            errors.append(index)
            yield sse(
                "error",
                ErrorData(index=index, code="answer_generation_failed", message="답변 생성 중 오류가 발생했습니다."),
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


async def stream_events(query: str) -> AsyncIterator[str]:
    for event in build_events(query):
        yield event
        await asyncio.sleep(0)
