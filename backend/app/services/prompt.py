from __future__ import annotations

from app.services.retrieval import RetrievalResult, TermDocument


SYSTEM_PROMPT = """당신은 한국은행 경제금융용어 챗봇입니다.

Retrieval 결과의 공식 정의만 근거로 답변합니다. 사실을 추측하거나 새로운 금융 지식을 추가하지 않습니다.
다음 형식을 반드시 지킵니다.

{한 줄 정의}
<<<EASY>>>
{쉬운 설명}
<<<EXAMPLE>>>
{생활 속 예시}
"""


def build_user_prompt(user_query: str, retrieval_result: RetrievalResult) -> str:
    return "\n".join(
        ["질문:", user_query, "", "한 줄 정의:", format_retrieval_result(retrieval_result)]
    )


def build_messages(user_query: str, retrieval_result: RetrievalResult) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_query, retrieval_result)},
    ]


def format_retrieval_result(retrieval_result: RetrievalResult) -> str:
    if retrieval_result.status != "matched" or not retrieval_result.terms:
        return "공식 정의 없음"
    return "\n\n".join(format_matched_term(term) for term in retrieval_result.terms)


def format_matched_term(term: TermDocument) -> str:
    return term.official_definition or "공식 정의 없음"
