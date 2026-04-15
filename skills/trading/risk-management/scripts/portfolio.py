"""Portfolio-level risk metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def historical_var(returns: pd.Series, alpha: float = 0.05) -> float:
    """Loss-positive VaR at `alpha`. Returns a positive number."""
    return float(-returns.quantile(alpha))


def historical_cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    var = -historical_var(returns, alpha)    # cutoff in returns-space (negative)
    tail = returns[returns <= var]
    return float(-tail.mean()) if len(tail) else 0.0


def parametric_var(returns: pd.Series, alpha: float = 0.05, horizon: int = 1) -> float:
    mu = returns.mean() * horizon
    sigma = returns.std() * np.sqrt(horizon)
    z = norm.ppf(alpha)
    return float(-(mu + z * sigma))


def portfolio_returns(weights: pd.Series, asset_returns: pd.DataFrame) -> pd.Series:
    aligned = asset_returns[weights.index].fillna(0)
    return aligned @ weights


def component_var(weights: pd.Series, asset_returns: pd.DataFrame,
                  alpha: float = 0.05) -> pd.Series:
    """Marginal contribution of each position to parametric portfolio VaR."""
    cov = asset_returns[weights.index].cov()
    port_vol = float(np.sqrt(weights @ cov @ weights))
    if port_vol == 0:
        return pd.Series(0.0, index=weights.index)
    marginal = (cov @ weights) / port_vol
    contribution = weights * marginal
    z = -norm.ppf(alpha)
    return contribution * z        # in VaR units, sums to portfolio VaR


def beta_to_benchmark(asset_returns: pd.Series, bench_returns: pd.Series) -> float:
    aligned = pd.concat([asset_returns, bench_returns], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    return float(cov / var) if var > 0 else float("nan")


def rolling_correlation(asset_returns: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Return the most recent rolling-window correlation matrix."""
    if len(asset_returns) < window:
        return asset_returns.corr()
    return asset_returns.iloc[-window:].corr()
