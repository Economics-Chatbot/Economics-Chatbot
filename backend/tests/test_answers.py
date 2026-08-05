import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import answers as answer_service


client = TestClient(app)


def events(response_text: str) -> list[tuple[str, dict]]:
    result = []
    for block in response_text.strip().split("\n\n"):
        lines = block.splitlines()
        result.append((lines[0][7:], json.loads(lines[1][6:])))
    return result


def test_success_stream() -> None:
    response = client.post("/api/answers", json={"query": "인플레이션"})
    parsed = events(response.text)

    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"
    assert [name for name, _ in parsed] == ["answer_start", "delta", "delta", "delta", "answer_done", "done"]
    assert parsed[-1][1]["status"] == "completed"


def test_search_failure_and_multiple_indices() -> None:
    response = client.post("/api/answers", json={"query": "인플레이션, 없는용어"})
    parsed = events(response.text)
    names = [name for name, _ in parsed]

    assert names[0] == "answer_start"
    assert names[-2:] == ["failure", "done"]
    assert parsed[0][1]["index"] == 0
    assert parsed[-2][1]["index"] == 1
    assert parsed[-1][1]["status"] == "partial"


def test_unknown_search_ends_as_failed() -> None:
    parsed = events(client.post("/api/answers", json={"query": "없는용어"}).text)
    assert [name for name, _ in parsed] == ["failure", "done"]
    assert parsed[-1][1]["status"] == "failed"


def test_candidate_suggestions_do_not_generate_an_answer() -> None:
    parsed = events(client.post("/api/answers", json={"query": "물가상승"}).text)
    assert [name for name, _ in parsed] == ["suggestions", "done"]
    assert parsed[0][1]["index"] == 0
    assert parsed[-1][1]["status"] == "suggestions"


def test_generation_error_has_error_event(monkeypatch) -> None:
    monkeypatch.setattr(answer_service, "_answer_text", lambda answer: (_ for _ in ()).throw(RuntimeError()))
    parsed = events(client.post("/api/answers", json={"query": "인플레이션"}).text)
    assert [name for name, _ in parsed] == ["answer_start", "error", "done"]
    assert parsed[1][1]["index"] == 0
    assert parsed[-1][1]["status"] == "error"
