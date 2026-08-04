from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import get_settings
from app.models.schemas import RetrievedTerm


FAILURE_MESSAGE = (
    "현재 등록된 공식 자료에서 관련 경제용어를 찾지 못했습니다. "
    "경제용어나 경제 현상을 조금 더 구체적으로 질문해주세요."
)


def _post_json(url: str, headers: dict[str, str], payload: Any) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed: HTTP {error.code} {message}") from error


def _get_json(url: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {url} failed: HTTP {error.code} {message}") from error


def _supabase_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _normalize_query(query: str) -> str:
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
            normalized = normalized[: -len(ending)].strip()
            break

    return normalized


def _to_retrieved_term(row: dict[str, Any], similarity: float | None = None) -> RetrievedTerm:
    return RetrievedTerm(
        term_name=row["term_name"],
        official_definition=row["official_definition"],
        source_name=row["source_name"],
        source_page=row.get("source_page"),
        related_terms=row.get("related_terms") or [],
        similarity=row.get("similarity", similarity),
    )


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


async def _search_exact(query: str) -> list[RetrievedTerm]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    candidate = _normalize_query(query)
    if not candidate:
        return []

    select = "term_name,official_definition,source_name,source_page,related_terms"
    encoded_term = urllib.parse.quote(candidate, safe="")
    endpoint = (
        f"{settings.supabase_url.rstrip('/')}/rest/v1/economic_terms"
        f"?select={select}&term_name=eq.{encoded_term}&limit=1"
    )
    rows = _get_json(endpoint, _supabase_headers()) or []
    if rows:
        return [_to_retrieved_term(rows[0], similarity=1.0)]

    return []


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


async def _search_text(query: str) -> list[RetrievedTerm]:
    settings = get_settings()
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    select = "term_name,official_definition,source_name,source_page,related_terms"
    headers = _supabase_headers()
    rows_by_term: dict[str, dict[str, Any]] = {}

    for keyword in keywords:
        encoded = urllib.parse.quote(f"*{keyword}*", safe="*")
        endpoint = (
            f"{settings.supabase_url.rstrip('/')}/rest/v1/economic_terms"
            f"?select={select}"
            f"&or=(term_name.ilike.{encoded},official_definition.ilike.{encoded})"
            "&limit=100"
        )
        for row in _get_json(endpoint, headers) or []:
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


async def _create_query_embedding(query: str) -> list[float]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    response = _post_json(
        "https://api.openai.com/v1/embeddings",
        {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        {"model": settings.openai_embedding_model, "input": query},
    )
    return response["data"][0]["embedding"]


async def _search_vector(query: str) -> list[RetrievedTerm]:
    settings = get_settings()
    embedding = await _create_query_embedding(query)
    endpoint = f"{settings.supabase_url.rstrip('/')}/rest/v1/rpc/match_economic_terms"
    rows = _post_json(
        endpoint,
        _supabase_headers(),
        {
            "query_embedding": _vector_literal(embedding),
            "match_count": settings.retrieval_top_k,
            "min_similarity": settings.retrieval_min_score,
        },
    )
    return [_to_retrieved_term(row) for row in rows or []]


async def retrieve_terms(query: str) -> list[RetrievedTerm]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    exact_terms = await _search_exact(normalized_query)
    if exact_terms:
        return exact_terms

    text_terms = await _search_text(normalized_query)
    if text_terms:
        return text_terms

    return await _search_vector(normalized_query)
