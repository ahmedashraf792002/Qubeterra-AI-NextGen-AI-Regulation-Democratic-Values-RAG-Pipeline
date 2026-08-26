"""
Data collection pipeline for the AI Regulations & Democratic Values
knowledge domain.

The pipeline:
1. Reads seed URLs from seed_urls.py.
2. Fetches web pages.
3. Extracts clean textual content.
4. Discovers additional links from the same domain.
5. Saves collected documents as JSON files (document_01.json, document_02.json, ...).
6. Preserves source metadata for downstream RAG processing.

The collector is intentionally repeatable and can be re-run safely:
re-running does NOT create duplicate files for URLs already collected —
each URL keeps the same sequential document number across runs.
"""

import argparse
import hashlib
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "test" / "collection"))
from seed_urls import SEED_URLS

# Configuration — read from .env

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0 Safari/537.36 "
    "Qubeterra-AI-NextGen-RAG/1.0"
)

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

DEFAULT_CRAWL_DEPTH = int(os.getenv("CRAWL_DEPTH", "1"))

DEFAULT_MAX_DOCUMENTS = int(os.getenv("MAX_DOCUMENTS", "60"))

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))

MIN_ACCEPTABLE_CHARS = int(os.getenv("MIN_ACCEPTABLE_CHARS", "200"))
MIN_QUALITY_CHARS = int(os.getenv("MIN_QUALITY_CHARS", "500"))

DOCUMENT_NAME_PREFIX = os.getenv("DOCUMENT_NAME_PREFIX", "document_")
DOCUMENT_NAME_DIGITS = int(os.getenv("DOCUMENT_NAME_DIGITS", "2"))

# URL utilities

def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and trailing whitespace."""

    url, _ = urldefrag(url.strip())

    if url.endswith("/"):
        url = url[:-1]

    return url


def is_http_url(url: str) -> bool:
    """Return True if the URL uses HTTP or HTTPS."""

    return urlparse(url).scheme in {"http", "https"}


def is_same_domain(url: str, seed_url: str) -> bool:
    """Check whether two URLs belong to the same domain."""

    url_domain = urlparse(url).netloc.lower().replace("www.", "")
    seed_domain = urlparse(seed_url).netloc.lower().replace("www.", "")

    return url_domain == seed_domain


def is_probably_document(url: str) -> bool:
    """
    Ignore files that are unlikely to contain HTML knowledge content.
    """

    blocked_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".css",
        ".js",
        ".zip",
        ".mp4",
        ".mp3",
        ".avi",
        ".mov",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }

    path = urlparse(url).path.lower()

    return not any(path.endswith(ext) for ext in blocked_extensions)


# Text extraction

def clean_text(text: str) -> str:
    """Normalize extracted text."""

    text = text.replace("\xa0", " ")

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text.strip()


def extract_content(html: str, url: str) -> tuple[str, str]:
    """
    Extract title and main textual content from HTML.

    Trafilatura is preferred because it removes much of the
    navigation and boilerplate commonly found on web pages.
    """

    title = ""

    soup = BeautifulSoup(html, "html.parser")

    if soup.title:
        title = soup.title.get_text(" ", strip=True)

    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_links=False,
        favor_precision=True,
    )

    if not text:
        text = soup.get_text("\n", strip=True)

    text = clean_text(text)

    return title, text


# Document identity (URL hash) vs. Document naming (sequential)

def generate_url_hash(url: str) -> str:
    """Generate a short stable fingerprint for a URL (identity check only)."""

    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def format_document_id(number: int) -> str:
    """Format a sequential document number as 'document_01', etc."""

    return f"{DOCUMENT_NAME_PREFIX}{number:0{DOCUMENT_NAME_DIGITS}d}"


def build_existing_index() -> tuple[dict[str, str], int]:
    """
    Scan data/raw for previously saved documents and build:

    - a mapping of {url_hash: document_id} so re-runs reuse the same
      sequential name for URLs already collected.
    - the highest sequential number already used, so new documents
      continue counting up from there.
    """

    url_hash_to_document_id: dict[str, str] = {}
    highest_number = 0

    if not RAW_DATA_DIR.exists():
        return url_hash_to_document_id, highest_number

    for path in RAW_DATA_DIR.glob(f"{DOCUMENT_NAME_PREFIX}*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                existing = json.load(file)
        except (json.JSONDecodeError, OSError):
            continue

        document_id = existing.get("document_id", path.stem)
        url_hash = existing.get("url_hash")

        if url_hash:
            url_hash_to_document_id[url_hash] = document_id

        match = re.fullmatch(rf"{DOCUMENT_NAME_PREFIX}(\d+)", document_id)
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return url_hash_to_document_id, highest_number

# HTTP fetching

def fetch_page(session: requests.Session, url: str) -> str | None:
    """Download a web page and return its HTML."""

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )

        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        if "text/html" not in content_type and "application/xhtml" not in content_type:
            print(f"[SKIP] Not HTML: {url}")
            return None

        return response.text

    except requests.RequestException as exc:
        print(f"[ERROR] Failed to fetch {url}")
        print(f"{exc}")

        return None

# Link discovery

def discover_links(
    html: str,
    current_url: str,
    seed_url: str,
) -> list[str]:
    """
    Discover additional links from the current page.

    Only links from the same domain as the seed URL are returned.
    """

    soup = BeautifulSoup(html, "html.parser")

    discovered = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if not href:
            continue

        absolute_url = urljoin(current_url, href)

        absolute_url = normalize_url(absolute_url)

        if not is_http_url(absolute_url):
            continue

        if not is_same_domain(absolute_url, seed_url):
            continue

        if not is_probably_document(absolute_url):
            continue

        discovered.add(absolute_url)

    return sorted(discovered)


# Saving documents

def save_document(document: dict) -> Path:
    """Save one document as JSON, named by its sequential document_id."""

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    document_id = document["document_id"]

    output_path = RAW_DATA_DIR / f"{document_id}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path

# Main collection pipeline

def collect_documents(
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
    crawl_depth: int = DEFAULT_CRAWL_DEPTH,
) -> int:
    """
    Collect documents from the configured seed URLs.

    Parameters
    ----------
    max_documents:
        Maximum number of documents to collect.

    crawl_depth:
        Number of link-discovery levels to follow from each seed.
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    # Load existing url_hash -> document_id mapping so re-runs are stable.
    url_hash_to_document_id, next_number = build_existing_index()

    # Queue contains:
    # (url, category, seed_url, depth)
    queue = deque()

    for seed_url, category in SEED_URLS:
        seed_url = normalize_url(seed_url)

        queue.append(
            (
                seed_url,
                category,
                seed_url,
                0,
            )
        )

    visited: set[str] = set()

    saved_documents = 0

    low_quality_documents: list[str] = []

    print("=" * 70)
    print("Qubeterra AI NextGen - Data Collection")
    print("Domain: AI Regulations & Democratic Values")
    print("=" * 70)

    print(f"Seed URLs       : {len(SEED_URLS)}")
    print(f"Maximum docs    : {max_documents}")
    print(f"Crawl depth     : {crawl_depth}")
    print(f"Output directory: {RAW_DATA_DIR}")
    print(f"Existing docs   : {len(url_hash_to_document_id)} (resuming numbering)")
    print("=" * 70)

    while queue and saved_documents < max_documents:

        url, category, seed_url, depth = queue.popleft()

        url = normalize_url(url)

        if url in visited:
            continue

        visited.add(url)

        print(
            f"\n[{saved_documents + 1}/{max_documents}] "
            f"Depth={depth} | {url}"
        )

        url_hash = generate_url_hash(url)

        html = fetch_page(session, url)

        if not html:
            continue

        title, text = extract_content(html, url)

        # Ignore pages with almost no useful textual content at all
        if len(text) < MIN_ACCEPTABLE_CHARS:
            print(
                f"[SKIP] Not enough textual content "
                f"({len(text)} chars < {MIN_ACCEPTABLE_CHARS})."
            )
            continue

        # Flag (but keep) documents that are thin — likely partial
        # extraction (JS-heavy page, tabs/accordions, etc.) rather than
        # a genuinely short source.
        is_low_quality = len(text) < MIN_QUALITY_CHARS

        if is_low_quality:
            print(
                f"[WARNING] Low content length: {len(text)} chars "
                f"(< {MIN_QUALITY_CHARS}). Saved but flagged as low quality."
            )
            low_quality_documents.append(url)

        # Reuse the existing sequential ID if this URL was already
        # collected in a previous run; otherwise assign the next one.
        if url_hash in url_hash_to_document_id:
            document_id = url_hash_to_document_id[url_hash]
            print(f"        Reusing existing ID: {document_id}")
        else:
            next_number += 1
            document_id = format_document_id(next_number)
            url_hash_to_document_id[url_hash] = document_id

        document = {
            "document_id": document_id,
            "url": url,
            "url_hash": url_hash,
            "source": urlparse(url).netloc,
            "title": title,
            "text": text,
            "category": category,
            "crawl_depth": depth,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "domain": "AI Regulations & Democratic Values",
            "char_count": len(text),
            "content_quality": "low" if is_low_quality else "ok",
        }

        output_path = save_document(document)

        saved_documents += 1

        print(f"[SAVED] {output_path.name}")
        print(f"        Title: {title[:100]}")
        print(f"        Characters: {len(text)}")

        # Discover more links

        if depth < crawl_depth:

            links = discover_links(
                html=html,
                current_url=url,
                seed_url=seed_url,
            )

            print(f"Discovered links: {len(links)}")

            for link in links:

                if link not in visited:
                    queue.append(
                        (
                            link,
                            category,
                            seed_url,
                            depth + 1,
                        )
                    )

        time.sleep(REQUEST_DELAY)

    session.close()

    print("\n" + "=" * 70)
    print("Collection completed")
    print("=" * 70)
    print(f"Documents collected: {saved_documents}")
    print(f"URLs visited      : {len(visited)}")
    print(f"Output directory   : {RAW_DATA_DIR}")
    print("=" * 70)

    total_on_disk = len(list(RAW_DATA_DIR.glob(f"{DOCUMENT_NAME_PREFIX}*.json")))

    if total_on_disk >= 50:
        print(f"[SUCCESS] Minimum requirement of 50 raw documents satisfied ({total_on_disk} on disk).")
    else:
        print(
            f"[WARNING] Only {total_on_disk} documents on disk. "
            "The project requires at least 50."
        )

    if low_quality_documents:
        print(
            f"\n[QUALITY] {len(low_quality_documents)} document(s) saved with "
            f"content_quality='low' (< {MIN_QUALITY_CHARS} chars). "
            "Review these before/during cleaning:"
        )
        for flagged_url in low_quality_documents:
            print(f"          - {flagged_url}")
    else:
        print("\n[QUALITY] No low-quality documents flagged this run.")

    print("=" * 70)

    return saved_documents


# ============================================================
# CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect raw documents for the Qubeterra RAG pipeline."
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=DEFAULT_MAX_DOCUMENTS,
        help="Maximum number of documents to collect.",
    )

    parser.add_argument(
        "--crawl-depth",
        type=int,
        default=DEFAULT_CRAWL_DEPTH,
        help="Number of link-discovery levels.",
    )

    args = parser.parse_args()

    collect_documents(
        max_documents=args.max_documents,
        crawl_depth=args.crawl_depth,
    )


if __name__ == "__main__":
    main()