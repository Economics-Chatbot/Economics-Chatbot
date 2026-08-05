from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class VectorRetrieveStatus(StrEnum):
    ANSWERABLE = "answerable"
    SUGGESTIONS = "suggestions"
    NOT_FOUND = "not_found"


class VectorRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)


class RetrievedTerm(BaseModel):
    term_id: int
    term_name: str
    official_definition: str
    related_terms: list[str] = Field(default_factory=list)


class TermSuggestion(BaseModel):
    term_id: int
    term_name: str
    similarity: float
    related_terms: list[str] = Field(default_factory=list)


class VectorRetrieveResult(BaseModel):
    status: VectorRetrieveStatus
    term: RetrievedTerm | None
    suggestions: list[TermSuggestion]
    query: str
