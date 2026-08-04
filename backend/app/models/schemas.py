from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)


class RetrievedTerm(BaseModel):
    term_name: str
    official_definition: str
    source_name: str
    source_page: int | None = None
    related_terms: list[str] = Field(default_factory=list)
    similarity: float | None = None


class ChatAnswer(BaseModel):
    term: str
    one_line: str
    easy_explanation: str
    example: str
    related_terms: list[str] = Field(default_factory=list)
    source_name: str
    source_page: int | None = None


class ChatResponse(BaseModel):
    query: str
    answer: ChatAnswer | None = None
    retrieved_terms: list[RetrievedTerm] = Field(default_factory=list)
    failure_message: str | None = None
