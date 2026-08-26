"""
Chunking pipeline for the AI Regulations & Democratic Values
knowledge domain.

Strategy: STRUCTURE-DRIVEN CHUNKING (not fixed-size packing).

Core idea
---------
The chunk boundary is the document's own structure, not a character/
token count. For legal/policy text this means:

    one Article / Section / Chapter / Recital / Annex  ==  one chunk

That's the retrievable unit a reader (or a downstream agent) actually
wants back — the full obligation, the full definition, the full
clause — not an arbitrary character-count slice that might cut a
sentence in half or separate an obligation from its scope.

There is NO target chunk size that the pipeline tries to "fill up to".
Chunks are exactly as long as their structural unit is.

Handling oversized sections
----------------------------
Some structural units (e.g. a long Article) are still too large to
embed safely or to be useful as a single retrieval result. For those
cases ONLY, the section is split at its own natural paragraph breaks
(`\n\n`) — never at an arbitrary character count. Each resulting piece
is exactly one paragraph (or a run of paragraphs, if a single one is
itself over the safety cap) — never a packed, size-targeted slice.

MAX_CHUNK_CHARS below is a SAFETY CAP tied to embedding-model context
limits, not a target: most chunks will be far smaller or larger than
it, since they're sized by the document's own structure.

If a single paragraph is itself still larger than the safety cap
(rare — e.g. a long unbroken clause with no paragraph breaks), it is
split at sentence boundaries as a last-resort fallback. This is
logged explicitly since it means the source document had no natural
break points to respect.

Documents with no structural markers at all (news/analysis content
with no Article/Section headers) are treated as a single section and
go through the same paragraph-based logic.

Output
------
data/chunks/chunks.jsonl — one JSON object per line, each chunk
carrying full traceability back to its source document, its
structural label, and its position.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEAN_DATA_DIR = PROJECT_ROOT / "data" / "clean"
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
CHUNKS_OUTPUT_PATH = CHUNKS_DIR / "chunks.jsonl"

CHARS_PER_TOKEN_APPROX = int(os.getenv("CHARS_PER_TOKEN_APPROX", "4"))
MAX_CHUNK_TOKENS_SAFETY_CAP = int(os.getenv("MAX_CHUNK_TOKENS_SAFETY_CAP", "600"))
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS_SAFETY_CAP * CHARS_PER_TOKEN_APPROX

MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "200"))

# ------------------------------------------------------------
# Structural boundary detection
# ------------------------------------------------------------
STRUCTURAL_HEADER_PATTERN = re.compile(
    r"^(Article\s+\d+[a-zA-Z]?|"
    r"Chapter\s+[IVXLCDM\d]+|"
    r"Section\s+\d+[a-zA-Z]?|"
    r"Recital\s+\d+|"
    r"Annex\s+[IVXLCDM\d]+|"
    r"Title\s+[IVXLCDM\d]+)"
    r"\b.*$",
    re.MULTILINE,
)

NON_BOUNDARY_ABBREVIATIONS = {
    # Abbreviations after which a "." must NOT be treated as a sentence
    # boundary (common in legal/policy English text). Matched against
    # the token immediately preceding the candidate split point.
    # Extend this list as new false-positive splits are found during
    # spot-checks.
    "e.g.", "i.e.", "etc.", "vs.", "cf.",
    "Art.", "Arts.", "Sec.", "Secs.", "No.", "Nos.",
    "para.", "paras.", "Fig.", "Annex.",
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.",
    "U.S.", "U.K.", "E.U.",
}


# ============================================================
# Structural segmentation
# ============================================================

def split_into_structural_sections(text: str) -> list[dict]:
    """
    Split text at structural header boundaries (Article/Section/etc).

    Returns a list of {"label": str | None, "text": str} sections —
    one per structural unit. If no structural headers are found at
    all, returns the whole text as a single section with label=None.
    """

    matches = list(STRUCTURAL_HEADER_PATTERN.finditer(text))

    if not matches:
        return [{"label": None, "text": text}]

    sections = []

    if matches[0].start() > 0:
        leading = text[: matches[0].start()].strip()
        if len(leading) >= MIN_CHUNK_CHARS:
            sections.append({"label": None, "text": leading})

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        section_text = text[start:end].strip()
        label = match.group(0).strip()[:60]

        if section_text:
            sections.append({"label": label, "text": section_text})

    return sections


def merge_orphaned_sections(sections: list[dict]) -> list[dict]:
    """
    Merge a section into its neighbor ONLY when it's too small to be a
    meaningful standalone chunk (e.g. a header with almost no body).
    This is a safety merge, not size-target packing: it only fires
    below MIN_CHUNK_CHARS, and only merges into the immediately
    following section (keeping the header attached to its own body).
    """

    if not sections:
        return sections

    merged: list[dict] = []
    i = 0

    while i < len(sections):
        current = sections[i]

        if len(current["text"]) < MIN_CHUNK_CHARS and i + 1 < len(sections):
            nxt = sections[i + 1]
            combined_label = current["label"] or nxt["label"]
            if current["label"] and nxt["label"]:
                combined_label = f"{current['label']} + {nxt['label']}"

            merged.append({
                "label": combined_label,
                "text": current["text"] + "\n\n" + nxt["text"],
            })
            i += 2
        else:
            merged.append(current)
            i += 1

    # A trailing orphan section (the very last one, so it had no
    # forward neighbor to merge into above — e.g. a short final
    # Article/Annex) is folded backward into the previous section
    # instead of being emitted alone. This is what let a near-empty
    # final section through as its own few-character chunk.
    if len(merged) >= 2 and len(merged[-1]["text"]) < MIN_CHUNK_CHARS:
        tail = merged.pop()
        prev = merged[-1]
        combined_label = prev["label"] or tail["label"]
        if prev["label"] and tail["label"]:
            combined_label = f"{prev['label']} + {tail['label']}"
        merged[-1] = {
            "label": combined_label,
            "text": prev["text"] + "\n\n" + tail["text"],
        }

    return merged


# ============================================================
# Paragraph-based splitting (oversized sections ONLY)
# ============================================================

def merge_orphaned_paragraphs(pieces: list[str], max_chars: int) -> list[str]:
    """
    Greedily accumulate consecutive small pieces into one chunk until
    the next piece would push it past max_chars — not just merging
    isolated adjacent PAIRS.

    Splitting on single `\n` (see split_on_natural_boundaries) turns a
    bullet-heavy document into dozens of individually tiny line-level
    pieces (a short header line, then a dozen ~40-char bullet items).
    Pairwise-only merging (the previous behavior) merges piece[0] into
    piece[1] and then leaves piece[2] to merge with piece[3], etc. —
    every *odd*-positioned small piece in a long run still ends up
    alone, including a lone final piece with no partner at all. That
    is what produced near-empty ("4-char") chunks. Accumulating keeps
    absorbing pieces into the current chunk for as long as it's still
    under MIN_CHUNK_CHARS and the combination still fits max_chars, so
    a whole run of short bullets lands in one chunk together instead
    of being split into isolated leftover fragments.

    A piece that is already >= MIN_CHUNK_CHARS on its own is never
    forced to merge with anything — this still isn't size-target
    packing, just orphan-avoidance applied without an artificial
    pairwise limit.
    """

    if not pieces:
        return pieces

    merged: list[str] = [pieces[0]]

    for piece in pieces[1:]:
        current = merged[-1]
        current_is_small = len(current) < MIN_CHUNK_CHARS
        combined_len = len(current) + 2 + len(piece)  # +2 for the "\n\n" join

        if current_is_small and combined_len <= max_chars:
            merged[-1] = current + "\n\n" + piece
        else:
            merged.append(piece)

    # A trailing piece with no later neighbor to absorb into (e.g. a
    # single leftover bullet at the very end of the section) is folded
    # backward into the previous chunk instead of being emitted alone,
    # as long as that still fits under the safety cap.
    if len(merged) >= 2 and len(merged[-1]) < MIN_CHUNK_CHARS:
        tail = merged.pop()
        if len(merged[-1]) + 2 + len(tail) <= max_chars:
            merged[-1] = merged[-1] + "\n\n" + tail
        else:
            merged.append(tail)  # can't merge without busting the cap -- keep as-is

    return merged


def split_on_natural_boundaries(text: str, max_chars: int) -> list[str]:
    """
    Split text at its own paragraph/line breaks only. Each returned
    piece is one paragraph, or a small run of consecutive paragraphs
    that together still exceed no fixed target — this simply avoids
    emitting a paragraph so short it isn't useful alone by attaching
    it to the next one. No size TARGET is being filled; pieces are
    only ever produced because the section didn't fit under the
    safety cap as a whole.

    Splits on ANY run of newlines (`\n+`), not just blank-line-style
    `\n\n`. The cleaned corpus is inconsistent here: legal/EUR-Lex
    text tends to have real blank-line paragraph breaks, but several
    government pages (e.g. digital-strategy.ec.europa.eu) come out of
    cleaning with a single `\n` between every paragraph/heading/bullet
    and NO blank lines at all. Splitting on `\n\n` only silently
    treated those documents as one giant unbreakable "paragraph",
    which is what pushed document_02 / document_13 past the safety
    cap: with no real break point detected, the whole section fell
    through to sentence-level splitting, and bullet lines with no
    terminal punctuation (e.g. "- \u201cAI Safety\u201d - unit A3") then merged
    into one unsplittable "sentence" well over the cap. `\n+` is a
    strict superset of the `\n\n` case (a blank line just yields an
    empty string that `if p.strip()` already filters out).

    If a single paragraph itself exceeds max_chars (no natural break
    point available), it is split on sentence boundaries as a
    last-resort fallback, and that fact is reported by the caller.
    """

    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]

    if not paragraphs:
        return []

    pieces: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
        else:
            # Last-resort fallback: no paragraph break available within
            # this unit, so we must cut at sentence boundaries instead.
            pieces.extend(_split_long_paragraph_by_sentence(paragraph, max_chars))

    return merge_orphaned_paragraphs(pieces, max_chars)


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences, avoiding false-positive splits after
    known abbreviations (e.g. "Art. 5" should stay one sentence, not
    split after "Art.").

    Approach: find every candidate boundary (a '.', '!', '?', or
    Arabic '؟' followed by whitespace), then reject any boundary whose
    preceding word — including the punctuation — matches a known
    abbreviation.
    """

    if not text:
        return []

    # Find all candidate boundary positions.
    boundary_pattern = re.compile(r"[.!?؟]\s+")
    sentences = []
    start = 0

    for match in boundary_pattern.finditer(text):
        boundary_end = match.end()
        punctuation_end = match.start() + 1  # position right after the punctuation mark

        preceding_text = text[start:punctuation_end]
        preceding_word = preceding_text.split()[-1] if preceding_text.split() else ""

        if preceding_word in NON_BOUNDARY_ABBREVIATIONS:
            # Not a real sentence boundary — keep accumulating.
            continue

        sentences.append(text[start:boundary_end].strip())
        start = boundary_end

    remainder = text[start:].strip()
    if remainder:
        sentences.append(remainder)

    return [s for s in sentences if s]


def _split_long_paragraph_by_sentence(paragraph: str, max_chars: int) -> list[str]:
    """Last-resort fallback for a single paragraph with no internal breaks."""

    sentences = split_into_sentences(paragraph)

    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = sentence

    if current:
        pieces.append(current)

    return pieces


# ============================================================
# Per-document chunking
# ============================================================

def chunk_document(document: dict) -> tuple[list[dict], list[str]]:
    """
    Chunk a single cleaned document.

    Returns (chunks, sentence_fallback_notes) — the notes list records
    any structural unit that had to fall back to sentence-level
    splitting because it had no natural paragraph breaks, so this can
    be surfaced and reviewed rather than happening silently.
    """

    text = document.get("text", "")

    if not text.strip():
        return [], []

    sections = split_into_structural_sections(text)
    sections = merge_orphaned_sections(sections)

    chunks = []
    fallback_notes = []
    position = 0

    for section in sections:
        section_text = section["text"]

        if len(section_text) <= MAX_CHUNK_CHARS:
            # The whole structural unit IS the chunk. No splitting.
            pieces = [section_text]
        else:
            pieces = split_on_natural_boundaries(section_text, MAX_CHUNK_CHARS)

            # Report (not force) whether sentence-level fallback was
            # needed anywhere in this section, i.e. some paragraph had
            # no natural break and still exceeded the safety cap.
            # Must use the SAME split as split_on_natural_boundaries
            # (re.split on \n+, not text.split("\n\n")) or this check
            # goes stale relative to the actual splitting logic and
            # reports a fallback that didn't really happen — which is
            # exactly what it was doing before this fix.
            paragraphs_in_section = [p for p in re.split(r"\n+", section_text) if p.strip()]
            had_long_single_paragraph = any(
                len(p.strip()) > MAX_CHUNK_CHARS for p in paragraphs_in_section
            )
            if had_long_single_paragraph:
                fallback_notes.append(
                    f"{document['document_id']} / {section['label'] or '(untitled section)'}: "
                    f"at least one paragraph exceeded the safety cap and was split by sentence."
                )

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            chunk = {
                "chunk_id": f"{document['document_id']}_chunk{position:03d}",
                "document_id": document["document_id"],
                "chunk_index": position,
                "structural_label": section["label"],
                "text": piece,
                "char_count": len(piece),
                "approx_token_count": round(len(piece) / CHARS_PER_TOKEN_APPROX),
                "url": document.get("url"),
                "title": document.get("title"),
                "source": document.get("source"),
                "category": document.get("category"),
                "domain": document.get("domain"),
                "content_quality": document.get("content_quality"),
            }
            chunks.append(chunk)
            position += 1

    return chunks, fallback_notes


# ============================================================
# I/O
# ============================================================

def load_clean_documents() -> list[dict]:
    if not CLEAN_DATA_DIR.exists():
        return []

    documents = []
    for path in sorted(CLEAN_DATA_DIR.glob("document_*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                documents.append(json.load(file))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[ERROR] Could not read {path.name}: {exc}")

    return documents


def write_chunks(chunks: list[dict]) -> Path:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    with CHUNKS_OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return CHUNKS_OUTPUT_PATH


# ============================================================
# Main pipeline
# ============================================================

def chunk_documents() -> None:
    print("=" * 70)
    print("Chunking")
    print("=" * 70)
    print("Strategy         : structure-driven (1 chunk = 1 Article/Section)")
    print(f"Safety cap only  : ~{MAX_CHUNK_TOKENS_SAFETY_CAP} tokens (~{MAX_CHUNK_CHARS} chars) "
          f"— NOT a target, only applies when a section must be split")
    print("Oversized split  : natural paragraph breaks only (sentence-level "
          "as last-resort fallback)")
    print("=" * 70)

    documents = load_clean_documents()

    if not documents:
        print(f"[ERROR] No cleaned documents found in {CLEAN_DATA_DIR}")
        return

    print(f"Cleaned documents found: {len(documents)}")

    all_chunks = []
    all_fallback_notes = []
    structural_doc_count = 0
    fallback_doc_count = 0
    single_chunk_docs = 0
    split_docs = 0

    for document in documents:
        doc_chunks, fallback_notes = chunk_document(document)
        all_chunks.extend(doc_chunks)
        all_fallback_notes.extend(fallback_notes)

        has_structure = any(c["structural_label"] for c in doc_chunks)
        if has_structure:
            structural_doc_count += 1
        else:
            fallback_doc_count += 1

        if len(doc_chunks) <= 1:
            single_chunk_docs += 1
        else:
            split_docs += 1

    output_path = write_chunks(all_chunks)

    print(f"\nDocuments with detected structure (Article/Section/...): {structural_doc_count}")
    print(f"Documents with no structure (whole doc = 1 unit)        : {fallback_doc_count}")
    print(f"Documents that stayed as a single chunk                  : {single_chunk_docs}")
    print(f"Documents split into multiple chunks (oversized sections): {split_docs}")
    print(f"Total chunks produced                                     : {len(all_chunks)}")

    if all_chunks:
        char_counts = [c["char_count"] for c in all_chunks]
        avg_chars = sum(char_counts) / len(char_counts)
        min_chars = min(char_counts)
        max_chars = max(char_counts)
        avg_chunks_per_doc = len(all_chunks) / len(documents)
        print(f"Chunk size (chars) — avg: {avg_chars:.0f}, min: {min_chars}, max: {max_chars}")
        print(f"(Wide variance is expected — chunk size follows document "
              f"structure, not a fixed target.)")
        print(f"Average chunks per document: {avg_chunks_per_doc:.1f}")

    over_cap = [c["chunk_id"] for c in all_chunks if c["char_count"] > MAX_CHUNK_CHARS]
    if over_cap:
        print(f"\n[WARNING] {len(over_cap)} chunk(s) still exceed the safety cap "
              f"({MAX_CHUNK_CHARS} chars) — likely a single sentence longer than the cap:")
        for cid in over_cap[:10]:
            print(f"          - {cid}")
    else:
        print("[CHECK] All chunks are within the safety cap. OK.")

    if all_fallback_notes:
        print(f"\n[NOTE] {len(all_fallback_notes)} section(s) had no natural paragraph "
              f"breaks and required sentence-level fallback splitting:")
        for note in all_fallback_notes:
            print(f"       - {note}")

    print(f"\nChunks written to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    chunk_documents()