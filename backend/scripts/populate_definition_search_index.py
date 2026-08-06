from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from openai import OpenAI

from app.core.config import get_settings
from app.services.retrieval import get_database_connection


BATCH_SIZE = 100
REPORT_PATH = Path(__file__).resolve().parents[2] / "data/processed/definition_search_names_report.json"
MIN_CHUNK_LENGTH = 20
MAX_CHUNK_LENGTH = 900


@dataclass(frozen=True)
class DefinitionSource:
    term_id: int
    term_name: str
    official_definition: str


@dataclass(frozen=True)
class DefinitionSearchText:
    term_id: int
    search_name: str


def load_definition_sources(connection: Any, *, limit: int | None = None) -> list[DefinitionSource]:
    query = """
        select
            t.term_id,
            t.term_name,
            t.official_definition
        from terms t
        where t.official_definition is not null
          and btrim(t.official_definition) <> ''
        order by t.term_id
    """
    params: dict[str, Any] = {}
    if limit is not None:
        query += "\nlimit %(limit)s"
        params["limit"] = limit

    rows = connection.execute(query, params).fetchall()
    return [
        DefinitionSource(
            term_id=int(row["term_id"]),
            term_name=str(row["term_name"]),
            official_definition=normalize_text(str(row["official_definition"])),
        )
        for row in rows
    ]


def load_existing_search_names(connection: Any) -> set[tuple[int, str]]:
    rows = connection.execute("select term_id, search_name from search_names", {}).fetchall()
    return {(int(row["term_id"]), str(row["search_name"])) for row in rows}


def build_definition_search_texts(sources: list[DefinitionSource]) -> list[DefinitionSearchText]:
    search_texts: list[DefinitionSearchText] = []
    seen: set[tuple[int, str]] = set()

    for source in sources:
        for search_name in definition_search_names(source):
            key = (source.term_id, search_name)
            if key in seen:
                continue
            seen.add(key)
            search_texts.append(DefinitionSearchText(term_id=source.term_id, search_name=search_name))

    return search_texts


def definition_search_names(source: DefinitionSource) -> list[str]:
    sentences = split_sentences(source.official_definition)
    candidates = [source.official_definition]
    candidates.extend(sentences)

    for index in range(len(sentences) - 1):
        pair = normalize_text(sentences[index] + " " + sentences[index + 1])
        candidates.append(pair)

    return [candidate for candidate in candidates if is_valid_chunk(candidate)]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    rough_sentences = re.split(r"(?<=[.!?。])\s+", normalized)
    sentences: list[str] = []
    for rough_sentence in rough_sentences:
        sentence = normalize_text(rough_sentence)
        if not sentence:
            continue
        if len(sentence) <= MAX_CHUNK_LENGTH:
            sentences.append(sentence)
            continue
        sentences.extend(split_long_sentence(sentence))
    return sentences


def split_long_sentence(sentence: str) -> list[str]:
    parts = [normalize_text(part) for part in re.split(r"(?<=[,;:])\s+", sentence)]
    chunks: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        candidate = normalize_text(f"{current} {part}" if current else part)
        if len(candidate) <= MAX_CHUNK_LENGTH:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = part
    if current:
        chunks.append(current)
    return chunks


def is_valid_chunk(text: str) -> bool:
    return MIN_CHUNK_LENGTH <= len(text) <= MAX_CHUNK_LENGTH


def chunks(items: list[DefinitionSearchText], size: int) -> list[list[DefinitionSearchText]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def populate(*, batch_size: int, limit: int | None, dry_run: bool) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    openai = OpenAI(api_key=settings.openai_api_key)
    connection = get_database_connection()
    try:
        sources = load_definition_sources(connection, limit=limit)
        existing = load_existing_search_names(connection)
        all_search_texts = build_definition_search_texts(sources)
        missing_search_texts = [
            item for item in all_search_texts if (item.term_id, item.search_name) not in existing
        ]
        report: dict[str, Any] = {
            "total_terms": len(sources),
            "candidate_definition_search_rows": len(all_search_texts),
            "total_missing_definition_rows": len(missing_search_texts),
            "processed_rows": 0,
            "inserted_rows": 0,
            "failed_batches": 0,
            "dry_run": dry_run,
            "embedding_model": settings.openai_embedding_model,
            "target_table": "search_names",
        }

        if dry_run:
            write_report(report)
            return report

        for search_batch in chunks(missing_search_texts, batch_size):
            try:
                response = openai.embeddings.create(
                    model=settings.openai_embedding_model,
                    input=[item.search_name for item in search_batch],
                )
                embeddings = [
                    item.embedding for item in sorted(response.data, key=lambda item: item.index)
                ]

                rows = [
                    {
                        "term_id": item.term_id,
                        "search_name": item.search_name,
                        "search_embedding": _format_vector(embedding),
                    }
                    for item, embedding in zip(search_batch, embeddings)
                ]
                cursor = connection.execute(
                    """
                    insert into search_names (term_id, search_name, search_embedding)
                    select
                        row_data.term_id,
                        row_data.search_name,
                        row_data.search_embedding::vector
                    from jsonb_to_recordset(%(rows)s::jsonb) as row_data(
                        term_id integer,
                        search_name text,
                        search_embedding text
                    )
                    on conflict on constraint uq_search_names_term_search_name do nothing
                    """,
                    {"rows": json.dumps(rows)},
                )
                connection.commit()
                inserted_count = cursor.rowcount if cursor.rowcount is not None else len(rows)
                report["processed_rows"] += len(search_batch)
                report["inserted_rows"] += inserted_count
                print(f"[INSERTED] {inserted_count} definition search_names rows")
            except Exception as error:
                connection.rollback()
                report["failed_batches"] += 1
                print(f"[ERROR] batch failed: {error}")

        write_report(report)
        return report
    finally:
        connection.close()


def _format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate search_names with official_definition embeddings used by search_index."
    )
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")

    report = populate(batch_size=args.batch_size, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()