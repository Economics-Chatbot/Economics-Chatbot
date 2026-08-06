from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.core.retrieval_config import CANDIDATE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD
from app.services import retrieval
from app.services.retrieval import (
    RetrievalResult,
    create_query_embedding,
    fetch_term_by_id,
    format_vector,
    retrieve,
    search_index,
)


class FakeEmbeddingsClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def create(self, *, model: str, input: str) -> SimpleNamespace:
        self.calls.append({"model": model, "input": input})
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0])])


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class FakeConnection:
    def __init__(
        self,
        *,
        search_rows: list[dict[str, object]],
        term_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.search_rows = search_rows
        self.term_rows = term_rows or []
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def execute(self, query: str, params: dict[str, object]) -> FakeCursor:
        self.calls.append((query, params))
        if "from search_index si" in query:
            return FakeCursor(self.search_rows[: int(params["match_count"])])
        if "from terms" in query:
            term_ids = params["term_ids"]
            return FakeCursor([row for row in self.term_rows if row["term_id"] in term_ids])
        raise AssertionError(f"unexpected query: {query}")

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_query_embedding_uses_text_embedding_3_small() -> None:
    embeddings_client = FakeEmbeddingsClient()

    embedding = create_query_embedding("base rate", embeddings_client)

    assert embedding == [1.0, 0.0]
    assert embeddings_client.calls == [
        {"model": "text-embedding-3-small", "input": "base rate"}
    ]


def test_create_query_embedding_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        create_query_embedding("   ", FakeEmbeddingsClient())


def test_format_vector_for_pgvector_parameter() -> None:
    assert format_vector([1.0, 0.5, -0.25]) == "[1.0,0.5,-0.25]"


def test_search_index_runs_pgvector_cosine_similarity_in_database() -> None:
    connection = FakeConnection(
        search_rows=[
            {"term_id": 1, "similarity": 0.82},
            {"term_id": 2, "similarity": 0.61},
        ]
    )

    hits = search_index([1.0, 0.0], connection=connection, match_count=3)

    assert [hit.term_id for hit in hits] == [1, 2]
    assert [hit.similarity for hit in hits] == [0.82, 0.61]
    query, params = connection.calls[0]
    assert "from search_index si" in query
    assert "si.embedding <=> %(query_embedding)s::vector" in query
    assert "group by si.term_id" in query
    assert params == {"query_embedding": "[1.0,0.0]", "match_count": 3}
    assert not connection.closed


def test_retrieve_closes_owned_database_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection(
        search_rows=[{"term_id": 10, "similarity": HIGH_CONFIDENCE_THRESHOLD}],
        term_rows=[
            {
                "term_id": 10,
                "term_name": "base rate",
                "official_definition": "A policy interest rate.",
                "related_terms": [],
            }
        ],
    )
    monkeypatch.setattr(retrieval, "get_database_connection", lambda: connection)

    result = retrieve("base rate", embeddings_client=FakeEmbeddingsClient())

    assert result.status == "matched"
    assert connection.closed


def test_retrieve_returns_terms_for_high_similarity() -> None:
    connection = FakeConnection(
        search_rows=[{"term_id": 10, "similarity": HIGH_CONFIDENCE_THRESHOLD}],
        term_rows=[
            {
                "term_id": 10,
                "term_name": "base rate",
                "official_definition": "A policy interest rate.",
                "related_terms": ["monetary policy"],
            }
        ],
    )

    result = retrieve("base rate", embeddings_client=FakeEmbeddingsClient(), connection=connection)

    assert result.status == "matched"
    assert result.terms[0].term_name == "base rate"
    assert result.terms[0].similarity == HIGH_CONFIDENCE_THRESHOLD
    assert result.candidates[0].term_name == "base rate"
    assert not connection.closed


def test_retrieve_returns_candidates_for_medium_similarity() -> None:
    connection = FakeConnection(
        search_rows=[{"term_id": 20, "similarity": CANDIDATE_THRESHOLD}],
        term_rows=[
            {
                "term_id": 20,
                "term_name": "household debt",
                "official_definition": "Debt owed by households.",
                "related_terms": [],
            }
        ],
    )

    result = retrieve("loan", embeddings_client=FakeEmbeddingsClient(), connection=connection)

    assert result.status == "candidates"
    assert result.terms == []
    assert result.candidates[0].term_name == "household debt"


def test_retrieve_returns_not_found_with_low_similarity_candidates() -> None:
    connection = FakeConnection(
        search_rows=[{"term_id": 30, "similarity": CANDIDATE_THRESHOLD - 0.01}],
        term_rows=[
            {
                "term_id": 30,
                "term_name": "near miss",
                "official_definition": "A low-similarity candidate.",
                "related_terms": [],
            }
        ],
    )

    result = retrieve("unknown", embeddings_client=FakeEmbeddingsClient(), connection=connection)

    assert isinstance(result, RetrievalResult)
    assert result.status == "not_found"
    assert result.terms == []
    assert result.candidates[0].term_name == "near miss"
    assert len(connection.calls) == 2

def test_fetch_term_by_id_uses_terms_table() -> None:
    connection = FakeConnection(
        search_rows=[],
        term_rows=[
            {
                "term_id": 99,
                "term_name": "selected",
                "official_definition": "Selected definition.",
                "related_terms": ["related"],
            }
        ],
    )

    term = fetch_term_by_id(99, connection=connection)

    assert term is not None
    assert term.term_name == "selected"
    assert term.related_terms == ["related"]
