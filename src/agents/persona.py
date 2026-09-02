"""Persona — loaded from JSON files in personas/ directory."""

import json
from pathlib import Path


PERSONAS_DIR = Path(__file__).resolve().parents[2] / "personas"


def load_persona(path):
    """Load a persona from a JSON file. Returns a dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_personas(directory=None):
    """Load all .json files from personas/ directory. Returns list of dicts."""
    directory = Path(directory) if directory else PERSONAS_DIR
    personas = []
    for path in sorted(directory.glob("*.json")):
        try:
            personas.append(load_persona(path))
        except json.JSONDecodeError as e:
            print(f"Skipping {path.name}: {e}")
    return personas


def persona_to_prompt(p):
    """Convert a persona dict to a system prompt section."""
    lines = [f"You are {p['name']}."]
    lines.append(f"Background: {p['background']}")
    lines.append(f"Your stance on AI regulation: {p['stance']}")
    lines.append(f"Communication style: {p['communication_style']}")

    if p.get("expertise"):
        lines.append(f"Expertise: {', '.join(p['expertise'])}.")
    if p.get("priorities"):
        lines.append(f"Priorities: {', '.join(p['priorities'])}.")
    if p.get("values"):
        lines.append(f"Values: {', '.join(p['values'])}.")
    if p.get("description"):
        lines.append(f"\n{p['description']}")

    return "\n".join(lines)
