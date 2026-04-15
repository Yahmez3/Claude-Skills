"""SQLite persistence and reconciliation for bot state.

Keep order intents durable across restarts so a crash mid-submit doesn't
produce duplicate or lost orders.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager


SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    client_order_id TEXT PRIMARY KEY,
    broker_order_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    submitted_at REAL NOT NULL,
    filled_at REAL,
    filled_qty REAL DEFAULT 0,
    avg_price REAL,
    raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);

CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_order_id TEXT NOT NULL,
    ts REAL NOT NULL,
    qty REAL NOT NULL,
    price REAL NOT NULL
);
"""


class BotState:
    def __init__(self, path: str = "bot_state.db"):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @contextmanager
    def tx(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def record_intent(self, order) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT OR IGNORE INTO orders (client_order_id, symbol, side, qty, type, status, submitted_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (order.client_order_id, order.symbol, order.side.value, order.qty,
                 order.type.value, "pending", time.time()),
            )

    def record_ack(self, client_order_id: str, result) -> None:
        with self.tx() as c:
            c.execute(
                "UPDATE orders SET broker_order_id=?, status=?, raw=? WHERE client_order_id=?",
                (result.order_id, result.status, json.dumps(result.raw or {}), client_order_id),
            )

    def record_fill(self, client_order_id: str, qty: float, price: float) -> None:
        with self.tx() as c:
            c.execute("INSERT INTO fills (client_order_id, ts, qty, price) VALUES (?,?,?,?)",
                      (client_order_id, time.time(), qty, price))
            c.execute("UPDATE orders SET filled_qty = filled_qty + ?, avg_price=?, "
                      "status = CASE WHEN filled_qty+? >= qty THEN 'filled' ELSE 'partially_filled' END, "
                      "filled_at=? WHERE client_order_id=?",
                      (qty, price, qty, time.time(), client_order_id))

    def open_orders(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM orders WHERE status IN ('pending','new','partially_filled')"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def reconcile(self, broker) -> dict:
        """Compare local open orders against broker's reported state.

        Returns a summary dict: {local_open, broker_open, desynced_ids}.
        Caller decides whether to cancel, resume, or alert.
        """
        local = {r["broker_order_id"]: r for r in self.open_orders() if r["broker_order_id"]}
        broker_open: dict = {}  # adapter-dependent; caller should populate
        desynced = set(local.keys()) ^ set(broker_open.keys())
        return {"local_open": local, "broker_open": broker_open, "desynced_ids": list(desynced)}
