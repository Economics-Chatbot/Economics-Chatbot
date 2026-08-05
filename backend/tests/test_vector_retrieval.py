from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import vector_retrieval as service
from app.services.vector_retrieval import (
    EmbeddingError,
    normalize_related_terms,
    vector_retrieve,
)


class FakeEmbeddingClient:
    def __init__(self, embedding: list[float] | None = None, error: Exception | None = None) -> None:
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.error = error

    def create(self, *, model: str, input: str):
        if self.error:
            raise self.error

        class Data:
            def __init__(self, embedding: list[float]) -> None:
                self.index = 0
                self.embedding = embedding

        class Response:
            def __init__(self, embedding: list[float]) -> None:
                self.data = [Data(embedding)]

        return Response(self.embedding)


class FakeRpcResponse:
    def __init__(self, data: list[dict]) -> None:
        self.data = data

    def execute(self) -> FakeRpcResponse:
        return self


class FakeSupabase:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.rpc_name = ""
        self.rpc_params = {}

    def rpc(self, name: str, params: dict) -> FakeRpcResponse:
        self.rpc_name = name
        self.rpc_params = params
        return FakeRpcResponse(self.rows)


def row(similarity: float, **overrides) -> dict:
    data = {
        "term_id": 1,
        "term_name": "기준금리",
        "official_definition": "한국은행 금융통화위원회에서 결정하는 정책금리",
        "related_terms": ["시장금리", "통화정책"],
        "similarity": similarity,
    }
    data.update(overrides)
    return data


def test_exact_term_question_is_answerable() -> None:
    result = vector_retrieve(
        "  기준금리가   뭐야?  ",
        embedding_client=FakeEmbeddingClient(),
        supabase=FakeSupabase([row(0.91)]),
    )

    assert result.status == "answerable"
    assert result.term is not None
    assert result.term.term_name == "기준금리"
    assert result.term.official_definition
    assert result.suggestions == []
    assert result.query == "  기준금리가   뭐야?  "


def test_similar_question_can_return_suggestions() -> None:
    result = vector_retrieve(
        "금리가 올라가면 왜 힘들어져?",
        embedding_client=FakeEmbeddingClient(),
        supabase=FakeSupabase([row(0.78), row(0.7, term_id=2, term_name="시장금리")]),
    )

    assert result.status == "suggestions"
    assert result.term is None
    assert [suggestion.term_name for suggestion in result.suggestions] == ["기준금리", "시장금리"]


def test_ambiguous_question_limits_suggestions_to_configured_max() -> None:
    rows = [
        row(0.7, term_id=term_id, term_name=f"후보{term_id}")
        for term_id in range(1, 6)
    ]
    result = vector_retrieve(
        "돈 관련된 거 알려줘",
        embedding_client=FakeEmbeddingClient(),
        supabase=FakeSupabase(rows),
    )

    assert result.status == "suggestions"
    assert len(result.suggestions) == service.MAX_SUGGESTIONS


def test_unrelated_question_returns_not_found() -> None:
    result = vector_retrieve(
        "오늘 점심 뭐 먹지?",
        embedding_client=FakeEmbeddingClient(),
        supabase=FakeSupabase([row(0.2)]),
    )

    assert result.status == "not_found"
    assert result.term is None
    assert result.suggestions == []


def test_related_terms_string_is_normalized_to_list() -> None:
    assert normalize_related_terms('["기준금리", "채권수익률"]') == ["기준금리", "채권수익률"]
    assert normalize_related_terms("{기준금리,채권수익률}") == ["기준금리", "채권수익률"]


def test_missing_official_definition_is_not_answerable() -> None:
    result = vector_retrieve(
        "기준금리가 뭐야?",
        embedding_client=FakeEmbeddingClient(),
        supabase=FakeSupabase([row(0.99, official_definition="")]),
    )

    assert result.status == "not_found"


def test_embedding_failure_raises_clear_error() -> None:
    with pytest.raises(EmbeddingError, match="Failed to create query embedding"):
        vector_retrieve(
            "기준금리가 뭐야?",
            embedding_client=FakeEmbeddingClient(error=RuntimeError("boom")),
            supabase=FakeSupabase([]),
        )


def test_route_returns_non_500_for_embedding_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_: str):
        raise EmbeddingError("embedding provider unavailable")

    monkeypatch.setattr("app.api.routes.vector_retrieval.vector_retrieve", fail)
    response = TestClient(app).post("/be2/vector-retrieve", json={"query": "기준금리"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "embedding_failed"
