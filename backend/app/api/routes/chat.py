from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.models.schemas import AnswerRequest
from app.services.chat import stream_chat_events
from app.services.llm import LLMClient, create_llm_client
from app.services.retrieval import RetrievalResult, retrieve

router = APIRouter(tags=["chat"])


class UnusedLLMClient(LLMClient):
    async def stream_answer(self, *, user_query: str, retrieval_result: RetrievalResult):
        raise RuntimeError("LLM client should not be used for this retrieval status")
        yield ""


def get_llm_client_factory() -> Callable[[], LLMClient]:
    return create_llm_client


@router.post("/chat")
async def chat(
    request: AnswerRequest,
    llm_client_factory: Callable[[], LLMClient] = Depends(get_llm_client_factory),
) -> StreamingResponse:
    try:
        retrieval_result = await run_in_threadpool(retrieve, request.query)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    llm_client = llm_client_factory() if retrieval_result.status == "matched" else UnusedLLMClient()
    return StreamingResponse(
        stream_chat_events(
            user_query=request.query,
            retrieval_result=retrieval_result,
            llm_client=llm_client,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
