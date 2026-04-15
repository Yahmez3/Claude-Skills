"""In-memory broker stub for local dev — no real orders placed."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass
class _Account:
    cash: float = 100_000.0
    equity: float = 100_000.0
    buying_power: float = 200_000.0
    currency: str = "USD"
    pattern_day_trader: bool = False


@dataclass
class _Position:
    symbol: str
    qty: float
    avg_entry_price: float
    unrealized_pnl: float = 0.0
    market_value: float = 0.0


@dataclass
class _Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    ts: float


@dataclass
class _OrderResult:
    order_id: str
    client_order_id: str
    status: str
    filled_qty: float
    avg_fill_price: float | None
    raw: dict | None = None


class StubBroker:
    def __init__(self, live: bool = False):
        self.live = live
        self._account = _Account()
        self._positions: dict[str, _Position] = {}

    def get_account(self):
        return self._account

    def get_positions(self):
        return list(self._positions.values())

    def get_quote(self, symbol: str):
        # Pretend we have a live quote — just a random walk around 100.
        import random
        base = 100 + (hash(symbol) % 50)
        mid = base + random.uniform(-1, 1)
        return _Quote(symbol, mid - 0.05, mid + 0.05, 100, 100, time.time())

    def submit_order(self, order, dry_run: bool = True):
        if dry_run:
            return _OrderResult(order_id="dryrun", client_order_id=str(uuid.uuid4()),
                                status="dry_run", filled_qty=0, avg_fill_price=None)
        px = self.get_quote(order.symbol).ask if order.side.value == "buy" else self.get_quote(order.symbol).bid
        qty = order.qty if order.side.value == "buy" else -order.qty
        pos = self._positions.get(order.symbol)
        if pos is None:
            self._positions[order.symbol] = _Position(order.symbol, qty, px)
        else:
            new_qty = pos.qty + qty
            if new_qty == 0:
                del self._positions[order.symbol]
            else:
                pos.qty = new_qty
        return _OrderResult(order_id=str(uuid.uuid4()), client_order_id=str(uuid.uuid4()),
                            status="filled", filled_qty=abs(qty), avg_fill_price=px)
