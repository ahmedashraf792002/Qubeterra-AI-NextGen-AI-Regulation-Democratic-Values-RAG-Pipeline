"""
Embedding generation pipeline for the AI Regulations & Democratic
Values knowledge domain.

Embedding model:      BAAI/bge-small-en-v1.5
Vector dimensionality: 384
Reason for selection:  Strong retrieval performance for its size on
                        the MTEB retrieval benchmark, fully local/free
                        (no API key or per-call cost), small footprint
                        (~130MB) that runs comfortably on CPU, and
                        widely used specifically for RAG pipelines.
                        Hosted on Hugging Face Hub, loaded via
                        sentence-transformers.

Notes on bge-small specifically
--------------------------------
- BGE models are trained with an asymmetric retrieval setup: QUERY
  text should be prefixed with an instruction, but DOCUMENT/chunk text
  should NOT. This pipeline embeds document chunks, so no prefix is
  applied here. The retrieval stage (Section 10) must apply the query
  instruction prefix when embedding the user's natural-language query
  — this file documents that requirement for downstream consistency.
- bge-small-en-v1.5's native context window is 512 tokens. Our
  chunking pipeline enforces a safety cap of ~600 tokens (~2400
  chars), which is slightly above this. Chunks are truncated at
  encode time by the tokenizer if they exceed the model's limit; this
  is logged so any truncation is visible rather than silent.

Input:  data/chunks/chunks.jsonl   (from src/chunking/chunk_documents.py)
Output: data/embeddings/embeddings.jsonl — one JSON object per chunk,
        carrying the original chunk fields plus its embedding vector.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
EMBEDDINGS_OUTPUT_PATH = EMBEDDINGS_DIR / "embeddings.jsonl"

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIMENSIONALITY = int(os.getenv("EMBEDDING_DIMENSIONALITY", "384"))
MODEL_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "512"))

QUERY_INSTRUCTION_PREFIX = "Represent this sentence for searching relevant passages: "

ENCODE_BATCH_SIZE = int(os.getenv("ENCODE_BATCH_SIZE", "32"))


# ============================================================
# I/O
# ============================================================

def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        return []

    chunks = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[ERROR] Malformed JSON at line {line_number}: {exc}")

    return chunks


def write_embeddings(records: list[dict]) -> Path:
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    with EMBEDDINGS_OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return EMBEDDINGS_OUTPUT_PATH


# ============================================================
# Model loading
# ============================================================

def load_model():
    """
    Load the embedding model. Imported lazily inside this function so
    that scripts which only need the constants above (e.g. the
    retrieval stage importing QUERY_INSTRUCTION_PREFIX) don't pay the
    cost of importing sentence-transformers / torch.
    """

    print(f"Loading model: {EMBEDDING_MODEL_NAME} "
          f"(first run downloads it from Hugging Face Hub and caches it locally)")

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return model


# ============================================================
# Truncation check (visibility only — the tokenizer truncates
# automatically, but we want this reported, not silent)
# ============================================================

def check_for_truncation(model, chunks: list[dict]) -> list[str]:
    """Return chunk_ids whose token count exceeds the model's max sequence length."""

    tokenizer = model.tokenizer
    truncated_chunk_ids = []

    for chunk in chunks:
        token_count = len(tokenizer.encode(chunk["text"], add_special_tokens=True))
        if token_count > MODEL_MAX_TOKENS:
            truncated_chunk_ids.append(chunk["chunk_id"])

    return truncated_chunk_ids


# ============================================================
# Main pipeline
# ============================================================

def generate_embeddings() -> None:
    print("=" * 70)
    print("Embedding Generation")
    print("=" * 70)
    print(f"Model            : {EMBEDDING_MODEL_NAME}")
    print(f"Dimensionality   : {EMBEDDING_DIMENSIONALITY}")
    print(f"Model max tokens : {MODEL_MAX_TOKENS}")
    print("=" * 70)

    chunks = load_chunks()

    if not chunks:
        print(f"[ERROR] No chunks found at {CHUNKS_PATH}. Run the chunking "
              f"pipeline first.")
        return

    print(f"Chunks loaded: {len(chunks)}")

    model = load_model()

    truncated_chunk_ids = check_for_truncation(model, chunks)
    if truncated_chunk_ids:
        print(f"\n[WARNING] {len(truncated_chunk_ids)} chunk(s) exceed the "
              f"model's {MODEL_MAX_TOKENS}-token limit and will be silently "
              f"truncated by the tokenizer at encode time:")
        for cid in truncated_chunk_ids[:10]:
            print(f"          - {cid}")
        print("          Consider lowering the chunking safety cap if this "
              "list is long.")
    else:
        print("[CHECK] All chunks fit within the model's token limit. OK.")

    texts = [chunk["text"] for chunk in chunks]

    print(f"\nEncoding {len(texts)} chunks in batches of {ENCODE_BATCH_SIZE}...")

    embeddings = model.encode(
        texts,
        batch_size=ENCODE_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # cosine similarity via dot product downstream
    )

    if len(embeddings) != len(chunks):
        print(f"[ERROR] Embedding count ({len(embeddings)}) does not match "
              f"chunk count ({len(chunks)}). Aborting write.")
        return

    records = []
    for chunk, vector in zip(chunks, embeddings):
        record = dict(chunk)  # keep all original chunk metadata
        record["embedding"] = vector.tolist()
        record["embedding_model"] = EMBEDDING_MODEL_NAME
        record["embedding_dim"] = EMBEDDING_DIMENSIONALITY
        records.append(record)

    output_path = write_embeddings(records)

    print(f"\n[SUCCESS] Generated {len(records)} embeddings "
          f"(matches chunk count: {len(records) == len(chunks)})")
    print(f"Embeddings written to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    generate_embeddings()