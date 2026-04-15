---
name: risk-management
description: Use for position sizing, portfolio risk analytics, and drawdown control. Triggers on "how big should this position be", "fixed-fractional / Kelly sizing", "compute portfolio VaR / CVaR", "correlation-adjusted risk", "set a stop loss at X ATR", or "detect a drawdown breach". Works at both the trade level (size one order) and the portfolio level (risk of a basket).
---

# Risk Management

Sizing, risk metrics, and drawdown control. Two layers:

1. **Trade-level sizing** — how many shares/contracts/lots to put on for a given signal.
2. **Portfolio-level risk** — aggregate exposure, VaR, CVaR, correlation, drawdown.

## Trade-level sizing

| Method | Formula | When to use |
|---|---|---|
| Fixed notional | `qty = cash_target / price` | Simple baseline |
| Fixed fractional | `qty = (equity * risk_pct) / stop_distance` | Most strategies — risk a fixed % per trade |
| ATR-based stop | `stop_distance = k * ATR(n)`, then fixed fractional | Volatility-adaptive |
| Volatility targeting | `qty = (equity * target_vol) / (price * realized_vol)` | Portfolio-level vol-targeted sizing |
| Kelly (fractional) | `f* = (p*b - q) / b`, cap at 0.25 × full | Edge known; use fractional Kelly, never full |

Default to **fixed fractional with ATR stops** at 1% risk per trade unless told otherwise. Full Kelly is almost always too aggressive — use 0.1–0.25 fractional.

## Stop-loss placement

- **ATR-based**: `entry - k * ATR(14)` for longs, typically k = 2 or 3
- **Structural**: swing low/high, prior day's low, Donchian band
- **Percent**: fixed % from entry — fine for baseline, ignores volatility
- **Time-based**: exit after N bars regardless of P&L

Always combine a money-stop with a time-stop so stale losers don't linger.

## Position limits

Enforce hard caps at the order-entry layer:

```python
MAX_POSITION_PCT = 0.15   # no single position > 15% of equity
MAX_LEVERAGE     = 2.0
MAX_DAILY_LOSS   = 0.02   # halt trading after 2% daily loss
MAX_DRAWDOWN     = 0.20   # halt if peak-to-trough loss exceeds 20%
MAX_CORRELATION  = 0.75   # don't stack correlated positions
```

`scripts/limits.py` exposes `RiskLimits` — check it before every order submit.

## Portfolio metrics

`scripts/portfolio.py` computes:

- **VaR (historical)** — percentile of historical returns
- **VaR (parametric)** — `z_alpha * sigma * sqrt(horizon)`
- **CVaR** — mean of losses beyond VaR
- **Component VaR** — contribution of each position to portfolio VaR
- **Correlation matrix** — rolling 63-bar window
- **Beta to benchmark** — for equity portfolios vs SPY

## Drawdown control

Rules to codify in the bot:

1. **Daily stop**: if today's P&L < -X%, close all positions and halt until tomorrow.
2. **Equity curve halt**: if drawdown from peak > Y%, reduce position sizes by 50% until equity recovers to within half the threshold.
3. **Consecutive losses**: after K consecutive losing trades, pause for M hours.

These go in `scripts/drawdown.py` as a `DrawdownMonitor` that the bot consults each cycle.

## Kelly properly

`f* = p/a - q/b` where a = win size, b = loss size, p = win prob, q = 1-p.

```python
from scripts.kelly import kelly_fraction
f = kelly_fraction(win_prob=0.55, avg_win=0.02, avg_loss=0.015, cap=0.25)
```

Estimate `p, avg_win, avg_loss` from a recent trade log — do not use the entire history if regime changes.

## Correlation-aware sizing

When adding a position, compute correlation with the existing book. Scale down if |corr| > 0.5 with another large position, so marginal VaR stays bounded.

## Scripts

- `scripts/sizing.py` — fixed-fractional, ATR-stop, vol-targeting
- `scripts/kelly.py` — Kelly fraction + bootstrap CI
- `scripts/portfolio.py` — VaR / CVaR / component VaR / beta
- `scripts/limits.py` — hard position & exposure caps
- `scripts/drawdown.py` — drawdown monitor with halt logic
