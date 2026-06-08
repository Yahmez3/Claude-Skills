"""Background runner that drives a TradingAgents analysis and broadcasts
per-node progress events to SSE subscribers.

Design:
  - Each /api/runs POST creates a Run row + a RunSession (event log + pub/sub)
    and spawns a daemon thread that drives ``ta.graph.stream(..., stream_mode="updates")``.
  - The thread emits events via ``loop.call_soon_threadsafe`` because the SSE
    side reads from an asyncio.Queue owned by the FastAPI event loop.
  - SSE subscribers first replay the session's full event log, then stream
    new events live. This handles late connects and reconnects.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional

from .runs import RunRegistry


logger = logging.getLogger(__name__)


# Friendly labels for the LangGraph node names — controls grouping in the UI.
NODE_GROUPS: dict[str, str] = {
    "Market Analyst": "analysts",
    "Social Analyst": "analysts",
    "News Analyst": "analysts",
    "Fundamentals Analyst": "analysts",
    "Bull Researcher": "researchers",
    "Bear Researcher": "researchers",
    "Research Manager": "researchers",
    "Trader": "trader",
    "Aggressive Analyst": "risk",
    "Conservative Analyst": "risk",
    "Neutral Analyst": "risk",
    "Portfolio Manager": "risk",
}

# State keys whose appearance/change we surface as report deltas.
REPORT_FIELDS: tuple[str, ...] = (
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
)


@dataclass
class RunSession:
    """In-memory event log + fan-out for one run.

    ``log`` lets a late SSE subscriber replay everything that already happened.
    ``subscribers`` are asyncio.Queues drained by live SSE connections.
    """
    run_id: str
    log: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    done: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, loop: asyncio.AbstractEventLoop, event: dict) -> None:
        """Called from the runner thread. Schedules fan-out on the event loop."""
        event = {**event, "ts": time.time()}
        with self._lock:
            self.log.append(event)
            subs = list(self.subscribers)
        for q in subs:
            loop.call_soon_threadsafe(_safe_put, q, event)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self.log)

    def add_subscriber(self, q: asyncio.Queue) -> None:
        with self._lock:
            self.subscribers.append(q)

    def remove_subscriber(self, q: asyncio.Queue) -> None:
        with self._lock:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass

    def mark_done(self, loop: asyncio.AbstractEventLoop) -> None:
        self.done = True
        # Wake any sleeping subscribers so they can exit cleanly.
        with self._lock:
            subs = list(self.subscribers)
        for q in subs:
            loop.call_soon_threadsafe(_safe_put, q, {"type": "_eof"})


def _safe_put(q: asyncio.Queue, event: dict) -> None:
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        # Drop the event for this slow subscriber rather than blocking the loop.
        logger.warning("SSE subscriber queue full; dropping event %s", event.get("type"))


class RunManager:
    """Owns the live RunSession map and dispatches background runs."""

    def __init__(self, registry: RunRegistry, loop: asyncio.AbstractEventLoop):
        self.registry = registry
        self.loop = loop
        self._sessions: dict[str, RunSession] = {}
        self._lock = threading.Lock()

    def get_session(self, run_id: str) -> Optional[RunSession]:
        with self._lock:
            return self._sessions.get(run_id)

    def start(
        self,
        ticker: str,
        trade_date: str,
        config_overrides: dict[str, Any],
        analysts: list[str],
    ) -> str:
        """Persist a new run, create its session, and launch the worker thread."""
        full_config = {**config_overrides, "selected_analysts": analysts}
        run = self.registry.create(ticker, trade_date, full_config)
        session = RunSession(run_id=run.id)
        with self._lock:
            self._sessions[run.id] = session
        thread = threading.Thread(
            target=self._worker,
            args=(run.id, ticker, trade_date, config_overrides, analysts),
            name=f"ta-run-{run.id}",
            daemon=True,
        )
        thread.start()
        return run.id

    def _worker(
        self,
        run_id: str,
        ticker: str,
        trade_date: str,
        config_overrides: dict[str, Any],
        analysts: list[str],
    ) -> None:
        session = self._sessions[run_id]
        try:
            self.registry.mark_started(run_id)
            session.emit(self.loop, {
                "type": "run_started",
                "ticker": ticker, "trade_date": trade_date,
                "analysts": analysts,
            })
            decision = self._drive_graph(run_id, ticker, trade_date, config_overrides, analysts, session)
            self.registry.mark_succeeded(run_id, decision)
            session.emit(self.loop, {"type": "run_succeeded", "decision": decision})
        except Exception as exc:
            tb = traceback.format_exc()
            logger.exception("Run %s failed", run_id)
            self.registry.mark_failed(run_id, str(exc))
            session.emit(self.loop, {"type": "run_failed", "error": str(exc), "traceback": tb})
        finally:
            session.mark_done(self.loop)

    def _drive_graph(
        self,
        run_id: str,
        ticker: str,
        trade_date: str,
        config_overrides: dict[str, Any],
        analysts: list[str],
        session: RunSession,
    ) -> Optional[str]:
        """Replicates TradingAgentsGraph._run_graph but with live event emission.

        We use stream_mode="updates" to get one chunk per node so the dashboard
        can show progress; we accumulate the full state ourselves to feed the
        memory log + signal processor at the end (matching propagate())."""
        # Imports are deferred so the module imports even when TradingAgents
        # is missing — useful for unit-testing the rest of the dashboard.
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        config = {**DEFAULT_CONFIG, **config_overrides}
        ta = TradingAgentsGraph(selected_analysts=analysts, debug=False, config=config)

        # Match the housekeeping propagate() does before invoking the graph.
        ta.ticker = ticker
        ta._resolve_pending_entries(ticker)

        past_context = ta.memory_log.get_past_context(ticker)
        init_state = ta.propagator.create_initial_state(
            ticker, trade_date, past_context=past_context
        )

        merged_state: dict[str, Any] = dict(init_state)
        seen_reports: set[str] = set()

        for chunk in ta.graph.stream(
            init_state,
            stream_mode="updates",
            config={"recursion_limit": config["max_recur_limit"]},
        ):
            if not isinstance(chunk, dict):
                continue
            for node_name, delta in chunk.items():
                if not isinstance(delta, dict):
                    continue
                merged_state.update(delta)
                session.emit(self.loop, {
                    "type": "node_completed",
                    "node": node_name,
                    "group": NODE_GROUPS.get(node_name, "other"),
                })
                # Surface any newly-populated report fields so the UI can
                # render them as soon as they exist, without waiting for end.
                for field in REPORT_FIELDS:
                    val = delta.get(field)
                    if val and field not in seen_reports:
                        seen_reports.add(field)
                        session.emit(self.loop, {
                            "type": "report",
                            "field": field,
                            "content": val,
                        })

        # Finalize like propagate() does: persist json log, store decision,
        # process the signal, return the BUY/SELL/HOLD label.
        ta.curr_state = merged_state
        ta._log_state(trade_date, merged_state)
        ta.memory_log.store_decision(
            ticker=ticker,
            trade_date=trade_date,
            final_trade_decision=merged_state.get("final_trade_decision", ""),
        )

        signal = ta.process_signal(merged_state.get("final_trade_decision", ""))
        return signal
