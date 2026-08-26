"""
Run the retrieval pipeline with a test query.

Usage:
    uv run python test/retrieval/run.py
    uv run python test/retrieval/run.py --query "What is Article 5?" --top-k 3
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "embeddings"))

from retrieve import retrieve

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test: Run retrieval query.")
    parser.add_argument("--query", type=str, default="What are the transparency obligations for high-risk AI systems?")
    parser.add_argument("--top-k", type=int, default=int(os.getenv("DEFAULT_TOP_K", "5")))
    parser.add_argument("--category", type=str, default=None)
    args = parser.parse_args()

    results = retrieve(args.query, top_k=args.top_k, category=args.category)

    print(f"\nQuery: {args.query!r}  (top_k={args.top_k}, category={args.category})")
    print(f"Results: {len(results)}\n")

    for i, r in enumerate(results, 1):
        print(f"[{i}] similarity={r['similarity']:.4f} | {r['chunk_id']}")
        print(f"    {r.get('title', '')} — {r.get('url', '')}")
        print(f"    {r['text'][:200]}...\n")
