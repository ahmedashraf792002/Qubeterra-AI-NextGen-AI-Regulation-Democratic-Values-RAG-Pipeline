"""
Retrieval interface for the AI Regulations & Democratic Values
knowledge base.

Strategy: basic vector similarity search (cosine, via pgvector inner
product on normalized embeddings), with optional metadata filtering
(category / content_quality). This is the right starting strategy for
this domain because:

  - The corpus is small-to-medium (hundreds to low thousands of
    chunks), where a plain HNSW vector search is fast and doesn't
    need re-ranking to stay accurate.
  - Chunk boundaries already follow document structure (Section 7),
    so each retrievable unit is already a coherent, self-contained
    piece of meaning — vector similarity alone tends to work well
    when chunks aren't arbitrary slices.
  - Metadata filtering (e.g. "official EU sources only") covers the
    main precision need for this domain (jurisdiction / source type)
    without the complexity of a hybrid BM25+vector setup.

Limitations (documented per the assignment's requirement):
  - Pure vector search can under-rank exact keyword/number matches
    (e.g. a specific Article number or a defined legal term) if the
    chunk's overall semantic content is less "on topic" than a
    keyword match would suggest. A hybrid (vector + keyword) approach
    would address this and is a reasonable extension.
  - No cross-encoder re-ranking step; results are ordered purely by
    the bi-encoder similarity score from the initial search.

Interface (see Section 22 / Week 2 handoff):
  Input:  a natural-language query string, optional top_k, optional
          category filter.
  Output: a list of ranked results, each with chunk text, source
          (url/title/document_id), and a similarity score.
  Access: Python function `retrieve()`, importable directly, or CLI
          (`python retrieve.py "query text"`).

Example:
  >>> from retrieve import retrieve
  >>> results = retrieve("What are the transparency obligations for high-risk AI systems?", top_k=5)
  >>> results[0]["text"], results[0]["similarity"], results[0]["url"]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "db"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "embeddings"))

from generate_embeddings import (  
    EMBEDDING_MODEL_NAME,
    QUERY_INSTRUCTION_PREFIX,
)

DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))

SEARCH_SQL = """
SELECT
    chunk_id,
    document_id,
    structural_label,
    text,
    url,
    title,
    source,
    category,
    content_quality,
    (embedding <#> %(query_vector)s::vector) * -1 AS similarity
FROM chunks
WHERE (%(category)s::text IS NULL OR category = %(category)s)
ORDER BY embedding <#> %(query_vector)s::vector
LIMIT %(top_k)s;
"""

_model_cache = None  

def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "ai_reg_rag"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )

def _get_model():
    global _model_cache

    if _model_cache is None:
        from sentence_transformers import SentenceTransformer
        _model_cache = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model_cache


def embed_query(query: str) -> list[float]:
    """
    Embed a natural-language query for retrieval.

    IMPORTANT: BGE models require a different instruction prefix for
    queries than for the documents/chunks they're compared against
    (see generate_embeddings.py). Using the wrong prefix — or none —
    measurably degrades retrieval quality, so this is applied here
    unconditionally rather than left to the caller.
    """

    model = _get_model()
    prefixed_query = QUERY_INSTRUCTION_PREFIX + query

    vector = model.encode(prefixed_query, normalize_embeddings=True)

    return vector.tolist()


def to_pgvector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    category: str | None = None,
) -> list[dict]:
    """
    Run a natural-language query against the knowledge base and
    return ranked, source-attributed chunks.

    Parameters
    ----------
    query:
        Natural-language question or search text.
    top_k:
        Number of ranked results to return.
    category:
        Optional exact-match filter on the `category` column
        (e.g. "official_eu"). None means no filtering.

    Returns
    -------
    A list of dicts, each containing at minimum:
        chunk_id, document_id, structural_label, text,
        url, title, source, category, content_quality, similarity
    ordered by similarity descending (most relevant first).
    """

    if not query or not query.strip():
        raise ValueError("Query must be a non-empty string.")

    query_vector = embed_query(query)
    query_vector_literal = to_pgvector_literal(query_vector)

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(SEARCH_SQL, {
                "query_vector": query_vector_literal,
                "category": category,
                "top_k": top_k,
            })
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

    finally:
        conn.close()

    results = [dict(zip(columns, row)) for row in rows]

    return results


# ============================================================
# CLI
# ============================================================

def _print_results(results: list[dict]) -> None:
    if not results:
        print("No results found.")
        return

    for rank, result in enumerate(results, start=1):
        print(f"\n[{rank}] similarity={result['similarity']:.4f} "
              f"| {result['chunk_id']} | {result.get('structural_label') or ''}")
        print(f"    Source: {result.get('title') or '(no title)'} — {result.get('url') or 'N/A'}")
        if result.get("content_quality") == "low":
            print("    [NOTE] Source flagged as low content quality during collection.")
        snippet = result["text"][:300]
        print(f"    {snippet}{'...' if len(result['text']) > 300 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query the AI Regulations & Democratic Values knowledge base."
    )
    parser.add_argument("query", type=str, help="Natural-language query.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                         help=f"Number of results to return (default: {DEFAULT_TOP_K}).")
    parser.add_argument("--category", type=str, default=None,
                         help="Optional category filter (e.g. official_eu).")
    parser.add_argument("--json", action="store_true",
                         help="Print raw JSON instead of formatted output.")

    args = parser.parse_args()

    results = retrieve(args.query, top_k=args.top_k, category=args.category)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"Query: {args.query!r}  (top_k={args.top_k}, category={args.category})")
        _print_results(results)


if __name__ == "__main__":
    main()