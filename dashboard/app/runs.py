"""SQLite registry for dashboard runs.

Stores only the dashboard's own metadata (which run, what status, when started).
The detailed agent output lives in the TradingAgents log dirs and memory log;
this table just lets us list/query runs and link to their artifacts.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            TEXT PRIMARY KEY,
    ticker        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    status        TEXT NOT NULL,           -- queued | running | succeeded | failed | cancelled
    config_json   TEXT NOT NULL,           -- the config dict the run was launched with
    decision      TEXT,                    -- final BUY/SELL/HOLD signal once known
    error         TEXT,                    -- error message if failed
    created_at    REAL NOT NULL,
    started_at    REAL,
    finished_at   REAL
);

CREATE INDEX IF NOT EXISTS runs_created_idx ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS runs_ticker_date_idx ON runs(ticker, trade_date);
"""


@dataclass
class Run:
    id: str
    ticker: str
    trade_date: str
    status: str
    config: dict
    decision: Optional[str]
    error: Optional[str]
    created_at: float
    started_at: Optional[float]
    finished_at: Optional[float]

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class RunRegistry:
    """Thread-safe SQLite-backed registry of dashboard runs."""

    def __init__(self, db_path: str | Path):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # check_same_thread=False so the FastAPI worker and runner thread can share.
        # We serialize all writes through self._lock; reads are fine concurrent.
        conn = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> Run:
        return Run(
            id=row["id"],
            ticker=row["ticker"],
            trade_date=row["trade_date"],
            status=row["status"],
            config=json.loads(row["config_json"]),
            decision=row["decision"],
            error=row["error"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    def create(self, ticker: str, trade_date: str, config: dict) -> Run:
        run = Run(
            id=uuid.uuid4().hex[:12],
            ticker=ticker,
            trade_date=trade_date,
            status="queued",
            config=config,
            decision=None,
            error=None,
            created_at=time.time(),
            started_at=None,
            finished_at=None,
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (id, ticker, trade_date, status, config_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run.id, run.ticker, run.trade_date, run.status,
                 json.dumps(run.config), run.created_at),
            )
        return run

    def mark_started(self, run_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = 'running', started_at = ? WHERE id = ?",
                (time.time(), run_id),
            )

    def mark_succeeded(self, run_id: str, decision: Optional[str]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = 'succeeded', decision = ?, finished_at = ? WHERE id = ?",
                (decision, time.time(), run_id),
            )

    def mark_failed(self, run_id: str, error: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
                (error, time.time(), run_id),
            )

    def get(self, run_id: str) -> Optional[Run]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list(self, limit: int = 50) -> list[Run]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_run(r) for r in rows]
