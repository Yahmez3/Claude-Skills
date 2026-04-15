"""Draft personalized press pitch emails.

Cold outreach only works when it's specific. The template forces a "reason I'm
emailing YOU" line — not a mail-merge token.
"""
from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass


SYSTEM_PROMPT = """You write concise, personalized pitches to journalists and newsletter
operators for indie / startup app launches.

Rules:
- 4-6 sentences. No more. Editors skim.
- Subject line: <50 chars, states the hook, no emojis, no "Re:".
- First line MUST reference something specific the recipient has published. If you
  don't have it, ASK — do not invent.
- Lead with the "one sentence" (what it is + who for + what's new), not the company.
- Include one hard number or specific fact if available (users, data point, launch date).
- Offer something concrete: a demo slot, an exclusive embargo, early access.
- Sign off with full name + role. No "Sent from my iPhone".
- Never attach; link to a press kit URL.

Output strict JSON: {"subject": "...", "body": "..."}
"""


@dataclass
class PressTarget:
    recipient_name: str
    outlet: str
    recent_article: str                  # title or URL of something they wrote
    beat: str                            # e.g. "indie iOS apps", "fintech", "dev tools"


@dataclass
class AppPitch:
    app_name: str
    one_sentence: str                    # what it is + who for + what's new
    hook: str                            # why now
    proof: str                           # a number / quote / milestone
    embargo_date: str | None             # e.g. "Tuesday May 5"
    press_kit_url: str
    founder_name: str
    founder_role: str


def draft_pitch(target: PressTarget, pitch: AppPitch,
                model: str = "claude-sonnet-4-6") -> dict[str, str]:
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Install `anthropic`") from e

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = textwrap.dedent(f"""
        TARGET:
        - Name: {target.recipient_name}
        - Outlet: {target.outlet}
        - Beat: {target.beat}
        - Something they recently published: {target.recent_article}

        PITCH:
        - App: {pitch.app_name}
        - One sentence: {pitch.one_sentence}
        - Hook / why now: {pitch.hook}
        - Proof: {pitch.proof}
        - Embargo / launch date: {pitch.embargo_date or "no embargo"}
        - Press kit: {pitch.press_kit_url}
        - From: {pitch.founder_name}, {pitch.founder_role}

        Write the email as strict JSON.
    """).strip()

    resp = client.messages.create(
        model=model,
        max_tokens=800,
        system=[{"type": "text", "text": SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    import json
    # Tolerant extract
    text = text.strip()
    if text.startswith("```"):
        text = text[text.find("\n") + 1:].rsplit("```", 1)[0].strip()
    start = text.find("{")
    if start == -1:
        return {"subject": "", "body": text}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    return {"subject": "", "body": text}
