"""Unified OHLCV fetchers across providers.

All functions return a pandas DataFrame with a tz-aware UTC DatetimeIndex
and columns [open, high, low, close, volume].
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def _to_utc(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "timestamp"
    return df


def fetch_yfinance(
    symbol: str,
    timeframe: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    import yfinance as yf

    interval_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "60m", "4h": "60m", "1d": "1d", "1w": "1wk",
    }
    interval = interval_map.get(timeframe, timeframe)

    df = yf.download(
        symbol, start=start, end=end, interval=interval,
        auto_adjust=True, progress=False, threads=False,
    )
    if df.empty:
        raise ValueError(f"No data returned for {symbol} {timeframe}")

    df = df.rename(columns=str.lower)[OHLCV_COLS]
    df = _to_utc(df)

    # Resample 4h from 1h
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum",
        }).dropna()
    return df


def fetch_ccxt(
    symbol: str,
    timeframe: str = "1h",
    start: Optional[str] = None,
    end: Optional[str] = None,
    exchange_id: str = "binance",
    limit: int = 1000,
) -> pd.DataFrame:
    import ccxt

    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since = None
    if start:
        since = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000) if end else None

    all_bars: list[list] = []
    while True:
        bars = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not bars:
            break
        all_bars.extend(bars)
        last_ts = bars[-1][0]
        if end_ms and last_ts >= end_ms:
            break
        if len(bars) < limit:
            break
        since = last_ts + 1
        time.sleep(ex.rateLimit / 1000)

    df = pd.DataFrame(all_bars, columns=["ts", *OHLCV_COLS])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("timestamp")[OHLCV_COLS]
    if end:
        df = df.loc[:end]
    return df


def fetch_alpaca(
    symbol: str,
    timeframe: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    key = os.environ["ALPACA_API_KEY"]
    secret = os.environ["ALPACA_SECRET_KEY"]
    client = StockHistoricalDataClient(key, secret)

    unit_map = {
        "1m": (1, TimeFrameUnit.Minute),
        "5m": (5, TimeFrameUnit.Minute),
        "15m": (15, TimeFrameUnit.Minute),
        "1h": (1, TimeFrameUnit.Hour),
        "1d": (1, TimeFrameUnit.Day),
    }
    amt, unit = unit_map[timeframe]
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(amt, unit),
        start=pd.Timestamp(start) if start else None,
        end=pd.Timestamp(end) if end else None,
    )
    bars = client.get_stock_bars(req).df
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.xs(symbol, level=0)
    bars = bars.rename(columns={"trade_count": "trades"})[OHLCV_COLS]
    return _to_utc(bars)


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    provider: str = "auto",
) -> pd.DataFrame:
    """Route to the right provider based on symbol format and env credentials."""
    if provider == "auto":
        if "/" in symbol:
            provider = "ccxt"
        elif os.environ.get("ALPACA_API_KEY"):
            provider = "alpaca"
        else:
            provider = "yfinance"

    if provider == "yfinance":
        return fetch_yfinance(symbol, timeframe, start, end)
    if provider == "ccxt":
        return fetch_ccxt(symbol, timeframe, start, end)
    if provider == "alpaca":
        return fetch_alpaca(symbol, timeframe, start, end)
    raise ValueError(f"Unknown provider: {provider}")
