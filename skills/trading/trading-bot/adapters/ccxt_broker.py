"""Generic crypto adapter using CCXT (Binance, Coinbase, Kraken, ...).

CCXT normalizes most venues. Pass sandbox=True where supported.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

from ..scripts.broker import (
    Account, Order, OrderResult, OrderSide, OrderType, Position, Quote, Trade,
)


class CCXTBroker:
    def __init__(self, exchange_id: str = "binance", live: bool = False):
        import ccxt

        self.live = live
        key = os.environ.get(f"{exchange_id.upper()}_API_KEY")
        secret = os.environ.get(f"{exchange_id.upper()}_SECRET_KEY")
        cls = getattr(ccxt, exchange_id)
        self.ex = cls({"apiKey": key, "secret": secret, "enableRateLimit": True})
        if not live and hasattr(self.ex, "set_sandbox_mode"):
            self.ex.set_sandbox_mode(True)

    def get_account(self) -> Account:
        bal = self.ex.fetch_balance()
        total_usd = float(bal.get("total", {}).get("USDT", 0.0)) or float(bal.get("total", {}).get("USD", 0.0))
        free_usd = float(bal.get("free", {}).get("USDT", 0.0)) or float(bal.get("free", {}).get("USD", 0.0))
        return Account(cash=free_usd, equity=total_usd, buying_power=free_usd, currency="USDT")

    def get_positions(self) -> list[Position]:
        if not self.ex.has.get("fetchPositions"):
            return []
        positions = []
        for p in self.ex.fetch_positions():
            if not p.get("contracts"):
                continue
            positions.append(Position(
                symbol=p["symbol"],
                qty=float(p["contracts"]) * (1 if p["side"] == "long" else -1),
                avg_entry_price=float(p.get("entryPrice") or 0),
                unrealized_pnl=float(p.get("unrealizedPnl") or 0),
                market_value=float(p.get("notional") or 0),
            ))
        return positions

    def get_positions_by_symbol(self, symbol: str) -> float:
        for p in self.get_positions():
            if p.symbol == symbol:
                return p.qty
        return 0.0

    def get_quote(self, symbol: str) -> Quote:
        t = self.ex.fetch_ticker(symbol)
        return Quote(symbol=symbol, bid=t["bid"], ask=t["ask"],
                     bid_size=t.get("bidVolume") or 0, ask_size=t.get("askVolume") or 0,
                     ts=(t["timestamp"] or time.time() * 1000) / 1000)

    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult:
        if dry_run:
            return OrderResult(order_id="dryrun", client_order_id=order.client_order_id,
                               status="dry_run")
        params = {"clientOrderId": order.client_order_id}
        if order.reduce_only:
            params["reduceOnly"] = True
        if order.post_only:
            params["postOnly"] = True

        type_map = {OrderType.MARKET: "market", OrderType.LIMIT: "limit"}
        o = self.ex.create_order(
            symbol=order.symbol,
            type=type_map[order.type],
            side=order.side.value,
            amount=order.qty,
            price=order.limit_price,
            params=params,
        )
        return OrderResult(
            order_id=str(o["id"]), client_order_id=order.client_order_id,
            status=o.get("status", "new"),
            filled_qty=float(o.get("filled") or 0),
            avg_fill_price=float(o["average"]) if o.get("average") else None,
            raw=o,
        )

    def cancel_order(self, order_id: str) -> None:
        self.ex.cancel_order(order_id)

    def cancel_all(self, symbol: str | None = None) -> None:
        for o in self.ex.fetch_open_orders(symbol):
            self.ex.cancel_order(o["id"], symbol=o["symbol"])

    def stream_trades(self, symbols: list[str]) -> Iterator[Trade]:
        # ccxt sync client has no websocket; use ccxt.pro for streaming.
        raise NotImplementedError("use ccxt.pro for streaming trades")
