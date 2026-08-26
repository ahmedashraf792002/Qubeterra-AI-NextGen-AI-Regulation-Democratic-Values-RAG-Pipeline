import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

EVAL_TOP_K = int(os.getenv("EVAL_TOP_K", "5"))
