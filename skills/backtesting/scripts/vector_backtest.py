"""Vectorized single-asset backtester.

Given OHLCV + signal {-1,0,+1}, produce equity curve, returns, and trade log.
Applies look-ahead-safe shift and realistic per-fill costs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_cash: float = 100_000.0
    fee_bps: float = 1.0
    slippage_bps: float = 5.0
    allow_short: bool = False
    assume_shifted: bool = False  # set True only if signal is already lagged


@dataclass
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    position: pd.Series
    trades: pd.DataFrame
    metrics: dict


def run(df: pd.DataFrame, signal: pd.Series, cfg: BacktestConfig | None = None) -> BacktestResult:
    cfg = cfg or BacktestConfig()

    # Align and lag
    sig = signal.reindex(df.index).fillna(0).astype(int)
    if not cfg.assume_shifted:
        sig = sig.shift(1).fillna(0).astype(int)
    if not cfg.allow_short:
        sig = sig.clip(lower=0)

    close = df["close"]
    ret = close.pct_change().fillna(0)

    # Transaction cost applied on position changes
    turnover = sig.diff().abs().fillna(sig.abs())
    cost_rate = (cfg.fee_bps + cfg.slippage_bps) / 10_000.0
    strat_ret = sig * ret - turnover * cost_rate

    equity = cfg.initial_cash * (1 + strat_ret).cumprod()

    # Trade log: compress runs of identical position
    trades = _trade_log(df, sig, cfg)

    from .metrics import compute_metrics
    metrics = compute_metrics(equity, strat_ret, trades, df.index)

    return BacktestResult(equity=equity, returns=strat_ret, position=sig,
                          trades=trades, metrics=metrics)


def _trade_log(df: pd.DataFrame, sig: pd.Series, cfg: BacktestConfig) -> pd.DataFrame:
    rows = []
    pos = 0
    entry_idx = None
    entry_px = None
    for ts, p in sig.items():
        if p != pos:
            if pos != 0 and entry_idx is not None:
                exit_px = df.loc[ts, "open"] if "open" in df.columns else df.loc[ts, "close"]
                pnl = pos * (exit_px - entry_px) / entry_px
                rows.append({
                    "entry_time": entry_idx, "exit_time": ts,
                    "side": "long" if pos == 1 else "short",
                    "entry_px": entry_px, "exit_px": exit_px,
                    "return": pnl - 2 * (cfg.fee_bps + cfg.slippage_bps) / 10_000.0,
                    "bars_held": df.index.get_loc(ts) - df.index.get_loc(entry_idx),
                })
            if p != 0:
                entry_idx = ts
                entry_px = df.loc[ts, "open"] if "open" in df.columns else df.loc[ts, "close"]
            else:
                entry_idx = None
                entry_px = None
            pos = p
    return pd.DataFrame(rows)
