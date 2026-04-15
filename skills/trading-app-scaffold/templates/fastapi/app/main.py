"""FastAPI trading backend starter."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .broker import get_broker
from .data import fetch_bars


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.broker = get_broker(live=False)
    yield


app = FastAPI(title="Trading Backend", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------- schemas ----------
class OrderIn(BaseModel):
    symbol: str
    side: str           # "buy" | "sell"
    qty: float
    type: str = "market"
    limit_price: float | None = None
    dry_run: bool = True


class BacktestIn(BaseModel):
    symbol: str
    timeframe: str = "1d"
    start: str
    end: str | None = None
    strategy: str = "sma_crossover"
    params: dict = {}


# ---------- routes ----------
@app.get("/health")
async def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


@app.get("/bars")
async def bars(symbol: str, timeframe: str = "1d", start: str | None = None):
    df = await asyncio.to_thread(fetch_bars, symbol, timeframe, start)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": [
            {"ts": ts.isoformat(), "o": r.open, "h": r.high, "l": r.low,
             "c": r.close, "v": r.volume}
            for ts, r in df.iterrows()
        ],
    }


@app.get("/account")
async def account():
    acc = app.state.broker.get_account()
    return acc.__dict__


@app.get("/positions")
async def positions():
    return [p.__dict__ for p in app.state.broker.get_positions()]


@app.post("/orders")
async def place_order(order: OrderIn):
    from .broker import Order, OrderSide, OrderType

    broker_order = Order(
        symbol=order.symbol,
        side=OrderSide(order.side),
        qty=order.qty,
        type=OrderType(order.type),
        limit_price=order.limit_price,
    )
    try:
        result = app.state.broker.submit_order(broker_order, dry_run=order.dry_run)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, str(e))
    return result.__dict__


@app.post("/backtest")
async def backtest(req: BacktestIn):
    from .backtest_runner import run_backtest
    return await asyncio.to_thread(run_backtest, req.symbol, req.timeframe,
                                   req.start, req.end, req.strategy, req.params)


# ---------- websocket: live quotes ----------
@app.websocket("/ws/quotes")
async def ws_quotes(ws: WebSocket, symbols: str = "SPY"):
    await ws.accept()
    syms = [s.strip() for s in symbols.split(",")]
    try:
        while True:
            for s in syms:
                q = app.state.broker.get_quote(s)
                await ws.send_json({"symbol": q.symbol, "bid": q.bid, "ask": q.ask, "ts": q.ts})
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
