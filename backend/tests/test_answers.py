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


def test_matched_answer_stream_keeps_existing_sse_shape(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM())
    response = client.post("/api/answers", json={"query": "inflation"})
    parsed = parse_events(response.text)

    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"
    assert [name for name, _ in parsed][0] == "answer_start"
    assert [name for name, _ in parsed][-2:] == ["answer_done", "done"]
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
        "sources": [{"title": "\ud55c\uad6d\uc740\ud589 \uacbd\uc81c\uae08\uc735\uc6a9\uc5b4 800\uc120", "url": None}],
    }
    assert parsed[-1][1] == {
        "status": "completed",
        "completed_indices": [0],
        "failed_indices": [],
        "message": None,
    }


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


def test_suggestions_payload_is_structured_sse_and_not_markdown(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        raise AssertionError("suggestions must not call LLM")

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[
            TermDocument(2, "interest futures", "official", similarity=0.61),
            TermDocument(3, "interest swap", "official", similarity=0.59),
        ],
    ))
    use_factory(monkeypatch, factory)
    response = client.post("/api/answers", json={"query": "interest"})
    parsed = parse_events(response.text)

    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert [name for name, _ in parsed] == ["suggestions", "done"]
    suggestions = parsed[0][1]
    assert suggestions == {
        "index": 0,
        "query": "interest",
        "suggestions": [
            {"term_id": 2, "term": "interest futures", "query": "interest futures", "reason": None},
            {"term_id": 3, "term": "interest swap", "query": "interest swap", "reason": None},
        ],
    }
    assert all(name != "delta" for name, _ in parsed)
    assert "- interest futures" not in response.text
    assert not called


def test_suggestions_are_limited_to_top3_and_sorted(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[
            TermDocument(4, "fourth", None, similarity=0.1),
            TermDocument(1, "first", None, similarity=0.9),
            TermDocument(3, "third", None, similarity=0.3),
            TermDocument(2, "second", None, similarity=0.6),
        ],
    ))
    parsed = parse_events(client.post("/api/answers", json={"query": "ambiguous"}).text)

    assert [item["term"] for item in parsed[0][1]["suggestions"]] == ["first", "second", "third"]
    assert [item["term_id"] for item in parsed[0][1]["suggestions"]] == [1, 2, 3]


def test_suggestions_do_not_emit_answer_events_or_call_llm(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeLLM()

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[TermDocument(2, "inflation", "official")],
    ))
    use_factory(monkeypatch, factory)
    parsed = parse_events(client.post("/api/answers", json={"query": "prices"}).text)

    assert [name for name, _ in parsed] == ["suggestions", "done"]
    assert all(name not in {"answer_start", "delta", "answer_done"} for name, _ in parsed)
    assert parsed[-1][1]["status"] == "suggestions"
    assert not called


def test_failure_without_candidates_does_not_call_llm(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeLLM()

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(status="not_found"))
    use_factory(monkeypatch, factory)
    parsed = parse_events(client.post("/api/answers", json={"query": "unknown"}).text)

    assert [name for name, _ in parsed] == ["failure", "done"]
    assert parsed[0][1]["index"] == 0
    assert parsed[0][1]["term"] == "unknown"
    assert parsed[-1][1]["status"] == "failed"
    assert all(name != "suggestions" for name, _ in parsed)
    assert not called


def test_retrieval_exception_returns_sse_error_event(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeLLM()

    def raise_retrieval_error(query: str) -> RetrievalResult:
        raise RuntimeError("database://secret")

    monkeypatch.setattr(answers_route, "retrieve", raise_retrieval_error)
    use_factory(monkeypatch, factory)
    response = client.post("/api/answers", json={"query": "interest"})
    parsed = parse_events(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert [name for name, _ in parsed] == ["error", "done"]
    assert parsed[0][1]["code"] == "retrieval_failed"
    assert "secret" not in json.dumps(parsed[0][1])
    assert parsed[-1][1]["status"] == "error"
    assert not called


def test_not_found_with_candidates_still_emits_failure(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeLLM()

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="not_found",
        candidates=[TermDocument(2, "low score candidate", "official", similarity=0.1)],
    ))
    use_factory(monkeypatch, factory)
    parsed = parse_events(client.post("/api/answers", json={"query": "low score"}).text)

    assert [name for name, _ in parsed] == ["failure", "done"]
    assert parsed[-1][1]["status"] == "failed"
    assert all(name != "suggestions" for name, _ in parsed)
    assert not called


def test_selected_term_id_payload_is_rejected() -> None:
    response = client.post("/api/answers", json={"query": "interest", "selected_term_id": 1})
    assert response.status_code == 422


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
    use_factory(monkeypatch, lambda: FakeLLM(["bad output"]))
    parsed = parse_events(client.post("/api/answers", json={"query": "inflation"}).text)
    assert parsed[-2][0] == "error"
    assert parsed[-2][1]["code"] == "answer_generation_failed"


def test_multiple_terms_preserve_indices_on_partial_success(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query) if query == "first" else RetrievalResult(status="not_found"))
    use_factory(monkeypatch, lambda: FakeLLM())
    parsed = parse_events(client.post("/api/answers", json={"query": "first, second"}).text)
    indexed = [(name, data["index"]) for name, data in parsed if "index" in data]
    assert indexed[0][1] == 0
    assert indexed[-1][1] == 1
    assert parsed[-1][1]["status"] == "partial"


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
