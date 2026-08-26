"""
Run all 7 pipeline steps sequentially.

Usage:
    uv run python test/run_all_steps.py
    uv run python test/run_all_steps.py --steps 1,2,3,4,5,6,7
    uv run python test/run_all_steps.py --query "What is Article 5?"
"""

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env", override=True)

sys.path.insert(0, str(PROJECT_ROOT / "src" / "collection"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "preprocessing"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "chunking"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "embeddings"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "storage"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "retrieval"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "evaluation"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "collection"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "evaluation"))

STEPS = {
    1: ("Collection", "src/collection/data_collection.py"),
    2: ("Preprocessing", "src/preprocessing/clean_documents.py"),
    3: ("Chunking", "src/chunking/chunk_documents.py"),
    4: ("Embeddings", "src/embeddings/generate_embeddings.py"),
    5: ("Storage", "src/storage/load_to_postgres.py"),
    6: ("Retrieval", "src/retrieval/retrieve.py"),
    7: ("Evaluation", "src/evaluation/run_evaluation.py"),
}


def step_1_collection():
    from data_collection import collect_documents
    collect_documents()


def step_2_preprocessing():
    from clean_documents import clean_documents
    clean_documents()


def step_3_chunking():
    from chunk_documents import chunk_documents
    chunk_documents()


def step_4_embeddings():
    from generate_embeddings import generate_embeddings
    generate_embeddings()


def step_5_storage():
    from load_to_postgres import load_to_postgres
    load_to_postgres()


def step_6_retrieval(query: str = "What are the transparency obligations for high-risk AI systems?"):
    from retrieve import retrieve
    results = retrieve(query, top_k=5)
    print(f"\nQuery: {query!r}")
    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r['similarity']:.4f} | {r['chunk_id']}")
        print(f"      {r['text'][:120]}...")


def step_7_evaluation():
    from run_evaluation import main
    main()


STEP_FUNCTIONS = {
    1: step_1_collection,
    2: step_2_preprocessing,
    3: step_3_chunking,
    4: step_4_embeddings,
    5: step_5_storage,
    6: step_6_retrieval,
    7: step_7_evaluation,
}


def main():
    parser = argparse.ArgumentParser(description="Run all pipeline steps.")
    parser.add_argument("--steps", type=str, default="1,2,3,4,5,6,7",
                        help="Comma-separated step numbers (default: all)")
    parser.add_argument("--query", type=str, default=None,
                        help="Query for retrieval step")
    args = parser.parse_args()

    steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]

    print("=" * 70)
    print("Qubeterra AI NextGen — Full Pipeline (7 Steps)")
    print(f"Steps: {', '.join(str(s) for s in steps)}")
    for s in steps:
        name, file = STEPS[s]
        print(f"  {s}. {name:20s} ({file})")
    print("=" * 70)

    total_start = time.time()

    for step_num in steps:
        if step_num not in STEPS:
            print(f"[ERROR] Unknown step: {step_num}")
            sys.exit(1)

        name, _ = STEPS[step_num]
        print(f"\n{'=' * 70}")
        print(f"  STEP {step_num}: {name.upper()}")
        print(f"{'=' * 70}\n")

        start = time.time()

        if step_num == 6 and args.query:
            STEP_FUNCTIONS[step_num](args.query)
        else:
            STEP_FUNCTIONS[step_num]()

        elapsed = time.time() - start
        print(f"\n[{name}] Done in {elapsed:.1f}s")

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE COMPLETE — {len(steps)} steps in {total_elapsed:.1f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
