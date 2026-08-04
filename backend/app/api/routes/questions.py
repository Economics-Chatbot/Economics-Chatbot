from fastapi import APIRouter

from app.models.schemas import ChatResponse, QuestionRequest
from app.services.answer_generator import generate_answer
from app.services.retrieval import FAILURE_MESSAGE, retrieve_terms_for_question

router = APIRouter()


async def _build_answer_response(query: str) -> ChatResponse:
    candidates = await retrieve_terms_for_question(query)

    if not candidates:
        return ChatResponse(query=query, failure_message=FAILURE_MESSAGE)

    answer = await generate_answer(query, candidates[0])
    return ChatResponse(query=query, answer=answer)


@router.post("/questions", response_model=ChatResponse)
async def create_question(request: QuestionRequest) -> ChatResponse:
    query = request.query.strip()
    return await _build_answer_response(query)
