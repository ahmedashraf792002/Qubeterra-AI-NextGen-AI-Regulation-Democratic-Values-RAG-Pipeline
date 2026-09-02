"""Prompts for agent behavior."""

SYSTEM_PROMPT = """\
You are {name}.

Background: {background}
Your stance on AI regulation: {stance}
Communication style: {communication_style}

Guidelines:
- Ground responses in retrieved evidence when available.
- Cite sources by title and URL.
- Distinguish facts from your interpretation.
- Be concise.
"""

OPINION_PROMPT = """\
Generate your initial opinion on this topic.

Topic: {topic}

Retrieved evidence:
{evidence}

Structure your response as:
1. **Summary opinion** (2-3 sentences)
2. **Key reasoning** (3-5 bullet points citing sources)
3. **Confidence level** (high/medium/low)
4. **Sources used**

Respond in character.
"""


def build_system_prompt(persona, extra=""):
    """Build system prompt from persona dict."""
    text = SYSTEM_PROMPT.format(
        name=persona["name"],
        background=persona["background"],
        stance=persona["stance"],
        communication_style=persona["communication_style"],
    )
    if extra:
        text += f"\n\n{extra}"
    return text


def build_opinion_prompt(topic, evidence):
    """Build opinion generation prompt."""
    return OPINION_PROMPT.format(topic=topic, evidence=evidence)
