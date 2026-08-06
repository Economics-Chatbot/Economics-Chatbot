from __future__ import annotations

from contextlib import contextmanager
import logging
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Protocol

from openai import OpenAI

from app.core.config import get_settings
from app.core.retrieval_config import CANDIDATE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD


DEFAULT_MATCH_COUNT = 3
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
RetrievalStatus = Literal["matched", "candidates", "not_found"]

QUESTION_SUFFIXES = ("무엇인가요", "무엇인가", "알려줘", "설명해줘", "뭐야", "뭐지", "뭔데", "뭐냐", "뭐니")
PARTICLE_SUFFIXES = ("에서", "으로", "이랑", "은", "는", "이", "가", "을", "를", "에", "로", "와", "과", "랑", "도", "만", "의")


class EmbeddingsClient(Protocol):
    def create(self, *, model: str, input: str) -> Any: ...


class DbConnection(Protocol):
    def execute(self, query: str, params: dict[str, Any]) -> Any: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class SearchHit:
    term_id: int
    similarity: float


@dataclass(frozen=True)
class TermDocument:
    term_id: int
    term_name: str
    official_definition: str | None
    related_terms: list[str] = field(default_factory=list)
    similarity: float | None = None


@dataclass(frozen=True)
class RetrievalResult:
    status: RetrievalStatus
    hits: list[SearchHit] = field(default_factory=list)
    terms: list[TermDocument] = field(default_factory=list)
    candidates: list[TermDocument] = field(default_factory=list)


def log_retrieval_result(query: str, result: RetrievalResult, *, method: str) -> None:
    documents = result.terms or result.candidates
    logger.info(
        "retrieval query=%r method=%s status=%s result_terms=%s similarities=%s",
        query,
        method,
        result.status,
        [document.term_name for document in documents],
        [document.similarity for document in documents],
    )


def normalize_query(query: str) -> str:
    normalized = query.strip().rstrip("?!。？！").strip()
    for suffix in QUESTION_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break
    for suffix in PARTICLE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break
    return normalized or query.strip()


def create_query_embedding(query: str, embeddings_client: EmbeddingsClient | None = None) -> list[float]:
    settings = get_settings()
    if not query.strip():
        raise ValueError("query must not be empty")
    if embeddings_client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required")
        embeddings_client = OpenAI(api_key=settings.openai_api_key).embeddings

    response = embeddings_client.create(
        model=settings.openai_embedding_model,
        input=query,
    )
    return list(response.data[0].embedding)


def format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def get_database_connection() -> DbConnection:
    settings = get_settings()
    if not settings.resolved_database_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL is required for pgvector retrieval")

    from psycopg import connect
    from psycopg.rows import dict_row

    return connect(settings.resolved_database_url, row_factory=dict_row)


@contextmanager
def managed_database_connection(connection: DbConnection | None = None) -> Iterator[DbConnection]:
    if connection is not None:
        yield connection
        return

    owned_connection = get_database_connection()
    try:
        yield owned_connection
    finally:
        owned_connection.close()


def search_index(
    query_embedding: list[float],
    *,
    connection: DbConnection | None = None,
    match_count: int = DEFAULT_MATCH_COUNT,
) -> list[SearchHit]:
    with managed_database_connection(connection) as active_connection:
        cursor = active_connection.execute(
            """
            select
                ranked.term_id,
                ranked.similarity
            from (
                select
                    si.term_id,
                    max(1 - (si.embedding <=> %(query_embedding)s::vector))::double precision as similarity
                from search_index si
                group by si.term_id
            ) ranked
            order by ranked.similarity desc
            limit %(match_count)s
            """,
            {
                "query_embedding": format_vector(query_embedding),
                "match_count": match_count,
            },
        )

        hits: list[SearchHit] = []
        for row in cursor.fetchall():
            if row.get("term_id") is None or row.get("similarity") is None:
                continue
            hits.append(SearchHit(term_id=int(row["term_id"]), similarity=float(row["similarity"])))
        return hits


def fetch_terms(term_ids: list[int], *, connection: DbConnection | None = None) -> list[TermDocument]:
    if not term_ids:
        return []

    with managed_database_connection(connection) as active_connection:
        cursor = active_connection.execute(
            """
            select
                term_id,
                term_name,
                official_definition,
                related_terms
            from terms
            where term_id = any(%(term_ids)s)
            """,
            {"term_ids": term_ids},
        )
        rows_by_id = {int(row["term_id"]): row for row in cursor.fetchall()}

        terms: list[TermDocument] = []
        for term_id in term_ids:
            row = rows_by_id.get(term_id)
            if not row:
                continue
            terms.append(
                TermDocument(
                    term_id=int(row["term_id"]),
                    term_name=str(row["term_name"]),
                    official_definition=row.get("official_definition"),
                    related_terms=list(row.get("related_terms") or []),
                )
            )
        return terms


def fetch_term_by_name(term_name: str, *, connection: DbConnection | None = None) -> TermDocument | None:
    with managed_database_connection(connection) as active_connection:
        cursor = active_connection.execute(
            """
            select term_id, term_name, official_definition, related_terms
            from terms
            where lower(trim(term_name)) = lower(trim(%(term_name)s))
            limit 1
            """,
            {"term_name": term_name},
        )
        row = cursor.fetchone()
        if not row:
            return None
        return TermDocument(
            term_id=int(row["term_id"]),
            term_name=str(row["term_name"]),
            official_definition=row.get("official_definition"),
            related_terms=list(row.get("related_terms") or []),
        )


def retrieve_by_term_name(term_name: str) -> RetrievalResult:
    direct_term = fetch_term_by_name(term_name)
    if direct_term and direct_term.official_definition:
        result = RetrievalResult(status="matched", terms=[direct_term])
        log_retrieval_result(term_name, result, method="term_name")
        return result
    logger.info("retrieval query=%r method=term_name status=not_found result_terms=[] similarities=[]", term_name)
    return retrieve(term_name)


def attach_similarity(terms: list[TermDocument], hits: list[SearchHit]) -> list[TermDocument]:
    similarity_by_id = {hit.term_id: hit.similarity for hit in hits}
    return [
        TermDocument(
            term_id=term.term_id,
            term_name=term.term_name,
            official_definition=term.official_definition,
            related_terms=term.related_terms,
            similarity=similarity_by_id.get(term.term_id),
        )
        for term in terms
    ]


def apply_thresholds(hits: list[SearchHit], *, connection: DbConnection | None = None) -> RetrievalResult:
    if not hits or hits[0].similarity < CANDIDATE_THRESHOLD:
        return RetrievalResult(status="not_found", hits=hits)

    if hits[0].similarity >= HIGH_CONFIDENCE_THRESHOLD:
        matched_hits = [hit for hit in hits if hit.similarity >= HIGH_CONFIDENCE_THRESHOLD]
        terms = attach_similarity(
            fetch_terms([hit.term_id for hit in matched_hits], connection=connection),
            matched_hits,
        )
        return RetrievalResult(status="matched", hits=hits, terms=terms)

    candidate_hits = [
        hit for hit in hits if CANDIDATE_THRESHOLD <= hit.similarity < HIGH_CONFIDENCE_THRESHOLD
    ]
    candidates = attach_similarity(
        fetch_terms([hit.term_id for hit in candidate_hits], connection=connection),
        candidate_hits,
    )
    return RetrievalResult(status="candidates", hits=hits, candidates=candidates)


def retrieve(
    query: str,
    *,
    embeddings_client: EmbeddingsClient | None = None,
    connection: DbConnection | None = None,
    match_count: int = DEFAULT_MATCH_COUNT,
) -> RetrievalResult:
    normalized_query = normalize_query(query)
    with managed_database_connection(connection) as active_connection:
        query_embedding = create_query_embedding(normalized_query, embeddings_client)
        hits = search_index(query_embedding, connection=active_connection, match_count=match_count)
        result = apply_thresholds(hits, connection=active_connection)
        log_retrieval_result(query, result, method="embedding")
        return result
