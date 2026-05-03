"""Read-only views over TradingAgents' on-disk artifacts.

We never mutate these files — TradingAgents owns them. The dashboard just
parses them so it can render past decisions and full per-run reports next
to the live event stream.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def _home() -> Path:
    return Path(os.path.expanduser("~")) / ".tradingagents"


def memory_log_path() -> Path:
    override = os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH")
    if override:
        return Path(override).expanduser()
    return _home() / "memory" / "trading_memory.md"


def results_dir() -> Path:
    override = os.getenv("TRADINGAGENTS_RESULTS_DIR")
    if override:
        return Path(override).expanduser()
    return _home() / "logs"


def load_memory_entries() -> list[dict]:
    """Parse all entries from the trading memory log.

    Delegates to TradingAgents' own parser when available so we stay in sync
    with its on-disk format. Falls back to an empty list if the package
    isn't installed (e.g. the dashboard is running without TradingAgents
    on the path for some smoke test)."""
    try:
        from tradingagents.agents.utils.memory import TradingMemoryLog
    except ImportError:
        return []
    log = TradingMemoryLog({"memory_log_path": str(memory_log_path())})
    return log.load_entries()


def load_run_artifacts(ticker: str, trade_date: str) -> Optional[dict[str, Any]]:
    """Load the full per-run JSON dump that TradingAgents writes after each run.

    Path: ``<results_dir>/<TICKER>/TradingAgentsStrategy_logs/full_states_log_<date>.json``
    Returns None if the file doesn't exist yet (run still in flight or never ran).
    """
    safe = ticker.replace("/", "_").replace("\\", "_")
    path = results_dir() / safe / "TradingAgentsStrategy_logs" / f"full_states_log_{trade_date}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
