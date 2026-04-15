"""Drawdown monitor with halt logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class DrawdownMonitor:
    max_drawdown_pct: float = 0.20
    daily_loss_pct: float = 0.02
    size_scaledown_threshold: float = 0.10   # scale to 0.5x at 10% dd
    consecutive_losses_pause: int = 5

    peak_equity: float = 0.0
    day_start_equity: float = 0.0
    current_day: date | None = None
    halted_today: bool = False
    consecutive_losses: int = 0
    pauses_until_trade: int = 0

    def on_new_day(self, equity: float, today: date) -> None:
        self.current_day = today
        self.day_start_equity = equity
        self.peak_equity = max(self.peak_equity, equity)
        self.halted_today = False

    def on_equity(self, equity: float) -> None:
        self.peak_equity = max(self.peak_equity, equity)

    def on_trade_closed(self, trade_pnl: float) -> None:
        if trade_pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.consecutive_losses_pause:
                self.pauses_until_trade = 3   # skip next N trade opportunities
        else:
            self.consecutive_losses = 0

    def current_drawdown(self, equity: float) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return (equity - self.peak_equity) / self.peak_equity

    def position_scale(self, equity: float) -> float:
        """Return a scaling factor in [0, 1] applied to new position sizes."""
        dd = abs(self.current_drawdown(equity))
        if dd >= self.max_drawdown_pct:
            return 0.0
        if dd >= self.size_scaledown_threshold:
            return 0.5
        return 1.0

    def should_halt(self, equity: float) -> tuple[bool, str]:
        if self.halted_today:
            return True, "halted_today"
        if self.day_start_equity > 0:
            day_ret = (equity - self.day_start_equity) / self.day_start_equity
            if day_ret <= -self.daily_loss_pct:
                self.halted_today = True
                return True, f"daily loss {day_ret:.2%}"
        if self.current_drawdown(equity) <= -self.max_drawdown_pct:
            return True, f"max drawdown breached"
        if self.pauses_until_trade > 0:
            self.pauses_until_trade -= 1
            return True, "consecutive loss pause"
        return False, ""
