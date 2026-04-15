"""Walk-forward analysis driver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .vector_backtest import BacktestConfig, run


@dataclass
class WalkForwardResult:
    windows: pd.DataFrame   # per-window metrics
    oos_equity: pd.Series   # stitched out-of-sample equity curve


def walk_forward(
    df: pd.DataFrame,
    signal_fn: Callable[[pd.DataFrame, dict], pd.Series],
    optimize_fn: Callable[[pd.DataFrame], dict],
    train_bars: int,
    test_bars: int,
    cfg: BacktestConfig | None = None,
) -> WalkForwardResult:
    """Rolling train/test windows.

    - `optimize_fn(train_df) -> best_params` is called on each training slice.
    - `signal_fn(df, params) -> signal` is evaluated on the test slice with those params.
    """
    cfg = cfg or BacktestConfig()
    rows = []
    oos_pieces = []
    start = 0
    while start + train_bars + test_bars <= len(df):
        train = df.iloc[start : start + train_bars]
        test = df.iloc[start + train_bars : start + train_bars + test_bars]
        params = optimize_fn(train)
        sig = signal_fn(test, params)
        res = run(test, sig, cfg)
        row = {"start": test.index[0], "end": test.index[-1], **params, **res.metrics}
        rows.append(row)
        oos_pieces.append(res.equity / res.equity.iloc[0])
        start += test_bars

    # Stitch OOS equity curves by compounding
    stitched = pd.concat(oos_pieces)
    stitched = stitched.groupby(stitched.index).last()
    return WalkForwardResult(windows=pd.DataFrame(rows), oos_equity=stitched)
