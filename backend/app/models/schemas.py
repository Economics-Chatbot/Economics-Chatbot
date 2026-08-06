from typing import Literal

from pydantic import BaseModel, Field


DoneStatus = Literal["completed", "partial", "suggestions", "failed", "error"]
FailureReason = Literal["not_found", "low_quality", "not_economic"]


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)


class Source(BaseModel):
    title: str
    url: str | None = None


class Answer(BaseModel):
    term: str
    one_line_definition: str
    easy_explanation: str
    example: str
    related_keywords: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class AnswerStartData(BaseModel):
    index: int = Field(ge=0)
    term: str


class DeltaData(BaseModel):
    index: int = Field(ge=0)
    text: str


class AnswerDoneData(BaseModel):
    index: int = Field(ge=0)
    answer: Answer


class Suggestion(BaseModel):
    term: str
    reason: str | None = None


class SuggestionsData(BaseModel):
    index: int = Field(ge=0)
    term: str
    suggestions: list[Suggestion]


class FailureData(BaseModel):
    index: int = Field(ge=0)
    term: str
    reason: FailureReason
    message: str


class ErrorData(BaseModel):
    # null means the error belongs to the whole request, not one term.
    index: int | None = Field(default=None, ge=0)
    code: str
    message: str
    retryable: bool = False


class DoneData(BaseModel):
    status: DoneStatus
    completed_indices: list[int] = Field(default_factory=list)
    failed_indices: list[int] = Field(default_factory=list)
    message: str | None = None
