"""
Run the chunking pipeline.

Usage:
    uv run python test/chunking/run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "chunking"))

from chunk_documents import chunk_documents

if __name__ == "__main__":
    chunk_documents()
