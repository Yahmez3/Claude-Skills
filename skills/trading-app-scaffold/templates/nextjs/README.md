# Trading Dashboard (Next.js)

Production web dashboard — App Router, TypeScript, Tailwind, lightweight-charts.

## Run

```bash
cp .env.example .env.local
pnpm install
pnpm dev
```

Needs the FastAPI backend (`templates/fastapi/`) running on `NEXT_PUBLIC_BACKEND_URL`.

## Extend

- `/app/dashboard/page.tsx` — candlestick chart wired to `/bars`
- Add `/app/backtest/page.tsx` to POST to `/backtest` and render equity curves
- Add auth with Clerk or NextAuth — drop provider in `app/layout.tsx`

## Deploy

Push to GitHub, connect on Vercel, set `NEXT_PUBLIC_BACKEND_URL` to your deployed backend.
