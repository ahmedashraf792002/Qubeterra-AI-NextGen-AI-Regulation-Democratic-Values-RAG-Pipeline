"""
Run the data collection pipeline.

Usage:
    uv run python test/collection/run.py
    uv run python test/collection/run.py --max-documents 10 --crawl-depth 1
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "collection"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_collection import collect_documents

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test: Run data collection.")
    parser.add_argument("--max-documents", type=int, default=int(os.getenv("MAX_DOCUMENTS", "60")))
    parser.add_argument("--crawl-depth", type=int, default=int(os.getenv("CRAWL_DEPTH", "1")))
    args = parser.parse_args()

    collect_documents(max_documents=args.max_documents, crawl_depth=args.crawl_depth)
