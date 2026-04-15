"""Position sizing formulas."""
from __future__ import annotations

import math


def fixed_notional(equity: float, target_pct: float, price: float,
                   lot_size: float = 1.0) -> float:
    target = equity * target_pct
    return math.floor((target / price) / lot_size) * lot_size


def fixed_fractional(equity: float, risk_pct: float, entry: float,
                     stop: float, lot_size: float = 1.0) -> float:
    """Risk `risk_pct` of equity on the distance from entry to stop."""
    if entry == stop:
        return 0.0
    risk_per_share = abs(entry - stop)
    qty = (equity * risk_pct) / risk_per_share
    return math.floor(qty / lot_size) * lot_size


def atr_stop_size(equity: float, risk_pct: float, entry: float, atr: float,
                  atr_mult: float = 2.0, side: str = "long",
                  lot_size: float = 1.0) -> tuple[float, float]:
    """Returns (qty, stop_price) for an ATR-scaled stop."""
    distance = atr_mult * atr
    stop = entry - distance if side == "long" else entry + distance
    qty = fixed_fractional(equity, risk_pct, entry, stop, lot_size)
    return qty, stop


def vol_target(equity: float, target_annual_vol: float, realized_annual_vol: float,
               price: float, lot_size: float = 1.0) -> float:
    """Vol-targeted notional: size so realized vol matches the target."""
    if realized_annual_vol <= 0:
        return 0.0
    scale = target_annual_vol / realized_annual_vol
    notional = equity * min(scale, 1.0)  # no leverage by default
    return math.floor((notional / price) / lot_size) * lot_size
