from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.models.schemas import ChatAnswer, RetrievedTerm


def _fallback_answer(term: RetrievedTerm) -> ChatAnswer:
    return ChatAnswer(
        term=term.term_name,
        one_line=term.official_definition[:160],
        easy_explanation="답변 생성에 실패해 공식 정의를 우선 표시합니다.",
        example="공식 정의를 확인한 뒤 다시 질문해 주세요.",
        related_terms=term.related_terms,
        source_name=term.source_name,
        source_page=term.source_page,
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


async def generate_answer(query: str, term: RetrievedTerm) -> ChatAnswer:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    system_prompt = (
        "너는 경제 입문자를 돕는 한국어 경제금융용어 설명 챗봇이다. "
        "반드시 제공된 공식 정의만 근거로 답한다. "
        "투자 추천, 매수/매도 권유, 자료에 없는 사실 단정은 하지 않는다. "
        "응답은 JSON 객체 하나로만 작성한다."
    )
    user_prompt = {
        "user_query": query,
        "retrieved_term": {
            "term_name": term.term_name,
            "official_definition": term.official_definition,
            "related_terms": term.related_terms,
            "source_name": term.source_name,
            "source_page": term.source_page,
        },
        "required_json_shape": {
            "term": "용어명",
            "one_line": "짧은 한 줄 정의",
            "easy_explanation": "경제 입문자가 이해할 수 있는 쉬운 설명",
            "example": "생활 속 예시",
            "related_terms": ["관련 키워드"],
        },
    }

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_json_object(content)
    except Exception:
        return _fallback_answer(term)

    return ChatAnswer(
        term=str(parsed.get("term") or term.term_name),
        one_line=str(parsed.get("one_line") or term.official_definition[:160]),
        easy_explanation=str(parsed.get("easy_explanation") or ""),
        example=str(parsed.get("example") or ""),
        related_terms=[
            str(item)
            for item in parsed.get("related_terms", term.related_terms)
            if str(item).strip()
        ],
        source_name=term.source_name,
        source_page=term.source_page,
    )
