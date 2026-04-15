"""Signal generators. All return int8 Series in {-1, 0, +1} aligned with input index.

Signals are intent — they DO NOT include execution lag. Apply `.shift(1)` before
using in a backtest to avoid look-ahead bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind


def _finalize(s: pd.Series) -> pd.Series:
    return s.fillna(0).astype("int8")


def sma_crossover(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    f, s = ind.sma(close, fast), ind.sma(close, slow)
    sig = pd.Series(np.where(f > s, 1, np.where(f < s, -1, 0)), index=close.index)
    return _finalize(sig)


def rsi_reversal(close: pd.Series, n: int = 14, lo: float = 30, hi: float = 70) -> pd.Series:
    r = ind.rsi(close, n)
    sig = pd.Series(0, index=close.index, dtype=float)
    sig[(r.shift() < lo) & (r >= lo)] = 1      # cross up through oversold
    sig[(r.shift() > hi) & (r <= hi)] = -1     # cross down through overbought
    return _finalize(sig)


def bollinger_breakout(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.Series:
    bb = ind.bollinger(df["close"], n, k)
    sig = pd.Series(np.where(df["close"] > bb["bb_up"], 1,
                    np.where(df["close"] < bb["bb_dn"], -1, 0)),
                    index=df.index)
    return _finalize(sig)


def macd_signal(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    m = ind.macd(close, fast, slow, signal)
    cross_up = (m["hist"].shift() <= 0) & (m["hist"] > 0)
    cross_dn = (m["hist"].shift() >= 0) & (m["hist"] < 0)
    sig = pd.Series(0, index=close.index, dtype=float)
    sig[cross_up] = 1
    sig[cross_dn] = -1
    return _finalize(sig)


def donchian_breakout(df: pd.DataFrame, n: int = 20) -> pd.Series:
    dc = ind.donchian(df, n)
    sig = pd.Series(np.where(df["close"] > dc["dc_up"].shift(), 1,
                    np.where(df["close"] < dc["dc_dn"].shift(), -1, 0)),
                    index=df.index)
    return _finalize(sig)


def regime_filter(df: pd.DataFrame, adx_threshold: float = 25.0) -> pd.Series:
    """Return 1 when trending (ADX above threshold), else 0. Use as mask."""
    a = ind.adx(df)
    return (a > adx_threshold).fillna(False).astype("int8")


def combine(*signals: pd.Series, mode: str = "unanimous") -> pd.Series:
    """Combine multiple signals.

    - unanimous: all must agree (same sign) else flat
    - majority: sign of the sum
    - first-nonzero: take the first non-zero from left to right
    """
    df = pd.concat(signals, axis=1).fillna(0).astype(int)
    if mode == "unanimous":
        pos = (df > 0).all(axis=1)
        neg = (df < 0).all(axis=1)
        return _finalize(pd.Series(np.where(pos, 1, np.where(neg, -1, 0)), index=df.index))
    if mode == "majority":
        return _finalize(np.sign(df.sum(axis=1)))
    if mode == "first-nonzero":
        out = pd.Series(0, index=df.index, dtype=int)
        for c in df.columns:
            mask = (out == 0)
            out.loc[mask] = df.loc[mask, c]
        return _finalize(out)
    raise ValueError(f"Unknown combine mode: {mode}")
