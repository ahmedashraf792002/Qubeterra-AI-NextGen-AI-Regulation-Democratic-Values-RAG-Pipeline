"""Agent — LangGraph-based state machine for persona-driven conversations.

Uses StateGraph for conditional routing between KB retrieval, web search,
and LLM generation. Memory is managed via InMemorySaver checkpointer.
"""

from typing import TypedDict, Literal, Annotated
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.persona import persona_to_prompt
from src.agents.memory import Memory
from src.agents.tools import ToolRegistry, Tool, make_calc_tool, log_conversation, log_error
from src.agents.retrieval import Retrieval
from src.agents.llm import build_model
from src.agents.prompts import build_system_prompt, build_opinion_prompt


# ── Cached retrieval instance (created once, reused) ─────────
_retrieval_cache = None
_kb_available = None  # None = not checked yet

def _get_retrieval():
    global _retrieval_cache, _kb_available
    if _retrieval_cache is None:
        _retrieval_cache = Retrieval()
        _kb_available = _retrieval_cache.available
    return _retrieval_cache

def is_kb_available():
    """Check if KB is available without creating connections."""
    global _kb_available
    if _kb_available is None:
        _get_retrieval()
    return _kb_available


# ── Agent State ──────────────────────────────────────────────

class AgentState(TypedDict):
    user_message: str
    persona: dict
    tool_choice: str
    evidence: str
    messages: list  # conversation history as [{"role": ..., "content": ...}]
    response: str


# ── Graph Node Functions ─────────────────────────────────────

def route_node(state: AgentState) -> Command[Literal["retrieve_kb", "search_web", "generate"]]:
    """Decide which tool to use based on keyword matching."""
    msg = state["user_message"].lower()
    kb_ready = is_kb_available()

    kb_keywords = ["ai act", "regulation", "european", "eu", "law", "legal", "article",
                   "transparency", "high-risk", "prohibited", "compliance", "gdpr"]
    web_keywords = ["news", "latest", "today", "current", "recent", "update",
                    "what is happening", "breaking", "new developments"]

    kb_score = sum(1 for kw in kb_keywords if kw in msg)
    web_score = sum(1 for kw in web_keywords if kw in msg)

    if not kb_ready:
        # KB not available — skip retrieval, go straight to generate
        return Command(update={"tool_choice": "none"}, goto="generate")

    if web_score > kb_score:
        return Command(update={"tool_choice": "web_search"}, goto="search_web")
    else:
        return Command(update={"tool_choice": "knowledge_retrieval"}, goto="retrieve_kb")


def retrieve_kb_node(state: AgentState) -> dict:
    """Search the knowledge base for relevant evidence."""
    retrieval = _get_retrieval()
    if not retrieval.available:
        return {"evidence": ""}

    results = retrieval.search(state["user_message"], top_k=5)
    evidence = retrieval.format_results(results)
    return {"evidence": evidence}


def search_web_node(state: AgentState) -> dict:
    """Search the live web for current information."""
    import trafilatura

    query = state["user_message"]
    results = []

    try:
        search_results = trafilatura.search(query, max_results=3)
    except Exception:
        search_results = []

    for item in (search_results or []):
        url = item.get("url", "")
        if not url:
            continue
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text and len(text) > 100:
                    results.append({"url": url, "text": text[:1500], "title": item.get("title", "")})
        except Exception:
            continue

    if not results:
        return {"evidence": ""}

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', 'Untitled')} ({r['url']})\n    {r['text'][:500]}")
    return {"evidence": "\n\n".join(lines)}


def generate_node(state: AgentState) -> dict:
    """Generate a response using the LLM with persona and evidence."""
    persona = state["persona"]
    evidence = state.get("evidence", "")
    user_message = state["user_message"]
    history = state.get("messages", [])

    llm = build_model()
    system_text = build_system_prompt(persona, extra=evidence if evidence else "")

    messages = [SystemMessage(content=system_text)]
    for msg in history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    content = response.content

    log_conversation(persona["name"], user_message, content, tool_used=state.get("tool_choice", ""))

    # Update conversation history
    new_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": content},
    ]

    return {"response": content, "messages": new_history}


# ── Build the Graph ──────────────────────────────────────────

def build_agent_graph():
    """Build and compile the LangGraph agent."""
    builder = StateGraph(AgentState)

    builder.add_node("route", route_node)
    builder.add_node("retrieve_kb", retrieve_kb_node)
    builder.add_node("search_web", search_web_node)
    builder.add_node("generate", generate_node)

    builder.add_edge(START, "route")
    builder.add_edge("retrieve_kb", "generate")
    builder.add_edge("search_web", "generate")
    builder.add_edge("generate", END)

    memory = InMemorySaver()
    return builder.compile(checkpointer=memory)


# Lazy-loaded compiled graph (avoids slow SentenceTransformer init on import)
_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


# ── Agent Wrapper (keeps same interface for app.py) ──────────

class Agent:
    """Agent class wrapping the LangGraph state machine."""

    def __init__(self, persona, provider=None):
        self.persona = persona
        self.name = persona["name"]
        self.memory = Memory()
        self.tools = ToolRegistry()
        self.retrieval = _get_retrieval()
        self._last_tool = None
        self._thread_id = f"{persona['id']}_{id(self)}"
        self._config = {"configurable": {"thread_id": self._thread_id}}

        # Register tools for backward compatibility
        if self.retrieval.available:
            self.tools.register(Tool(
                name="knowledge_retrieval",
                description="Search the AI regulations knowledge base.",
                func=lambda query, top_k=5: self.retrieval.search(query, top_k),
                parameters=[{"name": "query", "type": "string",
                              "description": "Search query", "required": True}]
            ))

        self.tools.register(make_calc_tool())

    def chat(self, message):
        """Chat using the LangGraph state machine."""
        # Add user message to local memory for history tracking
        self.memory.add_message("user", message)

        # Build initial state
        initial_state = {
            "user_message": message,
            "persona": self.persona,
            "tool_choice": "",
            "evidence": "",
            "messages": self.memory.get_recent(10),
            "response": "",
        }

        # Run the graph
        graph = get_agent_graph()
        result = graph.invoke(initial_state, self._config)
        tool_choice = result.get("tool_choice", "")
        response = result.get("response", "")

        # Update local memory with new messages from graph
        new_messages = result.get("messages", [])
        if len(new_messages) > len(self.memory.get_recent(10)):
            # Only add the new messages
            for msg in new_messages[len(self.memory.get_recent(10)):]:
                self.memory.add_message(msg["role"], msg["content"])

        self._last_tool = tool_choice
        return response, tool_choice

    def generate_opinion(self, topic):
        """Generate opinion using the LangGraph state machine."""
        retrieval = _get_retrieval()
        evidence = ""

        if retrieval.available:
            results = retrieval.search(topic, top_k=5)
            evidence = retrieval.format_results(results)

        user_prompt = build_opinion_prompt(topic, evidence)

        initial_state = {
            "user_message": user_prompt,
            "persona": self.persona,
            "tool_choice": "",
            "evidence": evidence,
            "messages": self.memory.get_recent(10),
            "response": "",
        }

        graph = get_agent_graph()
        result = graph.invoke(initial_state, self._config)
        opinion = result.get("response", "")
        tool_choice = result.get("tool_choice", "")

        key = f"opinion_{topic[:50].lower().replace(' ', '_')}"
        self.memory.store_fact(key, opinion, source="generated")

        log_conversation(self.name, topic, opinion, tool_used=tool_choice)

        return {
            "topic": topic,
            "persona": self.name,
            "persona_id": self.persona["id"],
            "opinion": opinion,
            "sources": retrieval.citations(retrieval.search(topic, top_k=5)) if retrieval.available else [],
            "tool_used": tool_choice,
        }
