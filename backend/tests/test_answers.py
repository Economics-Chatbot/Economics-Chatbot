import asyncio
import json

from fastapi.testclient import TestClient

from app.api.routes import answers as answers_route
from app.main import app
from app.services.llm import LLMClient, LLMError, LLMTimeoutError
from app.services.retrieval import RetrievalResult, TermDocument


client = TestClient(app)


def use_factory(monkeypatch, factory) -> None:
    monkeypatch.setitem(app.dependency_overrides, answers_route.get_llm_client_factory, lambda: factory)


def parse_events(text: str) -> list[tuple[str, dict]]:
    result = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        result.append((lines[0][7:], json.loads(lines[1][6:])))
    return result


def matched(term: str) -> RetrievalResult:
    return RetrievalResult(
        status="matched",
        terms=[TermDocument(1, term, f"{term} official definition", ["price"])],
    )


class FakeLLM(LLMClient):
    def __init__(self, chunks: list[str] | None = None, error: Exception | None = None):
        self.chunks = chunks or ["official definition", "\n<<<EASY>>>", "easy explanation", "\n<<<EXAMPLE>>>", "daily example"]
        self.error = error

    async def stream_answer(self, *, user_query: str, retrieval_result: RetrievalResult):
        if self.error:
            raise self.error
        for chunk in self.chunks:
            yield chunk


def test_matched_answer_stream(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM())
    response = client.post("/api/answers", json={"query": "inflation"})
    parsed = parse_events(response.text)

    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"
    assert [name for name, _ in parsed][0] == "answer_start"
    assert [name for name, _ in parsed][-2:] == ["answer_done", "done"]
    assert "delta" in [name for name, _ in parsed]
    assert [data["section"] for name, data in parsed if name == "delta"] == [
        "one_line_definition",
        "easy_explanation",
        "example",
    ]
    assert parsed[-2][1]["answer"] == {
        "term": "inflation",
        "one_line_definition": "official definition",
        "easy_explanation": "easy explanation",
        "example": "daily example",
        "related_keywords": ["price"],
        "sources": [{"title": "한국은행 경제금융용어 800선", "url": None}],
    }
    assert parsed[0][1]["related_keywords"] == ["price"]
    assert parsed[-1][1]["status"] == "completed"


def test_sse_delimiters_split_across_provider_chunks(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM(["definition", "\n<<<", "EASY>>>easy", "\n<<<EX", "AMPLE>>>example"]))
    parsed = parse_events(client.post("/api/answers", json={"query": "inflation"}).text)
    delta_text = "".join(data["text"] for name, data in parsed if name == "delta")
    assert delta_text == "definitioneasyexample"
    assert [data["section"] for name, data in parsed if name == "delta"] == [
        "one_line_definition",
        "easy_explanation",
        "example",
    ]


def test_candidates_return_json_and_do_not_call_llm(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        raise AssertionError("candidate must not call LLM")

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[
            TermDocument(2, "inflation", "official", similarity=0.61),
            TermDocument(3, "deflation", "official", similarity=0.59),
        ],
    ))
    use_factory(monkeypatch, factory)
    response = client.post("/api/answers", json={"query": "prices"})

    assert response.headers["content-type"] == "application/json"
    assert response.json()["status"] == "candidates"
    assert response.json()["candidates"] == [
        {"rank": 1, "term_id": 2, "term_name": "inflation", "similarity": 0.61},
        {"rank": 2, "term_id": 3, "term_name": "deflation", "similarity": 0.59},
    ]
    assert not called


def test_candidates_are_limited_to_top3_and_sorted(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[
            TermDocument(4, "fourth", None, similarity=0.1),
            TermDocument(1, "first", None, similarity=0.9),
            TermDocument(3, "third", None, similarity=0.3),
            TermDocument(2, "second", None, similarity=0.6),
        ],
    ))
    response = client.post("/api/answers", json={"query": "ambiguous"})

    assert [item["term_name"] for item in response.json()["candidates"]] == ["first", "second", "third"]
    assert [item["rank"] for item in response.json()["candidates"]] == [1, 2, 3]


def test_not_found_returns_json(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(status="not_found"))
    response = client.post("/api/answers", json={"query": "unknown"})
    assert response.headers["content-type"] == "application/json"
    assert response.json()["status"] == "not_found"
    assert response.json()["message"]


def test_timeout_and_llm_error_are_safe(monkeypatch) -> None:
    for exception, code in [(LLMTimeoutError(), "llm_timeout"), (LLMError("secret"), "llm_error")]:
        monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
        use_factory(monkeypatch, lambda exception=exception: FakeLLM(error=exception))
        parsed = parse_events(client.post("/api/answers", json={"query": "inflation"}).text)
        assert parsed[-2][0] == "error"
        assert parsed[-2][1]["code"] == code
        assert "secret" not in json.dumps(parsed[-2][1])
        assert parsed[-1][1]["status"] == "error"


def test_invalid_model_output_returns_generation_error(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM(["bad output"] ))
    parsed = parse_events(client.post("/api/answers", json={"query": "inflation"}).text)
    assert parsed[-2][0] == "error"
    assert parsed[-2][1]["code"] == "answer_generation_failed"


def test_selected_term_id_skips_retrieval_and_streams(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: (_ for _ in ()).throw(AssertionError("no retrieval")))
    monkeypatch.setattr(answers_route, "fetch_term_by_id", lambda term_id: TermDocument(7, "selected", "selected definition", ["related"]))
    use_factory(monkeypatch, lambda: FakeLLM())
    parsed = parse_events(client.post("/api/answers", json={"selected_term_id": 7}).text)
    assert [name for name, _ in parsed][0] == "answer_start"
    assert parsed[0][1]["term"] == "selected"
    assert parsed[-1][1]["status"] == "completed"


def test_invalid_selected_term_id_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "fetch_term_by_id", lambda term_id: None)
    response = client.post("/api/answers", json={"selected_term_id": 999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid candidate"


def test_selected_term_name_is_rejected() -> None:
    response = client.post("/api/answers", json={"selected_term": "inflation"})
    assert response.status_code == 422


def test_client_cancellation_propagates() -> None:
    class CancelledLLM(LLMClient):
        async def stream_answer(self, *, user_query: str, retrieval_result: RetrievalResult):
            raise asyncio.CancelledError
            yield "never"

    async def collect() -> None:
        stream = _stream_for_test(CancelledLLM())
        await stream.__anext__()
        await stream.__anext__()

    try:
        asyncio.run(collect())
    except asyncio.CancelledError:
        return
    raise AssertionError("client cancellation must propagate")


async def _stream_for_test(llm: LLMClient):
    from app.services.answers import stream_events

    async for event in stream_events("inflation", lambda query: matched(query), lambda: llm):
        yield event

