"""
Storage stage for the AI Regulations & Democratic Values RAG pipeline.

Joins data/chunks/chunks.jsonl (text + structural/source metadata) with
data/embeddings/embeddings.jsonl (vectors, keyed by chunk_id) and loads
the result into PostgreSQL using pgvector.

Schema
------
One row per chunk. The embedding column width is NOT hardcoded to 768:
it's read from the actual embeddings on disk at load time, so the
script fails loudly instead of silently corrupting data if the
embedding model (and therefore its dimensionality) ever changes.

Idempotency
-----------
Uses `INSERT ... ON CONFLICT (chunk_id) DO UPDATE`, so re-running this
script after re-chunking or re-embedding safely upserts rather than
duplicating or requiring a manual DROP TABLE first.

Configuration
-------------
Reads connection info from environment variables (see .env.example):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Usage:
    uv run python src/storage/load_to_postgres.py
    uv run python src/storage/load_to_postgres.py --batch-size 200
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "embeddings" / "embeddings.jsonl"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

TABLE_NAME = "chunks"


class StorageError(Exception):
    """Raised for unrecoverable data or configuration problems."""


# ============================================================
# Config
# ============================================================

def get_connection_string() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ai_reg_rag")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")

    if not password:
        logger.warning(
            "POSTGRES_PASSWORD is empty — set it in your .env file "
            "(copy .env.example to .env if you haven't already)."
        )

    return f"host={host} port={port} dbname={db} user={user} password={password}"


# ============================================================
# Load + join input files
# ============================================================

def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")

    records = []
    with path.open("r", encoding="utf-8") as file:
        for line_num, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed line %d in %s: %s", line_num, path.name, exc)
    return records


def join_chunks_and_embeddings(chunks: list[dict], embeddings: list[dict]) -> list[dict]:
    """
    Join on chunk_id. Chunks with no matching embedding (not yet
    embedded, or embedding failed) are reported and skipped rather
    than inserted with a NULL vector, which would silently break
    similarity search for that row.
    """
    embeddings_by_id = {e["chunk_id"]: e for e in embeddings}

    joined = []
    missing_embedding = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        embedding_record = embeddings_by_id.get(chunk_id)
        if embedding_record is None:
            missing_embedding.append(chunk_id)
            continue
        joined.append({**chunk, **embedding_record})

    if missing_embedding:
        logger.warning(
            "%d chunk(s) have no matching embedding and will be skipped "
            "(run generate_embeddings.py first, or check for failures):",
            len(missing_embedding),
        )
        for cid in missing_embedding[:10]:
            logger.warning("  - %s", cid)
        if len(missing_embedding) > 10:
            logger.warning("  ... and %d more", len(missing_embedding) - 10)

    return joined


def determine_dimension(joined_records: list[dict]) -> int:
    dimensions = {r["embedding_dim"] for r in joined_records}
    if len(dimensions) > 1:
        raise StorageError(
            f"Embeddings have inconsistent dimensions in the input data: {dimensions}. "
            f"This means embeddings were generated with more than one model/run — "
            f"re-generate them consistently before loading into a fixed-width vector column."
        )
    if not dimensions:
        raise StorageError("No records to load — nothing to determine dimension from.")
    return dimensions.pop()


# ============================================================
# Schema
# ============================================================

def ensure_schema(conn: psycopg.Connection, dimension: int) -> None:
    """
    Schema lives in sql/schema.sql, not inline in this file — this
    function just reads it and substitutes the actual embedding
    dimension (determined from the data at load time, see
    determine_dimension) into the `vector({dimension})` placeholder.
    """
    if not SCHEMA_PATH.exists():
        raise StorageError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_sql = schema_sql.replace("{dimension}", str(dimension))

    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()


# ============================================================
# Load
# ============================================================

def load_records(conn: psycopg.Connection, records: list[dict], batch_size: int) -> int:
    upsert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            chunk_id, document_id, chunk_index, structural_label, text,
            char_count, url, title, source, category, domain,
            content_quality, embedding_model, embedding
        ) VALUES (
            %(chunk_id)s, %(document_id)s, %(chunk_index)s, %(structural_label)s, %(text)s,
            %(char_count)s, %(url)s, %(title)s, %(source)s, %(category)s, %(domain)s,
            %(content_quality)s, %(embedding_model)s, %(embedding)s
        )
        ON CONFLICT (chunk_id) DO UPDATE SET
            document_id      = EXCLUDED.document_id,
            chunk_index      = EXCLUDED.chunk_index,
            structural_label = EXCLUDED.structural_label,
            text             = EXCLUDED.text,
            char_count       = EXCLUDED.char_count,
            url              = EXCLUDED.url,
            title            = EXCLUDED.title,
            source           = EXCLUDED.source,
            category         = EXCLUDED.category,
            domain           = EXCLUDED.domain,
            content_quality  = EXCLUDED.content_quality,
            embedding_model  = EXCLUDED.embedding_model,
            embedding        = EXCLUDED.embedding;
    """

    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            params = [
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "chunk_index": r.get("chunk_index"),
                    "structural_label": r.get("structural_label"),
                    "text": r["text"],
                    "char_count": r.get("char_count", len(r["text"])),
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "source": r.get("source"),
                    "category": r.get("category"),
                    "domain": r.get("domain"),
                    "content_quality": r.get("content_quality"),
                    "embedding_model": r.get("embedding_model"),
                    "embedding": str(r["embedding"]),  # pgvector accepts '[0.1,0.2,...]' text form
                }
                for r in batch
            ]
            cur.executemany(upsert_sql, params)
            total += len(batch)
            logger.info("Loaded %d/%d rows", total, len(records))
    conn.commit()
    return total


# ============================================================
# Verification
# ============================================================

def verify(conn: psycopg.Connection, expected_count: int, dimension: int) -> None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM {TABLE_NAME};")
        actual_count = cur.fetchone()["n"]

        cur.execute(f"""
            SELECT vector_dims(embedding) AS dims
            FROM {TABLE_NAME}
            LIMIT 1;
        """)
        row = cur.fetchone()
        actual_dim = row["dims"] if row else None

        # Sanity-check the index is actually usable for similarity search:
        # query with an arbitrary row's own embedding and confirm it comes
        # back as its own nearest neighbor (distance ~0).
        cur.execute(f"SELECT chunk_id, embedding FROM {TABLE_NAME} LIMIT 1;")
        sample = cur.fetchone()
        self_match = None
        if sample:
            cur.execute(
                f"""
                SELECT chunk_id, embedding <=> %(vec)s AS distance
                FROM {TABLE_NAME}
                ORDER BY embedding <=> %(vec)s
                LIMIT 1;
                """,
                {"vec": str(sample["embedding"])},
            )
            top = cur.fetchone()
            self_match = top["chunk_id"] == sample["chunk_id"]

    print(f"Rows in table          : {actual_count} (expected {expected_count})")
    print(f"Vector dimensionality   : {actual_dim} (expected {dimension})")
    print(f"Self-similarity sanity  : {'OK' if self_match else 'FAILED'} "
          f"(a row's own embedding should retrieve itself as nearest neighbor)")

    if actual_count != expected_count:
        print("[WARNING] Row count does not match expected — investigate before proceeding.")
    if actual_dim != dimension:
        print("[WARNING] Stored dimension does not match embeddings on disk — investigate.")
    if not self_match:
        print("[WARNING] Self-similarity check failed — the vector index or data may be corrupt.")
    if actual_count == expected_count and actual_dim == dimension and self_match:
        print("[CHECK] Storage verified: row count, dimensionality, and index all OK.")


# ============================================================
# Main
# ============================================================

def load_to_postgres(batch_size: int = 200) -> None:
    print("=" * 70)
    print("PostgreSQL + pgvector Storage")
    print("=" * 70)

    chunks = load_jsonl(CHUNKS_PATH)
    embeddings = load_jsonl(EMBEDDINGS_PATH)
    print(f"Chunks on disk     : {len(chunks)}")
    print(f"Embeddings on disk : {len(embeddings)}")

    joined = join_chunks_and_embeddings(chunks, embeddings)
    if not joined:
        raise StorageError("No chunks have matching embeddings — nothing to load.")

    dimension = determine_dimension(joined)
    print(f"Embedding dimension (from data): {dimension}")

    conn_str = get_connection_string()
    with psycopg.connect(conn_str) as conn:
        ensure_schema(conn, dimension)
        print(f"\nSchema ready (table '{TABLE_NAME}', pgvector extension enabled).")

        loaded = load_records(conn, joined, batch_size)
        print(f"\nRows upserted: {loaded}")

        print("\n--- Verification ---")
        verify(conn, expected_count=len(joined), dimension=dimension)

    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load chunks + embeddings into PostgreSQL/pgvector.")
    parser.add_argument("--batch-size", type=int, default=200, help="Rows per INSERT batch.")
    args = parser.parse_args()

    load_to_postgres(batch_size=args.batch_size)


if __name__ == "__main__":
    main()