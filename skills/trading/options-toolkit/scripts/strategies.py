"""Multi-leg strategy templates."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .pricing import bs_price, bs_greeks


@dataclass
class Leg:
    strike: float
    option_type: str                 # "C" or "P"
    qty: int                         # +long, -short (contracts, 1 contract = 100 shares)
    expiration_T: float              # years until expiry
    premium_paid: float = 0.0        # cost per contract when opened


@dataclass
class Strategy:
    name: str
    legs: list[Leg] = field(default_factory=list)

    def cost(self) -> float:
        return sum(leg.qty * leg.premium_paid * 100 for leg in self.legs)

    def price(self, S: float, sigma: float, r: float, q: float = 0.0) -> float:
        return sum(
            leg.qty * bs_price(S, leg.strike, leg.expiration_T, r, sigma, leg.option_type, q) * 100
            for leg in self.legs
        )

    def greeks(self, S: float, sigma: float, r: float, q: float = 0.0) -> dict:
        agg = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}
        for leg in self.legs:
            g = bs_greeks(S, leg.strike, leg.expiration_T, r, sigma, leg.option_type, q)
            for k in agg:
                agg[k] += leg.qty * g[k] * 100
        return agg

    def payoff(self, S_range: np.ndarray) -> np.ndarray:
        """Expiration P&L."""
        total = np.zeros_like(S_range, dtype=float)
        for leg in self.legs:
            if leg.option_type.upper() == "C":
                payoff = np.maximum(S_range - leg.strike, 0.0)
            else:
                payoff = np.maximum(leg.strike - S_range, 0.0)
            total += leg.qty * (payoff - leg.premium_paid) * 100
        return total

    def break_even(self, S_range: np.ndarray) -> list[float]:
        payoff = self.payoff(S_range)
        signs = np.sign(payoff)
        crossings = np.where(np.diff(signs) != 0)[0]
        return [float(S_range[i]) for i in crossings]


# ---------- templates ----------

def long_call(strike: float, T: float, premium: float) -> Strategy:
    return Strategy("long_call", [Leg(strike, "C", +1, T, premium)])


def long_put(strike: float, T: float, premium: float) -> Strategy:
    return Strategy("long_put", [Leg(strike, "P", +1, T, premium)])


def bull_call_spread(long_k: float, short_k: float, T: float,
                     long_prem: float, short_prem: float) -> Strategy:
    return Strategy("bull_call_spread", [
        Leg(long_k, "C", +1, T, long_prem),
        Leg(short_k, "C", -1, T, short_prem),
    ])


def bear_put_spread(long_k: float, short_k: float, T: float,
                    long_prem: float, short_prem: float) -> Strategy:
    return Strategy("bear_put_spread", [
        Leg(long_k, "P", +1, T, long_prem),
        Leg(short_k, "P", -1, T, short_prem),
    ])


def straddle(strike: float, T: float, call_prem: float, put_prem: float) -> Strategy:
    return Strategy("straddle", [
        Leg(strike, "C", +1, T, call_prem),
        Leg(strike, "P", +1, T, put_prem),
    ])


def strangle(call_k: float, put_k: float, T: float,
             call_prem: float, put_prem: float) -> Strategy:
    return Strategy("strangle", [
        Leg(call_k, "C", +1, T, call_prem),
        Leg(put_k, "P", +1, T, put_prem),
    ])


def iron_condor(put_long_k: float, put_short_k: float,
                call_short_k: float, call_long_k: float, T: float,
                prems: dict[str, float]) -> Strategy:
    """prems keys: p_long, p_short, c_short, c_long (credit received = c_short+p_short - c_long - p_long)."""
    return Strategy("iron_condor", [
        Leg(put_long_k, "P", +1, T, prems["p_long"]),
        Leg(put_short_k, "P", -1, T, prems["p_short"]),
        Leg(call_short_k, "C", -1, T, prems["c_short"]),
        Leg(call_long_k, "C", +1, T, prems["c_long"]),
    ])


def iron_butterfly(atm_k: float, wing: float, T: float, prems: dict[str, float]) -> Strategy:
    return iron_condor(atm_k - wing, atm_k, atm_k, atm_k + wing, T, prems)


def calendar_spread(strike: float, short_T: float, long_T: float,
                    short_prem: float, long_prem: float, option_type: str = "C") -> Strategy:
    return Strategy("calendar_spread", [
        Leg(strike, option_type, -1, short_T, short_prem),
        Leg(strike, option_type, +1, long_T, long_prem),
    ])
