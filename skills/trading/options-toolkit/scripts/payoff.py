"""P&L diagrams for option strategies."""
from __future__ import annotations

import numpy as np

from .strategies import Strategy


def plot_payoff(strategy: Strategy, S_now: float, sigma: float, r: float = 0.05,
                q: float = 0.0, width_pct: float = 0.3, snapshots_days: list[int] | None = None):
    import matplotlib.pyplot as plt

    S_range = np.linspace(S_now * (1 - width_pct), S_now * (1 + width_pct), 200)
    expiration = strategy.payoff(S_range)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(S_range, expiration, label="at expiration", linewidth=2, color="black")

    for days in (snapshots_days or [30, 7, 0]):
        T_rem = days / 365.0
        if T_rem <= 0:
            continue
        # Recompute strategy value at each spot with T_remaining
        pnl = np.zeros_like(S_range)
        for leg in strategy.legs:
            T_leg = max(leg.expiration_T - (leg.expiration_T - T_rem), 1e-6)
            from .pricing import bs_price
            prices = np.array([bs_price(S, leg.strike, T_leg, r, sigma, leg.option_type, q)
                               for S in S_range])
            pnl += leg.qty * (prices - leg.premium_paid) * 100
        ax.plot(S_range, pnl, linestyle="--", alpha=0.6, label=f"T-{days}d")

    # Break-evens and current spot
    for be in strategy.break_even(S_range):
        ax.axvline(be, color="grey", linestyle=":", alpha=0.5)
    ax.axvline(S_now, color="blue", linestyle="-", alpha=0.3, label="spot")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Underlying price")
    ax.set_ylabel("P&L ($)")
    ax.set_title(f"{strategy.name} payoff")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig
