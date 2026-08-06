from collections.abc import Callable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.schemas import AnswerRequest
from app.services.answers import stream_events
from app.services.llm import LLMClient, create_llm_client
from app.services.retrieval import retrieve

router = APIRouter(prefix="/api")


def get_llm_client_factory() -> Callable[[], LLMClient]:
    return create_llm_client


@router.post("/answers")
async def answers(
    request: AnswerRequest,
    llm_client_factory: Callable[[], LLMClient] = Depends(get_llm_client_factory),
) -> StreamingResponse:
    # Starlette cancels the generator when the client disconnects; no final
    # `done` event can be delivered after that point.
    return StreamingResponse(
        stream_events(request.query, retrieve, llm_client_factory),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
