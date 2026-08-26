# Qubeterra AI NextGen — AI Regulations & Democratic Values RAG

Retrieval-Augmented Generation pipeline for AI regulations and democratic values knowledge domain.

## Project Structure

```
├── src/
│   ├── collection/          # Step 1: Web scraping & data collection
│   ├── preprocessing/       # Step 2: Cleaning & normalization
│   ├── chunking/            # Step 3: Structure-driven chunking
│   ├── embeddings/          # Step 4: Vector embedding generation
│   ├── storage/             # Step 5: PostgreSQL + pgvector storage
│   ├── retrieval/           # Step 6: Vector similarity search
│   └── evaluation/          # Step 7: Precision/Recall/MRR metrics
├── tests/
│   ├── collection/          # run.py + seed_urls.py
│   ├── preprocessing/       # run.py
│   ├── chunking/            # run.py
│   ├── embeddings/          # run.py
│   ├── storage/             # run.py + check_postgres.py
│   ├── retrieval/           # run.py
│   ├── evaluation/          # run.py + eval_dataset.py
│   └── run_all_steps.py     # Run all 7 steps together
├── data/
│   ├── raw/                 # Raw collected documents
│   ├── clean/               # Cleaned documents
│   ├── chunks/              # Chunked documents (chunks.jsonl)
│   ├── embeddings/          # Generated embeddings (embeddings.jsonl)
│   └── evaluation/          # Evaluation results & reports
├── sql/schema.sql           # PostgreSQL schema
├── .env                     # Configuration (all parameters)
└── .env.example             # Template configuration
```

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- uv (package manager)

## Installation

```bash
# Clone the project
git clone <repo-url>
cd QUBETERRA-AI-NEXTGEN-AI-REGULATIONS-DEMOCRATIC-VALUES-RAG

# Install dependencies
uv pip install -r requirements.txt
uv pip install sentence-transformers psycopg python-dotenv pytest

# Copy and edit .env
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

## Database Setup (PostgreSQL + pgvector)

### 1. Start PostgreSQL

**Using Docker (recommended):**

```bash
# Start PostgreSQL with pgvector
docker-compose up -d
```

**Or use local PostgreSQL:**

Make sure PostgreSQL is running on port 5433 (or change `POSTGRES_PORT` in `.env`).

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres -h localhost -p 5433

# Create the database
CREATE DATABASE ai_reg_rag;

# Exit
\q
```

### 3. Enable pgvector Extension

The `sql/schema.sql` file handles this automatically when you run Step 5 (Storage). But if you want to do it manually:

```bash
psql -U postgres -h localhost -p 5433 -d ai_reg_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Configure .env

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=ai_reg_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 5. Load Data into Database

```bash
# Run storage step (loads chunks + embeddings into PostgreSQL)
uv run python tests/storage/run.py
```

### 6. Verify Database Contents

```bash
# Check a specific chunk in the database
uv run python tests/storage/check_postgres.py
```

### 7. Query the Database

```bash
# Run a retrieval query
uv run python tests/retrieval/run.py

# Custom query
uv run python tests/retrieval/run.py --query "What is Article 5?" --top-k 3
```

## Configuration (.env)

All pipeline parameters are configured in `.env`:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=ai_reg_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Collection
MAX_DOCUMENTS=60
CRAWL_DEPTH=1
DOCUMENT_NAME_PREFIX=document_
DOCUMENT_NAME_DIGITS=2

# Embeddings
EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSIONALITY=384
MODEL_MAX_TOKENS=512
ENCODE_BATCH_SIZE=32

# Retrieval
DEFAULT_TOP_K=5
EVAL_TOP_K=5
```

## Running the Pipeline

### Run all 7 steps at once

```bash
uv run python tests/run_all_steps.py
```

### Run specific steps

```bash
uv run python tests/run_all_steps.py --steps 1,2,3    # collection + clean + chunk
uv run python tests/run_all_steps.py --steps 4,5       # embeddings + storage
uv run python tests/run_all_steps.py --steps 6,7       # retrieval + evaluation
```

### Run individual steps

| Step | Command |
|------|---------|
| 1. Collection | `uv run python tests/collection/run.py` |
| 2. Preprocessing | `uv run python tests/preprocessing/run.py` |
| 3. Chunking | `uv run python tests/chunking/run.py` |
| 4. Embeddings | `uv run python tests/embeddings/run.py` |
| 5. Storage | `uv run python tests/storage/run.py` |
| 6. Retrieval | `uv run python tests/retrieval/run.py` |
| 7. Evaluation | `uv run python tests/evaluation/run.py` |

### Custom queries

```bash
uv run python tests/retrieval/run.py --query "What is Article 5?" --top-k 3
```

## Pipeline Steps

1. **Collection** — Scrapes web pages from seed URLs, saves as JSON
2. **Preprocessing** — Removes HTML, normalizes unicode, strips boilerplate
3. **Chunking** — Splits documents at structural boundaries (Articles/Sections)
4. **Embeddings** — Generates vectors using BAAI/bge-small-en-v1.5
5. **Storage** — Loads chunks + embeddings into PostgreSQL with pgvector
6. **Retrieval** — Vector similarity search with optional metadata filtering
7. **Evaluation** — Computes Precision@K, Recall@K, MRR

## Output

- `data/raw/` — Raw collected documents
- `data/clean/` — Cleaned documents
- `data/chunks/chunks.jsonl` — Chunked documents
- `data/embeddings/embeddings.jsonl` — Generated embeddings
- `data/evaluation/results.json` — Evaluation metrics
- `data/evaluation/report.md` — Human-readable evaluation report

## Database Schema

The PostgreSQL table `chunks` stores:

| Column | Type | Description |
|--------|------|-------------|
| chunk_id | TEXT | Primary key (e.g. document_01_chunk003) |
| document_id | TEXT | Source document ID |
| chunk_index | INTEGER | Position in document |
| structural_label | TEXT | e.g. "Article 5" |
| text | TEXT | Chunk content |
| char_count | INTEGER | Character count |
| url | TEXT | Source URL |
| title | TEXT | Document title |
| source | TEXT | Source domain |
| category | TEXT | e.g. official_eu, official_us |
| domain | TEXT | Knowledge domain |
| content_quality | TEXT | ok or low |
| embedding_model | TEXT | e.g. BAAI/bge-small-en-v1.5 |
| embedding | vector(384) | 384-dimensional vector |

## Useful SQL Queries

```sql
-- Count total chunks
SELECT COUNT(*) FROM chunks;

-- Count chunks per document
SELECT document_id, COUNT(*) as chunks FROM chunks GROUP BY document_id ORDER BY chunks DESC;

-- Search for chunks containing specific text
SELECT chunk_id, document_id, title, LEFT(text, 100) as snippet FROM chunks WHERE text ILIKE '%transparency%';

-- Find chunks by category
SELECT category, COUNT(*) FROM chunks GROUP BY category;

-- Find low quality documents
SELECT chunk_id, document_id, content_quality FROM chunks WHERE content_quality = 'low';
```
