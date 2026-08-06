import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_route
from app.main import app
from app.services.chat import build_candidate_response, build_not_found_response, stream_chat_answer
from app.services.llm import LLMClient, LLMError, LLMTimeoutError, OpenAILLMClient
from app.services.prompt import build_messages, build_user_prompt
from app.services.retrieval import RetrievalResult, SearchHit, TermDocument


class FakeLLMClient(LLMClient):
    def __init__(self, tokens: list[str] | None = None, error: Exception | None = None) -> None:
        self.tokens = tokens or ["answer"]
        self.error = error
        self.calls = 0

    async def stream_answer(self, *, user_query: str, retrieval_result: RetrievalResult):
        self.calls += 1
        if self.error:
            raise self.error
        for token in self.tokens:
            yield token


def matched_term() -> TermDocument:
    return TermDocument(
        term_id=1,
        term_name="inflation",
        official_definition="official definition from retrieval",
        related_terms=["prices", "deflation"],
        similarity=0.91,
    )


def matched_result() -> RetrievalResult:
    return RetrievalResult(
        status="matched",
        hits=[SearchHit(term_id=1, similarity=0.91)],
        terms=[matched_term()],
        candidates=[matched_term()],
    )


def candidate_result() -> RetrievalResult:
    return RetrievalResult(
        status="candidates",
        hits=[SearchHit(term_id=2, similarity=0.61), SearchHit(term_id=3, similarity=0.59)],
        candidates=[
            TermDocument(term_id=2, term_name="virtual asset", official_definition=None, similarity=0.61),
            TermDocument(term_id=3, term_name="ICO", official_definition=None, similarity=0.59),
        ],
    )


def not_found_with_candidates_result() -> RetrievalResult:
    return RetrievalResult(
        status="not_found",
        hits=[SearchHit(term_id=4, similarity=0.41)],
        candidates=[TermDocument(term_id=4, term_name="low match", official_definition=None, similarity=0.41)],
    )


def not_found_result() -> RetrievalResult:
    return RetrievalResult(status="not_found", hits=[])


async def collect(stream) -> str:
    return "".join([chunk async for chunk in stream])


def test_prompt_includes_retrieval_content() -> None:
    prompt = build_user_prompt("what is inflation", matched_result())

    assert "what is inflation" in prompt
    assert "inflation" in prompt
    assert "official definition from retrieval" in prompt
    assert "deflation" in prompt


def test_build_messages_has_system_and_user_prompt() -> None:
    messages = build_messages("question", matched_result())

    assert messages[0]["role"] == "system"
    assert "Retrieval" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "inflation" in messages[1]["content"]


def test_matched_starts_streaming_from_llm() -> None:
    llm = FakeLLMClient(tokens=["first", " token"])

    text = asyncio.run(
        collect(stream_chat_answer(user_query="question", retrieval_result=matched_result(), llm_client=llm))
    )

    assert text == "first token"
    assert llm.calls == 1


def test_candidate_response_schema() -> None:
    response = build_candidate_response(candidate_result().candidates)

    assert response.status == "candidates"
    assert response.candidates[0].rank == 1
    assert response.candidates[0].term_id == 2
    assert response.candidates[0].term_name == "virtual asset"
    assert response.candidates[0].similarity == 0.61


def test_not_found_response_schema() -> None:
    response = build_not_found_response()

    assert response.status == "not_found"
    assert response.message


def test_should_stream_answer_is_the_single_llm_gate() -> None:
    assert chat_route.should_stream_answer(matched_result()) is True
    assert chat_route.should_stream_answer(candidate_result()) is False
    assert chat_route.should_stream_answer(not_found_result()) is False


def test_chat_route_matched_returns_streaming_response(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = FakeLLMClient(tokens=["stream", "ed"])
    app.dependency_overrides[chat_route.get_llm_client_factory] = lambda: lambda: fake_llm
    monkeypatch.setattr(chat_route, "retrieve", lambda query: matched_result())

    try:
        response = TestClient(app).post("/chat", json={"query": "what is inflation?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"
    assert response.text == "data: stream\n\ndata: ed\n\n"
    assert fake_llm.calls == 1


def test_chat_route_candidates_returns_json_and_does_not_create_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    created = False

    def factory():
        nonlocal created
        created = True
        return FakeLLMClient()

    app.dependency_overrides[chat_route.get_llm_client_factory] = lambda: factory
    monkeypatch.setattr(chat_route, "retrieve", lambda query: candidate_result())

    try:
        response = TestClient(app).post("/chat", json={"query": "virtual"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    payload = response.json()
    assert payload["status"] == "candidates"
    assert payload["message"]
    assert payload["candidates"] == [
        {"rank": 1, "term_id": 2, "term_name": "virtual asset", "similarity": 0.61},
        {"rank": 2, "term_id": 3, "term_name": "ICO", "similarity": 0.59},
    ]
    assert created is False


def test_chat_route_low_similarity_candidates_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_route, "retrieve", lambda query: not_found_with_candidates_result())

    response = TestClient(app).post("/chat", json={"query": "unclear"})

    assert response.status_code == 200
    assert response.json()["status"] == "candidates"
    assert response.json()["candidates"][0]["term_name"] == "low match"


def test_chat_route_not_found_returns_json_and_does_not_create_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    created = False

    def factory():
        nonlocal created
        created = True
        return FakeLLMClient()

    app.dependency_overrides[chat_route.get_llm_client_factory] = lambda: factory
    monkeypatch.setattr(chat_route, "retrieve", lambda query: not_found_result())

    try:
        response = TestClient(app).post("/chat", json={"query": "nothing"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "not_found"
    assert response.json()["message"]
    assert created is False


def test_chat_route_selected_term_id_skips_retrieval_and_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = FakeLLMClient(tokens=["selected"])
    retrieved = False

    def fail_retrieve(query: str):
        nonlocal retrieved
        retrieved = True
        raise AssertionError("retrieval must not run")

    app.dependency_overrides[chat_route.get_llm_client_factory] = lambda: lambda: fake_llm
    monkeypatch.setattr(chat_route, "retrieve", fail_retrieve)
    monkeypatch.setattr(chat_route, "fetch_term_by_id", lambda term_id: matched_term())

    try:
        response = TestClient(app).post("/chat", json={"selected_term_id": 1})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.text == "data: selected\n\n"
    assert fake_llm.calls == 1
    assert retrieved is False


def test_chat_route_selected_term_name_is_not_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def retrieve_spy(query: str):
        nonlocal called
        called = True
        return matched_result()

    monkeypatch.setattr(chat_route, "retrieve", retrieve_spy)

    response = TestClient(app).post("/chat", json={"selected_term": "inflation"})

    assert response.status_code == 422
    assert called is False


def test_chat_route_invalid_selected_term_id_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[chat_route.get_llm_client_factory] = lambda: lambda: FakeLLMClient()
    monkeypatch.setattr(chat_route, "fetch_term_by_id", lambda term_id: None)

    try:
        response = TestClient(app).post("/chat", json={"selected_term_id": 999})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "selected term not found"


class FakeOpenAIStream:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.tokens:
            raise StopAsyncIteration
        token = self.tokens.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=token))])


class FakeCompletions:
    def __init__(self, stream=None, error: Exception | None = None) -> None:
        self.stream = stream
        self.error = error
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.stream


class FakeOpenAIClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def test_openai_mock_uses_stream_true_and_yields_tokens() -> None:
    completions = FakeCompletions(stream=FakeOpenAIStream(["A", "B"]))
    client = OpenAILLMClient(api_key="test", model="test-model", timeout=1.0, client=FakeOpenAIClient(completions))

    text = asyncio.run(collect(client.stream_answer(user_query="question", retrieval_result=matched_result())))

    assert text == "AB"
    assert completions.kwargs["model"] == "test-model"
    assert completions.kwargs["stream"] is True
    assert "inflation" in completions.kwargs["messages"][1]["content"]


def test_openai_timeout_is_wrapped() -> None:
    completions = FakeCompletions(error=asyncio.TimeoutError())
    client = OpenAILLMClient(api_key="test", model="test-model", timeout=1.0, client=FakeOpenAIClient(completions))

    with pytest.raises(LLMTimeoutError):
        asyncio.run(collect(client.stream_answer(user_query="question", retrieval_result=matched_result())))


def test_chat_stream_converts_llm_exception() -> None:
    llm = FakeLLMClient(error=LLMError("boom"))

    text = asyncio.run(
        collect(stream_chat_answer(user_query="question", retrieval_result=matched_result(), llm_client=llm))
    )

    assert text
    assert llm.calls == 1
