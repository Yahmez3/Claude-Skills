"""Hard risk limits — check before every order submit."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_position_pct: float = 0.15       # of equity
    max_leverage: float = 1.0            # gross notional / equity
    max_daily_loss_pct: float = 0.02
    max_drawdown_pct: float = 0.20
    max_correlation: float = 0.75
    max_positions: int = 20


@dataclass
class LimitCheck:
    ok: bool
    reason: str = ""


def check_new_position(
    limits: RiskLimits,
    *,
    equity: float,
    open_positions_count: int,
    gross_exposure: float,
    proposed_notional: float,
    today_pnl: float,
    peak_equity: float,
    max_corr_with_book: float = 0.0,
) -> LimitCheck:
    if open_positions_count >= limits.max_positions:
        return LimitCheck(False, f"max_positions={limits.max_positions}")
    if proposed_notional / equity > limits.max_position_pct:
        return LimitCheck(False,
                          f"position size {proposed_notional / equity:.1%} > {limits.max_position_pct:.0%}")
    if (gross_exposure + proposed_notional) / equity > limits.max_leverage:
        return LimitCheck(False,
                          f"leverage would exceed {limits.max_leverage:.1f}x")
    if today_pnl / equity < -limits.max_daily_loss_pct:
        return LimitCheck(False, f"daily loss breached {limits.max_daily_loss_pct:.0%}")
    if (equity - peak_equity) / peak_equity < -limits.max_drawdown_pct:
        return LimitCheck(False, f"drawdown breached {limits.max_drawdown_pct:.0%}")
    if max_corr_with_book > limits.max_correlation:
        return LimitCheck(False, f"correlation {max_corr_with_book:.2f} > {limits.max_correlation:.2f}")
    return LimitCheck(True)
