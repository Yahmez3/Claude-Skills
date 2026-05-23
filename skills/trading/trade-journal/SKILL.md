---
name: trade-journal
description: Use for logging trades, reviewing trading performance, and getting AI coaching. Triggers on "log this trade", "show my stats", "how am I doing on strategy X", "review my last 20 trades", "import trades from CSV", "what's my win rate", "equity curve", "generate a performance report", or "coach me on my entries". Stores trades in SQLite, computes per-strategy and per-symbol stats, and uses Claude for qualitative trade review.
---

# Trade Journal

Log trades, tag strategies, compute performance stats, and get LLM-powered coaching.

## Trade logging

Every trade is stored in a local SQLite database (`trades.db` by default) with full metadata:

| Field | Type | Notes |
|---|---|---|
| id | UUID | Auto-generated |
| symbol | str | Ticker / pair |
| side | str | "buy" or "sell" |
| quantity | float | Units traded |
| price | float | Fill price |
| timestamp | datetime | Execution time |
| strategy | str | Strategy name for grouping |
| tags | list[str] | Freeform tags, stored as JSON |
| notes | str | Trade rationale |
| fees | float | Commission + slippage cost |
| pnl | float or None | Realized P&L, filled on close |
| closed_at | datetime or None | When the position was closed |
| entry_id | str or None | Links an exit trade to its entry |

Use `JournalDB.log()` to insert and `JournalDB.close_trade()` to mark an entry as closed with realized P&L.

## Strategy tagging

Every trade carries a `strategy` string and a `tags` list. Use these to slice performance:

```python
from scripts.models import JournalDB
db = JournalDB("trades.db")
momentum_trades = db.query(strategy="momentum")
scalps = db.query(tags=["scalp", "intraday"])
```

## Performance stats

`scripts/stats.py` computes:

- **Win rate** — winners / total closed trades
- **Avg win / avg loss** — mean P&L of winners vs losers
- **Profit factor** — gross wins / gross losses
- **Expectancy** — avg P&L per trade
- **Sharpe** — annualized if enough data points (>30)
- **Max win / max loss** — extremes
- **Avg hold time** — mean time between entry and close

Stats can be grouped by strategy, symbol, or time period (day/week/month).

## LLM review and coaching

`scripts/review.py` sends recent trades + stats to Claude for qualitative analysis. Focus areas:

| Focus | What it looks at |
|---|---|
| general | Overall performance patterns |
| risk | Position sizing, stop placement, risk/reward |
| entries | Entry timing, confirmation signals |
| exits | Exit timing, profit-taking, stop management |
| psychology | Revenge trading, FOMO, discipline patterns |

The review returns strengths, weaknesses, patterns, action items, and an overall grade (A-F).

```python
from scripts.review import quick_review
from scripts.models import JournalDB
report = quick_review(JournalDB("trades.db"), strategy="momentum", last_n=20)
```

## CSV import

Import trades from broker exports or spreadsheets:

```python
db.import_csv("exports/trades.csv")
```

See `templates/trade_log.csv` for the expected column format. Custom column mappings are supported via the `mapping` parameter.

## Reporting

`scripts/report.py` generates a full performance report:

- `summary.md` — overall and per-strategy stats tables
- `equity.png` — cumulative P&L chart
- Per-strategy breakdowns

CLI usage:

```bash
python -m scripts.report --db trades.db --output ./reports
python -m scripts.report --db trades.db --strategy momentum --period month
```

## Scripts

- `scripts/models.py` — Trade dataclass and JournalDB (SQLite)
- `scripts/stats.py` — TradeStats computation, grouping, equity curve
- `scripts/review.py` — LLM-powered trade review and coaching
- `scripts/report.py` — Markdown + chart report generation, CLI
