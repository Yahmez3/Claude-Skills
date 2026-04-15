"""Backtest wrapper. Wire to the `backtesting` skill for real use."""
from __future__ import annotations

import pandas as pd

from .data import fetch_bars


def run_backtest(symbol: str, timeframe: str, start: str, end: str | None,
                 strategy: str, params: dict) -> dict:
    df = fetch_bars(symbol, timeframe, start)
    if end:
        df = df.loc[:end]

    # Minimal inline SMA crossover for the starter. Replace with the backtesting skill.
    fast = int(params.get("fast", 20))
    slow = int(params.get("slow", 50))
    import numpy as np
    f, s = df["close"].rolling(fast).mean(), df["close"].rolling(slow).mean()
    signal = pd.Series(np.where(f > s, 1, 0), index=df.index).shift(1).fillna(0)

    ret = df["close"].pct_change().fillna(0)
    strat = signal * ret - signal.diff().abs().fillna(0) * 0.0005
    equity = (1 + strat).cumprod()

    return {
        "symbol": symbol,
        "strategy": strategy,
        "params": params,
        "total_return": float(equity.iloc[-1] - 1),
        "sharpe": float((strat.mean() / (strat.std() or 1e-9)) * (252 ** 0.5)),
        "max_drawdown": float((equity / equity.cummax() - 1).min()),
        "equity": [{"ts": ts.isoformat(), "v": float(v)} for ts, v in equity.items()],
    }
