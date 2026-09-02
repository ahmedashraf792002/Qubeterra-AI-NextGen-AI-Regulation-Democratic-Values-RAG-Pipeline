# How to Run

## Prerequisites

- Python 3.11+
- PostgreSQL (or Docker)
- API key from one LLM provider

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install sentence-transformers psycopg python-dotenv fastapi uvicorn
pip install langchain langchain-openai langchain-ollama langchain-anthropic langchain-google-genai langchain-groq
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=ai_reg_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# LLM — pick one provider
MODEL_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

### 3. Start database

```bash
docker-compose up -d
```

### 4. Run pipeline (first time only)

```bash
uv run python tests/run_all_steps.py --steps 1,2,3,4,5
```

### 5. Start Web UI

```bash
uvicorn src.webui.app:app --reload --port 8000
```

Open: **http://localhost:8000**

## LLM Providers

### OpenRouter (recommended)

```env
MODEL_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Get key: https://openrouter.ai/keys

### Ollama (local, free)

```bash
# Install Ollama: https://ollama.com
ollama pull qwen3:8b
```

```env
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

### Claude

```env
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
CLAUDE_MODEL=anthropic/claude-sonnet-4
```

### Gemini

```env
MODEL_PROVIDER=gemini
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Groq

```env
MODEL_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

## Demo (without Web UI)

```bash
uv run python tests/agents/demo.py
```

## Useful commands

```bash
# Search knowledge base
uv run python tests/retrieval/run.py --query "What is Article 5?"

# Check database
psql -U postgres -h localhost -p 5433 -d ai_reg_rag -c "SELECT COUNT(*) FROM chunks;"

# Re-run pipeline
uv run python tests/run_all_steps.py --steps 4,5
```
