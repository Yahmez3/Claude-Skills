---
name: sentiment-analysis
description: Use when the user wants to gauge market sentiment from social media, news, or forums and convert it into trading signals. Triggers on requests like "what's the sentiment on AAPL", "scrape Reddit for crypto sentiment", "build a contrarian signal from news sentiment", or "score social media buzz for TSLA". Fetches text from Reddit, Twitter/X, and news sources, scores sentiment via VADER, TextBlob, or LLM, and produces directional signals based on rolling z-scores.
---

# Sentiment Analysis

Scrapes social and news sentiment, scores it, and turns it into discrete trading signals compatible with the `technical-analysis` and `backtesting` skills.

## Supported sources

| Source | Library | Free tier | Notes |
|---|---|---|---|
| Reddit | `praw` | Yes (OAuth app) | r/wallstreetbets, r/stocks, r/cryptocurrency |
| News | `feedparser` / NewsAPI | RSS free; NewsAPI free tier 100 req/day | Google News, Yahoo Finance RSS |
| Twitter/X | `snscrape` or X API v2 | snscrape free; API v2 requires credentials | Placeholder — X API access is volatile |

All sources return a common `TextItem` dataclass. Each accepts a symbol filter and a lookback window.

## Sentiment engines

| Engine | Library | Speed | Quality | Cost |
|---|---|---|---|---|
| VADER | `nltk.sentiment.vader` | Very fast | Good for social media slang | Free |
| TextBlob | `textblob` | Fast | Decent general-purpose | Free |
| LLM (Claude) | `anthropic` SDK | Slow (API) | Best nuance, sarcasm detection | Per-token |

The LLM engine uses batch scoring — multiple texts per request with prompt caching to reduce cost. Default model is `claude-sonnet-4-6`.

`ensemble_score` averages across multiple methods for a more robust reading.

## Signal generation

Signals follow the same `{-1, 0, +1}` convention as `technical-analysis`.

1. **Aggregate** scored text into `SentimentSnapshot` per symbol per time window.
2. **Compute rolling z-scores** across the snapshot time series.
3. **Generate signal** in one of two modes:
   - **Momentum**: z-score above threshold => +1 (bullish crowd = buy), below -threshold => -1.
   - **Contrarian**: reverse of momentum (extreme bullish crowd = sell into euphoria).

Default z-score threshold is 1.5. Adjust based on asset class — crypto tends to need higher thresholds due to noisier sentiment.

## Safety

- **Rate limits**: respect per-source rate limits. PRAW handles its own; NewsAPI has a 100 req/day free cap; Twitter requires careful throttling.
- **API keys**: read from environment variables (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `NEWSAPI_KEY`, `TWITTER_BEARER_TOKEN`, `ANTHROPIC_API_KEY`). Never hardcode.
- **No PII storage**: text items are scored and aggregated; raw text is not persisted to disk by default.
- **Deduplication**: `text_id` (hash of source + URL) prevents double-counting cross-posted content.

## Credentials

```
REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT
NEWSAPI_KEY
TWITTER_BEARER_TOKEN
ANTHROPIC_API_KEY
```

## Scripts

- `scripts/sources.py` — data fetchers for Reddit, news, and Twitter
- `scripts/sentiment.py` — VADER, TextBlob, and LLM scoring engines
- `scripts/aggregator.py` — time-window aggregation and z-score computation
- `scripts/signals.py` — signal generation (momentum and contrarian modes)
- `scripts/pipeline.py` — end-to-end orchestration with CLI entrypoint
