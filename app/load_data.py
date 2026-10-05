"""Load CSV (text, created_date, rubrics[, id]) into Postgres and Elasticsearch.

    python -m app.load_data data/posts.csv --recreate
"""

import argparse
import ast
import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

from elasticsearch import AsyncElasticsearch
from sqlalchemy import insert, text

from app.config import get_settings
from app.db import Document, create_tables, make_engine
from app.search import SearchIndex

csv.field_size_limit(sys.maxsize)


def parse_rubrics(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return [r.strip() for r in raw.split(",") if r.strip()]
    return [str(v) for v in value] if isinstance(value, (list, tuple)) else [str(value)]


def parse_row(row: dict) -> dict:
    doc = {
        "text": row["text"],
        "created_date": datetime.fromisoformat(row["created_date"].strip()),
        "rubrics": parse_rubrics(row.get("rubrics", "")),
    }
    if row.get("id"):
        doc["id"] = int(row["id"])
    return doc


def read_batches(path: Path, batch_size: int):
    with path.open(encoding="utf-8", newline="") as f:
        batch = []
        for row in csv.DictReader(f):
            batch.append(parse_row(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


async def load(path: Path, recreate: bool, batch_size: int) -> int:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    es = AsyncElasticsearch(settings.es_url)
    index = SearchIndex(es, settings.es_index)
    total = 0
    has_explicit_ids = False
    try:
        await create_tables(engine, drop=recreate)
        await index.ensure_index(recreate=recreate)
        for batch in read_batches(path, batch_size):
            has_explicit_ids |= any("id" in d for d in batch)
            async with engine.begin() as conn:
                rows = await conn.execute(
                    insert(Document).returning(Document.id, Document.text), batch
                )
                pairs = [(r.id, r.text) for r in rows]
            await index.index_documents(pairs)
            total += len(pairs)
            print(f"loaded {total}", flush=True)
        if has_explicit_ids:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "SELECT setval(pg_get_serial_sequence('documents', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM documents), 1))"
                ))
        await index.refresh()
    finally:
        await es.close()
        await engine.dispose()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--recreate", action="store_true", help="drop and recreate table and index")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    total = asyncio.run(load(args.csv_path, args.recreate, args.batch_size))
    print(f"done: {total} documents")


if __name__ == "__main__":
    main()
