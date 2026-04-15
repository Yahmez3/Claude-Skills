"""Data fetchers — wire to the market-data skill in production."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


def fetch_bars(symbol: str, timeframe: str = "1d", start: str | None = None) -> pd.DataFrame:
    import yfinance as yf

    interval = {"1d": "1d", "1h": "60m", "15m": "15m", "5m": "5m"}.get(timeframe, "1d")
    if start is None:
        start = (date.today() - timedelta(days=365)).isoformat()
    df = yf.download(symbol, start=start, interval=interval,
                     auto_adjust=True, progress=False, threads=False)
    df = df.rename(columns=str.lower)
    return df
