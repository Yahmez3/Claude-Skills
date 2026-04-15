# Streamlit Trading Dashboard

Single-file trading dashboard. Starts in seconds, zero framework ceremony.

## Run

```bash
make install
make dev
```

## Extend

- Add a new page by creating `pages/02_strategy.py` — Streamlit will auto-route.
- Wire the `backtesting` skill: import `vector_backtest.run` and render a tear sheet.
- Wire the `trading-bot` skill: add a "Submit order" form that calls an adapter (paper only).
