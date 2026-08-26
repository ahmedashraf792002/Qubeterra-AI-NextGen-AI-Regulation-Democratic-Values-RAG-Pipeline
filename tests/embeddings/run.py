"""
Run the embedding generation pipeline.

Usage:
    uv run python test/embeddings/run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "embeddings"))

from generate_embeddings import generate_embeddings

if __name__ == "__main__":
    generate_embeddings()
