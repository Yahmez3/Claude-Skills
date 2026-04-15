"""Black-Scholes-Merton pricing, Greeks, and implied volatility."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0):
    if T <= 0 or sigma <= 0:
        return np.nan, np.nan
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S: float, K: float, T: float, r: float, sigma: float,
             option_type: str = "C", q: float = 0.0) -> float:
    """Black-Scholes-Merton price with continuous dividend yield q."""
    if T <= 0:
        if option_type.upper() == "C":
            return max(S - K, 0.0)
        return max(K - S, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    df_r = math.exp(-r * T)
    df_q = math.exp(-q * T)
    if option_type.upper() == "C":
        return S * df_q * norm.cdf(d1) - K * df_r * norm.cdf(d2)
    return K * df_r * norm.cdf(-d2) - S * df_q * norm.cdf(-d1)


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
              option_type: str = "C", q: float = 0.0) -> dict:
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    df_r = math.exp(-r * T)
    df_q = math.exp(-q * T)
    pdf_d1 = norm.pdf(d1)

    if option_type.upper() == "C":
        delta = df_q * norm.cdf(d1)
        theta = (-S * df_q * pdf_d1 * sigma / (2 * math.sqrt(T))
                 - r * K * df_r * norm.cdf(d2) + q * S * df_q * norm.cdf(d1))
        rho = K * T * df_r * norm.cdf(d2)
    else:
        delta = -df_q * norm.cdf(-d1)
        theta = (-S * df_q * pdf_d1 * sigma / (2 * math.sqrt(T))
                 + r * K * df_r * norm.cdf(-d2) - q * S * df_q * norm.cdf(-d1))
        rho = -K * T * df_r * norm.cdf(-d2)

    gamma = df_q * pdf_d1 / (S * sigma * math.sqrt(T))
    vega = S * df_q * pdf_d1 * math.sqrt(T)          # per 1 vol point
    vanna = -df_q * pdf_d1 * d2 / sigma              # d²V/dSdσ
    vomma = vega * d1 * d2 / sigma                   # d²V/dσ²

    return {
        "price": bs_price(S, K, T, r, sigma, option_type, q),
        "delta": delta,
        "gamma": gamma,
        "theta": theta / 365.0,                      # per calendar day
        "vega": vega / 100.0,                        # per 1 % vol
        "rho": rho / 100.0,                          # per 1 % rate
        "vanna": vanna,
        "vomma": vomma,
    }


def implied_vol(price: float, S: float, K: float, T: float, r: float,
                option_type: str = "C", q: float = 0.0) -> float:
    """Solve for IV. Returns nan if no root (arbitrage-violating quote)."""
    intrinsic_c = max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
    intrinsic_p = max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0)
    lower = intrinsic_c if option_type.upper() == "C" else intrinsic_p
    if price < lower - 1e-8:
        return float("nan")

    def f(sigma):
        return bs_price(S, K, T, r, sigma, option_type, q) - price

    try:
        return brentq(f, 1e-6, 5.0, maxiter=200, xtol=1e-6)
    except ValueError:
        return float("nan")


def crr_american(S: float, K: float, T: float, r: float, sigma: float,
                 option_type: str = "C", q: float = 0.0, steps: int = 200) -> float:
    """Cox-Ross-Rubinstein binomial price for American options."""
    if T <= 0:
        return max((S - K) if option_type.upper() == "C" else (K - S), 0.0)
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    # Terminal prices
    prices = np.array([S * (u ** (steps - i)) * (d ** i) for i in range(steps + 1)])
    if option_type.upper() == "C":
        values = np.maximum(prices - K, 0.0)
    else:
        values = np.maximum(K - prices, 0.0)

    for step in range(steps - 1, -1, -1):
        prices = prices[:-1] / u
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        if option_type.upper() == "C":
            exercise = np.maximum(prices - K, 0.0)
        else:
            exercise = np.maximum(K - prices, 0.0)
        values = np.maximum(values, exercise)
    return float(values[0])
