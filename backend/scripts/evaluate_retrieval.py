from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.retrieval_config import CANDIDATE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD
from app.services.retrieval import TermDocument, attach_similarity, fetch_terms, retrieve


DEFAULT_TOP_K = 3
DEFAULT_QUERIES_PATH = Path(__file__).with_name("test_queries.json")
SEPARATOR = "=" * 50


@dataclass(frozen=True)
class TestQuery:
    query: str
    answer: str


@dataclass(frozen=True)
class FailedCase:
    question: str
    expected: str
    top1: str
    similarity: float | None
    matched_in_top3: bool


def load_test_queries(path: Path) -> list[TestQuery]:
    with path.open(encoding="utf-8") as file:
        raw_queries = json.load(file)

    if not isinstance(raw_queries, list):
        raise ValueError("test_queries.json must contain a list of query objects")

    queries: list[TestQuery] = []
    for index, item in enumerate(raw_queries, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"query #{index} must be an object")

        query = _required_string(item, "query", index)
        answer = _required_string(item, "answer", index)
        queries.append(TestQuery(query=query, answer=answer))

    return queries


def _required_string(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"query #{index} must have a non-empty string field: {key}")
    return value.strip()


def normalize_term_name(term_name: str) -> str:
    return term_name.strip().casefold()


def is_answer(term: TermDocument, expected_answer: str) -> bool:
    return normalize_term_name(term.term_name) == normalize_term_name(expected_answer)


def format_similarity(similarity: float | None) -> str:
    if similarity is None:
        return "N/A"
    return f"{similarity:.2f}"


def print_query_result(test_query: TestQuery, terms: list[TermDocument], top_k: int) -> None:
    print(SEPARATOR)
    print(f"Question : {test_query.query}")
    print()

    for rank in range(1, top_k + 1):
        term = terms[rank - 1] if rank <= len(terms) else None
        if term is None:
            print(f"Top{rank} {'(no result)':<16} N/A")
            continue

        marker = " [OK]" if is_answer(term, test_query.answer) else ""
        print(f"Top{rank} {term.term_name:<16} {format_similarity(term.similarity)}{marker}")

    print()
    print(f"Expected : {test_query.answer}")
    print()


def print_summary(
    *,
    total_count: int,
    top1_match_count: int,
    top3_match_count: int,
    top1_similarities: list[float],
    failed_cases: list[FailedCase],
) -> None:
    top1_accuracy = top1_match_count / total_count if total_count else 0.0
    top3_accuracy = top3_match_count / total_count if total_count else 0.0
    average_similarity = (
        sum(top1_similarities) / len(top1_similarities) if top1_similarities else 0.0
    )

    print(SEPARATOR)
    print("Summary")
    print()
    print(f"High Confidence Threshold : {HIGH_CONFIDENCE_THRESHOLD:.2f}")
    print(f"Candidate Threshold       : {CANDIDATE_THRESHOLD:.2f}")
    print(f"Top1 Accuracy             : {top1_accuracy:.2%}")
    print(f"Top3 Accuracy             : {top3_accuracy:.2%}")
    print(f"Matched Count             : {top1_match_count}")
    print(f"Failed Count              : {len(failed_cases)}")
    print(f"Average Similarity        : {average_similarity:.2f}")
    print()

    print("Failed Cases")
    print()
    if not failed_cases:
        print("(none)")
        return

    for failed_case in failed_cases:
        print(f"Question : {failed_case.question}")
        print(f"Expected : {failed_case.expected}")
        print(f"Top1 : {failed_case.top1}")
        print(f"Similarity : {format_similarity(failed_case.similarity)}")
        print(f"Matched In Top3 : {failed_case.matched_in_top3}")
        print()


def evaluate(queries_path: Path, top_k: int) -> None:
    test_queries = load_test_queries(queries_path)

    top1_match_count = 0
    top3_match_count = 0
    top1_similarities: list[float] = []
    failed_cases: list[FailedCase] = []

    for test_query in test_queries:
        result = retrieve(test_query.query, match_count=top_k)
        terms = attach_similarity(
            fetch_terms([hit.term_id for hit in result.hits]),
            result.hits,
        )

        print_query_result(test_query, terms, top_k)

        top1 = terms[0] if terms else None
        top1_matched = top1 is not None and is_answer(top1, test_query.answer)
        top3_matched = any(is_answer(term, test_query.answer) for term in terms[:top_k])

        if top1 and top1.similarity is not None:
            top1_similarities.append(top1.similarity)

        if top1_matched:
            top1_match_count += 1
        else:
            failed_cases.append(
                FailedCase(
                    question=test_query.query,
                    expected=test_query.answer,
                    top1=top1.term_name if top1 else "(no result)",
                    similarity=top1.similarity if top1 else None,
                    matched_in_top3=top3_matched,
                )
            )

        if top3_matched:
            top3_match_count += 1

    print_summary(
        total_count=len(test_queries),
        top1_match_count=top1_match_count,
        top3_match_count=top3_match_count,
        top1_similarities=top1_similarities,
        failed_cases=failed_cases,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality without chat completion.")
    parser.add_argument(
        "--queries",
        type=Path,
        default=DEFAULT_QUERIES_PATH,
        help=f"Path to test queries JSON. Default: {DEFAULT_QUERIES_PATH}",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"Number of retrieval results to evaluate. Default: {DEFAULT_TOP_K}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise ValueError("--top-k must be at least 1")
    evaluate(args.queries, args.top_k)


if __name__ == "__main__":
    main()

