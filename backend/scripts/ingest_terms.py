"""Generate embeddings and upsert economic terms into Supabase.

This script reads `data/processed/economic_terms.json`, creates OpenAI embeddings,
and writes rows to the `economic_terms` table created by the Supabase migration.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("data/processed/economic_terms.json")
DEFAULT_BATCH_SIZE = 50


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required in .env")
    return value


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def post_json(url: str, headers: dict[str, str], payload: Any) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed: HTTP {error.code} {message}") from error


def create_embeddings(
    terms: list[dict[str, Any]],
    api_key: str,
    model: str,
    batch_size: int,
) -> list[list[float]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    embeddings: list[list[float]] = []

    batches = chunked(terms, batch_size)
    for batch_index, batch in enumerate(batches, start=1):
        inputs = [
            f"용어명: {term['term_name']}\n공식 정의: {term['official_definition']}"
            for term in batch
        ]
        response = post_json(
            "https://api.openai.com/v1/embeddings",
            headers,
            {"model": model, "input": inputs},
        )
        embeddings.extend(item["embedding"] for item in response["data"])
        print(f"embedded batch {batch_index}/{len(batches)} ({len(embeddings)}/{len(terms)})")
        time.sleep(0.2)

    return embeddings


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def upsert_terms(
    terms: list[dict[str, Any]],
    embeddings: list[list[float]],
    supabase_url: str,
    service_role_key: str,
    batch_size: int,
) -> None:
    endpoint = f"{supabase_url.rstrip('/')}/rest/v1/economic_terms?on_conflict=term_name"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    rows = []
    for term, embedding in zip(terms, embeddings, strict=True):
        rows.append(
            {
                "term_name": term["term_name"],
                "official_definition": term["official_definition"],
                "source_name": term["source_name"],
                "source_page": term["source_page"],
                "related_terms": term.get("related_terms", []),
                "embedding": vector_literal(embedding),
            }
        )

    batches = chunked(rows, batch_size)
    for batch_index, batch in enumerate(batches, start=1):
        post_json(endpoint, headers, batch)
        print(f"upserted batch {batch_index}/{len(batches)} ({min(batch_index * batch_size, len(rows))}/{len(rows)})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    load_dotenv(Path(".env"))
    load_dotenv(Path("../.env"))

    openai_api_key = require_env("OPENAI_API_KEY")
    supabase_url = require_env("SUPABASE_URL")
    service_role_key = require_env("SUPABASE_SERVICE_ROLE_KEY")
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    terms = json.loads(args.input.read_text(encoding="utf-8"))
    if args.limit:
        terms = terms[: args.limit]

    print(f"loaded terms={len(terms)}")
    embeddings = create_embeddings(terms, openai_api_key, embedding_model, args.batch_size)
    upsert_terms(terms, embeddings, supabase_url, service_role_key, args.batch_size)
    print("done")


if __name__ == "__main__":
    main()
