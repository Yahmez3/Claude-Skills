"""Minimal alerting via webhooks (Discord / Slack) for fills, errors, daily summaries."""
from __future__ import annotations

import json
import os
from urllib import request


def post_webhook(url: str, text: str) -> None:
    body = json.dumps({"content": text, "text": text}).encode()
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        request.urlopen(req, timeout=5)
    except Exception:
        pass  # alerts should never crash the bot


def alert(text: str) -> None:
    for env in ("DISCORD_WEBHOOK_URL", "SLACK_WEBHOOK_URL"):
        url = os.environ.get(env)
        if url:
            post_webhook(url, text)


def daily_summary(account_equity: float, pnl: float, n_trades: int) -> None:
    sign = "+" if pnl >= 0 else ""
    alert(f"Daily: equity=${account_equity:,.2f} pnl={sign}${pnl:,.2f} trades={n_trades}")
