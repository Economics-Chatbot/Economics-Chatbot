from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.schemas import ChatRequest
from app.services.chat import build_candidate_response, build_not_found_response, stream_chat_events
from app.services.llm import LLMClient, create_llm_client
from app.services.retrieval import RetrievalResult, TermDocument, fetch_term_by_id, retrieve

router = APIRouter(tags=["chat"])


def get_llm_client_factory() -> Callable[[], LLMClient]:
    return create_llm_client


@router.post("/chat", response_model=None)
async def chat(
    request: ChatRequest,
    llm_client_factory: Callable[[], LLMClient] = Depends(get_llm_client_factory),
) -> StreamingResponse | JSONResponse:
    if request.selected_term_id is not None:
        selected_term = await load_selected_term(request.selected_term_id)
        return stream_matched_answer(
            user_query=selected_term.term_name,
            term=selected_term,
            llm_client_factory=llm_client_factory,
        )

    if request.query is None:
        raise HTTPException(status_code=422, detail="query or selected_term_id is required")

    try:
        retrieval_result = await run_in_threadpool(retrieve, request.query)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    if should_stream_answer(retrieval_result):
        return stream_retrieval_answer(
            user_query=request.query,
            retrieval_result=retrieval_result,
            llm_client_factory=llm_client_factory,
        )

    if retrieval_result.candidates:
        return JSONResponse(build_candidate_response(retrieval_result.candidates).model_dump())

    return JSONResponse(build_not_found_response().model_dump())


async def load_selected_term(term_id: int) -> TermDocument:
    try:
        term = await run_in_threadpool(fetch_term_by_id, term_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if term is None:
        raise HTTPException(status_code=404, detail="selected term not found")
    return term


def should_stream_answer(retrieval_result: RetrievalResult) -> bool:
    return retrieval_result.status == "matched" and bool(retrieval_result.terms)


def stream_matched_answer(
    *,
    user_query: str,
    term: TermDocument,
    llm_client_factory: Callable[[], LLMClient],
) -> StreamingResponse:
    retrieval_result = RetrievalResult(status="matched", terms=[term])
    return stream_retrieval_answer(
        user_query=user_query,
        retrieval_result=retrieval_result,
        llm_client_factory=llm_client_factory,
    )


def stream_retrieval_answer(
    *,
    user_query: str,
    retrieval_result: RetrievalResult,
    llm_client_factory: Callable[[], LLMClient],
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_events(
            user_query=user_query,
            retrieval_result=retrieval_result,
            llm_client=llm_client_factory(),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
