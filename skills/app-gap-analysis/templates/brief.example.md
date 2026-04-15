# Opportunity: beat ExampleBudget

_Underserved needs in ExampleBudget — especially offline-first use and one-time pricing — create room for a focused competitor targeting churned subscribers._

Generated: 2026-04-15T12:00:00Z

## Incumbent
**ExampleBudget** — Finance, ios, $9.99/month
Rating: 3.1 (42,104 ratings)
[Store listing](https://apps.apple.com/us/app/example/id123)

## Target user
- **Persona:** Former ExampleBudget paying user who churned over pricing
- **Unmet need:** Wants full envelope budgeting without a recurring subscription
- **Coping strategy:** Currently uses spreadsheets or a free-but-limited alternative

## Gap analysis
### 1. subscription-fatigue [high-confidence] (stat=24.3%, llm=30%)
Users complain the monthly fee stacks with other subscriptions and the value doesn't scale with usage.
Tags: `pricing, missing_feature`
**Opportunity:** Ship a one-time-purchase tier with full feature parity; optional cloud sync as a small monthly add-on.
> Used to be a great app, now every feature is behind a paywall...
> I have 12 subscriptions already. I would gladly pay $40 once for this.

### 2. sync-reliability [high-confidence] (stat=18.1%, llm=22%)
Reports of transactions disappearing after sync, duplicate entries after restoring from backup.
Tags: `reliability`
**Opportunity:** Offline-first architecture with CRDT-based conflict resolution; visible sync audit log.
> Lost two weeks of categorizations overnight. Support took 5 days to respond.

### 3. android-parity (stat=11.7%, llm=15%)
iOS features ship months ahead of Android; tablet layouts are poor.
Tags: `platform_gap`
**Opportunity:** Release-day parity across iOS, Android, and iPad with shared codebase (React Native).

_(gaps 4-5 omitted for brevity)_

## Incumbent strengths (don't attack head-on)
- Beautiful, well-polished iOS UI
- Deep bank-connection coverage via Plaid
- Established brand trust in the budgeting niche

## MVP scope
### Must-have
- One-time purchase tier with full envelope-budgeting feature set
- Offline-first with conflict-free sync
- iOS + Android + iPad from day one

### Nice-to-have
- Shared household budgets (up to 4 members)
- CSV import / export for all tables
- Optional self-hosted sync backend

### Non-goals
- Do not try to out-polish ExampleBudget on: Beautiful iOS UI
- Do not try to out-polish ExampleBudget on: Deep bank-connection coverage
- Will not ship tax prep or investment tracking in v1

## Monetization
**Model:** one-time purchase (no subscription)
**Rationale:** Pricing friction is the top-ranked complaint; a pay-once model directly removes that pain.

## Risks
- **Market:** Validate that the 24% subscription-fatigue cohort will actually pay $39 once (landing-page test).
- **Execution:** Parity on bank connections is expensive — consider manual import + limited Plaid tier at launch.
- **Legal:** Trademarked UI patterns in category; avoid ExampleBudget's envelope-icon metaphor.

## Recommended stack
- **mobile:** React Native + Expo
- **backend:** FastAPI + Postgres
- **web:** Next.js (App Router)

Scaffold skill: `trading-app-scaffold`

## Next steps
- 5 user interviews with churned ExampleBudget subscribers
- Landing page A/B test on "Budget once. Pay once." headline
- 3-week prototype: transaction entry + envelope allocation + offline sync
- Invoke scaffold: trading-app-scaffold
