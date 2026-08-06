from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.services.retrieval import RetrievalResult, retrieve

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    match_count: int = Field(default=3, ge=1, le=20)


class RetrievalHitResponse(BaseModel):
    term_id: int
    similarity: float


class RetrievalTermResponse(BaseModel):
    term_id: int
    term_name: str
    official_definition: str | None
    related_terms: list[str]
    similarity: float | None


class RetrievalResponse(BaseModel):
    status: str
    hits: list[RetrievalHitResponse]
    terms: list[RetrievalTermResponse]
    candidates: list[RetrievalTermResponse]


def serialize_result(result: RetrievalResult) -> RetrievalResponse:
    return RetrievalResponse(
        status=result.status,
        hits=[RetrievalHitResponse(**hit.__dict__) for hit in result.hits],
        terms=[RetrievalTermResponse(**term.__dict__) for term in result.terms],
        candidates=[RetrievalTermResponse(**term.__dict__) for term in result.candidates],
    )


@router.post("/test", response_model=RetrievalResponse)
async def test_retrieval(request: RetrievalRequest) -> RetrievalResponse:
    try:
        result = await run_in_threadpool(
            retrieve,
            request.query,
            match_count=request.match_count,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return serialize_result(result)
