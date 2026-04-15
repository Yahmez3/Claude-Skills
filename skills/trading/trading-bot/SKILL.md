---
name: trading-bot
description: Use when building a live or paper trading bot that connects to a broker / exchange API to fetch quotes, submit orders, manage positions, and react to fills. Triggers on "build a trading bot", "connect to Alpaca/Binance/IBKR", "place a live order", or "stream real-time quotes". Defaults to paper-trading endpoints; real-money trading requires explicit opt-in.
---

# Trading Bot

Live and paper execution across brokers and exchanges. This skill provides a **unified `Broker` interface** so strategies can be written once and routed to any venue.

## Safety — read first

1. **Default to paper endpoints.** Every adapter requires `live=True` to hit a real-money endpoint. Never flip this flag without explicit user confirmation in the current session.
2. **Confirm before the first live order.** Print account, symbol, side, qty, estimated cost, and require a typed confirmation.
3. **Dry run first.** `submit(..., dry_run=True)` logs the intended order without sending. Use this in new code paths.
4. **Rate-limit your order flow.** A runaway loop can place thousands of orders in seconds and burn through capital or get the account banned.
5. **Kill switch.** Every bot loop checks a `./STOP` file at the top of each iteration and exits cleanly if present. Document this to the user.

## Supported venues

| Venue | Asset | Paper? | Adapter |
|---|---|---|---|
| Alpaca | US equities, crypto | yes | `adapters/alpaca.py` |
| Binance | Crypto spot + perps | yes (testnet) | `adapters/binance.py` (via ccxt) |
| IBKR | Equities, options, futures, FX | yes | `adapters/ibkr.py` (ib_insync) |
| OANDA | Forex | yes (demo) | `adapters/oanda.py` |
| Coinbase | Crypto | sandbox | `adapters/coinbase.py` (via ccxt) |

## The `Broker` interface

```python
class Broker(Protocol):
    def get_account(self) -> Account: ...
    def get_positions(self) -> list[Position]: ...
    def get_quote(self, symbol: str) -> Quote: ...
    def submit_order(self, order: Order, dry_run: bool = False) -> OrderResult: ...
    def cancel_order(self, order_id: str) -> None: ...
    def stream_trades(self, symbols: list[str]): ...  # generator
```

See `scripts/broker.py` for the full dataclass definitions and `adapters/*.py` for implementations.

## Order types

Support these at the interface level; adapters map to venue-specific names:

- `market`, `limit`, `stop`, `stop_limit`, `trailing_stop`
- Time in force: `day`, `gtc`, `ioc`, `fok`
- Post-only / reduce-only flags for crypto venues

## Bot loop template

```python
from scripts.broker import Order, OrderSide
from adapters.alpaca import AlpacaBroker

broker = AlpacaBroker(live=False)  # paper

while not stop_flag():
    bars = broker.get_bars("SPY", "1m", lookback=200)
    signal = strategy(bars)  # from technical-analysis skill
    target_pos = size(signal, account=broker.get_account())
    current = broker.get_positions_by_symbol("SPY")
    delta = target_pos - current
    if delta != 0:
        broker.submit_order(Order(
            symbol="SPY",
            side=OrderSide.BUY if delta > 0 else OrderSide.SELL,
            qty=abs(delta),
            type="market",
        ))
    sleep_until_next_bar()
```

Reference loop in `scripts/bot_runner.py` handles the scaffolding (signal polling, kill switch, retry-with-backoff on transient errors, structured logging).

## State & idempotency

Trading loops crash. Assume every one of them will. Design for recovery:

- Persist intended orders to a local SQLite DB (`bot_state.db`) BEFORE sending.
- On submit, record the broker order ID. On restart, reconcile open orders and positions against persisted state before resuming the strategy.
- Use a `client_order_id` (UUID) on every order so duplicate sends are rejected by the venue.

`scripts/state.py` provides the reconciliation helper.

## Error handling

- **Transient** (network, 5xx, rate limit 429): exponential backoff, retry up to N times
- **Permanent** (insufficient funds, invalid symbol): log, alert, skip — do not retry
- **Partial fill**: treat the remainder as a new decision at the next cycle; don't blindly re-send

## Monitoring

Structured logs to stdout (JSON lines) with fields: `ts, level, event, symbol, order_id, qty, price, pnl`.
Hook into `scripts/telemetry.py` for Discord/Slack webhook alerts on fills, errors, and daily P&L summary.

## Scripts & adapters

- `scripts/broker.py` — protocol, dataclasses
- `scripts/bot_runner.py` — resilient loop harness
- `scripts/state.py` — SQLite state + reconciliation
- `scripts/telemetry.py` — alert webhooks
- `adapters/alpaca.py`, `adapters/ccxt_broker.py`, `adapters/ibkr.py`, `adapters/oanda.py`
