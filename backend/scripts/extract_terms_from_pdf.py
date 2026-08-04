"""Extract economic terms from the Bank of Korea PDF.

The script creates `data/processed/economic_terms.json` without embeddings.
Embeddings are generated later by `ingest_terms.py`.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader


DEFAULT_INPUT = Path("data/raw/economic_terms_800_2026.pdf")
DEFAULT_OUTPUT = Path("data/processed/economic_terms.json")
SOURCE_NAME = "한국은행 경제금융용어 800선"
BODY_START_PDF_INDEX = 18
BODY_END_PDF_INDEX = 422
TOC_START_PDF_INDEX = 3
TOC_END_PDF_INDEX = 16


@dataclass
class TocEntry:
    term_name: str
    source_page: int


@dataclass
class EconomicTerm:
    term_name: str
    official_definition: str
    source_name: str
    source_page: int
    related_terms: list[str]


@dataclass
class SkippedTerm:
    term_name: str
    source_page: int
    reason: str


def normalize_text(value: str) -> str:
    value = value.replace("\u0000", "")
    value = value.replace("·", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize_term(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s*;\s*", "; ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_toc(reader: PdfReader) -> list[TocEntry]:
    entries: list[TocEntry] = []
    pending = ""

    for page_index in range(TOC_START_PDF_INDEX, TOC_END_PDF_INDEX + 1):
        text = reader.pages[page_index].extract_text() or ""
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in {"ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ", "ABC"}:
                continue
            if re.fullmatch(r"[ivxlcdm]+", line, flags=re.IGNORECASE):
                continue
            if "찾아보기" in line or "경제금융용어" in line:
                continue

            cleaned = normalize_text(line)
            match = re.search(r"(.+?)\s+(\d[\d ]*)$", cleaned)
            if match:
                term = normalize_term(f"{pending} {match.group(1)}")
                page = int(match.group(2).replace(" ", ""))
                if term and not term.isdigit():
                    entries.append(TocEntry(term_name=term, source_page=page))
                pending = ""
            else:
                pending = normalize_term(f"{pending} {cleaned}")

    deduped: list[TocEntry] = []
    seen: set[tuple[str, int]] = set()
    for entry in entries:
        key = (entry.term_name, entry.source_page)
        if key not in seen:
            deduped.append(entry)
            seen.add(key)
    return deduped


def extract_body_pages(reader: PdfReader) -> dict[int, str]:
    pages: dict[int, str] = {}
    for pdf_index in range(BODY_START_PDF_INDEX, BODY_END_PDF_INDEX + 1):
        source_page = pdf_index - BODY_START_PDF_INDEX + 1
        text = reader.pages[pdf_index].extract_text() or ""
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if (
            len(raw_lines) >= 3
            and raw_lines[0] != str(source_page)
            and str(source_page) in raw_lines[1:3]
        ):
            raw_lines = raw_lines[1:]

        lines = []
        for line in raw_lines:
            if line in {"ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ", "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ", "ABC"}:
                continue
            if line == str(source_page):
                continue
            if re.search(r"경제금융용어\s+800선", line) or "찾아보기" in line:
                continue
            lines.append(line)
        pages[source_page] = "\n".join(lines)
    return pages


def find_heading(text: str, term_name: str) -> re.Match[str] | None:
    escaped = re.escape(term_name)
    flexible = escaped.replace(r"\ ", r"[\s·]*")
    flexible = flexible.replace("'", "['’]")
    compact = re.escape(term_name.replace(" ", ""))
    patterns = [
        rf"(?m)^{escaped}\s*$",
        rf"(?m)^{flexible}\s*$",
        rf"(?m)^{compact}\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match
    return None


def split_related_terms(definition: str) -> tuple[str, list[str]]:
    marker = "연관검색어"
    if marker not in definition:
        return normalize_text(definition), []

    body, related = definition.split(marker, 1)
    related = normalize_text(related)
    related_terms = [
        normalize_term(item)
        for item in re.split(r",|ㆍ|，", related)
        if normalize_term(item)
    ]
    return normalize_text(body), related_terms


def build_records(entries: list[TocEntry], pages: dict[int, str]) -> tuple[list[EconomicTerm], list[SkippedTerm]]:
    records: list[EconomicTerm] = []
    skipped: list[SkippedTerm] = []

    for index, entry in enumerate(entries):
        next_entry = entries[index + 1] if index + 1 < len(entries) else None
        candidate_pages = [pages.get(page, "") for page in range(entry.source_page, min(entry.source_page + 3, 406))]
        text = "\n".join(candidate_pages)

        start = find_heading(text, entry.term_name)
        if not start:
            skipped.append(SkippedTerm(entry.term_name, entry.source_page, "heading_not_found"))
            continue

        content_start = start.end()
        content_end = len(text)
        if next_entry:
            next_match = find_heading(text[content_start:], next_entry.term_name)
            if next_match:
                content_end = content_start + next_match.start()

        definition, related_terms = split_related_terms(text[content_start:content_end])
        if len(definition) < 20:
            skipped.append(SkippedTerm(entry.term_name, entry.source_page, "definition_too_short"))
            continue

        records.append(
            EconomicTerm(
                term_name=entry.term_name,
                official_definition=definition,
                source_name=SOURCE_NAME,
                source_page=entry.source_page,
                related_terms=related_terms,
            )
        )

    return records, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=Path("data/processed/extraction_report.json"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    reader = PdfReader(str(args.input))
    entries = parse_toc(reader)
    if args.limit:
        entries = entries[: args.limit]

    pages = extract_body_pages(reader)
    records, skipped = build_records(entries, pages)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "source_file": str(args.input),
                "toc_entries": len(entries),
                "records": len(records),
                "skipped": [asdict(term) for term in skipped],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"toc_entries={len(entries)}")
    print(f"records={len(records)}")
    print(f"skipped={len(skipped)}")
    print(f"output={args.output}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
