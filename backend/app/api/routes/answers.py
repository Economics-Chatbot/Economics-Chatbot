from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import AnswerRequest
from app.services.answers import stream_events

router = APIRouter(prefix="/api")


@router.post("/answers")
async def answers(request: AnswerRequest) -> StreamingResponse:
    # Starlette cancels the generator when the client disconnects; no final
    # `done` event can be delivered after that point.
    return StreamingResponse(
        stream_events(request.query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
