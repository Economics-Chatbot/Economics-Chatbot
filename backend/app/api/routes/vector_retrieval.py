from fastapi import APIRouter, HTTPException
import logging

from app.models.vector_retrieval import VectorRetrieveRequest, VectorRetrieveResult
from app.services.vector_retrieval import (
    EmbeddingError,
    VectorSearchError,
    vector_retrieve,
)

router = APIRouter(prefix="/be2", tags=["be2"])

logger = logging.getLogger(__name__)


@router.post("/vector-retrieve", response_model=VectorRetrieveResult)
def retrieve_term(request: VectorRetrieveRequest) -> VectorRetrieveResult:
    try:
        return vector_retrieve(request.query)
    except EmbeddingError as error:
        logger.exception("EmbeddingError in BE2 vector_retrieve: %s", error)
        raise HTTPException(
            status_code=503,
            detail={"code": "embedding_failed", "message": str(error)},
        ) from error
    except VectorSearchError as error:
        logger.exception("VectorSearchError in BE2 vector_retrieve: %s", error)
        raise HTTPException(
            status_code=503,
            detail={"code": "vector_search_failed", "message": str(error)},
        ) from error
