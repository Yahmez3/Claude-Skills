"""Kelly fractional sizing with bootstrap confidence intervals."""
from __future__ import annotations

import numpy as np
import pandas as pd


def kelly_fraction(win_prob: float, avg_win: float, avg_loss: float,
                   cap: float = 0.25) -> float:
    """Fractional Kelly, capped. avg_loss should be positive (absolute value)."""
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    b = avg_win / avg_loss
    q = 1 - win_prob
    f = win_prob - q / b
    if f <= 0:
        return 0.0
    return min(f, cap)


def kelly_from_trades(returns: pd.Series, cap: float = 0.25) -> float:
    """Compute Kelly from a trade-return series."""
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    if len(wins) == 0 or len(losses) == 0:
        return 0.0
    p = len(wins) / len(returns)
    return kelly_fraction(p, wins.mean(), -losses.mean(), cap)


def kelly_bootstrap_ci(returns: pd.Series, n_boot: int = 2000,
                       alpha: float = 0.05, cap: float = 0.25) -> tuple[float, float, float]:
    """Return (point, lower, upper) Kelly estimates via bootstrap."""
    rng = np.random.default_rng(42)
    n = len(returns)
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        samples.append(kelly_from_trades(returns.iloc[idx], cap))
    point = kelly_from_trades(returns, cap)
    lo = float(np.quantile(samples, alpha / 2))
    hi = float(np.quantile(samples, 1 - alpha / 2))
    return point, lo, hi
