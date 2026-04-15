"""Performance metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def infer_bars_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 252.0
    median_delta = pd.Series(index).diff().median()
    if median_delta is pd.NaT:
        return 252.0
    secs = median_delta.total_seconds()
    if secs >= 86400 * 5:       # weekly
        return 52.0
    if secs >= 86400:           # daily
        return 252.0
    if secs >= 3600:            # hourly-ish
        return 24 * 365 if secs < 86400 else 252 * 6.5
    return 365 * 24 * 60 / (secs / 60)  # minute-bars, crypto


def compute_metrics(equity: pd.Series, returns: pd.Series,
                    trades: pd.DataFrame, index: pd.DatetimeIndex) -> dict:
    bpy = infer_bars_per_year(index)
    total_ret = equity.iloc[-1] / equity.iloc[0] - 1
    years = len(equity) / bpy
    cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else 0.0

    mean = returns.mean()
    std = returns.std(ddof=0)
    sharpe = (mean / std) * np.sqrt(bpy) if std > 0 else 0.0

    downside = returns[returns < 0].std(ddof=0)
    sortino = (mean / downside) * np.sqrt(bpy) if downside and downside > 0 else 0.0

    running_max = equity.cummax()
    dd = equity / running_max - 1
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0

    exposure = float((returns != 0).mean())

    out = {
        "total_return": float(total_ret),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": float(max_dd),
        "calmar": float(calmar),
        "exposure": exposure,
        "n_trades": int(len(trades)),
    }
    if not trades.empty:
        wins = trades[trades["return"] > 0]
        losses = trades[trades["return"] <= 0]
        out["hit_rate"] = len(wins) / len(trades)
        out["avg_win"] = float(wins["return"].mean()) if len(wins) else 0.0
        out["avg_loss"] = float(losses["return"].mean()) if len(losses) else 0.0
        out["expectancy"] = float(trades["return"].mean())
        gross_win = wins["return"].sum()
        gross_loss = -losses["return"].sum()
        out["profit_factor"] = float(gross_win / gross_loss) if gross_loss > 0 else np.inf
    return out
