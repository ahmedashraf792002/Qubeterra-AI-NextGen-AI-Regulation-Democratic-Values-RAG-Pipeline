# AI Regulation RAG — Week 1 (in progress)

Knowledge infrastructure for a RAG pipeline on the **AI Regulation** domain
(EU AI Act, US/NIST AI risk-management approach, international/OECD
principles), for the Qubeterra AI NextGen Week 1 milestone.

**Status:** Task 1 (data collection) implemented. Cleaning, chunking,
embedding, PostgreSQL storage, retrieval, and evaluation are not built yet.

## Overview

- **Domain:** AI regulation and governance (EU AI Act as primary reference,
  plus US/NIST and international sources) — see `src/collection/seeds.py`.
- **What's built so far:** a repeatable data-collection pipeline
  (`src/collection/collect.py`) that fetches seed pages, optionally
  crawls one hop of same-domain links to grow the set, extracts main body
  text, cleans it, deduplicates by content hash, and writes one JSON
  document per page into `data/raw/`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # not needed yet for this task, but create it early
```

Requires Python 3.10+ (uses `X | None` type hints).

## Running the data-collection pipeline

```bash
# Default run: seed URLs + 1 hop of same-domain crawling, up to 70 docs
python -m src.collection.collect

# Seeds only, no crawling
python -m src.collection.collect --crawl-depth 0

# Add extra URLs from a text file (one URL per line) on top of seeds.py
python -m src.collection.collect --seeds-file more_urls.txt --max-docs 80
```

Output:
- `data/raw/<doc_id>.json` — one file per collected document
- `data/raw/manifest.json` — collection summary (count, breakdown by
  source category)

Each document JSON contains: `url`, `title`, `text`, `category`,
`source_domain`, `content_hash`, `scraped_at`, `author`, `date`,
`description`, `word_count`.

## Design decisions

**Source selection.** Seeds are curated official/primary sources
(European Commission digital-strategy pages, EUR-Lex, NIST AI RMF,
OECD AI Principles) plus a few reference/analysis pages, grouped by
`category` in `seeds.py` so retrieval results can later be filtered or
weighted by source type. This satisfies the brief's "prefer primary
sources" guidance in the Research & Bias Rules section of the Theme 1
brief. The list is intentionally a starting point — `--crawl-depth 1`
follows in-domain links from each seed to grow past it, and it can be
extended further via `--seeds-file` or by editing `seeds.py` directly.

**Fetching.** Plain `httpx` GET with a browser-like User-Agent and
exponential-backoff retries (`src/collection/fetch.py`). No paid
scraping API — the sources here serve static HTML, so a direct request
is enough. If a future source needs JS rendering, only `fetch.py` needs
to change; `fetch_page(url) -> str` is the interface the rest of the
pipeline depends on.

**Extraction.** `trafilatura` (`src/collection/extract.py`) — open
source, combines DOM heuristics with text-density scoring, and handles
both news-style and structured government/legal pages better than
naive tag-stripping.

**Cleaning/normalization.** Unicode NFKC normalization, invisible/
non-breaking whitespace removal, collapsed blank lines, and dropped
short nav-fragment lines (`src/collection/normalize.py`).

**Concurrency.** Threads (`ThreadPoolExecutor`), not `asyncio` —
chosen deliberately to avoid event-loop/shared-async-client issues.

**Deduplication.** SHA-256 hash (first 16 chars) of the normalized
text, checked in-memory during a run. The same content sometimes
appears at multiple URLs (query params, mirrors); hashing content
rather than normalizing URLs catches that reliably.

**Minimum length filter.** Documents under 40 words after cleaning are
dropped as extraction stubs/noise (table fragments, empty shells).

## Running tests

```bash
python -m pytest tests/
```

(Test suite not yet written — placeholder for now.)

## Known limitations

- No JS-rendering support yet; any source requiring a headless browser
  would currently fail extraction.
- Crawl discovery is same-domain only and one hop by default — deep
  crawling / pagination handling not yet implemented.
- No scheduled re-scrape / freshness TTL yet — this is a one-shot
  collection run.

## Next steps (not yet implemented)

Cleaning spot-checks, chunking strategy, embedding generation,
PostgreSQL + pgvector storage, retrieval interface, and quantitative
RAGAS-style evaluation — per the Week 1 milestone spec.
