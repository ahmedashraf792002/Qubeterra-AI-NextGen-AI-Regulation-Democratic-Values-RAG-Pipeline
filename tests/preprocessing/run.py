"""
Run the cleaning/preprocessing pipeline.

Usage:
    uv run python test/preprocessing/run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "preprocessing"))

from clean_documents import clean_documents

if __name__ == "__main__":
    clean_documents()
