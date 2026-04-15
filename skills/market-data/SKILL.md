---
name: market-data
description: Use when the user needs to fetch market data — OHLCV bars, quotes, order books, options chains, or fundamentals — for stocks, crypto, options, forex, or futures. Triggers on requests like "get historical prices for AAPL", "download BTC/USDT 1h candles", "pull the SPY options chain", or "load EURUSD tick data". Normalizes output to a pandas DataFrame with a tz-aware DatetimeIndex.
---

# Market Data

Unified data-access layer across asset classes. Every fetcher returns a pandas DataFrame with a UTC `DatetimeIndex` and columns `open, high, low, close, volume` (plus extras per asset class).

## Provider selection

Pick the provider based on asset class and the user's credentials. Ask if unclear.

| Asset class | Default (free) | Pro |
|---|---|---|
| US equities | `yfinance` | `alpaca-py`, `polygon` |
| Crypto | `ccxt` (Binance spot) | `ccxt` with API keys |
| Options | `yfinance.Ticker.option_chain` | `polygon`, CBOE DataShop |
| Forex | `yfinance` (e.g. `EURUSD=X`) | `oandapyV20` |
| Futures | `yfinance` continuous (`ES=F`) | IBKR via `ib_insync` |

Install on demand — do not assume any library is present. Prefer `uv pip install` or `pip install` with the minimal set.

## Core interface

All fetchers follow this signature pattern:

```python
def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",        # 1m, 5m, 15m, 1h, 4h, 1d, 1w
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    limit: int | None = None,
    provider: str = "auto",
) -> pd.DataFrame: ...
```

Output frame: index is tz-aware UTC, columns `["open", "high", "low", "close", "volume"]`, dtype float64 (volume may be int64).

## Usage workflow

1. **Clarify** the symbol format if ambiguous (e.g. `BTC/USDT` vs `BTCUSDT`; `SPY` vs `SPY 240621C00500000`).
2. **Select a provider** based on asset class and credentials. Prefer free sources unless the user has specified a paid one.
3. **Call the fetcher** from `scripts/fetchers.py` and normalize.
4. **Cache** to `./data/{provider}/{symbol}/{timeframe}.parquet` if the user will reuse — avoids re-hitting rate limits.
5. **Validate** — check for gaps, duplicate timestamps, and NaN close prices. Report anomalies rather than silently papering over them.

## Scripts

- `scripts/fetchers.py` — reference implementations for each provider
- `scripts/normalize.py` — frame normalization and gap detection
- `scripts/options_chain.py` — options chain fetching and filtering

## Rate limiting

- yfinance: no hard limit but throttle bulk requests (sleep 0.5s between symbols)
- ccxt: respect `exchange.rateLimit` (ms) — use `exchange.fetch_ohlcv` loop with `time.sleep`
- polygon free tier: 5 calls/minute — batch and back off on 429

## Credentials

Read API keys from environment variables. Never hardcode. Standard names:

```
ALPACA_API_KEY / ALPACA_SECRET_KEY
POLYGON_API_KEY
BINANCE_API_KEY / BINANCE_SECRET_KEY
OANDA_API_KEY / OANDA_ACCOUNT_ID
IBKR_ACCOUNT
```

If a key is missing, fall back to the free provider and notify the user.

## Common pitfalls

- **Timezones** — yfinance returns market-local times for equities; always convert to UTC.
- **Adjusted vs unadjusted** — yfinance `auto_adjust=True` is the default; for backtests on dividends, use unadjusted + separate dividend series.
- **Crypto symbol casing** — CCXT expects `BTC/USDT` with a slash; exchange-native APIs typically use `BTCUSDT`.
- **Options expiries** — always in the exchange's local timezone (usually America/New_York for US).
