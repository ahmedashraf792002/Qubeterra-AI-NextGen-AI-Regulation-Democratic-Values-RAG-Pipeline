-- Schema for the AI Regulations & Democratic Values RAG knowledge base.
--
-- One row per chunk (see src/chunking/chunk_documents.py for how chunks
-- are produced). Loaded by src/storage/load_to_postgres.py.
--
-- {dimension} is a placeholder substituted at load time with the
-- actual embedding vector width read from data/embeddings/embeddings.jsonl
-- (currently 768 for nomic-embed-text) — NOT hardcoded here, so this
-- file stays correct if the embedding model ever changes.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id          TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL,
    chunk_index       INTEGER,
    structural_label  TEXT,       -- e.g. "Article 5" — NULL if the source document had no detected structure
    text              TEXT NOT NULL,
    char_count        INTEGER,
    url               TEXT,
    title             TEXT,
    source            TEXT,       -- source domain, e.g. digital-strategy.ec.europa.eu
    category          TEXT,       -- e.g. official_eu, official_us, analysis
    domain            TEXT,       -- knowledge domain label, e.g. "AI Regulations & Democratic Values"
    content_quality   TEXT,
    embedding_model   TEXT,       -- e.g. nomic-embed-text
    embedding         vector({dimension})
);

-- HNSW index for cosine-similarity search — the standard choice for
-- text embeddings, where direction (not magnitude) carries the meaning.
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Supports "all chunks for this document" lookups (e.g. reconstructing
-- a document from its chunks, or de-duplicating retrieval results).
CREATE INDEX IF NOT EXISTS chunks_document_id_idx
    ON chunks (document_id);