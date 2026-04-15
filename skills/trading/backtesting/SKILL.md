---
name: backtesting
description: Use when backtesting a trading strategy — evaluating a signal series against historical price data and computing performance metrics (Sharpe, Sortino, max drawdown, CAGR, win rate, expectancy). Triggers on "backtest this strategy", "what's the Sharpe on X", "run a walk-forward test", or "compare strategies A and B". Produces equity curves, trade logs, and tear sheets.
---

# Backtesting

Evaluate trading strategies on historical data. Two modes depending on complexity:

| Mode | When to use | Engine |
|---|---|---|
| Vector | Single asset, simple entry/exit, no stops | `scripts/vector_backtest.py` (built-in) |
| Event-driven | Multi-asset, stops, position sizing, slippage | `backtesting.py`, `vectorbt`, `backtrader` |

**Default to vector mode** for research. Promote to event-driven only when the question demands it.

## Required inputs

1. An OHLCV DataFrame from the `market-data` skill.
2. A signal Series from the `technical-analysis` skill, in `{-1, 0, +1}`.
3. Parameters: `initial_cash`, `fee_bps`, `slippage_bps`, `allow_short` (bool).

## Look-ahead hygiene

**Always `signal.shift(1)`** before multiplying by returns. The signal generated on bar `t` is acted on at the open of `t+1`. Violations of this rule produce unrealistic Sharpes. The backtest runner enforces this by default — disable only with `assume_shifted=True` and a loud warning.

## Costs

Include both:

- **Fees** — in basis points of notional, per fill (10 bps = 0.10%)
- **Slippage** — bps of notional, applied on entry and exit

Defaults per asset class (starting point, tune per venue):

| Asset | Fee (bps) | Slippage (bps) |
|---|---|---|
| US equities (retail) | 1 | 5 |
| Crypto spot | 10 | 10 |
| Futures | 0.5 (per side) | 2 |

## Metrics produced

- **CAGR** — annualized return
- **Sharpe** (rf=0) — annualized, using daily returns or scaled by `sqrt(bars_per_year)`
- **Sortino** — downside-only denominator
- **Max drawdown** — peak-to-trough
- **Calmar** — CAGR / |MDD|
- **Hit rate, expectancy, profit factor** — from the trade log
- **Exposure** — fraction of bars in a position

Annualization factor is timeframe-aware: `252 * bars_per_day` for equities, `365 * bars_per_day` for crypto.

## Robustness checks

Before trusting a backtest, run:

1. **Out-of-sample split** — train on first 70%, test on last 30%.
2. **Walk-forward** — rolling 12-month train, 3-month test windows.
3. **Parameter sensitivity** — vary each parameter +/- 30%, check Sharpe surface isn't a needle.
4. **Randomized entries** — replace signals with random same-frequency entries; real edge should beat this by a meaningful margin.
5. **Regime slicing** — report metrics separately for bull / bear / chop periods.

Any strategy that only works with one exact parameter combination is overfit.

## Reporting

Generate a tear sheet via `scripts/tearsheet.py`:
- Equity curve vs buy-and-hold
- Drawdown chart
- Monthly returns heatmap
- Rolling Sharpe (63-bar window)
- Trade distribution histogram

Save as a single HTML file for sharing.

## Scripts

- `scripts/vector_backtest.py` — fast vectorized backtester
- `scripts/metrics.py` — performance metrics
- `scripts/walk_forward.py` — walk-forward driver
- `scripts/tearsheet.py` — HTML tear sheet generator
