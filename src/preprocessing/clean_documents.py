"""
Cleaning & Preprocessing pipeline for the AI Regulations & Democratic
Values knowledge domain.

Raw documents already went through trafilatura extraction during
collection (see src/collection/data_collection.py), so most HTML
markup, scripts, and nav elements are already gone. This stage handles
what trafilatura commonly misses:

1. Unicode / whitespace / encoding normalization.
2. Corpus-level boilerplate removal: lines that appear near-verbatim
   across many documents (cookie banners, "Share on X", footers,
   breadcrumb trails, "Skip to content", newsletter prompts, etc.)
   are detected statistically and stripped, rather than relying on a
   fixed keyword blocklist.
3. Removal of leftover HTML-entity artifacts / control characters.
4. Preservation of full source traceability (raw file path, URL,
   document_id, char counts before/after).

Output: data/clean/document_XX.json (same IDs as data/raw).

Also produces a spot-check report (data/clean/spot_check_report.md)
sampling documents for manual review, per the assignment's minimum
5-document spot-check requirement.
"""

from __future__ import annotations

import html
import json
import os
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DATA_DIR = PROJECT_ROOT / "data" / "clean"

SPOT_CHECK_SAMPLE_SIZE = int(os.getenv("SPOT_CHECK_SAMPLE_SIZE", "5"))
SPOT_CHECK_SNIPPET_CHARS = int(os.getenv("SPOT_CHECK_SNIPPET_CHARS", "600"))

BOILERPLATE_LINE_FREQUENCY_THRESHOLD = float(os.getenv("BOILERPLATE_LINE_FREQUENCY_THRESHOLD", "0.25"))
BOILERPLATE_MAX_LINE_LENGTH = int(os.getenv("BOILERPLATE_MAX_LINE_LENGTH", "120"))

# Regex-based residual noise that survives trafilatura extraction.
NOISE_PATTERNS = [
    re.compile(r"^\s*(cookie|cookies)\b.*(accept|consent|preferences)\b.*$", re.IGNORECASE),
    re.compile(r"^\s*(share (this|on)|follow us on)\b.*$", re.IGNORECASE),
    re.compile(r"^\s*(subscribe to (our )?newsletter)\b.*$", re.IGNORECASE),
    re.compile(r"^\s*(skip to (main )?content)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(all rights reserved|©\s*\d{4})\b.*$", re.IGNORECASE),
    re.compile(r"^\s*(home\s*[>/|]\s*)+\S.*$", re.IGNORECASE),  # breadcrumb trails
    re.compile(r"^\s*(read more|learn more|click here)\s*[.:]?\s*$", re.IGNORECASE),
]


# ============================================================
# HTML safety net
# ============================================================
#
# The raw text should already be markup-free (trafilatura extracts
# plain text during collection), but this is not guaranteed for every
# page — some sources can leave residual tags, inline <script>/<style>
# fragments, or HTML entities behind. This is an explicit safety net
# so the cleaning stage itself satisfies the "no HTML tags / no
# script/style content" acceptance criterion, rather than trusting an
# earlier stage.

HTML_TAG_HINT = re.compile(r"</?[a-zA-Z][^>]{0,200}>")


def strip_html(text: str) -> str:
    """
    Remove any residual HTML markup, script/style content, and decode
    leftover HTML entities (e.g. &amp; -> &, &nbsp; -> space).
    """

    if not HTML_TAG_HINT.search(text):
        # No tag-like patterns found — still decode any stray entities.
        return html.unescape(text)

    soup = BeautifulSoup(text, "html.parser")

    # Drop script/style content entirely rather than keeping their text.
    for tag in soup(["script", "style"]):
        tag.decompose()

    stripped = soup.get_text("\n")

    return html.unescape(stripped)


# ============================================================
# Text normalization
# ============================================================

def normalize_unicode(text: str) -> str:
    """Normalize Unicode form and strip stray control characters."""

    text = unicodedata.normalize("NFKC", text)

    # Remove non-printable control characters (keep \n and \t for now,
    # they get normalized separately below).
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C"
    )

    return text


def normalize_whitespace(text: str) -> str:
    """Collapse repeated spaces/tabs and excessive blank lines."""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text.strip()


def strip_regex_noise(text: str) -> str:
    """Remove lines matching known residual boilerplate patterns."""

    kept_lines = []

    for line in text.split("\n"):
        if any(pattern.match(line) for pattern in NOISE_PATTERNS):
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines)


# ============================================================
# Corpus-level boilerplate detection
# ============================================================

def build_boilerplate_line_set(documents: list[dict]) -> set[str]:
    """
    Identify lines that repeat near-verbatim across a large fraction of
    documents. These are almost always template/navigation/footer
    elements rather than substantive content, since genuine article
    text rarely repeats word-for-word across unrelated sources.
    """

    line_document_counts: Counter[str] = Counter()
    total_documents = len(documents)

    for doc in documents:
        text = doc.get("text", "")
        unique_lines_in_doc = {
            line.strip()
            for line in text.split("\n")
            if line.strip() and len(line.strip()) <= BOILERPLATE_MAX_LINE_LENGTH
        }
        for line in unique_lines_in_doc:
            line_document_counts[line] += 1

    threshold_count = max(2, int(total_documents * BOILERPLATE_LINE_FREQUENCY_THRESHOLD))

    boilerplate_lines = {
        line for line, count in line_document_counts.items()
        if count >= threshold_count
    }

    return boilerplate_lines


def strip_corpus_boilerplate(text: str, boilerplate_lines: set[str]) -> str:
    """Remove lines identified as corpus-level boilerplate."""

    kept_lines = [
        line for line in text.split("\n")
        if line.strip() not in boilerplate_lines
    ]

    return "\n".join(kept_lines)


# ============================================================
# Per-document cleaning
# ============================================================

def clean_document_text(raw_text: str, boilerplate_lines: set[str]) -> str:
    """Apply the full cleaning pipeline to a single document's text."""

    text = strip_html(raw_text)  # safety net, even though raw text should be plain already
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = strip_regex_noise(text)
    text = strip_corpus_boilerplate(text, boilerplate_lines)
    text = normalize_whitespace(text)  # re-collapse blank lines left by removals

    return text


# ============================================================
# I/O
# ============================================================

def load_raw_documents() -> list[dict]:
    if not RAW_DATA_DIR.exists():
        return []

    documents = []
    for path in sorted(RAW_DATA_DIR.glob("document_*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                doc = json.load(file)
                doc["_raw_path"] = str(path)
                documents.append(doc)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[ERROR] Could not read {path.name}: {exc}")

    return documents


def save_clean_document(document: dict) -> Path:
    CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

    output_path = CLEAN_DATA_DIR / f"{document['document_id']}.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)

    return output_path


# ============================================================
# Spot-check report
# ============================================================

def write_spot_check_report(cleaned_documents: list[dict]) -> Path:
    """
    Sample documents for manual review and write a Markdown report
    satisfying the assignment's "manually spot-check at least 5
    cleaned documents" requirement.
    """

    CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

    sample_size = min(SPOT_CHECK_SAMPLE_SIZE, len(cleaned_documents))
    sample = random.sample(cleaned_documents, sample_size) if cleaned_documents else []

    report_path = CLEAN_DATA_DIR / "spot_check_report.md"

    lines = [
        "# Cleaning Spot-Check Report",
        "",
        f"Sampled {sample_size} of {len(cleaned_documents)} cleaned documents "
        "for manual review.",
        "",
        "Reviewer checklist per document:",
        "- [ ] No HTML tags visible",
        "- [ ] No script/style content visible",
        "- [ ] No obvious navigation/boilerplate remaining",
        "- [ ] Substantive content is preserved and readable",
        "",
        "---",
        "",
    ]

    for doc in sample:
        snippet = doc["text"][:SPOT_CHECK_SNIPPET_CHARS]
        lines.extend([
            f"## {doc['document_id']} — {doc.get('title', '(no title)')}",
            "",
            f"- Source URL: {doc.get('url', 'N/A')}",
            f"- Raw chars: {doc.get('raw_char_count', 'N/A')} → "
            f"Clean chars: {doc.get('clean_char_count', 'N/A')}",
            f"- Chars removed: {doc.get('chars_removed', 'N/A')}",
            "",
            "**Text snippet:**",
            "",
            "```",
            snippet + ("..." if len(doc["text"]) > SPOT_CHECK_SNIPPET_CHARS else ""),
            "```",
            "",
            "**Reviewer notes:** _(fill in during manual check)_",
            "",
            "- [ ] HTML tags found? \n- [ ] Script/style found? \n- [ ] Boilerplate found? \n- [ ] Content OK?",
            "",
            "---",
            "",
        ])

    with report_path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    return report_path


# ============================================================
# Main pipeline
# ============================================================

def clean_documents() -> None:
    print("=" * 70)
    print("Cleaning & Preprocessing")
    print("=" * 70)

    raw_documents = load_raw_documents()

    if not raw_documents:
        print(f"[ERROR] No raw documents found in {RAW_DATA_DIR}")
        return

    print(f"Raw documents found: {len(raw_documents)}")

    boilerplate_lines = build_boilerplate_line_set(raw_documents)
    print(f"Corpus-level boilerplate lines detected: {len(boilerplate_lines)}")

    if boilerplate_lines:
        preview = list(boilerplate_lines)[:5]
        print("Examples:")
        for line in preview:
            print(f"  - {line[:80]!r}")

    cleaned_documents = []
    empty_after_cleaning = []

    for doc in raw_documents:
        raw_text = doc.get("text", "")
        raw_char_count = len(raw_text)

        clean_text_value = clean_document_text(raw_text, boilerplate_lines)
        clean_char_count = len(clean_text_value)

        if clean_char_count < 50:
            empty_after_cleaning.append(doc["document_id"])

        cleaned_doc = {
            "document_id": doc["document_id"],
            "url": doc.get("url"),
            "url_hash": doc.get("url_hash"),
            "source": doc.get("source"),
            "title": doc.get("title"),
            "text": clean_text_value,
            "category": doc.get("category"),
            "domain": doc.get("domain"),
            "collected_at": doc.get("collected_at"),
            "raw_char_count": raw_char_count,
            "clean_char_count": clean_char_count,
            "chars_removed": raw_char_count - clean_char_count,
            "raw_source_path": doc.get("_raw_path"),
            "content_quality": doc.get("content_quality", "ok"),
        }

        save_clean_document(cleaned_doc)
        cleaned_documents.append(cleaned_doc)

    print(f"\nCleaned documents written to: {CLEAN_DATA_DIR}")
    print(f"Documents cleaned: {len(cleaned_documents)}")

    # Verify: after cleaning, no document should still contain HTML-tag-like
    # patterns. This is a direct, automated check of the assignment's
    # "no obvious HTML tags" acceptance criterion (in addition to the
    # manual spot-check report below).
    still_has_html = [
        d["document_id"] for d in cleaned_documents
        if HTML_TAG_HINT.search(d["text"])
    ]
    if still_has_html:
        print(f"\n[WARNING] {len(still_has_html)} document(s) still contain "
              f"HTML-tag-like patterns after cleaning:")
        for doc_id in still_has_html:
            print(f"          - {doc_id}")
    else:
        print("[CHECK] No HTML tags detected in any cleaned document. OK.")

    total_raw_chars = sum(d["raw_char_count"] for d in cleaned_documents)
    total_clean_chars = sum(d["clean_char_count"] for d in cleaned_documents)
    reduction_pct = (
        100 * (total_raw_chars - total_clean_chars) / total_raw_chars
        if total_raw_chars else 0
    )
    print(f"Total chars: {total_raw_chars} -> {total_clean_chars} "
          f"({reduction_pct:.1f}% removed)")

    if empty_after_cleaning:
        print(f"\n[WARNING] {len(empty_after_cleaning)} document(s) nearly empty "
              f"after cleaning (<50 chars) — likely over-aggressive boilerplate "
              f"removal or an already-thin raw document:")
        for doc_id in empty_after_cleaning:
            print(f"          - {doc_id}")

    report_path = write_spot_check_report(cleaned_documents)
    print(f"\nSpot-check report written to: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    clean_documents()