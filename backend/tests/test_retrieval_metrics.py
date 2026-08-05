import pytest

from app.evaluation.retrieval_metrics import (
    RetrievalEvaluationConfig,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_default_threshold_config() -> None:
    config = RetrievalEvaluationConfig()

    assert config.high_confidence_threshold == 0.72
    assert config.candidate_threshold == 0.55


def test_precision_at_k() -> None:
    assert precision_at_k([1, 2, 3], {1, 3, 5}, 2) == 0.5


def test_recall_at_k() -> None:
    assert recall_at_k([1, 2, 3], {1, 3, 5}, 3) == pytest.approx(2 / 3)


def test_ndcg_at_k_is_one_for_ideal_ranking() -> None:
    assert ndcg_at_k([1, 2, 3], {1, 2, 3}, 3) == pytest.approx(1.0)


def test_metrics_return_zero_for_empty_inputs() -> None:
    assert precision_at_k([], {1}, 3) == 0.0
    assert recall_at_k([1], set(), 3) == 0.0
    assert ndcg_at_k([1], set(), 3) == 0.0
