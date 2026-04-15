# Trading Backend (FastAPI)

REST + WebSocket backend for trading apps.

## Endpoints

- `GET /health` — liveness
- `GET /bars?symbol=SPY&timeframe=1d` — historical bars
- `GET /account` — broker account summary
- `GET /positions` — open positions
- `POST /orders` — submit an order (default `dry_run=true`)
- `POST /backtest` — run a strategy backtest
- `WS /ws/quotes?symbols=SPY,QQQ` — live quotes

## Run

```bash
cp .env.example .env
make install
make dev
```

Visit http://localhost:8000/docs for the OpenAPI UI.

## Wire real brokers

Replace `app/stub_broker.py` with an adapter from the `trading-bot` skill. The contract is
identical — `get_account`, `get_positions`, `get_quote`, `submit_order`, `cancel_order`.

## Deploy

- **Fly.io** — `fly launch` → `fly deploy`
- **Railway / Render** — point at the repo, set env vars
- **Docker** — a minimal Dockerfile is left as an exercise; use `python:3.11-slim` + uv

## Safety

`TRADING_LIVE=false` by default. Flipping to `true` routes orders to the live broker endpoint.
The backend logs a loud warning on startup if live is enabled.
