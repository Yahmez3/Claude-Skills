# Claude Skills — Trading & App Development

A collection of Claude Code skills for building trading systems and trading-focused applications.

## Skills

Skills are split into two top-level categories:

### Trading (`skills/trading/`)

| Skill | Purpose |
|---|---|
| [market-data](skills/trading/market-data) | Fetch OHLCV and quote data across stocks, crypto, options, forex |
| [technical-analysis](skills/trading/technical-analysis) | Compute indicators and generate trading signals |
| [backtesting](skills/trading/backtesting) | Backtest strategies with performance metrics and reports |
| [trading-bot](skills/trading/trading-bot) | Build live trading bots against broker / exchange APIs |
| [options-toolkit](skills/trading/options-toolkit) | Options pricing, Greeks, and multi-leg strategy analysis |
| [risk-management](skills/trading/risk-management) | Position sizing, portfolio risk, drawdown control |
| [sentiment-analysis](skills/trading/sentiment-analysis) | Scrape social/news sentiment (Reddit, Twitter, news) and generate trading signals |
| [trade-journal](skills/trading/trade-journal) | Log trades, tag strategies, compute per-strategy stats, LLM coaching reviews |

### Apps (`skills/apps/`)

| Skill | Purpose |
|---|---|
| [trading-app-scaffold](skills/apps/trading-app-scaffold) | Bootstrap trading web dashboards, mobile apps, backends, and CLIs |
| [app-gap-analysis](skills/apps/app-gap-analysis) | Analyze the top-selling app of the day, extract market gaps from reviews, produce an OpportunityBrief for building a better competitor |
| [app-marketing](skills/apps/app-marketing) | Market a shipped app — positioning, ASO, launch playbook, analytics instrumentation, reviews, lifecycle email, referrals, landing page |

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
