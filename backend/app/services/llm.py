from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI

from app.core.config import get_settings
from app.services.prompt import build_messages
from app.services.retrieval import RetrievalResult


class LLMError(RuntimeError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMClient(ABC):
    @abstractmethod
    async def stream_answer(
        self,
        *,
        user_query: str,
        retrieval_result: RetrievalResult,
    ) -> AsyncIterator[str]:
        raise NotImplementedError


class OpenAILLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise RuntimeError("OPENAI_API_KEY is required")
        self.model = model
        self.client = client or AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def stream_answer(
        self,
        *,
        user_query: str,
        retrieval_result: RetrievalResult,
    ) -> AsyncIterator[str]:
        messages = build_messages(user_query, retrieval_result)
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content if chunk.choices else None
                if token:
                    yield token
        except APITimeoutError as error:
            raise LLMTimeoutError("LLM request timed out") from error
        except (APIConnectionError, APIError) as error:
            raise LLMError("LLM request failed") from error
        except asyncio.TimeoutError as error:
            raise LLMTimeoutError("LLM request timed out") from error


def create_llm_client() -> LLMClient:
    settings = get_settings()
    return OpenAILLMClient(
        api_key=settings.openai_api_key,
        model=settings.resolved_chat_model,
        timeout=settings.timeout,
    )
