from __future__ import annotations

import json
from typing import Any, Protocol

import logging

from openai import OpenAI

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.models.vector_retrieval import (
    RetrievedTerm,
    TermSuggestion,
    VectorRetrieveResult,
    VectorRetrieveStatus,
)

ANSWERABLE_THRESHOLD = 0.82
SUGGESTION_THRESHOLD = 0.65
MAX_SUGGESTIONS = 3
MATCH_COUNT = 8


class EmbeddingError(RuntimeError):
    pass


class VectorSearchError(RuntimeError):
    pass


class EmbeddingClient(Protocol):
    def create(self, *, model: str, input: str) -> Any:
        ...


def normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


logger = logging.getLogger(__name__)


def normalize_related_terms(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        if stripped.startswith("{") and stripped.endswith("}"):
            stripped = stripped[1:-1]
        return [
            item.strip().strip('"').strip("'")
            for item in stripped.split(",")
            if item.strip().strip('"').strip("'")
        ]
    return [str(value).strip()] if str(value).strip() else []


def create_query_embedding(query: str, embedding_client: EmbeddingClient | None = None) -> list[float]:
    settings = get_settings()
    if embedding_client is None and not settings.openai_api_key:
        raise EmbeddingError("OPENAI_API_KEY is required")

    client = embedding_client or OpenAI(api_key=settings.openai_api_key).embeddings
    try:
        response = client.create(
            model=settings.openai_embedding_model,
            input=query,
        )
    except Exception as error:  # OpenAI SDK raises provider-specific exceptions.
        logger.exception("Failed to create query embedding")
        raise EmbeddingError(f"Failed to create query embedding: {error}") from error

    embedding = response.data[0].embedding
    if not embedding:
        raise EmbeddingError("OpenAI returned an empty embedding")
    return embedding


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_retrieved_term(row: dict[str, Any]) -> RetrievedTerm:
    return RetrievedTerm(
        term_id=int(row["term_id"]),
        term_name=str(row["term_name"]),
        official_definition=str(row["official_definition"]),
        related_terms=normalize_related_terms(row.get("related_terms")),
    )


def _to_suggestion(row: dict[str, Any]) -> TermSuggestion:
    return TermSuggestion(
        term_id=int(row["term_id"]),
        term_name=str(row["term_name"]),
        similarity=_as_float(row.get("similarity")),
        related_terms=normalize_related_terms(row.get("related_terms")),
    )


def _search_terms(query_embedding: list[float], supabase: Any | None = None) -> list[dict[str, Any]]:
    client = supabase or get_supabase_client()
    try:
        response = client.rpc(
            "match_economic_terms",
            {
                "query_embedding": query_embedding,
                "match_count": MATCH_COUNT,
                "min_similarity": SUGGESTION_THRESHOLD,
            },
        ).execute()
    except Exception as error:
        logger.exception("Failed to search economic term vectors")
        raise VectorSearchError(f"Failed to search economic term vectors: {error}") from error
MOCK_TERMS = [
    {
        "term_id": 1,
        "term_name": "인플레이션",
        "official_definition": "인플레이션(Inflation)은 통화량 증가 등으로 인해 전반적인 물가 수준이 지속적으로 상승하고 화폐 가치가 하락하는 현상을 의미합니다. 인플레이션이 발생하면 구매력이 감소하여 동일한 금액으로 살 수 있는 상품이나 서비스의 양이 줄어듭니다.",
        "related_terms": ["디플레이션", "스태그플레이션", "기준금리"]
    },
    {
        "term_id": 2,
        "term_name": "기준금리",
        "official_definition": "기준금리는 한국은행 금융통화위원회가 결정하는 정책금리로, 금융기관 간 거래 시 기준이 되는 금리입니다. 기준금리가 변하면 시중 은행의 대출금리와 예금금리에 영향을 미치고 물가 및 경제 전반의 흐름을 조절합니다.",
        "related_terms": ["시장금리", "통화정책", "한국은행"]
    },
    {
        "term_id": 3,
        "term_name": "ETF",
        "official_definition": "ETF(상장지수펀드, Exchange Traded Fund)는 주식처럼 거래소에서 자유롭게 매매할 수 있는 펀드로, KOSPI 200이나 특정 산업 지수 등의 성과를 추종하도록 설계된 금융 상품입니다.",
        "related_terms": ["펀드", "주식", "지수"]
    },
    {
        "term_id": 4,
        "term_name": "GDP",
        "official_definition": "GDP(국내총생산, Gross Domestic Product)는 일정 기간 동안 한 국가의 영토 안에서 생산된 최종 생산물의 시장 가치의 합계를 나타내는 대표적인 경제 성장 지표입니다.",
        "related_terms": ["GNI", "경제성장률", "국민소득"]
    }
]

def _search_terms_by_keyword(query: str, supabase: Any | None = None) -> list[dict[str, Any]]:
    client = supabase or get_supabase_client()
    try:
        response = client.table("economic_terms") \
            .select("term_id, term_name, official_definition, related_terms") \
            .ilike("term_name", f"%{query}%") \
            .limit(MATCH_COUNT) \
            .execute()
        rows = response.data or []
        for r in rows:
            r["similarity"] = 0.85 if str(r.get("term_name")).strip() == query else 0.72
        if rows:
            return rows
    except Exception as error:
        logger.warning("Failed to search economic terms in Supabase DB: %s. Using local fallback dictionary.", error)

    # DB 테이블이 없거나 연결 장애 시 local fallback dictionary에서 검색
    matched_rows = []
    q = query.strip().lower()
    for t in MOCK_TERMS:
        t_name = t["term_name"].lower()
        if q in t_name or t_name in q:
            sim = 0.90 if t_name == q else 0.75
            matched_rows.append({**t, "similarity": sim})
    return matched_rows


def vector_retrieve(
    query: str,
    *,
    embedding_client: EmbeddingClient | None = None,
    supabase: Any | None = None,
) -> VectorRetrieveResult:
    normalized_query = normalize_query(query)
    if not normalized_query:
        return VectorRetrieveResult(
            status=VectorRetrieveStatus.NOT_FOUND,
            term=None,
            suggestions=[],
            query=query,
        )

    try:
        query_embedding = create_query_embedding(normalized_query, embedding_client)
        rows = [
            row
            for row in _search_terms(query_embedding, supabase)
            if row.get("official_definition") and str(row.get("official_definition")).strip()
        ]
    except EmbeddingError:
        logger.warning("Embedding search unavailable. Falling back to DB keyword search for '%s'", normalized_query)
        rows = [
            row
            for row in _search_terms_by_keyword(normalized_query, supabase)
            if row.get("official_definition") and str(row.get("official_definition")).strip()
        ]

    rows.sort(key=lambda row: _as_float(row.get("similarity")), reverse=True)

    if not rows:
        return VectorRetrieveResult(
            status=VectorRetrieveStatus.NOT_FOUND,
            term=None,
            suggestions=[],
            query=query,
        )

    best = rows[0]
    if _as_float(best.get("similarity")) >= ANSWERABLE_THRESHOLD:
        return VectorRetrieveResult(
            status=VectorRetrieveStatus.ANSWERABLE,
            term=_to_retrieved_term(best),
            suggestions=[],
            query=query,
        )

    suggestions = [
        _to_suggestion(row)
        for row in rows
        if _as_float(row.get("similarity")) >= SUGGESTION_THRESHOLD
    ][:MAX_SUGGESTIONS]
    if suggestions:
        return VectorRetrieveResult(
            status=VectorRetrieveStatus.SUGGESTIONS,
            term=None,
            suggestions=suggestions,
            query=query,
        )

    return VectorRetrieveResult(
        status=VectorRetrieveStatus.NOT_FOUND,
        term=None,
        suggestions=[],
        query=query,
    )
