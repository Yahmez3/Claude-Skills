"""LLM-powered trade review and coaching via the Anthropic SDK."""
from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field
from typing import Optional

from .models import JournalDB, Trade
from .stats import TradeStats, compute


SYSTEM_PROMPT = """\
You are an elite trading coach reviewing a trader's journal. You receive their recent \
trades and performance statistics. Your job is to identify patterns, strengths, weaknesses, \
and give actionable coaching advice.

You MUST respond with strict JSON matching this schema:

{
  "strengths": ["list of things the trader is doing well"],
  "weaknesses": ["list of areas needing improvement"],
  "patterns": ["behavioral or market patterns you notice in the trade data"],
  "action_items": ["specific, actionable steps the trader should take"],
  "overall_grade": "A single letter grade A through F"
}

Rules:
- Ground every observation in the actual trade data provided. Never invent trades.
- Be direct and specific. "Your win rate on momentum trades is 38%, well below breakeven \
for your avg win/loss ratio" is better than "Consider improving your win rate."
- Identify psychological patterns: revenge trading (rapid entries after losses), FOMO \
(chasing extended moves), premature exits (cutting winners short vs avg loss size).
- Compare risk/reward: if avg_loss > avg_win, flag it prominently.
- If the sample size is small (<10 trades), note that conclusions are tentative.
- Grade holistically: A = excellent discipline + positive expectancy, F = significant \
risk of ruin. Most active traders fall in the B-D range.
"""


@dataclass
class ReviewRequest:
    trades: list[Trade]
    stats: TradeStats
    focus: str = "general"


@dataclass
class ReviewReport:
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    overall_grade: str = ""


def _format_trades(trades: list[Trade], limit: int = 50) -> str:
    closed = [t for t in trades if t.pnl is not None]
    if not closed:
        closed = trades[:limit]
    else:
        closed = closed[:limit]

    lines: list[str] = []
    for t in closed:
        hold = ""
        if t.closed_at and t.timestamp:
            delta = t.closed_at - t.timestamp
            hours = delta.total_seconds() / 3600
            hold = f" hold={hours:.1f}h"

        pnl_str = f" pnl={t.pnl:+.2f}" if t.pnl is not None else ""
        tags_str = f" [{','.join(t.tags)}]" if t.tags else ""
        lines.append(
            f"{t.timestamp.strftime('%Y-%m-%d %H:%M')} {t.side.upper()} "
            f"{t.quantity} {t.symbol} @{t.price:.2f} "
            f"strategy={t.strategy}{tags_str}{pnl_str}{hold}"
            f"{' | ' + t.notes if t.notes else ''}"
        )
    return "\n".join(lines)


def _format_stats(stats: TradeStats) -> str:
    lines = [
        f"Strategy: {stats.strategy} | Symbol: {stats.symbol}",
        f"Total trades: {stats.total_trades}",
        f"Win rate: {stats.win_rate:.1%} ({stats.winners}W / {stats.losers}L)",
        f"Avg win: {stats.avg_win:+.2f} | Avg loss: {stats.avg_loss:+.2f}",
        f"Profit factor: {stats.profit_factor:.2f}",
        f"Total P&L: {stats.total_pnl:+.2f}",
        f"Max win: {stats.max_win:+.2f} | Max loss: {stats.max_loss:+.2f}",
        f"Expectancy: {stats.expectancy:+.2f}",
    ]
    if stats.sharpe is not None:
        lines.append(f"Sharpe: {stats.sharpe:.2f}")
    if stats.avg_hold_time is not None:
        hours = stats.avg_hold_time.total_seconds() / 3600
        lines.append(f"Avg hold time: {hours:.1f}h")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        text = text[first_nl + 1:].rstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()
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
                return json.loads(text[start : i + 1])
    return {}


def review(
    request: ReviewRequest,
    model: str = "claude-sonnet-4-6",
) -> ReviewReport:
    """Run an LLM trade review. Requires ANTHROPIC_API_KEY env var."""
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Install `anthropic` to use LLM review") from e

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    focus_instructions = {
        "general": "Give an overall assessment of trading performance.",
        "risk": "Focus on position sizing, stop placement, and risk/reward ratios.",
        "entries": "Focus on entry timing, signal quality, and confirmation.",
        "exits": "Focus on exit timing, profit-taking discipline, and stop management.",
        "psychology": "Focus on emotional patterns: revenge trading, FOMO, overtrading, "
        "discipline breakdown after losses.",
    }

    user_msg = textwrap.dedent(f"""
        FOCUS: {request.focus} — {focus_instructions.get(request.focus, focus_instructions['general'])}

        PERFORMANCE STATS:
        {_format_stats(request.stats)}

        TRADE LOG:
        {_format_trades(request.trades)}

        Produce the JSON coaching report now.
    """).strip()

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_msg}],
    )

    text = "".join(b.text for b in resp.content if b.type == "text")
    data = _extract_json(text)

    return ReviewReport(
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        patterns=data.get("patterns", []),
        action_items=data.get("action_items", []),
        overall_grade=data.get("overall_grade", ""),
    )


def quick_review(
    db: JournalDB,
    strategy: Optional[str] = None,
    last_n: int = 20,
    focus: str = "general",
    model: str = "claude-sonnet-4-6",
) -> ReviewReport:
    """Convenience wrapper: pull recent trades from the DB and review them."""
    trades = db.query(strategy=strategy)
    trades = trades[-last_n:]
    if not trades:
        return ReviewReport(
            strengths=[],
            weaknesses=["No trades found to review."],
            patterns=[],
            action_items=["Start logging trades to enable coaching."],
            overall_grade="N/A",
        )
    stats = compute(trades)
    return review(ReviewRequest(trades=trades, stats=stats, focus=focus), model=model)
