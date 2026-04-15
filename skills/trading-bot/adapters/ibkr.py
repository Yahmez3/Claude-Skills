"""Interactive Brokers adapter via ib_insync.

Requires TWS or IB Gateway running on localhost. Paper account uses port 7497,
live uses 7496. The `live` flag here just picks the right port — you must
still log into the paper gateway for paper trading.
"""
from __future__ import annotations

from typing import Iterator

from ..scripts.broker import (
    Account, Order, OrderResult, OrderSide, OrderType, Position, Quote, Trade,
)


class IBKRBroker:
    def __init__(self, live: bool = False, host: str = "127.0.0.1", client_id: int = 1):
        from ib_insync import IB

        self.live = live
        self.ib = IB()
        self.ib.connect(host, 7496 if live else 7497, clientId=client_id)

    def _contract(self, symbol: str):
        from ib_insync import Stock, Forex, Future
        if "/" in symbol:          # FX like EUR/USD
            base, quote = symbol.split("/")
            return Forex(base + quote)
        if symbol.endswith("=F"):  # futures continuous (best-effort)
            return Future(symbol.replace("=F", ""), exchange="CME")
        return Stock(symbol, "SMART", "USD")

    def get_account(self) -> Account:
        summary = {v.tag: v.value for v in self.ib.accountSummary()}
        return Account(
            cash=float(summary.get("TotalCashValue", 0)),
            equity=float(summary.get("NetLiquidation", 0)),
            buying_power=float(summary.get("BuyingPower", 0)),
        )

    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.contract.symbol,
                qty=float(p.position),
                avg_entry_price=float(p.avgCost),
            ) for p in self.ib.positions()
        ]

    def get_positions_by_symbol(self, symbol: str) -> float:
        for p in self.get_positions():
            if p.symbol == symbol:
                return p.qty
        return 0.0

    def get_quote(self, symbol: str) -> Quote:
        import time
        c = self._contract(symbol)
        t = self.ib.reqMktData(c, "", False, False)
        self.ib.sleep(1)  # let ticks populate
        return Quote(symbol=symbol, bid=t.bid or 0, ask=t.ask or 0,
                     bid_size=t.bidSize or 0, ask_size=t.askSize or 0, ts=time.time())

    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult:
        from ib_insync import MarketOrder, LimitOrder

        if dry_run:
            return OrderResult(order_id="dryrun", client_order_id=order.client_order_id,
                               status="dry_run")
        action = "BUY" if order.side == OrderSide.BUY else "SELL"
        if order.type == OrderType.MARKET:
            ib_order = MarketOrder(action, order.qty)
        elif order.type == OrderType.LIMIT:
            ib_order = LimitOrder(action, order.qty, order.limit_price)
        else:
            raise NotImplementedError(f"type {order.type}")

        trade = self.ib.placeOrder(self._contract(order.symbol), ib_order)
        self.ib.sleep(0.5)
        return OrderResult(
            order_id=str(trade.order.orderId),
            client_order_id=order.client_order_id,
            status=str(trade.orderStatus.status),
            filled_qty=float(trade.orderStatus.filled),
            avg_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
        )

    def cancel_order(self, order_id: str) -> None:
        for t in self.ib.openTrades():
            if str(t.order.orderId) == order_id:
                self.ib.cancelOrder(t.order)

    def cancel_all(self, symbol: str | None = None) -> None:
        for t in self.ib.openTrades():
            if symbol is None or t.contract.symbol == symbol:
                self.ib.cancelOrder(t.order)

    def stream_trades(self, symbols: list[str]) -> Iterator[Trade]:
        raise NotImplementedError("use IB.pendingTickersEvent or reqTickByTickData")
