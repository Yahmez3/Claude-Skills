"""Normalize and validate OHLCV frames."""
from __future__ import annotations

import pandas as pd


def detect_gaps(df: pd.DataFrame, timeframe: str) -> pd.DatetimeIndex:
    """Return timestamps where expected bars are missing."""
    freq_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
                "1h": "1h", "4h": "4h", "1d": "1D", "1w": "1W"}
    freq = freq_map.get(timeframe)
    if not freq:
        return pd.DatetimeIndex([])
    expected = pd.date_range(df.index.min(), df.index.max(), freq=freq, tz="UTC")
    return expected.difference(df.index)


def validate(df: pd.DataFrame, timeframe: str = "1d") -> dict:
    """Produce a quality report for an OHLCV frame."""
    report = {
        "rows": len(df),
        "start": df.index.min(),
        "end": df.index.max(),
        "duplicates": int(df.index.duplicated().sum()),
        "nan_close": int(df["close"].isna().sum()),
        "zero_volume": int((df["volume"] == 0).sum()),
        "gaps": len(detect_gaps(df, timeframe)),
    }
    # Sanity: high >= max(open, close), low <= min(open, close)
    bad_hi = int((df["high"] < df[["open", "close"]].max(axis=1)).sum())
    bad_lo = int((df["low"] > df[["open", "close"]].min(axis=1)).sum())
    report["ohlc_violations"] = bad_hi + bad_lo
    return report


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    freq_map = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}
    rule = freq_map[timeframe]
    return df.resample(rule).agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()
