from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatResponse
from app.services.answer_generator import generate_answer
from app.services.retrieval import get_term_by_name

router = APIRouter()


@router.get("/terms/{term}", response_model=ChatResponse)
async def get_term(term: str) -> ChatResponse:
    retrieved_term = await get_term_by_name(term)
    if retrieved_term is None:
        raise HTTPException(status_code=404, detail="해당 경제용어를 찾지 못했습니다.")

    answer = await generate_answer(term, retrieved_term)
    return ChatResponse(query=term, answer=answer)
