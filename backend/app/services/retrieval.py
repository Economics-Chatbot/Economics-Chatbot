from __future__ import annotations

import re
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.models.schemas import RetrievedTerm


FAILURE_MESSAGE = (
    "현재 등록된 공식 자료에서 관련 경제용어를 찾지 못했습니다. "
    "경제용어나 경제 현상을 조금 더 구체적으로 질문해주세요."
)

TERM_SELECT = "term_name,official_definition,source_name,source_page,related_terms"


def _to_retrieved_term(row: dict[str, Any], similarity: float | None = None) -> RetrievedTerm:
    return RetrievedTerm(
        term_name=row["term_name"],
        official_definition=row["official_definition"],
        source_name=row["source_name"],
        source_page=row.get("source_page"),
        related_terms=row.get("related_terms") or [],
        similarity=row.get("similarity", similarity),
    )


def _normalize_direct_term(query: str) -> str:
    normalized = query.strip()
    normalized = re.sub(r"[?？!！.。]+$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    endings = [
        "이 뭐야",
        "가 뭐야",
        "은 뭐야",
        "는 뭐야",
        "이란",
        "란",
        "뜻이야",
        "무슨 뜻이야",
        "설명해줘",
        "알려줘",
    ]
    for ending in endings:
        if normalized.endswith(ending):
            return normalized[: -len(ending)].strip()

    return normalized


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def create_query_embedding(query: str) -> list[float]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=query,
    )
    return response.data[0].embedding


async def get_term_by_name(term: str) -> RetrievedTerm | None:
    candidate = _normalize_direct_term(term)
    if not candidate:
        return None

    response = (
        get_supabase_client()
        .table("economic_terms")
        .select(TERM_SELECT)
        .eq("term_name", candidate)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    return _to_retrieved_term(response.data[0], similarity=1.0)


def _extract_keywords(query: str) -> list[str]:
    stopwords = {
        "뭐야",
        "무슨",
        "뜻이야",
        "뭐라고",
        "해",
        "계속",
        "현상",
        "설명",
        "알려줘",
        "하는",
        "되는",
        "왜",
    }
    keywords = []
    for token in re.findall(r"[가-힣A-Za-z0-9]+", query):
        if len(token) < 2 or token in stopwords:
            continue
        keywords.append(token)

    if re.search(r"오르|올라|상승", query):
        keywords.append("상승")
    if re.search(r"내리|떨어|하락", query):
        keywords.append("하락")

    deduped = []
    for keyword in keywords:
        if keyword not in deduped:
            deduped.append(keyword)
    return deduped[:6]


def _score_text_candidate(row: dict[str, Any], query: str, keywords: list[str]) -> int:
    term_name = row["term_name"]
    definition = row["official_definition"]
    related = " ".join(row.get("related_terms") or [])
    score = 0

    for keyword in keywords:
        if keyword in term_name:
            score += 4
        if keyword in related:
            score += 3
        if keyword in definition:
            score += 1

    if "물가" in query and re.search(r"오르|올라|상승", query):
        if term_name == "인플레이션":
            score += 12
        elif "인플레이션" in term_name:
            score += 5

    if "돈" in query and re.search(r"가치|물가", query) and term_name == "인플레이션":
        score += 6

    return score


async def _search_text_candidates(query: str) -> list[RetrievedTerm]:
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    rows_by_term: dict[str, dict[str, Any]] = {}
    supabase = get_supabase_client()

    for keyword in keywords:
        pattern = f"%{keyword}%"
        response = (
            supabase.table("economic_terms")
            .select(TERM_SELECT)
            .or_(f"term_name.ilike.{pattern},official_definition.ilike.{pattern}")
            .limit(100)
            .execute()
        )
        for row in response.data or []:
            rows_by_term[row["term_name"]] = row

    scored_rows = [
        (_score_text_candidate(row, query, keywords), row)
        for row in rows_by_term.values()
    ]
    scored_rows = [item for item in scored_rows if item[0] >= 2]
    scored_rows.sort(key=lambda item: item[0], reverse=True)

    return [
        _to_retrieved_term(row, similarity=min(score / 20, 0.99))
        for score, row in scored_rows[: get_settings().retrieval_top_k]
    ]


async def _search_vector_candidates(query: str) -> list[RetrievedTerm]:
    settings = get_settings()
    embedding = create_query_embedding(query)
    response = get_supabase_client().rpc(
        "match_economic_terms",
        {
            "query_embedding": _vector_literal(embedding),
            "match_count": max(settings.retrieval_top_k, 10),
            "min_similarity": 0.0,
        },
    ).execute()

    candidates = [_to_retrieved_term(row) for row in response.data or []]
    return [
        candidate
        for candidate in candidates
        if (candidate.similarity or 0) >= settings.retrieval_min_score
    ][: settings.retrieval_top_k]


def _merge_candidates(*groups: list[RetrievedTerm]) -> list[RetrievedTerm]:
    merged: dict[str, RetrievedTerm] = {}
    for group in groups:
        for candidate in group:
            current = merged.get(candidate.term_name)
            if current is None or (candidate.similarity or 0) > (current.similarity or 0):
                merged[candidate.term_name] = candidate

    return sorted(
        merged.values(),
        key=lambda candidate: candidate.similarity or 0,
        reverse=True,
    )[: get_settings().retrieval_top_k]


async def retrieve_terms_for_question(query: str) -> list[RetrievedTerm]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    # The product flow starts with question embeddings and vector search. Exact and
    # text candidates are then merged in so direct-term and simple natural language
    # questions remain reliable in the PoC dataset.
    vector_candidates = await _search_vector_candidates(normalized_query)
    exact_candidate = await get_term_by_name(normalized_query)
    text_candidates = await _search_text_candidates(normalized_query)

    exact_candidates = [exact_candidate] if exact_candidate else []
    return _merge_candidates(exact_candidates, text_candidates, vector_candidates)


async def retrieve_terms(query: str) -> list[RetrievedTerm]:
    return await retrieve_terms_for_question(query)
