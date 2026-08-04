from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import ChatResponse, QuestionRequest
from app.services.answer_generator import generate_answer
from app.services.retrieval import FAILURE_MESSAGE, retrieve_terms

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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: QuestionRequest) -> ChatResponse:
    query = request.query.strip()
    retrieved_terms = await retrieve_terms(query)

    if not retrieved_terms:
        return ChatResponse(
            query=query,
            retrieved_terms=[],
            failure_message=FAILURE_MESSAGE,
        )

    answer = await generate_answer(query, retrieved_terms[0])
    return ChatResponse(query=query, answer=answer, retrieved_terms=retrieved_terms)
