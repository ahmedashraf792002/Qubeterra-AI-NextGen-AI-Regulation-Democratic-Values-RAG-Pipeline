"""
Run the storage pipeline (load chunks + embeddings into PostgreSQL).

Usage:
    uv run python test/storage/run.py
    uv run python test/storage/run.py --batch-size 100
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "storage"))

from load_to_postgres import load_to_postgres

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test: Load into PostgreSQL.")
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    load_to_postgres(batch_size=args.batch_size)
