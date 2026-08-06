from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.schemas import AnswerRequest
from app.services.answers import (
    build_candidate_response,
    build_not_found_response,
    should_call_llm,
    stream_answer_events,
)
from app.services.llm import LLMClient, create_llm_client
from app.services.retrieval import fetch_term_by_id, retrieve

router = APIRouter(prefix="/api")


def get_llm_client_factory() -> Callable[[], LLMClient]:
    return create_llm_client


async def handle_answer_request(
    request: AnswerRequest,
    llm_client_factory: Callable[[], LLMClient],
) -> StreamingResponse | JSONResponse:
    if request.selected_term_id is not None:
        try:
            term = await run_in_threadpool(fetch_term_by_id, request.selected_term_id)
        except Exception as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        if term is None:
            raise HTTPException(status_code=404, detail="Invalid candidate")
        return stream_response(stream_answer_events(query=term.term_name, terms=[term], llm_client_factory=llm_client_factory))

    if request.query is None:
        raise HTTPException(status_code=422, detail="query or selected_term_id is required")

    try:
        result = await run_in_threadpool(retrieve, request.query)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if should_call_llm(result):
        return stream_response(stream_answer_events(query=request.query, terms=result.terms[:1], llm_client_factory=llm_client_factory))

    if result.candidates:
        return JSONResponse(build_candidate_response(result.candidates).model_dump())

    return JSONResponse(build_not_found_response().model_dump())


def stream_response(events) -> StreamingResponse:
    # Starlette cancels the generator when the client disconnects; no final
    # `done` event can be delivered after that point.
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/answers", response_model=None)
async def answers(
    request: AnswerRequest,
    llm_client_factory: Callable[[], LLMClient] = Depends(get_llm_client_factory),
) -> StreamingResponse | JSONResponse:
    return await handle_answer_request(request, llm_client_factory)
