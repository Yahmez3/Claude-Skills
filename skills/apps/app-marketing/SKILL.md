---
name: app-marketing
description: Use after an app is built to drive acquisition, activation, and retention. Covers positioning and messaging, App Store & Play Store Optimization (ASO), launch playbooks (Product Hunt, Hacker News, press, communities), paid acquisition (Apple Search Ads, Google Ads, Meta, TikTok), analytics instrumentation, review management, email/push lifecycle, and referral loops. Triggers on "how do I market this app", "write my App Store listing", "plan my Product Hunt launch", "help with ASO keywords", "respond to these reviews", or "set up analytics events".
---

# App Marketing

Turn a shipped app into a growing one. This skill covers the full funnel — discovery, install, activation, retention, monetization — with copy templates, scripts, and opinionated playbooks.

## Decision tree — pick the first move

Ask what matters most today. Don't run everything at once.

| Situation | First move |
|---|---|
| App is built, no users yet | Positioning + ASO + landing page |
| Have a landing page, no installs | Launch playbook (PH / HN / communities) |
| Installs but low activation | Instrumentation + onboarding audit |
| Activated but churning | Lifecycle (email / push) + retention loops |
| Retention OK but not growing | Referral + paid acquisition test |
| Negative reviews hurting ranking | Review response + bug-fix sprint |

## Positioning — do this first

Before any channel work, write the positioning in one page. Use the template in `templates/positioning.md`. It forces these answers:

1. **Category** — what shelf do you sit on? (e.g., "budgeting app" not "money tool")
2. **Target user** — specific persona, not "everyone"
3. **Alternatives** — what they use today (spreadsheets, incumbent app, nothing)
4. **Unique value** — the one thing you do that alternatives don't
5. **Proof** — why someone should believe it
6. **Category-defining words** — the 3-5 terms your ideal user would Google

Every piece of copy downstream (landing page headline, App Store title, ads) references this document. Revise the positioning before revising the copy.

## App Store Optimization (ASO)

Listing metadata is 60%+ of organic discovery. Get it right once, then iterate monthly.

### Metadata budget (iOS)

| Field | Limit | Indexed? | Priority |
|---|---|---|---|
| App Name | 30 chars | yes — high weight | critical |
| Subtitle | 30 chars | yes | critical |
| Keywords field | 100 chars | yes (not visible) | critical |
| Promotional Text | 170 chars | no | launch/updates only |
| Description | 4000 chars | no (App Store), but yes for Play | SEO for web |
| Screenshots | up to 10, first 3 matter | — | critical |

### Metadata budget (Android / Play)

| Field | Limit | Indexed? |
|---|---|---|
| Title | 30 chars | yes |
| Short description | 80 chars | yes (heavy weight) |
| Full description | 4000 chars | yes (all of it) |
| Feature graphic, screenshots | — | — |

### Workflow

1. **Seed keywords** — from positioning + category, list 20 candidates.
2. **Expand** — run `scripts/aso_keywords.py` to pull long-tail variants, volume proxies, and competitor usage from the iTunes search suggestions endpoint.
3. **Score** — each keyword gets `(relevance, difficulty, volume_proxy)`. Keep high-relevance, low-to-mid-difficulty terms. Difficulty = count of top-ranked competitors already using the term in title/subtitle.
4. **Pack** — fit top 8-12 terms into App Name + Subtitle + Keywords field. Never repeat words across fields (iOS indexes them separately — repetition wastes budget).
5. **Lint** — run `scripts/aso_lint.py` on the draft listing for character limits, Apple guideline violations, and common mistakes (brand-names you don't own, prohibited terms).
6. **A/B test** — use App Store Connect's "Product Page Optimization" (up to 3 variants against control).

### Screenshots

The first 3 screenshots are what users see without swiping. Rules:

- **Screenshot 1:** biggest promise + social proof if you have it (e.g., "Budget in 2 taps — 4.8★ from 12k users").
- **Screenshot 2:** the core product interaction, big and readable.
- **Screenshot 3:** the unique differentiator (the gap you identified vs the market leader).
- **4-6:** feature highlights, one claim each.
- **7+:** use case variety.

Composition guide in `templates/screenshots/README.md`. Use device frames, large text overlays (min 36px), contrast-checked colors.

## Launch playbook

A launch is a one-time spike. Don't depend on it for ongoing growth. But do it properly — a soft launch plus a hard launch in one week.

### 2 weeks before
- Landing page live with email capture
- Press kit ready (`templates/press-kit/`)
- Analytics wired: installs, activation, retention D1/D7
- Support email routed
- Ten friendly early users installed and giving feedback

### 1 week before
- Product Hunt teaser page (scheduled for Tuesday 12:01am PT — see note below)
- Pitch emails to 5-10 journalists/newsletters in your niche
- Schedule tweets / LinkedIn post / Reddit post drafts
- "Hunt kit" ready: 5 screenshots, 30-second demo video, GIF, tagline

### Launch day
- Post at 12:01am PT on Product Hunt (the hunting window is calendar-day PT)
- Email the waitlist with a personal note from founder
- Ship your tweet thread and LinkedIn at 9am ET for US reach
- Post in 3-5 relevant communities you're already known in (never a cold drop)
- Respond to every comment on PH within 2 hours — this is the #1 ranking signal
- Monitor for bugs; have a push ready if something breaks

### +1 day
- Hacker News "Show HN" if the app fits (indie, technical, or genuinely novel)
  - Tuesday-Thursday morning ET gets the best traction
  - Never "Show HN:" without the prefix; never link-drop in /r
- Email any press contacts who haven't responded

### +1 week
- Post a "launch retrospective" thread with real numbers (honesty beats hype for second-wave traffic)
- Reach out to the PH top-10 commenters personally
- Send the launch recap to your investors / advisors

See `scripts/launch_checklist.py` for a generator that emits a dated checklist from a YAML config.

## Analytics — instrument before launch

You cannot improve what you don't measure. Minimum event schema in `scripts/analytics_schema.py` with bindings for PostHog, Mixpanel, and GA4.

### Minimum viable events

| Event | When | Props |
|---|---|---|
| `install` | first open | source, campaign, device, country |
| `signup_started` | auth form shown | method |
| `signup_completed` | account created | method |
| `activation` | user does the thing (defined per-app) | time_to_activation_s |
| `key_action` | core repeat action | count_today |
| `paywall_shown` | paywall impression | offer, context |
| `subscribe_started` | tapped "buy" | offer |
| `subscribe_completed` | purchase verified | offer, ltv_est |
| `uninstall` (Android) / inferred | — | days_since_install |

### The activation metric

Define a single "aha moment" action for your app. Retention D7 and LTV track closely with whether a user hits it within 24 hours. Examples:

- Budgeting app: categorized 10 transactions
- Social app: followed 5 accounts + posted once
- Note app: created 3 notes and returned the next day
- Trading app: connected broker + placed first (paper) trade

Put the entire onboarding flow behind optimizing this one number.

## Paid acquisition — only after organic works

Rule of thumb: paid is for scaling a proven funnel, not discovering one. If organic CAC/LTV is unknown, paid data is noise. When ready:

| Channel | Best for | Starting budget |
|---|---|---|
| Apple Search Ads (basic) | High-intent iOS installs, branded defense | $30-100/day |
| Google Ads UAC | Android scale | $50-150/day |
| Meta / Instagram | Visual products, consumer | $50-200/day |
| TikTok | Gen-Z, entertainment-leaning | $50-200/day |
| Reddit | Niche B2C, developer tools | $30-100/day |

Per channel, run one tight creative test for 5-7 days before judging. `templates/paid/campaign-brief.md` captures the test parameters.

### Attribution

For iOS 14.5+, use **Apple Search Ads Attribution API** + SKAdNetwork. For Android, use **Google Play Install Referrer** + standard UTMs. Wrap both in a server-side layer that posts events to your warehouse. Third-party attribution (Adjust, AppsFlyer) is worth it above $500/mo ad spend; below that, hand-roll.

## Reviews

Reviews are a compounding asset — they drive both ranking and conversion. Manage them like product work.

### Prompting

Never prompt on first open. Prompt **after an activation event** (not before), and only if the user has engaged 3+ times. Use the native rating API (iOS `SKStoreReviewController`, Android In-App Review API). Apple caps at 3 prompts/year per user — don't waste them.

### Responding

Respond to:
- All 1-3 star reviews within 48 hours
- All 4-5 star reviews that mention a feature request
- New reviews after a major update (acknowledge fixes)

Use `scripts/review_response.py` for Claude-drafted responses (you edit, never auto-post). The prompt encodes tone: warm, specific, no corporate-speak, acknowledge first then explain.

## Lifecycle — email, push, in-app

Three moments matter disproportionately:

1. **First 24 hours** — get to activation. Automated email 1h after signup with the single next step. Push notification (permission requested *after* activation, not on first open) if they don't return by day 2.
2. **First churn signal** — usually day 3 or day 7. Win-back email with a specific piece of value (not "we miss you").
3. **Before billing** — for subscription apps, an email 3 days before renewal reminding them of what they got this month. Counterintuitively lowers chargebacks more than it hurts revenue.

Templates in `templates/email/`.

## Referral loops

Build a referral mechanism only if your core loop is strong (good retention). Otherwise you're paying users to install a leaky bucket.

Good patterns:
- **Give-and-get** — referrer + referee both get something (Dropbox classic)
- **Contentful referral** — share a result, not a generic link (Duolingo streaks, Wrapped)
- **Collaboration-native** — referral == inviting someone into shared content (Notion, Figma)

Avoid pure cashback referrals for consumer apps — attracts bounty hunters.

## Landing page

A launch without a landing page wastes 50% of the spike. The `templates/landing-page/` is a Next.js 14 starter with:

- Above-the-fold headline, subhead, CTA (waitlist or App Store badges)
- Social proof row (logos or "As seen in")
- 3 feature sections with screenshots
- Waitlist form → Resend / Loops / ConvertKit
- OG image for social shares
- Analytics preinstalled (Plausible or PostHog)
- Deploy on Vercel in one command

Copy structure in `templates/landing-page/COPY.md`.

## Press & outreach

Cold outreach works. The trick is specificity. Use `scripts/press_outreach.py` to draft pitches from the positioning doc + a list of target outlets. It produces personalized first lines (not mail-merge tokens).

Targets by app type:

| App type | Outlets |
|---|---|
| Indie productivity | The Sweet Setup, MacStories, Beautiful Pixels, Hacker News |
| Developer tool | Changelog, Hacker Newsletter, Rundown AI |
| Consumer social | TechCrunch, The Verge, niche subreddits |
| Finance / fintech | Finextra, TearSheet, niche newsletters |

## Critical judgment calls

- **Don't fake traction.** Fake reviews, bot installs, paid-for PH upvotes — all short-term wins, long-term damage (and Apple/PH do notice). Build real.
- **Vanity vs. value.** Install count is vanity. D7 retention + weekly active users is value. Report the latter internally.
- **Don't over-brand.** Early on, clear beats clever. "Budgeting app for people who hate budgeting" > "Finlux: your financial canvas".
- **Respond to the loudest critics, not the average user.** A single thoughtful response to a 1-star review converts the onlookers.
- **Keep a changelog.** Public changelogs drive retention. Users love knowing you're alive.

## Scripts

- `scripts/aso_keywords.py` — keyword expansion + scoring via iTunes search suggestions
- `scripts/aso_lint.py` — listing validator (character limits, keyword density, guideline flags)
- `scripts/launch_checklist.py` — date-based launch checklist generator
- `scripts/analytics_schema.py` — canonical event schema + PostHog/Mixpanel/GA4 emitters
- `scripts/review_response.py` — Claude-drafted review replies (never auto-post)
- `scripts/press_outreach.py` — personalized pitch email generator

## Templates

- `templates/positioning.md` — one-page positioning doc
- `templates/landing-page/` — Next.js landing page starter
- `templates/email/` — onboarding, win-back, pre-renewal, launch announcement
- `templates/press-kit/` — boilerplate, fact sheet, asset list
- `templates/aso/listing.md` — iOS + Android listing skeleton
- `templates/screenshots/README.md` — composition guide
- `templates/social/` — Twitter thread, LinkedIn, Reddit post skeletons
