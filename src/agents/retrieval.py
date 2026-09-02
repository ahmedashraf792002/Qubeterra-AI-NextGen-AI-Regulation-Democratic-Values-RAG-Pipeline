"""Retrieval — interface to Week 1 knowledge base."""

import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Add retrieval module to path
_RETRIEVAL_DIR = Path(__file__).resolve().parents[2] / "src" / "retrieval"
if str(_RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_RETRIEVAL_DIR))


def _test_db_connection():
    """Try to connect to PostgreSQL. Returns True if successful."""
    import psycopg
    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "ai_reg_rag"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        connect_timeout=3,
    )
    conn.close()
    return True


class Retrieval:
    def __init__(self):
        self.available = False
        self._retrieve = None
        try:
            from retrieve import retrieve
            self._retrieve = retrieve
            # Test DB connection with timeout (non-blocking on Windows)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_test_db_connection)
                future.result(timeout=5)
            self.available = True
        except Exception:
            self.available = False

    def search(self, query, top_k=5, category=None):
        """Search the knowledge base. Returns list of result dicts."""
        if not self.available:
            return [{"chunk_id": "N/A", "text": f"Retrieval unavailable for: {query}",
                      "title": "N/A", "url": "", "similarity": 0}]
        return self._retrieve(query, top_k=top_k, category=category)

    def format_results(self, results):
        """Format results as readable text for prompts."""
        if not results:
            return "No relevant sources found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            text = r.get("text", "")[:500]
            sim = r.get("similarity", 0)
            lines.append(f"[{i}] {title} (relevance: {sim:.2f})\n    {url}\n    {text}")
        return "\n\n".join(lines)

    def citations(self, results):
        """Extract clean citations."""
        return [{"title": r.get("title", ""), "url": r.get("url", ""),
                 "similarity": r.get("similarity", 0)} for r in results]
