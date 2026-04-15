"""Unified broker interface shared by every adapter."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Protocol


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: float
    type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    tif: TimeInForce = TimeInForce.DAY
    reduce_only: bool = False
    post_only: bool = False
    client_order_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class OrderResult:
    order_id: str
    client_order_id: str
    status: str                 # new / filled / partially_filled / canceled / rejected
    filled_qty: float = 0.0
    avg_fill_price: float | None = None
    raw: dict | None = None


@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    ts: float                   # unix seconds

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


@dataclass
class Position:
    symbol: str
    qty: float                  # signed
    avg_entry_price: float
    unrealized_pnl: float = 0.0
    market_value: float = 0.0


@dataclass
class Account:
    cash: float
    equity: float
    buying_power: float
    currency: str = "USD"
    pattern_day_trader: bool = False


@dataclass
class Trade:
    symbol: str
    price: float
    size: float
    side: OrderSide
    ts: float


class Broker(Protocol):
    live: bool

    def get_account(self) -> Account: ...
    def get_positions(self) -> list[Position]: ...
    def get_positions_by_symbol(self, symbol: str) -> float: ...
    def get_quote(self, symbol: str) -> Quote: ...
    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult: ...
    def cancel_order(self, order_id: str) -> None: ...
    def cancel_all(self, symbol: str | None = None) -> None: ...
    def stream_trades(self, symbols: list[str]) -> Iterator[Trade]: ...
