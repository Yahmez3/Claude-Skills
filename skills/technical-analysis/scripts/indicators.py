"""Zero-dep indicator reference implementations.

All functions take a pandas Series (price) or DataFrame (OHLCV) and return
aligned Series/DataFrames. Fully vectorized — no Python-level loops.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    std = close.rolling(n, min_periods=n).std(ddof=0)
    return pd.DataFrame({"bb_mid": mid, "bb_up": mid + k * std, "bb_dn": mid - k * std,
                         "bb_width": (2 * k * std) / mid})


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = atr(df, n) * n  # undo smoothing to get TR sum proxy
    atr_n = atr(df, n)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def stochastic(df: pd.DataFrame, k: int = 14, d: int = 3) -> pd.DataFrame:
    low = df["low"].rolling(k, min_periods=k).min()
    high = df["high"].rolling(k, min_periods=k).max()
    pk = 100 * (df["close"] - low) / (high - low)
    return pd.DataFrame({"stoch_k": pk, "stoch_d": pk.rolling(d).mean()})


def vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum()
    return (typical * df["volume"]).cumsum() / cum_vol


def donchian(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    return pd.DataFrame({
        "dc_up": df["high"].rolling(n).max(),
        "dc_dn": df["low"].rolling(n).min(),
        "dc_mid": (df["high"].rolling(n).max() + df["low"].rolling(n).min()) / 2,
    })


def supertrend(df: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.DataFrame:
    a = atr(df, n)
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + mult * a
    lower = hl2 - mult * a
    # Simplified — production implementations carry direction state forward
    direction = np.where(df["close"] > upper.shift(), 1,
                np.where(df["close"] < lower.shift(), -1, np.nan))
    direction = pd.Series(direction, index=df.index).ffill().fillna(1)
    line = np.where(direction == 1, lower, upper)
    return pd.DataFrame({"st_line": line, "st_dir": direction})
