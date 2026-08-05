"""Extract aliases from term definitions and populate ``search_names``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.core.supabase import get_supabase_client


BATCH_SIZE = 100
REPORT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data/processed/search_names_ingestion_report.json"
)
TERM_COLUMNS = "term_id,term_name,official_definition"
TERM_NAME_PATTERN = re.compile(r"^(?P<base>.+?)\s*[\(（](?P<inside>[^\)）]+)[\)）]\s*$")
UNIT_NAMES = {
    "%",
    "‰",
    "bp",
    "bps",
    "℃",
    "ℓ",
    "kg",
    "m",
    "cm",
    "km",
    "$",
    "₩",
    "€",
    "¥",
}
EXCLUDED_KOREAN_NAMES = {"지정", "비지정", "신규", "폐지", "국내", "해외"}


def extract_search_names(term_name: str, official_definition: str | None) -> list[str]:
    """Return aliases from a title suffix and the first body parenthesis."""
    if not term_name or not official_definition:
        return []

    title_match = TERM_NAME_PATTERN.match(term_name)
    base_term_name = title_match.group("base").strip() if title_match else term_name
    found: list[str] = []

    if title_match:
        found.extend(
            _valid_candidates(
                title_match.group("inside"),
                base_term_name,
            )
        )

    pattern = re.compile(
        re.escape(base_term_name) + r"\s*[\(（]([^\)）]*)[\)）]",
        re.IGNORECASE,
    )
    match = pattern.search(official_definition)
    if match:
        for candidate in _valid_candidates(match.group(1), base_term_name):
            if candidate not in found:
                found.append(candidate)
    return found


def _valid_candidates(parenthetical: str, term_name: str) -> list[str]:
    candidates: list[str] = []
    for candidate in re.split(r"[,，;；]", parenthetical):
        candidate = re.sub(r"\s+", " ", candidate.strip())
        candidate = re.sub(r"^(?:또는|혹은|일명|즉|약칭)\s+", "", candidate)
        if _is_search_name(candidate, term_name) and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _is_search_name(candidate: str, term_name: str) -> bool:
    normalized = candidate.casefold()
    if (
        not candidate
        or normalized in UNIT_NAMES
        or normalized in EXCLUDED_KOREAN_NAMES
        or candidate == term_name
    ):
        return False

    if not re.search(r"[A-Za-z가-힣]", candidate):
        return False
    if re.fullmatch(r"[A-Z][A-Z0-9-]*", candidate):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", candidate):
        return True
    if re.fullmatch(r"[A-Za-z]+(?:[ -][A-Za-z]+)+", candidate):
        return True
    if re.fullmatch(r"[a-z]+", candidate):
        return True
    return bool(re.fullmatch(r"[가-힣]+(?: [가-힣]+)*", candidate))


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _load_terms(supabase: Any) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            supabase.table("terms")
            .select(TERM_COLUMNS)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        terms.extend(batch)
        if len(batch) < BATCH_SIZE:
            return terms
        offset += BATCH_SIZE


def _load_existing_names(supabase: Any) -> set[tuple[Any, str]]:
    existing: set[tuple[Any, str]] = set()
    offset = 0
    while True:
        response = (
            supabase.table("search_names")
            .select("term_id,search_name")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        existing.update((row["term_id"], row["search_name"]) for row in batch)
        if len(batch) < BATCH_SIZE:
            return existing
        offset += BATCH_SIZE


def _write_report(report: dict[str, int]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    supabase = get_supabase_client()
    openai = OpenAI(api_key=settings.openai_api_key)
    terms = _load_terms(supabase)
    existing = _load_existing_names(supabase)
    extracted: list[tuple[dict[str, Any], list[str]]] = []

    for term in terms:
        term_id = term["term_id"]
        print(f"[START] term_id={term_id}")
        names = extract_search_names(term["term_name"], term.get("official_definition"))
        for name in names:
            print(f"[EXTRACTED] {name}")
        extracted.append((term, names))

    report = {
        "total_terms": len(terms),
        "processed_terms": 0,
        "inserted_rows": 0,
        "updated_rows": 0,
        "failed_terms": 0,
    }

    for term_batch in _chunks(extracted, BATCH_SIZE):
        try:
            aliases = [name for _, names in term_batch for name in names]
            embeddings: list[list[float]] = []
            if aliases:
                response = openai.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=aliases,
                )
                embeddings = [
                    item.embedding for item in sorted(response.data, key=lambda item: item.index)
                ]

            rows: list[dict[str, Any]] = []
            embedding_index = 0
            for term, names in term_batch:
                for name in names:
                    rows.append(
                        {
                            "term_id": term["term_id"],
                            "search_name": name,
                            "search_embedding": embeddings[embedding_index],
                        }
                    )
                    embedding_index += 1

            if rows:
                supabase.table("search_names").upsert(rows, on_conflict="term_id,search_name").execute()

            for term, names in term_batch:
                report["processed_terms"] += 1
                for name in names:
                    key = (term["term_id"], name)
                    report["updated_rows" if key in existing else "inserted_rows"] += 1
                    existing.add(key)
                print(f"[UPSERTED] {len(names)} rows")
                print(f"[DONE] term_id={term['term_id']}")
        except Exception as error:
            report["failed_terms"] += len(term_batch)
            print(f"[ERROR] batch failed: {error}")

    _write_report(report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
