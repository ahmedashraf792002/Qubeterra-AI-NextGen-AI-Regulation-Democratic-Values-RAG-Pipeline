"""Week 2 Demo — Intelligent Agent Framework

Run:  uv run python tests/agents/demo.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.agents.persona import load_all_personas
from src.agents.agent import Agent

OUTPUTS = PROJECT_ROOT / "outputs"


def main():
    print("=" * 60)
    print("  Week 2 — Agent Framework Demo")
    print("=" * 60)

    # 1. Load personas
    personas = load_all_personas()
    print(f"\nLoaded {len(personas)} personas:")
    for p in personas:
        print(f"  - {p['name']} ({p['id']})")

    # 2. Create agents
    agents = [Agent(persona=p) for p in personas]

    # 3. Topic
    topic = "Should the EU AI Act impose strict penalties for high-risk AI violations?"
    print(f"\nTopic: {topic}")

    # 4. Show retrieval works
    print("\n--- Retrieval ---")
    if agents[0].retrieval.available:
        results = agents[0].retrieval.search(topic, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r.get('title', '?')} (sim: {r.get('similarity', 0):.4f})")
    else:
        print("  Database not running — using LLM only")

    # 5. Show memory works
    print("\n--- Memory Demo ---")
    a = agents[0]
    a.chat("I'm worried about compliance costs for startups.")
    response = a.chat("Based on what I told you, what do you think about penalties?")
    print(f"  User: I'm worried about compliance costs for startups.")
    print(f"  {a.name}: {response[:200]}...")

    # 6. Show tools work
    print("\n--- Tools ---")
    result = a.tools.invoke("calculate", expression="500000 * 0.04")
    print(f"  500,000 x 4% = {result['result']}")

    # 7. Generate opinions for ALL personas
    print("\n--- Opinions ---")
    opinions = []
    for agent in agents:
        print(f"\n  {agent.name}:")
        opinion = agent.generate_opinion(topic)
        opinions.append(opinion)
        print(f"  {opinion['opinion'][:300]}...")
        print(f"  Sources: {len(opinion['sources'])}")

    # 8. Save
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(OUTPUTS / "demo_opinions.json", "w", encoding="utf-8") as f:
        json.dump(opinions, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print("  Done! Opinions saved to outputs/demo_opinions.json")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
