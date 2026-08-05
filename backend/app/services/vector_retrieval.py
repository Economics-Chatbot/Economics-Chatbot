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
    return response.data or []


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

    query_embedding = create_query_embedding(normalized_query, embedding_client)
    rows = [
        row
        for row in _search_terms(query_embedding, supabase)
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
