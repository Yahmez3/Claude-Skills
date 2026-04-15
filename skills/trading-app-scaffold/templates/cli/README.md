# Trading CLI

Typer-based CLI for common trading-ops tasks.

## Install

```bash
pipx install -e .
```

## Commands

```
trade fetch SPY --timeframe 1d --days 365 --out spy.parquet
trade backtest SPY --fast 20 --slow 50
trade signal SPY --strategy sma_crossover
trade bot config.yaml
```
