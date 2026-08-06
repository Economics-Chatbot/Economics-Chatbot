from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.models.schemas import ChatCandidate, ChatCandidateResponse, ChatNotFoundResponse
from app.services.llm import LLMClient, LLMError, LLMTimeoutError
from app.services.retrieval import RetrievalResult, TermDocument


CANDIDATE_MESSAGE = "\uc544\ub798 \uc6a9\uc5b4 \uc911 \ucc3e\uc73c\uc2dc\ub294 \uac83\uc744 \uc120\ud0dd\ud574\uc8fc\uc138\uc694."
NOT_FOUND_MESSAGE = "\uac80\uc0c9 \uacb0\uacfc\uac00 \uc5c6\uc2b5\ub2c8\ub2e4."


async def stream_chat_answer(
    *,
    user_query: str,
    retrieval_result: RetrievalResult,
    llm_client: LLMClient,
) -> AsyncIterator[str]:
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


def build_candidate_response(candidates: list[TermDocument]) -> ChatCandidateResponse:
    return ChatCandidateResponse(
        message=CANDIDATE_MESSAGE,
        candidates=[
            ChatCandidate(
                rank=index,
                term_id=term.term_id,
                term_name=term.term_name,
                similarity=term.similarity,
            )
            for index, term in enumerate(candidates[:3], start=1)
        ],
    )


def build_not_found_response() -> ChatNotFoundResponse:
    return ChatNotFoundResponse(message=NOT_FOUND_MESSAGE)
