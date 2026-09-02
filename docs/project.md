# AI Regulations & Democratic Values — Project Documentation

## What is this project?

A system that studies how AI regulation affects democratic values. It has two parts:

1. **Knowledge Pipeline** — Collects documents about AI laws (EU AI Act, etc.), processes them, and makes them searchable
2. **Agent Framework** — Creates AI agents with different viewpoints who can discuss these topics and generate grounded opinions

## Why?

AI regulation is complex and affects different people differently. This project creates multiple AI "experts" — each with a different perspective (tech industry, civil rights, economics, government) — who can analyze the same topic and produce different, well-researched opinions.

## How it works

```
Web pages → Clean → Split → Vectorize → Store → Search
                                                    ↓
Personas → Agents → Retrieve Knowledge → Generate Opinions
```

## Project structure

```
├── src/
│   ├── agents/          # AI agent framework
│   ├── webui/           # Web interface
│   ├── collection/      # Data collection from web
│   ├── preprocessing/   # Text cleaning
│   ├── chunking/        # Document splitting
│   ├── embeddings/      # Vector generation
│   ├── storage/         # Database storage
│   ├── retrieval/       # Knowledge search
│   └── evaluation/      # Quality metrics
├── personas/            # Agent personality configs
├── docs/                # This documentation
├── data/                # Pipeline data
├── tests/               # Demos and tests
└── outputs/             # Generated opinions
```

## Tech used

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL + pgvector |
| Embeddings | BAAI/bge-small-en-v1.5 |
| LLM | LangChain (OpenRouter, Claude, Ollama, Gemini, Groq) |
| Web UI | FastAPI + HTML/CSS/JS |
| Scraping | trafilatura |

## Key concepts

### Persona
A JSON file defining an agent's identity, background, stance, and communication style. Different personas produce different opinions on the same topic.

### Memory
Agents remember previous conversations. Two types: conversation history (full message list) and structured facts (key-value storage).

### Retrieval
Agents search the knowledge base for relevant documents before forming opinions. This grounds their responses in actual sources.

### Tools
External capabilities agents can use. The knowledge base is one tool. A calculator is another.

## Links

- [Web UI Guide](webui.md)
- [Running Instructions](running.md)
