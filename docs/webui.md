# Web UI Guide

## Start

```bash
uvicorn src.webui.app:app --reload --port 8000
```

Open: http://localhost:8000

## Provider Selection

At the top of the page, click a provider button to switch between:
- Ollama (local)
- OpenRouter
- Claude
- Gemini
- Groq

## Week 1 — Knowledge Pipeline

### Run Pipeline
1. Check the steps you want to run (1-5)
2. Click "Run Selected"
3. View output for each step

### Search Knowledge Base
1. Type a question or search term
2. Choose category (optional)
3. Click "Search"
4. View results with similarity scores

### Scrape Documents

**By URL:**
1. Enter a URL (e.g., EU AI Act page)
2. Click "Scrape URL"
3. View extracted text

**By Text Query:**
1. Enter a search term
2. Click "Search & Scrape"
3. System finds relevant pages and extracts content

## Week 2 — Agent Framework

### Generate Opinions
1. Enter a topic (or use the default)
2. Select which agents to use
3. Click "Generate Opinions"
4. View each agent's opinion with sources

### Chat
1. Select an agent from the dropdown
2. Type a message
3. Press Enter or click Send
4. Agent responds based on its persona

## API

The web UI uses these endpoints:

| Endpoint | What it does |
|----------|-------------|
| `GET /api/personas` | List all personas |
| `GET /api/providers` | List LLM providers |
| `POST /api/opinion` | Generate opinion |
| `POST /api/chat` | Chat with agent |
| `POST /api/search` | Search knowledge base |
| `POST /api/scrape` | Scrape URL or query |
| `POST /api/pipeline/run` | Run pipeline steps |
