# Landing page starter

Next.js 14 App Router, TypeScript, Tailwind. One page, waitlist capture, OG image slot.

## Run

```bash
cp .env.example .env.local
pnpm install
pnpm dev
```

## Wire the waitlist

Default: posts to Resend Audiences. To swap:

- **Loops**: replace the fetch in `app/api/waitlist/route.ts` with `POST https://app.loops.so/api/v1/contacts/create`
- **ConvertKit**: `POST https://api.convertkit.com/v3/forms/{form_id}/subscribe`
- **Postgres**: swap for a Drizzle/Prisma insert

## Deploy

Push to GitHub → connect to Vercel → set env vars → done.

## Checklists

- `COPY.md` — headline / subhead / CTA checklist before launch
