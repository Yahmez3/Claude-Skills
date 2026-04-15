"""OANDA FX adapter. Defaults to practice (demo) environment."""
from __future__ import annotations

import os
import time
from typing import Iterator

from ..scripts.broker import (
    Account, Order, OrderResult, OrderSide, OrderType, Position, Quote, Trade,
)


class OandaBroker:
    def __init__(self, live: bool = False):
        import oandapyV20
        self.live = live
        env = "live" if live else "practice"
        self.token = os.environ["OANDA_API_KEY"]
        self.account_id = os.environ["OANDA_ACCOUNT_ID"]
        self.client = oandapyV20.API(access_token=self.token, environment=env)

    def get_account(self) -> Account:
        from oandapyV20.endpoints.accounts import AccountSummary
        r = AccountSummary(self.account_id)
        self.client.request(r)
        a = r.response["account"]
        return Account(
            cash=float(a["balance"]),
            equity=float(a["NAV"]),
            buying_power=float(a["marginAvailable"]),
            currency=a["currency"],
        )

    def get_positions(self) -> list[Position]:
        from oandapyV20.endpoints.positions import OpenPositions
        r = OpenPositions(self.account_id)
        self.client.request(r)
        out = []
        for p in r.response.get("positions", []):
            long_units = float(p["long"]["units"])
            short_units = float(p["short"]["units"])
            qty = long_units + short_units  # short already negative
            if qty == 0:
                continue
            entry = p["long"]["averagePrice"] if long_units else p["short"]["averagePrice"]
            out.append(Position(symbol=p["instrument"], qty=qty, avg_entry_price=float(entry)))
        return out

    def get_positions_by_symbol(self, symbol: str) -> float:
        for p in self.get_positions():
            if p.symbol == symbol:
                return p.qty
        return 0.0

    def get_quote(self, symbol: str) -> Quote:
        from oandapyV20.endpoints.pricing import PricingInfo
        r = PricingInfo(self.account_id, params={"instruments": symbol})
        self.client.request(r)
        p = r.response["prices"][0]
        bid = float(p["bids"][0]["price"])
        ask = float(p["asks"][0]["price"])
        return Quote(symbol=symbol, bid=bid, ask=ask,
                     bid_size=float(p["bids"][0]["liquidity"]),
                     ask_size=float(p["asks"][0]["liquidity"]), ts=time.time())

    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult:
        if dry_run:
            return OrderResult(order_id="dryrun", client_order_id=order.client_order_id,
                               status="dry_run")
        from oandapyV20.endpoints.orders import OrderCreate
        units = order.qty if order.side == OrderSide.BUY else -order.qty
        data = {
            "order": {
                "instrument": order.symbol,
                "units": str(int(units)),
                "type": "MARKET" if order.type == OrderType.MARKET else "LIMIT",
                "clientExtensions": {"id": order.client_order_id},
            }
        }
        if order.type == OrderType.LIMIT:
            data["order"]["price"] = str(order.limit_price)
        r = OrderCreate(self.account_id, data=data)
        self.client.request(r)
        resp = r.response
        tx = resp.get("orderFillTransaction") or resp.get("orderCreateTransaction") or {}
        return OrderResult(
            order_id=str(tx.get("id", "")),
            client_order_id=order.client_order_id,
            status="filled" if "orderFillTransaction" in resp else "new",
            filled_qty=float(tx.get("units", 0)),
            avg_fill_price=float(tx["price"]) if tx.get("price") else None,
            raw=resp,
        )

    def cancel_order(self, order_id: str) -> None:
        from oandapyV20.endpoints.orders import OrderCancel
        self.client.request(OrderCancel(self.account_id, order_id))

    def cancel_all(self, symbol: str | None = None) -> None:
        raise NotImplementedError

    def stream_trades(self, symbols: list[str]) -> Iterator[Trade]:
        raise NotImplementedError("use oandapyV20.endpoints.pricing.PricingStream")
