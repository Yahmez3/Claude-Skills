---
name: options-toolkit
description: Use for options pricing, Greek calculations, implied volatility solving, and multi-leg strategy analysis (spreads, straddles, iron condors, calendars). Triggers on "price this call", "compute delta/gamma/vega", "build an iron condor", "plot the P&L diagram", or "find IV for this premium". Handles American and European style via Black-Scholes and binomial models.
---

# Options Toolkit

Options pricing, Greeks, implied volatility, and strategy construction.

## Models

| Model | When to use |
|---|---|
| Black-Scholes-Merton | European options, dividends via continuous yield |
| Cox-Ross-Rubinstein binomial | American options, early exercise |
| Bjerksund-Stensland 2002 | Fast American approximation — use for bulk pricing |

Reference implementations in `scripts/pricing.py`. For production-grade pricing use `QuantLib-Python`; the in-house module is for prototyping and education.

## Greeks

All Greeks are computed analytically under BSM where possible:

- **Delta** — `dV/dS`
- **Gamma** — `d²V/dS²`
- **Theta** — `dV/dt` (per day; divide BSM theta by 365)
- **Vega** — `dV/dσ` (per 1 vol point — multiply by 0.01 if reporting per %)
- **Rho** — `dV/dr`
- **Vanna** — `d²V/dSdσ`
- **Charm** — `d²V/dSdt`
- **Vomma** — `d²V/dσ²`

For American: finite difference on the binomial lattice.

## Implied volatility

Use `brentq` on BS price minus market price. Bracket `[1e-6, 5.0]`. If no root (price arbitrage-violating), return `nan` and warn.

```python
from scripts.pricing import implied_vol
iv = implied_vol(price=5.20, S=100, K=105, T=30/365, r=0.05, q=0.0, option_type="C")
```

## Strategies

Build strategies as lists of `Leg(strike, expiration, option_type, qty)`. Negative qty = short. See `scripts/strategies.py` for common templates:

- `long_call`, `long_put`, `covered_call`, `protective_put`
- `bull_call_spread`, `bear_put_spread`, `calendar_spread`
- `straddle`, `strangle`, `iron_condor`, `iron_butterfly`
- `ratio_spread`, `diagonal`

Each template returns a `Strategy` with methods:

- `.price(S, vol, r, T_remaining, q=0)` — total cost
- `.greeks(S, vol, r, T_remaining, q=0)` — aggregated Greeks dict
- `.payoff(S_range)` — expiration P&L curve
- `.pnl_now(S_range, vol, T_remaining)` — current P&L curve

## P&L diagrams

`scripts/payoff.py` plots:
1. Expiration payoff (piecewise-linear)
2. P&L today at current vol and T
3. P&L at user-selected snapshots (T-30d, T-7d, T-0)

Mark break-even, max profit, max loss on the plot.

## Volatility surface

For quick surface building from a chain:
1. Fetch chain via `market-data` skill (`options_chain.fetch_chain`).
2. Solve IV for each strike/expiry.
3. Plot surface with matplotlib (`X=moneyness, Y=DTE, Z=IV`).
4. Filter illiquid quotes: `volume > 10 and bid > 0 and (ask - bid) / mid < 0.15`.

## Workflow

1. Clarify: underlying, current spot, strategy intent, directional view, vol view.
2. Pull chain, filter liquid contracts.
3. Construct strategy via templates or ad-hoc legs.
4. Report cost, max P/L, break-even, current Greeks.
5. Plot payoff and P&L-now diagrams.
6. For execution: hand off to `trading-bot` skill with the leg list.

## Scripts

- `scripts/pricing.py` — BSM + binomial + IV solver + Greeks
- `scripts/strategies.py` — strategy templates and `Strategy` class
- `scripts/payoff.py` — P&L diagram plotting
- `scripts/surface.py` — vol surface building from chains
