"""Memory — conversation history + simple fact storage."""

import json
from pathlib import Path


class Memory:
    def __init__(self):
        self.messages = []      # [{"role": "user/assistant", "content": "..."}]
        self.facts = {}         # {"key": "value"}

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return list(self.messages)

    def get_recent(self, n=10):
        return self.messages[-n:]

    def store_fact(self, key, value, source=""):
        self.facts[key] = {"value": value, "source": source}

    def get_fact(self, key):
        return self.facts.get(key, {}).get("value")

    def facts_to_prompt(self):
        """Render stored facts for the system prompt."""
        if not self.facts:
            return ""
        lines = ["Known information:"]
        for k, v in self.facts.items():
            src = f" (from {v['source']})" if v.get("source") else ""
            lines.append(f"- {k}: {v['value']}{src}")
        return "\n".join(lines)

    def save(self, path):
        """Save facts to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, indent=2, ensure_ascii=False)

    def load(self, path):
        """Load facts from a JSON file."""
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self.facts = json.load(f)
