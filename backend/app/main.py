from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import ChatResponse, QuestionRequest
from app.services.answer_generator import generate_answer
from app.services.retrieval import (
    FAILURE_MESSAGE,
    get_term_by_name,
    retrieve_terms_for_question,
)

app = FastAPI(title="EconomyMate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _build_answer_response(query: str) -> ChatResponse:
    retrieved_terms = await retrieve_terms_for_question(query)

    if not retrieved_terms:
        return ChatResponse(
            query=query,
            retrieved_terms=[],
            failure_message=FAILURE_MESSAGE,
        )

    answer = await generate_answer(query, retrieved_terms[0])
    return ChatResponse(query=query, answer=answer, retrieved_terms=retrieved_terms)


@app.post("/questions", response_model=ChatResponse)
async def create_question(request: QuestionRequest) -> ChatResponse:
    query = request.query.strip()
    return await _build_answer_response(query)


@app.get("/terms/{term}", response_model=ChatResponse)
async def get_term(term: str) -> ChatResponse:
    retrieved_term = await get_term_by_name(term)
    if retrieved_term is None:
        raise HTTPException(status_code=404, detail="해당 경제용어를 찾지 못했습니다.")

    answer = await generate_answer(term, retrieved_term)
    return ChatResponse(query=term, answer=answer, retrieved_terms=[retrieved_term])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: QuestionRequest) -> ChatResponse:
    return await create_question(request)
