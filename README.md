# Qubeterra AI NextGen — AI Regulations & Democratic Values RAG

RAG pipeline + Intelligent Agent Framework for AI regulations and democratic values.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install sentence-transformers psycopg python-dotenv streamlit

# 2. Configure
cp .env.example .env
# Edit .env with your API key and database credentials

# 3. Start database
docker-compose up -d

# 4. Run pipeline (Week 1)
uv run python tests/run_all_steps.py

# 5. Run agents (Week 2)
uv run python tests/agents/demo.py

# 6. Open Web UI
streamlit run app.py
```

## Project Structure

```
├── app.py                          # Web UI (Streamlit)
├── src/
│   ├── collection/                 # Step 1: Web scraping
│   ├── preprocessing/              # Step 2: Cleaning
│   ├── chunking/                   # Step 3: Document splitting
│   ├── embeddings/                 # Step 4: Vector generation
│   ├── storage/                    # Step 5: PostgreSQL + pgvector
│   ├── retrieval/                  # Step 6: Vector search
│   ├── evaluation/                 # Step 7: Metrics
│   └── agents/                     # Week 2: Agent framework
│       ├── agent.py                # Core Agent class
│       ├── persona.py              # Persona loader
│       ├── memory.py               # Conversation + facts
│       ├── tools.py                # Tool registry
│       ├── llm.py                  # Multi-provider LLM client
│       └── retrieval.py            # Week 1 integration
├── personas/                       # Agent persona configs
│   ├── tech_advocate.json          # Dr. Sarah Chen
│   ├── civil_rights_expert.json    # Prof. Marcus Williams
│   ├── economist.json              # Dr. Elena Petrov
│   └── government_regulator.json   # Minister James Okonkwo
├── tests/agents/
│   └── demo.py                     # End-to-end demo
├── outputs/                        # Generated opinions
├── data/                           # Pipeline data
├── .env                            # Your config (secrets)
└── .env.example                    # Config template
```

## Week 1 — Knowledge Pipeline

7-step RAG pipeline:

| Step | Name | What it does |
|------|------|-------------|
| 1 | Collection | Scrapes web pages from seed URLs |
| 2 | Preprocessing | Removes HTML, normalizes text |
| 3 | Chunking | Splits at structural boundaries |
| 4 | Embeddings | Generates vectors (BAAI/bge-small-en-v1.5) |
| 5 | Storage | Loads into PostgreSQL + pgvector |
| 6 | Retrieval | Vector similarity search |
| 7 | Evaluation | Precision/Recall/MRR metrics |

### Run pipeline

```bash
# All steps
uv run python tests/run_all_steps.py

# Specific steps
uv run python tests/run_all_steps.py --steps 1,2,3

# Custom query
uv run python tests/retrieval/run.py --query "What is Article 5?" --top-k 3
```

## Week 2 — Agent Framework

Configurable AI agents with:
- **Personas** — JSON-defined identity, background, stance
- **Memory** — Conversation history + structured facts
- **Tools** — Extensible tool registry
- **Retrieval** — Week 1 knowledge base integration
- **LLM** — Multi-provider support

### LLM Providers

| Provider | Models | API Key |
|----------|--------|---------|
| **OpenRouter** | GPT-4o, Claude, Llama, etc. | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Gemini** | gemini-2.0-flash, gemini-1.5-pro | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Ollama** | llama3, mistral, phi3 (local) | None needed |
| **Grok** | grok-2, grok-2-mini | [console.x.ai](https://console.x.ai) |

### Configure provider

In `.env`:
```env
LLM_PROVIDER=gemini          # or openrouter, ollama, grok
GEMINI_API_KEY=your_key      # set the key for your provider
```

### Run agents

```bash
# Demo
uv run python tests/agents/demo.py

# Web UI
streamlit run app.py
```

### Personas

| Persona | Perspective |
|---------|------------|
| Dr. Sarah Chen | Pro-innovation, worries about startups |
| Prof. Marcus Williams | Rights-first, wants strong enforcement |
| Dr. Elena Petrov | Economist, cost-benefit analysis |
| Minister James Okonkwo | Global governance, international cooperation |

### Add a new persona

Create `personas/my_persona.json`:
```json
{
    "name": "Dr. Example",
    "id": "example",
    "background": "...",
    "stance": "...",
    "communication_style": "...",
    "expertise": ["area1"],
    "priorities": ["priority1"],
    "values": ["value1"]
}
```

## Web UI

```bash
streamlit run app.py
```

### Week 1 tab
- Run pipeline steps (1-5)
- Search knowledge base
- View results with sources

### Week 2 tab
- Select LLM provider
- Generate opinions from multiple agents
- Chat with agents
- View sources and grounding

## Database

```bash
# Start
docker-compose up -d

# Connect
psql -U postgres -h localhost -p 5433 -d ai_reg_rag

# Useful queries
SELECT COUNT(*) FROM chunks;
SELECT category, COUNT(*) FROM chunks GROUP BY category;
```

## Configuration

All config in `.env`. See `.env.example` for all options.

| Variable | Description |
|----------|------------|
| `POSTGRES_*` | Database connection |
| `LLM_PROVIDER` | openrouter / gemini / ollama / grok |
| `LLM_API_KEY` | API key for your provider |
| `LLM_MODEL` | Model name (auto-set by provider) |
| `LLM_TEMPERATURE` | 0.0-1.0 (default: 0.7) |

## Architecture

```
┌─────────────────┐
│  Persona (JSON) │
└────────┬────────┘
         ▼
    ┌─────────┐
    │  Agent  │
    └────┬────┘
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
 Memory Tools Retrieval LLM
                │        │
                ▼        ▼
          Week 1 DB   Provider
```
