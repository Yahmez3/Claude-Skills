"""Quick visual QA plots for indicators and signals."""
from __future__ import annotations

import pandas as pd


def plot_overlay(df: pd.DataFrame, indicators: dict[str, pd.Series],
                 signals: pd.Series | None = None, title: str = "") -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df.index, df["close"], color="black", linewidth=1, label="close")
    for name, series in indicators.items():
        ax.plot(series.index, series.values, linewidth=1, label=name)
    if signals is not None:
        longs = df.loc[signals == 1, "close"]
        shorts = df.loc[signals == -1, "close"]
        ax.scatter(longs.index, longs.values, marker="^", color="green", s=40, label="long")
        ax.scatter(shorts.index, shorts.values, marker="v", color="red", s=40, label="short")
    ax.set_title(title or "Price + indicators")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()
