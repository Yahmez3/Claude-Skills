# Claude Skills — Trading & App Development

A collection of Claude Code skills for building trading systems and trading-focused applications.

## Skills

| Skill | Purpose |
|---|---|
| [market-data](skills/market-data) | Fetch OHLCV and quote data across stocks, crypto, options, forex |
| [technical-analysis](skills/technical-analysis) | Compute indicators and generate trading signals |
| [backtesting](skills/backtesting) | Backtest strategies with performance metrics and reports |
| [trading-bot](skills/trading-bot) | Build live trading bots against broker / exchange APIs |
| [options-toolkit](skills/options-toolkit) | Options pricing, Greeks, and multi-leg strategy analysis |
| [risk-management](skills/risk-management) | Position sizing, portfolio risk, drawdown control |
| [trading-app-scaffold](skills/trading-app-scaffold) | Bootstrap trading web dashboards, mobile apps, backends, and CLIs |

## Installing

Clone into `~/.claude/skills/` (or symlink the individual skill directories) so Claude Code can discover them:

```bash
git clone <this-repo> ~/.claude/skills/trading
```

Each skill is self-contained in its own directory with a `SKILL.md` manifest.

## Asset-class coverage

- **Equities** — yfinance, Alpaca, Polygon, IBKR
- **Crypto** — CCXT (Binance, Coinbase, Kraken, etc.)
- **Options** — yfinance chains, CBOE, QuantLib pricing
- **Forex / Futures** — OANDA, IBKR, CCXT perpetuals

## Safety

Live-trading skills default to **paper-trading endpoints**. Switching to real money requires an explicit opt-in flag documented in each skill.
