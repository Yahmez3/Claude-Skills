"""Draft review responses using Claude.

Output is always a DRAFT — human must review and post manually. App Store and Play
Store treat developer responses as public statements; a bad auto-reply does real damage.
"""
from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass


SYSTEM_PROMPT = """You draft developer replies to app-store reviews.

Style:
- Warm, specific, human. No corporate-speak, no "Thanks for reaching out!".
- Acknowledge the reviewer's actual complaint first. Name it.
- If a bug: confirm the fix status. If fixed: name the version. If in-progress: give a rough window. Never promise a date.
- If a feature request: say whether it's on the roadmap honestly. Don't commit to things that aren't.
- If a misunderstanding: gently clarify without making the user feel dumb.
- End with one concrete next step (email support@, wait for vX.Y, check a Settings path).
- 2-4 sentences. Under 350 characters where possible (Apple cuts off earlier on mobile).
- Never apologize reflexively for things that aren't the team's fault. Don't grovel.
- Never reference competitors by name.
- Never ask the user to change their rating (violation of store policies).

Output strict JSON: {"response": "...", "requires_action": "brief internal note or empty", "tags": ["bug"|"feature"|"ux"|"pricing"|"support"|"misunderstanding"]}
"""


@dataclass
class ReviewInput:
    stars: int
    title: str
    body: str
    version: str = ""
    author: str = ""


@dataclass
class ResponseDraft:
    response: str
    requires_action: str = ""
    tags: list[str] = None


def draft_response(review: ReviewInput,
                   app_name: str,
                   app_context: str = "",
                   current_version: str = "",
                   known_issues: list[str] | None = None,
                   roadmap: list[str] | None = None,
                   model: str = "claude-sonnet-4-6") -> ResponseDraft:
    """Draft a single review response. Requires ANTHROPIC_API_KEY."""
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Install `anthropic`") from e

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    context = textwrap.dedent(f"""
        APP: {app_name}
        APP CONTEXT: {app_context}
        CURRENT VERSION: {current_version}
        KNOWN ISSUES (confirmed bugs): {known_issues or []}
        ON ROADMAP (features we intend to ship): {roadmap or []}

        REVIEW:
        {review.stars}★  v{review.version}  by {review.author}
        Title: {review.title}
        Body:  {review.body}

        Draft the response now as strict JSON.
    """).strip()

    resp = client.messages.create(
        model=model,
        max_tokens=800,
        system=[{
            "type": "text", "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": context}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = _extract_json(text)
    return ResponseDraft(
        response=data.get("response", "").strip(),
        requires_action=data.get("requires_action", ""),
        tags=data.get("tags", []),
    )


def batch_draft(reviews: list[ReviewInput], app_name: str, **kwargs) -> list[ResponseDraft]:
    return [draft_response(r, app_name, **kwargs) for r in reviews]


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        nl = text.find("\n")
        text = text[nl + 1:].rsplit("```", 1)[0].strip()
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


if __name__ == "__main__":
    example = ReviewInput(
        stars=2,
        title="Sync broke after last update",
        body="Everything was fine until 2.3. Now my transactions from last week are gone when I switch devices.",
        version="2.3.0", author="mcolby",
    )
    draft = draft_response(
        example,
        app_name="Budget Buddy",
        app_context="Personal finance / budgeting app",
        current_version="2.3.1",
        known_issues=["sync race on iCloud in 2.3.0 — fix shipped in 2.3.1"],
    )
    print(draft.response)
    print(f"[internal] {draft.requires_action} / tags={draft.tags}")
