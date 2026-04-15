"""LLM-powered qualitative gap analysis via the Anthropic SDK.

Call this when you want themes the statistical pipeline can miss — emotional tone,
implied workflows, specific competitor mentions, pricing psychology.

Uses prompt caching on the system prompt so repeat runs are cheap.
"""
from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field
from typing import Optional

from .reviews import Review


SYSTEM_PROMPT = """You are a senior product strategist performing a gap analysis on a \
competitor app. You receive the app's category, description, and a sample of 1-2 star \
reviews. You MUST respond with strict JSON matching this schema:

{
  "themes": [
    {
      "name": "short kebab-case id",
      "description": "one sentence plain-English theme",
      "severity": 1-5 integer (user impact),
      "frequency_estimate_pct": 0-100 number (est. share of complaints),
      "tags": [one-or-more-of: missing_feature, ux_friction, performance, pricing, \
reliability, privacy, platform_gap, support],
      "quotes": [up to 3 short verbatim excerpts, <=200 chars each],
      "opportunity": "one sentence on what a competitor could offer to address this"
    }
  ],
  "underserved_segments": [
    {"segment": "who", "evidence": "why from reviews"}
  ],
  "incumbent_strengths": ["things NOT to try to beat head-on"],
  "differentiation_thesis": "2-3 sentences: where a new entrant can credibly win"
}

Rules:
- Only use evidence grounded in the reviews provided. Don't invent complaints.
- If reviews are sparse or thin, say so in differentiation_thesis.
- Deduplicate themes; aim for 4-7 distinct themes total.
- Tag each theme with taxonomy tags — multi-tag is fine.
- Quotes must be faithful (may truncate with ellipsis; never paraphrase).
"""


@dataclass
class LLMReport:
    themes: list[dict] = field(default_factory=list)
    underserved_segments: list[dict] = field(default_factory=list)
    incumbent_strengths: list[str] = field(default_factory=list)
    differentiation_thesis: str = ""
    raw: dict = field(default_factory=dict)


def _format_reviews(reviews: list[Review], limit: int = 80) -> str:
    # Sort by helpfulness first, then recency
    sorted_r = sorted(reviews, key=lambda r: (r.helpful, r.posted_at or ""), reverse=True)[:limit]
    lines = []
    for i, r in enumerate(sorted_r, start=1):
        body = (r.body or "").replace("\n", " ").strip()
        if len(body) > 400:
            body = body[:397] + "..."
        title = (r.title or "").strip()
        lines.append(f"[{i}] {r.stars}★ v{r.version} helpful={r.helpful}: "
                     f"{title + ' — ' if title else ''}{body}")
    return "\n".join(lines)


def analyze(
    app_name: str,
    category: str,
    description: str,
    negative_reviews: list[Review],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> LLMReport:
    """Run the LLM gap analysis. Requires ANTHROPIC_API_KEY env var."""
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Install `anthropic` to use LLM analysis") from e

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    reviews_block = _format_reviews(negative_reviews)

    user = textwrap.dedent(f"""
        APP: {app_name}
        CATEGORY: {category}
        DESCRIPTION:
        {description.strip()[:2000]}

        NEGATIVE REVIEWS (1-2 stars, sorted by helpfulness):
        {reviews_block}

        Produce the JSON report now.
    """).strip()

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user}],
    )

    text = "".join(b.text for b in resp.content if b.type == "text")
    data = _extract_json(text)
    return LLMReport(
        themes=data.get("themes", []),
        underserved_segments=data.get("underserved_segments", []),
        incumbent_strengths=data.get("incumbent_strengths", []),
        differentiation_thesis=data.get("differentiation_thesis", ""),
        raw=data,
    )


def _extract_json(text: str) -> dict:
    """Tolerant JSON extraction — handles code fences and leading prose."""
    text = text.strip()
    if text.startswith("```"):
        # strip fence
        first_nl = text.find("\n")
        text = text[first_nl + 1:].rstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()
    # Find first { and match braces
    start = text.find("{")
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    return {}


def reconcile(statistical_gaps, llm_report: LLMReport) -> list[dict]:
    """Intersect statistical clusters with LLM themes by tag overlap + keyword match.

    Returns a unified list of gaps with both evidences.
    """
    unified: list[dict] = []
    for theme in llm_report.themes:
        theme_tags = set(theme.get("tags", []))
        best = None
        for gap in statistical_gaps:
            if theme_tags & set(gap.tags):
                if best is None or gap.n_reviews > best.n_reviews:
                    best = gap
        unified.append({
            "name": theme.get("name"),
            "description": theme.get("description"),
            "severity_llm": theme.get("severity"),
            "frequency_llm_pct": theme.get("frequency_estimate_pct"),
            "frequency_stat_pct": best.frequency_pct if best else None,
            "tags": list(theme_tags),
            "quotes_llm": theme.get("quotes", []),
            "quotes_stat": best.examples if best else [],
            "keywords_stat": best.keywords if best else [],
            "opportunity": theme.get("opportunity", ""),
            "high_confidence": bool(best),
        })
    return unified
