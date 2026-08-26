"""
Run retrieval evaluation.

Usage:
    uv run python test/evaluation/run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "evaluation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "embeddings"))

from run_evaluation import main

if __name__ == "__main__":
    main()
