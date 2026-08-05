from fastapi.testclient import TestClient

from app.api.routes import retrieval as retrieval_route
from app.services.retrieval import RetrievalResult, SearchHit, TermDocument
from app.main import app


def test_retrieval_route_returns_matched_result(monkeypatch) -> None:
    def fake_retrieve(query: str):
        assert query == "base rate"
        return RetrievalResult(
            status="matched",
            hits=[SearchHit(term_id=1, similarity=0.82)],
            terms=[
                TermDocument(
                    term_id=1,
                    term_name="base rate",
                    official_definition="A policy interest rate.",
                    related_terms=["monetary policy"],
                    similarity=0.82,
                )
            ],
        )

    monkeypatch.setattr(retrieval_route.retrieval, "retrieve", fake_retrieve)
    client = TestClient(app)

    response = client.post("/retrieval", json={"query": "base rate"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "matched",
        "hits": [{"term_id": 1, "similarity": 0.82}],
        "terms": [
            {
                "term_id": 1,
                "term_name": "base rate",
                "official_definition": "A policy interest rate.",
                "related_terms": ["monetary policy"],
                "similarity": 0.82,
            }
        ],
        "candidates": [],
    }


def test_retrieval_route_returns_candidate_names_only(monkeypatch) -> None:
    def fake_retrieve(query: str):
        assert query == "loan"
        return RetrievalResult(
            status="candidates",
            hits=[SearchHit(term_id=2, similarity=0.65)],
            candidates=[
                TermDocument(
                    term_id=2,
                    term_name="household debt",
                    official_definition="Debt owed by households.",
                    related_terms=[],
                    similarity=0.65,
                )
            ],
        )

    monkeypatch.setattr(retrieval_route.retrieval, "retrieve", fake_retrieve)
    client = TestClient(app)

    response = client.post("/retrieval", json={"query": "loan"})

    assert response.status_code == 200
    assert response.json()["status"] == "candidates"
    assert response.json()["terms"] == []
    assert response.json()["candidates"] == ["household debt"]