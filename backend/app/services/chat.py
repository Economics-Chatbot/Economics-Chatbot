from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.services.llm import LLMClient, LLMError, LLMTimeoutError
from app.services.retrieval import RetrievalResult


NOT_FOUND_MESSAGE = "\uac80\uc0c9 \uacb0\uacfc\ub97c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.\n\ub2e4\ub978 \ud45c\ud604\uc73c\ub85c \uc9c8\ubb38\ud574\uc8fc\uc138\uc694."


async def stream_chat_answer(
    *,
    user_query: str,
    retrieval_result: RetrievalResult,
    llm_client: LLMClient,
) -> AsyncIterator[str]:
    if retrieval_result.status == "not_found":
        yield NOT_FOUND_MESSAGE
        return

    if retrieval_result.status == "candidates":
        yield format_candidate_message(retrieval_result)
        return

    try:
        async for token in llm_client.stream_answer(
            user_query=user_query,
            retrieval_result=retrieval_result,
        ):
            yield token
    except asyncio.CancelledError:
        raise
    except LLMTimeoutError:
        yield "\n\n\ub2f5\ubcc0 \uc0dd\uc131 \uc2dc\uac04\uc774 \ucd08\uacfc\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
    except LLMError:
        yield "\n\n\ub2f5\ubcc0 \uc0dd\uc131 \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
    except Exception:
        yield "\n\n\ub2f5\ubcc0 \uc2a4\ud2b8\ub9ac\ubc0d \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4."


async def stream_chat_events(
    *,
    user_query: str,
    retrieval_result: RetrievalResult,
    llm_client: LLMClient,
) -> AsyncIterator[str]:
    async for token in stream_chat_answer(
        user_query=user_query,
        retrieval_result=retrieval_result,
        llm_client=llm_client,
    ):
        yield format_sse_data(token)


def format_sse_data(token: str) -> str:
    lines = token.splitlines() or [""]
    return "".join(f"data: {line}\n" for line in lines) + "\n"


def format_candidate_message(retrieval_result: RetrievalResult) -> str:
    names = [term.term_name for term in retrieval_result.candidates]
    if not names:
        return NOT_FOUND_MESSAGE
    bullets = "\n".join(f"- {name}" for name in names)
    return f"\ud639\uc2dc \uc544\ub798 \uc6a9\uc5b4\ub97c \ub9d0\uc500\ud558\uc168\ub098\uc694?\n\n{bullets}\n\n\uc6d0\ud558\uc2dc\ub294 \uc6a9\uc5b4\ub85c \ub2e4\uc2dc \uc9c8\ubb38\ud574\uc8fc\uc138\uc694."
