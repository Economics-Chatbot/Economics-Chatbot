from __future__ import annotations

from dataclasses import dataclass
from math import log2

from app.core.retrieval_config import CANDIDATE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD


@dataclass(frozen=True)
class RetrievalEvaluationConfig:
    high_confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD
    candidate_threshold: float = CANDIDATE_THRESHOLD


def precision_at_k(retrieved_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    return sum(1 for term_id in top_k if term_id in relevant_ids) / k


def recall_at_k(retrieved_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    return sum(1 for term_id in top_k if term_id in relevant_ids) / len(relevant_ids)


def ndcg_at_k(retrieved_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    dcg = 0.0
    for index, term_id in enumerate(retrieved_ids[:k], start=1):
        relevance = 1.0 if term_id in relevant_ids else 0.0
        dcg += relevance / log2(index + 1)

    ideal_hits = min(len(relevant_ids), k)
    ideal_dcg = sum(1.0 / log2(index + 1) for index in range(1, ideal_hits + 1))
    if ideal_dcg == 0:
        return 0.0
    return dcg / ideal_dcg