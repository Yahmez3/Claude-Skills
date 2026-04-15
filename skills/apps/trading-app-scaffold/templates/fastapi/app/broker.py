"""Broker wiring. Replace with imports from the `trading-bot` skill's adapters."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: float
    type: OrderType = OrderType.MARKET
    limit_price: float | None = None


def get_broker(live: bool = False):
    """Return a broker implementation. Swap to trading-bot adapters in production."""
    # from trading_bot.adapters.alpaca import AlpacaBroker
    # return AlpacaBroker(live=live)
    from .stub_broker import StubBroker
    return StubBroker(live=live)
