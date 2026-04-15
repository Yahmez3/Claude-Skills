---
name: trading-app-scaffold
description: Use when bootstrapping a new trading-focused application — dashboards, mobile apps, backend APIs, or CLI tools. Triggers on "scaffold a trading dashboard", "build a FastAPI backend for my bot", "create a React Native trading app", or "set up a CLI for my strategy". Generates a minimal-but-complete project with routing, state management, market-data integration hooks, and deployment config.
---

# Trading App Scaffold

Bootstrap trading applications across four shapes. Pick the right one based on the user's need.

| Shape | Template | Best for |
|---|---|---|
| Web dashboard — fast | `templates/streamlit` | Personal research dashboards, internal tools |
| Web dashboard — prod | `templates/nextjs` | Shareable dashboards with auth, charts |
| Mobile app | `templates/react-native` | iOS/Android portfolio & alerting |
| Backend / API | `templates/fastapi` | Bot services, webhooks, WebSocket streaming |
| CLI tool | `templates/cli` | Quick scripts, cron jobs, ops tooling |

## Decision flow

Ask the user if unclear:

1. **"Is this for you alone, or for others?"** → personal = Streamlit or CLI; others = Next.js / React Native.
2. **"Do you need real-time streaming?"** → yes = add WebSocket layer (Next.js + FastAPI, React Native + FastAPI).
3. **"Mobile or web?"** → mobile = React Native; web = Next.js.
4. **"Does it execute trades, or just display?"** → executes = pair with `trading-bot` skill; display-only = data fetch + charts.

## Shared components

Every template includes:

- **Price chart** — lightweight-charts (web) or react-native-wagmi-charts (mobile)
- **Market data hook** — pulls from `market-data` skill's normalized output
- **Auth stub** — JWT via Clerk / Supabase / NextAuth
- **Env management** — `.env.example` with every secret the app needs
- **Deploy config** — Vercel (Next.js), Fly.io (FastAPI), Expo EAS (RN)

## Workflow

1. **Clarify scope** — ask the 4 questions above.
2. **Copy the template** — `cp -r templates/<chosen> <dest>`.
3. **Patch the name** — update `package.json` / `pyproject.toml` / `app.json`.
4. **Inject integrations** — wire up market-data calls, broker adapters if needed.
5. **Add features one at a time** — don't pile on; commit after each.
6. **Run locally** — the template always includes a `make dev` or equivalent that works out of the box.

## Templates

### Streamlit (fast web dashboard)
`templates/streamlit/` — single-file app with sidebar config, chart, live metrics, and a "Refresh" button. Auto-reloads on save.

### Next.js (production dashboard)
`templates/nextjs/` — App Router, TypeScript, Tailwind, lightweight-charts, tRPC, Postgres via Drizzle, Clerk auth. Includes a `/dashboard` page with portfolio view and a `/backtest` page that runs against the FastAPI backend.

### React Native (mobile)
`templates/react-native/` — Expo Router, TypeScript, NativeWind, Zustand store, react-native-wagmi-charts, Expo Secure Store for credentials. Includes watchlist, alerts (via Expo Notifications), and broker connection screens.

### FastAPI (backend)
`templates/fastapi/` — FastAPI + Uvicorn, SQLAlchemy async, Postgres + TimescaleDB, Redis for pub/sub, WebSocket endpoints for live quotes, REST for orders/positions/backtests. Integrates with `trading-bot` skill's `Broker` adapters.

### CLI
`templates/cli/` — Typer app with subcommands: `fetch`, `backtest`, `signal`, `bot`. Includes rich-powered progress bars and pretty tables. Installable via `pipx install -e .`.

## After scaffolding

Point the user at:
- How to start dev server (`make dev`)
- Where to add env vars (`.env.local` / app secrets)
- How to deploy (template-specific README)
- How to integrate the other skills (market-data, backtesting, trading-bot)

## Conventions

- **TypeScript for web/mobile**, **Python 3.11+ for backend/CLI**.
- No "kitchen sink" starters — each template fits on one screen's worth of files.
- Every template ships with one working page/endpoint and clear extension points.
- All templates use pinned deps and `pnpm` / `uv` for installs.
