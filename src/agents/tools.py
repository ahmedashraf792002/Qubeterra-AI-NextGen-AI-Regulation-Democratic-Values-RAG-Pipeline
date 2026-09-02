"""Tools — simple function registry with web search capability."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Conversation logger
conversation_logger = logging.getLogger("conversation")
conversation_handler = logging.FileHandler(LOG_DIR / "conversations.log", encoding="utf-8")
conversation_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
conversation_logger.addHandler(conversation_handler)
conversation_logger.setLevel(logging.INFO)

# Error logger
error_logger = logging.getLogger("errors")
error_handler = logging.FileHandler(LOG_DIR / "errors.log", encoding="utf-8")
error_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.INFO)


def log_conversation(agent_name, message, response, tool_used=None):
    """Log a conversation turn."""
    tool_info = f" | tool: {tool_used}" if tool_used else ""
    conversation_logger.info(f"{agent_name} | user: {message[:100]}... | response: {response[:100]}...{tool_info}")


def log_error(agent_name, error, context=""):
    """Log an error."""
    error_logger.info(f"{agent_name} | {context} | {error}")


class Tool:
    def __init__(self, name, description, func, parameters=None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or []

    def run(self, **kwargs):
        try:
            return {"ok": True, "result": self.func(**kwargs)}
        except Exception as e:
            log_error("tool", str(e), context=f"tool:{self.name}")
            return {"ok": False, "error": str(e)}

    def to_prompt(self):
        """Human-readable description for the system prompt."""
        params = []
        for p in self.parameters:
            req = "required" if p.get("required", True) else "optional"
            params.append(f"  - {p['name']} ({p['type']}): {p['description']} [{req}]")
        param_str = "\n".join(params) if params else "  (no parameters)"
        return f"Tool: {self.name}\n{self.description}\nParameters:\n{param_str}"


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    def invoke(self, name, **kwargs):
        tool = self.tools.get(name)
        if not tool:
            return {"ok": False, "error": f"Tool '{name}' not found"}
        return tool.run(**kwargs)

    def descriptions(self):
        if not self.tools:
            return "No tools available."
        return "\n\n".join(t.to_prompt() for t in self.tools.values())

    def list_names(self):
        return list(self.tools.keys())


def make_calc_tool():
    """A simple calculator tool."""
    def calc(expression):
        return str(eval(compile(
            __import__("ast").parse(expression, mode="eval"),
            "<calc>", "eval"
        )))
    return Tool(
        name="calculate",
        description="Evaluate a math expression (e.g. 2+3*4).",
        func=calc,
        parameters=[{"name": "expression", "type": "string",
                      "description": "Math expression to evaluate", "required": True}]
    )


def make_web_search_tool(retrieval, scrape_func=None):
    """Web search tool that searches knowledge base or scrapes web."""
    def search(query, source="knowledge_base", top_k=5):
        if source == "web" and scrape_func:
            return scrape_func(query)
        return retrieval.search(query, top_k=top_k)
    return Tool(
        name="search",
        description="Search for information. Use source='knowledge_base' for existing documents or source='web' for live web search.",
        func=search,
        parameters=[
            {"name": "query", "type": "string", "description": "Search query", "required": True},
            {"name": "source", "type": "string", "description": "Source: 'knowledge_base' or 'web'", "required": False},
            {"name": "top_k", "type": "integer", "description": "Number of results", "required": False},
        ]
    )
