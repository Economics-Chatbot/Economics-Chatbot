from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import retrieval

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)


class SearchHitResponse(BaseModel):
    term_id: int
    similarity: float


class TermResponse(BaseModel):
    term_id: int
    term_name: str
    official_definition: str | None
    related_terms: list[str]
    similarity: float | None


class RetrievalResponse(BaseModel):
    status: Literal["matched", "candidates", "not_found"]
    hits: list[SearchHitResponse]
    terms: list[TermResponse]
    candidates: list[str]


@router.post("/retrieval", response_model=RetrievalResponse)
async def retrieve_terms(request: RetrievalRequest) -> RetrievalResponse:
    try:
        result = retrieval.retrieve(request.query)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RetrievalResponse(
        status=result.status,
        hits=[SearchHitResponse(term_id=hit.term_id, similarity=hit.similarity) for hit in result.hits],
        terms=[
            TermResponse(
                term_id=term.term_id,
                term_name=term.term_name,
                official_definition=term.official_definition,
                related_terms=term.related_terms,
                similarity=term.similarity,
            )
            for term in result.terms
        ],
        candidates=[candidate.term_name for candidate in result.candidates],
    )