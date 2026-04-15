---
name: app-gap-analysis
description: Use when the user wants to identify a top-selling / top-grossing / top-ranked app (by category, country, date) and extract the market gaps where it falls short — missing features, recurring user complaints, underserved segments, pricing friction — to brief a new competing or complementary app. Triggers on "what are people complaining about in <app>", "find gaps in the #1 finance app", "give me an opportunity brief for the top travel app", or "what should I build that beats <app>". Output is a structured OpportunityBrief ready to hand off to a scaffold skill.
---

# App Gap Analysis

Turn the market leader into your product brief. Pipeline:

```
pick chart → fetch top apps → pull reviews+metadata → extract pain points
          → cluster into gaps → synthesize OpportunityBrief → hand off to scaffold
```

## When to use

- "What's the top grossing app in Finance US today and what do users hate about it?"
- "Analyze the #1 free iOS app this week and propose a better alternative."
- "Find three underserved features in the top habit-tracking app."
- "Build me a product brief for a Calm competitor."

## Data sources

| Source | Free? | Coverage | Notes |
|---|---|---|---|
| Apple RSS Marketing Tools | yes | top-free, top-paid, top-grossing, new, apps by category and country | JSON, no auth: `rss.applemarketingtools.com` |
| iTunes Lookup API | yes | app metadata (price, genre, ratings summary, description, version) | JSON, no auth |
| iTunes Customer Reviews RSS | yes | up to ~500 reviews per app per country | paginated, per-country |
| `google-play-scraper` (pypi) | yes | Play Store charts + reviews + app details | unofficial, rate-limit politely |
| Sensor Tower / data.ai | paid | deep rankings, revenue estimates | use if the user has credentials |

**Start with free sources.** Escalate to paid only if the user specifies. Never scrape behind authentication walls.

## Chart selection

Ask the user for:

1. **Country** — default `us`
2. **Platform** — `ios`, `android`, or `both`
3. **Chart type** — `top-free`, `top-paid`, `top-grossing` (iOS only, requires legacy endpoint), `top-new`
4. **Category** — `all`, `finance`, `games`, `productivity`, etc.
5. **Depth** — just the #1, or top N (typically N = 5 for a category sweep)

If ambiguous, default to: US, iOS, top-grossing, all categories, top 1.

## Pipeline steps

### 1. Fetch the chart
`scripts/fetch_top_apps.py` — returns a list of `AppEntry(rank, id, name, developer, category, price, url, icon)`.

### 2. Pull app metadata + reviews
`scripts/reviews.py` — for each app:
- Metadata: rating avg, rating count, description, version, last update, size, in-app purchases
- Reviews: fetch the most recent ~200 reviews + the top-rated and lowest-rated subsets
- Normalize to `Review(stars, title, body, posted_at, version, helpful_count)`

### 3. Extract pain points
Two extraction modes — run both and reconcile:

**Statistical (zero-API-cost):**
- Filter to reviews with stars <= 2
- Tokenize, remove stopwords, lemmatize
- TF-IDF against the positive-review corpus to surface terms that are distinctive to negatives
- Cluster negative reviews (MiniBatchKMeans on TF-IDF vectors, k=5-8)
- Per cluster: centroid keywords + 3 representative reviews

**LLM (deeper):**
- `scripts/llm_analysis.py` calls Claude with a structured prompt
- Input: a sample of 50–100 negative reviews, app description, category
- Output: ranked list of pain-point themes with severity, frequency, sample quotes

Reconcile by intersecting themes — anything both methods surface is a high-confidence gap.

### 4. Classify into a gap taxonomy

Every gap is tagged with one or more of:

- `missing_feature` — users requesting functionality not present
- `ux_friction` — confusing flows, excessive steps, bad defaults
- `performance` — slow, crashes, battery drain, large downloads
- `pricing` — paywalls, subscription fatigue, unclear value
- `reliability` — sync issues, data loss, bugs
- `privacy` — tracking concerns, data handling
- `platform_gap` — missing Android / tablet / web parity
- `underserved_segment` — specific demographic or use case ignored

### 5. Produce the OpportunityBrief

A structured document — markdown with a JSON sidecar for programmatic handoff. Contents:

```
Title
One-line thesis

Target user
  Primary persona
  Specific unmet need
  Current coping strategy

Competitive landscape
  Incumbent: <app> — strengths, weaknesses, review sentiment
  Adjacent alternatives

Gap analysis
  Top 5 gaps, ranked by (frequency × severity)
  Evidence: quoted reviews per gap

Opportunity thesis
  How a new product can win (differentiation strategy)
  Defensibility — why incumbent won't close this in 6 months

MVP scope
  Must-have features (addresses top 3 gaps)
  Nice-to-have (top 4-5)
  Explicit non-goals (what we won't build)

Monetization
  Model proposal (freemium, one-time, subscription, etc.)
  Rationale tied to user pain with incumbent pricing

Risks
  Market: is demand real or vocal minority?
  Execution: platform restrictions, API deps, moat
  Legal: trademark, scraping, DMCA

Next steps
  Validation experiments (5 interviews + landing-page test)
  Tech stack recommendation
  Scaffold skill to invoke next
```

### 6. Hand off to scaffold

If the brief's tech stack points at mobile / web / backend / CLI, invoke `trading-app-scaffold` (or a future general app-scaffold). Pass the brief's `features` list so the scaffold can stub the right screens.

## Critical judgment calls

**Signal vs noise in reviews.** 1-star reviews are biased toward churned users and brigading. Counter-balance by:
- Weighting by helpful-votes where available
- Looking at version-specific reviews to isolate current pain vs legacy issues
- Checking rating distribution shape — a bimodal (lots of 5s and 1s) means a polarizing feature, not a bad app
- Reading the positives too — features users love are moats, not gaps

**Vocal minority detection.** If a pain point appears in < 2% of reviews, it's probably not a market gap — it's an edge case. Don't build a company around it.

**Revenue vs rank.** Top-grossing != most-downloaded. A top-grossing app often has high churn and angry paying users (great gap target). A top-free app may be loved but unmonetized. Match chart type to the opportunity type you want.

**Don't copy, differentiate.** If your brief's "opportunity thesis" is "do the same thing but better", it's weak. Strong theses name a segment the incumbent ignores, a workflow they fumble, or a pricing model they refuse to offer.

## Legal & ethical

- Respect `robots.txt` and Terms of Service. The RSS and lookup APIs are explicitly public.
- Don't scrape behind login or auth walls.
- Trademarks: don't copy names, icons, or protected trade dress in the new app.
- Patents: flag if the incumbent has claimed IP on a core mechanic.
- Never fabricate reviews or use competitor review text as training data for anything user-facing.

## Scripts

- `scripts/fetch_top_apps.py` — Apple RSS + google-play-scraper wrapper
- `scripts/reviews.py` — review fetchers + normalization
- `scripts/analyze.py` — statistical pain-point extraction
- `scripts/llm_analysis.py` — Claude-powered qualitative analysis
- `scripts/brief.py` — OpportunityBrief dataclass + markdown/JSON rendering
- `scripts/pipeline.py` — end-to-end driver that ties the above together

## Templates

- `templates/brief.md.j2` — Jinja2 template for the rendered brief
- `templates/analysis_prompt.md` — the Claude analysis prompt with few-shot examples
