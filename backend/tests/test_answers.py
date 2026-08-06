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
        terms=[TermDocument(1, term, f"{term}의 공식 정의입니다.", ["물가"])],
    )


class FakeLLM(LLMClient):
    def __init__(self, chunks: list[str] | None = None, error: Exception | None = None):
        self.chunks = chunks or ["공식 정의입니다.", "\n<<<EASY>>>", "쉽게 설명합니다.", "\n<<<EXAMPLE>>>", "생활 속 예시입니다."]
        self.error = error

    async def stream_answer(self, *, user_query: str, retrieval_result: RetrievalResult):
        if self.error:
            raise self.error
        for chunk in self.chunks:
            yield chunk


def test_matched_answer_stream(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM())
    response = client.post("/api/answers", json={"query": "인플레이션"})
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
        "term": "인플레이션",
        "one_line_definition": "공식 정의입니다.",
        "easy_explanation": "쉽게 설명합니다.",
        "example": "생활 속 예시입니다.",
        "related_keywords": ["물가"],
        "sources": [{"title": "한국은행 경제금융용어 800선", "url": None}],
    }
    assert parsed[0][1]["related_keywords"] == ["물가"]
    assert parsed[-1][1]["status"] == "completed"


def test_sse_delimiters_split_across_provider_chunks(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM(["정의", "\n<<<", "EASY>>>쉬운", "\n<<<EX", "AMPLE>>>예시"]))
    parsed = parse_events(client.post("/api/answers", json={"query": "인플레이션"}).text)
    delta_text = "".join(data["text"] for name, data in parsed if name == "delta")
    assert delta_text == "정의쉬운예시"
    assert [data["section"] for name, data in parsed if name == "delta"] == [
        "one_line_definition",
        "easy_explanation",
        "example",
    ]


def test_candidates_do_not_call_llm(monkeypatch) -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        raise AssertionError("candidate must not call LLM")

    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(
        status="candidates",
        candidates=[TermDocument(2, "인플레이션", "공식 정의")],
    ))
    use_factory(monkeypatch, factory)
    parsed = parse_events(client.post("/api/answers", json={"query": "물가상승"}).text)

    assert [name for name, _ in parsed] == ["suggestions", "done"]
    assert parsed[-1][1]["status"] == "suggestions"
    assert not called


def test_not_found(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: RetrievalResult(status="not_found"))
    parsed = parse_events(client.post("/api/answers", json={"query": "없는용어"}).text)
    assert [name for name, _ in parsed] == ["failure", "done"]
    assert parsed[-1][1]["status"] == "failed"


def test_timeout_and_llm_error_are_safe(monkeypatch) -> None:
    for exception, code in [(LLMTimeoutError(), "llm_timeout"), (LLMError("secret"), "llm_error")]:
        monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
        use_factory(monkeypatch, lambda exception=exception: FakeLLM(error=exception))
        parsed = parse_events(client.post("/api/answers", json={"query": "인플레이션"}).text)
        assert parsed[-2][0] == "error"
        assert parsed[-2][1]["code"] == code
        assert "secret" not in json.dumps(parsed[-2][1])
        assert parsed[-1][1]["status"] == "error"


def test_invalid_model_output_returns_generation_error(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query))
    use_factory(monkeypatch, lambda: FakeLLM(["잘못된 출력"]))
    parsed = parse_events(client.post("/api/answers", json={"query": "인플레이션"}).text)
    assert parsed[-2][0] == "error"
    assert parsed[-2][1]["code"] == "answer_generation_failed"


def test_multiple_terms_preserve_indices_on_partial_success(monkeypatch) -> None:
    monkeypatch.setattr(answers_route, "retrieve", lambda query: matched(query) if query == "첫용어" else RetrievalResult(status="not_found"))
    use_factory(monkeypatch, lambda: FakeLLM())
    parsed = parse_events(client.post("/api/answers", json={"query": "첫용어, 둘째용어"}).text)
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

    async for event in stream_events("인플레이션", lambda query: matched(query), lambda: llm):
        yield event
