import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_route
from app.main import app
from app.services.chat import stream_chat_answer
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


def matched_result() -> RetrievalResult:
    return RetrievalResult(
        status="matched",
        hits=[SearchHit(term_id=1, similarity=0.91)],
        terms=[
            TermDocument(
                term_id=1,
                term_name="inflation",
                official_definition="official definition from retrieval",
                related_terms=["prices", "deflation"],
                similarity=0.91,
            )
        ],
    )


def candidate_result() -> RetrievalResult:
    return RetrievalResult(
        status="candidates",
        hits=[SearchHit(term_id=2, similarity=0.61)],
        candidates=[
            TermDocument(term_id=2, term_name="virtual asset", official_definition=None, similarity=0.61),
            TermDocument(term_id=3, term_name="ICO", official_definition=None, similarity=0.59),
        ],
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


def test_candidate_does_not_call_llm() -> None:
    llm = FakeLLMClient()

    text = asyncio.run(
        collect(stream_chat_answer(user_query="question", retrieval_result=candidate_result(), llm_client=llm))
    )

    assert "virtual asset" in text
    assert "ICO" in text
    assert llm.calls == 0


def test_not_found_does_not_call_llm() -> None:
    llm = FakeLLMClient()

    text = asyncio.run(
        collect(stream_chat_answer(user_query="question", retrieval_result=not_found_result(), llm_client=llm))
    )

    assert text
    assert llm.calls == 0


def test_chat_route_returns_streaming_response(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_chat_route_candidate_does_not_create_llm(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert "virtual asset" in response.text
    assert created is False


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
