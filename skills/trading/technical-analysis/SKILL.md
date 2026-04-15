---
name: technical-analysis
description: Use when computing technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic, Ichimoku, VWAP) or generating discrete trading signals (crossovers, breakouts, divergences, regime filters) from OHLCV data. Triggers on "add an RSI", "detect MACD crossover", "build a mean-reversion signal", or "compute Bollinger squeeze".
---

# Technical Analysis

Indicators and signal generation on OHLCV frames produced by the `market-data` skill.

## Library preference

1. **`pandas-ta`** — broadest coverage, DataFrame-native. Default choice.
2. **`ta-lib`** — faster but requires a C dependency. Use when perf matters on intraday data.
3. **Hand-rolled** (`scripts/indicators.py`) — zero-dep fallback, audited reference implementations.

Install `pandas-ta` on demand. If it fails to install, fall back to the hand-rolled module.

## Indicator catalog

Grouped by purpose so you can pick the right tool:

| Group | Indicators |
|---|---|
| Trend | SMA, EMA, WMA, HMA, MACD, ADX, Ichimoku, Supertrend |
| Momentum | RSI, Stochastic, Williams %R, ROC, CCI, MFI |
| Volatility | ATR, Bollinger Bands, Keltner Channels, Donchian |
| Volume | OBV, VWAP, A/D Line, Chaikin MF, Volume Profile |
| Regime | ADX > 25 (trending), BBW percentile (squeeze) |

## Signal patterns

Signals should be returned as an `int8` Series aligned with the price index, with values in `{-1, 0, +1}` (short, flat, long). When combining, use explicit aggregation — never `&` on floats.

Reference generators in `scripts/signals.py`:

- `sma_crossover(fast, slow)` — classic dual moving average
- `rsi_reversal(period=14, oversold=30, overbought=70)`
- `bollinger_breakout(period=20, k=2)`
- `macd_signal(fast=12, slow=26, signal=9)`
- `donchian_breakout(period=20)` — turtle-style
- `regime_filter(adx_threshold=25)` — gate other signals by trend strength

## Workflow

1. Fetch OHLCV via the `market-data` skill.
2. Compute indicators — append as columns, keep the index.
3. Generate signals — return a clean `int8` Series.
4. Offset by one bar before using in a backtest (`signal.shift(1)`) to avoid look-ahead.
5. Plot with `scripts/plot.py` for eyeball verification before production.

## Look-ahead bias — common traps

- `rolling(...).mean()` on bar `t` includes bar `t` itself. For an entry "at open", use bar `t-1`'s indicator.
- `pct_change()` at bar `t` uses close of `t-1` → close of `t`. That's fine for features, not for executable signals.
- `.resample().last()` after the session close is fine; during the session, it leaks future info.
- `ffill` across gaps can silently zero out the gap — prefer `dropna()` then rejoin.

## Multi-timeframe

For mixing timeframes (e.g., 1h signal filtered by 1d trend):

1. Compute the higher-TF indicator on the higher-TF frame.
2. `reindex(lower_tf.index, method="ffill")` to broadcast down.
3. Always lag the higher-TF value by one higher-TF bar.

## Scripts

- `scripts/indicators.py` — zero-dep reference implementations
- `scripts/signals.py` — signal generators returning `{-1, 0, +1}`
- `scripts/plot.py` — matplotlib overlay plots for visual QA
