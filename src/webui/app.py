"""Qubeterra AI NextGen — Web UI Backend (FastAPI)

Run:  uvicorn src.webui.app:app --reload --port 8000
"""

import os
import sys
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

app = FastAPI(title="Qubeterra AI NextGen")
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE_DIR = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class OpinionRequest(BaseModel):
    topic: str
    persona_ids: list[str]
    provider: str = "ollama"

class ChatRequest(BaseModel):
    message: str
    persona_id: str
    provider: str = "ollama"
    history: list[dict] = []

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str = ""

class ScrapeRequest(BaseModel):
    url: str = ""
    text_query: str = ""

class PipelineRequest(BaseModel):
    steps: list[int]


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = TEMPLATE_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/personas")
def list_personas():
    from src.agents.persona import load_all_personas
    return load_all_personas()


@app.get("/api/providers")
def list_providers():
    from src.agents.llm import PROVIDERS
    return PROVIDERS


@app.post("/api/opinion")
def generate_opinion(req: OpinionRequest):
    from src.agents.persona import load_all_personas
    from src.agents.agent import Agent
    personas = load_all_personas()
    results = []
    for pid in req.persona_ids:
        p = next((x for x in personas if x["id"] == pid), None)
        if not p:
            continue
        agent = Agent(persona=p, provider=req.provider)
        opinion = agent.generate_opinion(req.topic)
        results.append(opinion)
    return {"opinions": results}


@app.post("/api/chat")
def chat(req: ChatRequest):
    from src.agents.persona import load_all_personas
    from src.agents.agent import Agent
    personas = load_all_personas()
    p = next((x for x in personas if x["id"] == req.persona_id), None)
    if not p:
        return {"error": "Persona not found"}
    agent = Agent(persona=p, provider=req.provider)
    for msg in req.history:
        agent.memory.add_message(msg["role"], msg["content"])
    result = agent.chat(req.message)
    response, tool_used = result[0], result[1]
    return {"response": response, "tool_used": tool_used}


@app.post("/api/search")
def search(req: SearchRequest):
    from src.agents.agent import _get_retrieval
    r = _get_retrieval()
    cat = req.category if req.category else None
    top_k = max(1, min(req.top_k, 50))
    if not r.available:
        return {"results": [], "error": "Knowledge base not available. Run Week 1 pipeline first."}
    results = r.search(req.query, top_k=top_k, category=cat)
    return {"results": results}


@app.post("/api/scrape")
def scrape(req: ScrapeRequest):
    results = []
    if req.url:
        try:
            import trafilatura
            import httpx
            downloaded = trafilatura.fetch_url(req.url)
            if not downloaded:
                try:
                    r = httpx.get(req.url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    }, timeout=15, follow_redirects=True)
                    downloaded = r.text if r.status_code == 200 else None
                except:
                    downloaded = None
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text:
                    results.append({"url": req.url, "text": text[:2000], "status": "ok"})
                else:
                    results.append({"url": req.url, "text": "", "status": "no_content"})
            else:
                results.append({"url": req.url, "text": "", "status": "fetch_failed (JS-heavy or blocked)"})
        except Exception as e:
            results.append({"url": req.url, "text": "", "status": f"error: {e}"})

    elif req.text_query:
        try:
            import trafilatura
            # Use trafilatura's built-in search
            try:
                search_results = trafilatura.search(req.text_query, max_results=5)
            except:
                search_results = []
            
            if not search_results:
                # Fallback: use curated URLs
                curated_urls = [
                    "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
                    "https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act",
                    "https://digital-strategy.ec.europa.eu/en/news/commission-starts-enforcing-ai-act-rules-and-new-transparency-requirements-2-august",
                    "https://digital-strategy.ec.europa.eu/en/policies/ai-board",
                    "https://en.wikipedia.org/wiki/Artificial_Intelligence_Act",
                ]
                search_results = [{"url": u, "title": ""} for u in curated_urls[:5]]
            
            for item in search_results:
                url = item.get("url", "")
                if not url:
                    continue
                try:
                    downloaded = trafilatura.fetch_url(url)
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text and len(text) > 100:
                            results.append({"url": url, "text": text[:2000], "status": "ok"})
                except:
                    continue
        except Exception as e:
            results.append({"url": "", "text": f"Search error: {e}", "status": "error"})

    return {"results": results, "count": len(results)}


@app.post("/api/pipeline/run")
def run_pipeline(req: PipelineRequest):
    STEPS = {
        1: ("Collection", "src/collection/data_collection.py"),
        2: ("Preprocessing", "src/preprocessing/clean_documents.py"),
        3: ("Chunking", "src/chunking/chunk_documents.py"),
        4: ("Embeddings", "src/embeddings/generate_embeddings.py"),
        5: ("Storage", "src/storage/load_to_postgres.py"),
    }
    outputs = []
    for step_num in req.steps:
        if step_num not in STEPS:
            outputs.append({"step": step_num, "status": "unknown"})
            continue
        name, script = STEPS[step_num]
        try:
            result = subprocess.run(
                ["uv", "run", "python", script],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=300,
            )
            outputs.append({
                "step": step_num, "name": name,
                "status": "ok" if result.returncode == 0 else "error",
                "output": result.stdout[-1000:] if result.stdout else "",
                "error": result.stderr[-500:] if result.returncode != 0 else "",
            })
        except subprocess.TimeoutExpired:
            outputs.append({"step": step_num, "name": name, "status": "timeout"})
        except Exception as e:
            outputs.append({"step": step_num, "name": name, "status": f"error: {e}"})
    return {"results": outputs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
