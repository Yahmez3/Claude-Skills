# TradingAgents Dashboard

A web UI for launching [TradingAgents](https://github.com/TauricResearch/TradingAgents) analyses and watching agent progress in real time.

## What it does

- **Launch runs from the browser** — pick a ticker, date, LLM provider, analyst team, debate rounds.
- **Live progress stream** — Server-Sent Events push each LangGraph node transition (Market Analyst → Bull/Bear debate → Trader → Risk team → Portfolio Manager) as it happens.
- **Per-run report viewer** — once a node completes, its report (market, sentiment, news, fundamentals, debates, final decision) is rendered.
- **Historical decisions** — parses `~/.tradingagents/memory/trading_memory.md` and shows past decisions, realised returns, alpha vs SPY, and reflections.

## Layout

```
dashboard/
├── app/
│   ├── main.py        # FastAPI app + routes
│   ├── runner.py      # Background TradingAgents runner with SSE event queue
│   ├── runs.py        # SQLite run registry
│   ├── memory.py      # Wraps TradingAgents' memory log + per-run JSON
│   ├── templates/
│   └── static/
├── pyproject.toml
├── .env.example
└── README.md
```

The dashboard depends on a sibling `TradingAgents/` checkout (the `[tool.uv.sources]` block in `pyproject.toml` installs it as an editable local dep).

## Setup

```bash
# from the repo root
git clone https://github.com/TauricResearch/TradingAgents.git    # if not already cloned
cd dashboard
cp .env.example .env                                              # add at least one provider key
uv sync                                                           # or: pip install -e . -e ../TradingAgents
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000.

## Architecture notes

- **Streaming**: each run launches a background thread that drives `graph.stream()` and pushes node events into an `asyncio.Queue`. The SSE endpoint drains the queue.
- **State**: the dashboard's own run registry is a tiny SQLite DB (`runs.db`). TradingAgents writes its own per-run JSON to `~/.tradingagents/logs/<TICKER>/...` — the dashboard reads from there.
- **No key storage**: API keys live only in `.env`. The dashboard never persists them.
