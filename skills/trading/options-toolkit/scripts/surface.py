"""Implied volatility surface from an options chain."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .pricing import implied_vol


def build_surface(chain: pd.DataFrame, spot: float, r: float = 0.05, q: float = 0.0,
                  min_volume: int = 10, max_spread_pct: float = 0.15) -> pd.DataFrame:
    """Return DataFrame with columns [expiration, strike, moneyness, dte, iv]."""
    df = chain.copy()
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df = df[(df["bid"] > 0) & (df["volume"] >= min_volume)]
    df = df[((df["ask"] - df["bid"]) / df["mid"]).abs() <= max_spread_pct]

    today = pd.Timestamp.utcnow().normalize()
    df["dte"] = (pd.to_datetime(df["expiration"]) - today).dt.days.clip(lower=1)
    df["T"] = df["dte"] / 365.0
    df["moneyness"] = df["strike"] / spot

    df["iv"] = df.apply(
        lambda r_: implied_vol(r_["mid"], spot, r_["strike"], r_["T"], r, r_["type"], q),
        axis=1,
    )
    return df.dropna(subset=["iv"])[["expiration", "strike", "moneyness", "dte", "iv", "type"]]


def plot_surface(surface: pd.DataFrame, option_type: str = "C"):
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    df = surface[surface["type"] == option_type]
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(df["moneyness"], df["dte"], df["iv"] * 100, c=df["iv"], cmap="viridis")
    ax.set_xlabel("Moneyness (K/S)")
    ax.set_ylabel("DTE")
    ax.set_zlabel("IV (%)")
    ax.set_title(f"Implied Vol Surface — {option_type}")
    return fig
