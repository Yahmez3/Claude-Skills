"""Alpaca adapter implementing the Broker protocol.

Defaults to paper endpoint. Pass live=True to hit real money.
"""
from __future__ import annotations

import os
import time
from typing import Iterator

from ..scripts.broker import (
    Account, Order, OrderResult, OrderSide, OrderType, Position, Quote, Trade,
    TimeInForce,
)

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"


class AlpacaBroker:
    def __init__(self, live: bool = False):
        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import StockHistoricalDataClient

        self.live = live
        key = os.environ["ALPACA_API_KEY"]
        secret = os.environ["ALPACA_SECRET_KEY"]
        self._client = TradingClient(key, secret, paper=not live)
        self._data = StockHistoricalDataClient(key, secret)

    # ---------- account / positions ----------
    def get_account(self) -> Account:
        a = self._client.get_account()
        return Account(
            cash=float(a.cash),
            equity=float(a.equity),
            buying_power=float(a.buying_power),
            currency=a.currency,
            pattern_day_trader=bool(a.pattern_day_trader),
        )

    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.symbol, qty=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                unrealized_pnl=float(p.unrealized_pl),
                market_value=float(p.market_value),
            ) for p in self._client.get_all_positions()
        ]

    def get_positions_by_symbol(self, symbol: str) -> float:
        try:
            p = self._client.get_open_position(symbol)
            return float(p.qty)
        except Exception:
            return 0.0

    # ---------- quotes ----------
    def get_quote(self, symbol: str) -> Quote:
        from alpaca.data.requests import StockLatestQuoteRequest
        req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        q = self._data.get_stock_latest_quote(req)[symbol]
        return Quote(symbol=symbol, bid=q.bid_price, ask=q.ask_price,
                     bid_size=q.bid_size, ask_size=q.ask_size, ts=q.timestamp.timestamp())

    # ---------- orders ----------
    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult:
        if dry_run:
            return OrderResult(order_id="dryrun", client_order_id=order.client_order_id,
                               status="dry_run")
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide as AlSide, TimeInForce as AlTIF

        side = AlSide.BUY if order.side == OrderSide.BUY else AlSide.SELL
        tif = {"day": AlTIF.DAY, "gtc": AlTIF.GTC, "ioc": AlTIF.IOC, "fok": AlTIF.FOK}[order.tif.value]

        if order.type == OrderType.MARKET:
            req = MarketOrderRequest(symbol=order.symbol, qty=order.qty, side=side,
                                     time_in_force=tif, client_order_id=order.client_order_id)
        elif order.type == OrderType.LIMIT:
            req = LimitOrderRequest(symbol=order.symbol, qty=order.qty, side=side,
                                    limit_price=order.limit_price, time_in_force=tif,
                                    client_order_id=order.client_order_id)
        else:
            raise NotImplementedError(f"order type {order.type} not mapped")

        resp = self._client.submit_order(order_data=req)
        return OrderResult(
            order_id=str(resp.id), client_order_id=order.client_order_id,
            status=str(resp.status.value) if resp.status else "unknown",
            filled_qty=float(resp.filled_qty or 0),
            avg_fill_price=float(resp.filled_avg_price) if resp.filled_avg_price else None,
            raw=resp.model_dump(),
        )

    def cancel_order(self, order_id: str) -> None:
        self._client.cancel_order_by_id(order_id)

    def cancel_all(self, symbol: str | None = None) -> None:
        if symbol:
            for o in self._client.get_orders():
                if o.symbol == symbol:
                    self._client.cancel_order_by_id(o.id)
        else:
            self._client.cancel_orders()

    def stream_trades(self, symbols: list[str]) -> Iterator[Trade]:
        raise NotImplementedError("use alpaca.data.live.StockDataStream for streaming")
