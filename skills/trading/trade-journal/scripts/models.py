"""Trade data model and SQLite journal database."""
from __future__ import annotations

import csv
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Trade:
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    strategy: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    fees: float = 0.0
    pnl: Optional[float] = None
    closed_at: Optional[datetime] = None
    entry_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_row(self) -> tuple:
        return (
            self.id,
            self.symbol,
            self.side,
            self.quantity,
            self.price,
            self.timestamp.isoformat(),
            self.strategy,
            json.dumps(self.tags),
            self.notes,
            self.fees,
            self.pnl,
            self.closed_at.isoformat() if self.closed_at else None,
            self.entry_id,
        )

    @classmethod
    def from_row(cls, row: tuple) -> Trade:
        return cls(
            id=row[0],
            symbol=row[1],
            side=row[2],
            quantity=row[3],
            price=row[4],
            timestamp=datetime.fromisoformat(row[5]),
            strategy=row[6] or "",
            tags=json.loads(row[7]) if row[7] else [],
            notes=row[8] or "",
            fees=row[9] or 0.0,
            pnl=row[10],
            closed_at=datetime.fromisoformat(row[11]) if row[11] else None,
            entry_id=row[12],
        )


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL,
    strategy TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    notes TEXT DEFAULT '',
    fees REAL DEFAULT 0.0,
    pnl REAL,
    closed_at TEXT,
    entry_id TEXT
)
"""

_INSERT = """
INSERT INTO trades (id, symbol, side, quantity, price, timestamp, strategy, tags, notes, fees, pnl, closed_at, entry_id)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class JournalDB:
    def __init__(self, db_path: str = "trades.db") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def __enter__(self) -> JournalDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self.close()

    def close(self) -> None:
        self._conn.close()

    def log(self, trade: Trade) -> None:
        self._conn.execute(_INSERT, trade.to_row())
        self._conn.commit()

    def close_trade(
        self,
        entry_id: str,
        exit_price: float,
        exit_time: datetime,
        fees: float = 0.0,
    ) -> None:
        cur = self._conn.execute(
            "SELECT side, quantity, price, fees FROM trades WHERE id = ?",
            (entry_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No trade found with id={entry_id}")

        side, qty, entry_price, entry_fees = row
        if side == "buy":
            pnl = (exit_price - entry_price) * qty - entry_fees - fees
        else:
            pnl = (entry_price - exit_price) * qty - entry_fees - fees

        self._conn.execute(
            "UPDATE trades SET pnl = ?, closed_at = ?, fees = fees + ? WHERE id = ?",
            (pnl, exit_time.isoformat(), fees, entry_id),
        )
        self._conn.commit()

    def query(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Trade]:
        clauses: list[str] = []
        params: list = []

        if symbol is not None:
            clauses.append("symbol = ?")
            params.append(symbol)
        if strategy is not None:
            clauses.append("strategy = ?")
            params.append(strategy)
        if start is not None:
            clauses.append("timestamp >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp <= ?")
            params.append(end.isoformat())

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM trades{where} ORDER BY timestamp"
        rows = self._conn.execute(sql, params).fetchall()
        trades = [Trade.from_row(r) for r in rows]

        if tags:
            tag_set = set(tags)
            trades = [t for t in trades if tag_set & set(t.tags)]

        return trades

    def all_strategies(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT strategy FROM trades WHERE strategy != '' ORDER BY strategy"
        ).fetchall()
        return [r[0] for r in rows]

    def all_symbols(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT symbol FROM trades ORDER BY symbol"
        ).fetchall()
        return [r[0] for r in rows]

    def import_csv(self, path: str, mapping: Optional[dict[str, str]] = None) -> int:
        """Import trades from a CSV file. Returns count of imported trades.

        mapping: optional dict mapping CSV column names to Trade field names,
        e.g. {"ticker": "symbol", "direction": "side"}
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        mapping = mapping or {}
        count = 0

        with open(p, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mapped: dict[str, str] = {}
                for csv_col, value in row.items():
                    field_name = mapping.get(csv_col, csv_col)
                    mapped[field_name] = value

                tags_raw = mapped.get("tags", "")
                if tags_raw.startswith("["):
                    tags = json.loads(tags_raw)
                else:
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

                trade = Trade(
                    id=mapped.get("id") or str(uuid.uuid4()),
                    symbol=mapped["symbol"],
                    side=mapped["side"],
                    quantity=float(mapped["quantity"]),
                    price=float(mapped["price"]),
                    timestamp=datetime.fromisoformat(mapped["timestamp"]),
                    strategy=mapped.get("strategy", ""),
                    tags=tags,
                    notes=mapped.get("notes", ""),
                    fees=float(mapped.get("fees", 0)),
                    pnl=float(mapped["pnl"]) if mapped.get("pnl") else None,
                    closed_at=(
                        datetime.fromisoformat(mapped["closed_at"])
                        if mapped.get("closed_at")
                        else None
                    ),
                    entry_id=mapped.get("entry_id") or None,
                )
                self.log(trade)
                count += 1

        return count
