"""Data sources for sentiment analysis. Each source returns TextItem lists."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

try:
    import praw
except ImportError:
    praw = None  # type: ignore[assignment]

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment]

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]


@dataclass
class TextItem:
    text: str
    source: str  # "reddit" | "news" | "twitter"
    symbol: str | None
    timestamp: datetime
    url: str
    text_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.text_id:
            raw = f"{self.source}:{self.url}"
            self.text_id = hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cutoff(lookback_hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


class RedditSource:
    DEFAULT_SUBS = ["wallstreetbets", "stocks", "cryptocurrency"]

    def __init__(
        self,
        subreddits: list[str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if praw is None:
            raise ImportError("pip install praw — required for RedditSource")
        self.subreddits = subreddits or self.DEFAULT_SUBS
        self.reddit = praw.Reddit(
            client_id=client_id or os.environ["REDDIT_CLIENT_ID"],
            client_secret=client_secret or os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=user_agent or os.environ.get("REDDIT_USER_AGENT", "sentiment-analysis/1.0"),
        )

    def fetch(
        self,
        symbol: str | None = None,
        lookback_hours: float = 24,
        limit: int = 100,
    ) -> list[TextItem]:
        cutoff = _cutoff(lookback_hours)
        items: list[TextItem] = []

        for sub_name in self.subreddits:
            subreddit = self.reddit.subreddit(sub_name)
            query = symbol if symbol else None
            submissions = subreddit.search(query, sort="new", time_filter="day", limit=limit) if query else subreddit.new(limit=limit)

            for post in submissions:
                ts = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if ts < cutoff:
                    continue
                body = f"{post.title} {post.selftext}".strip()
                items.append(TextItem(
                    text=body,
                    source="reddit",
                    symbol=symbol,
                    timestamp=ts,
                    url=f"https://reddit.com{post.permalink}",
                ))
                post.comments.replace_more(limit=0)
                for comment in post.comments[:10]:
                    c_ts = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
                    if c_ts < cutoff:
                        continue
                    items.append(TextItem(
                        text=comment.body,
                        source="reddit",
                        symbol=symbol,
                        timestamp=c_ts,
                        url=f"https://reddit.com{comment.permalink}",
                    ))

        return items


class NewsSource:
    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    YAHOO_FINANCE_RSS = "https://finance.yahoo.com/rss/headline?s={symbol}"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("NEWSAPI_KEY")

    def fetch(
        self,
        symbol: str | None = None,
        lookback_hours: float = 24,
        limit: int = 50,
        use_newsapi: bool = False,
    ) -> list[TextItem]:
        if use_newsapi and self.api_key:
            return self._fetch_newsapi(symbol, lookback_hours, limit)
        return self._fetch_rss(symbol, lookback_hours, limit)

    def _fetch_rss(
        self,
        symbol: str | None,
        lookback_hours: float,
        limit: int,
    ) -> list[TextItem]:
        if feedparser is None:
            raise ImportError("pip install feedparser — required for RSS-based NewsSource")

        cutoff = _cutoff(lookback_hours)
        urls = []
        if symbol:
            urls.append(self.GOOGLE_NEWS_RSS.format(query=symbol))
            urls.append(self.YAHOO_FINANCE_RSS.format(symbol=symbol))
        else:
            urls.append(self.GOOGLE_NEWS_RSS.format(query="stock+market"))

        items: list[TextItem] = []
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                ts = datetime.now(timezone.utc)
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    from calendar import timegm
                    ts = datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
                if ts < cutoff:
                    continue
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".strip()
                items.append(TextItem(
                    text=text,
                    source="news",
                    symbol=symbol,
                    timestamp=ts,
                    url=entry.get("link", ""),
                ))

        return items

    def _fetch_newsapi(
        self,
        symbol: str | None,
        lookback_hours: float,
        limit: int,
    ) -> list[TextItem]:
        if _requests is None:
            raise ImportError("pip install requests — required for NewsAPI")

        cutoff = _cutoff(lookback_hours)
        query = symbol or "stock market"
        resp = _requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "sortBy": "publishedAt",
                "pageSize": min(limit, 100),
                "apiKey": self.api_key,
                "from": cutoff.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        items: list[TextItem] = []
        for article in data.get("articles", []):
            ts = datetime.now(timezone.utc)
            if article.get("publishedAt"):
                ts = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
            text = f"{article.get('title', '')} {article.get('description', '')}".strip()
            items.append(TextItem(
                text=text,
                source="news",
                symbol=symbol,
                timestamp=ts,
                url=article.get("url", ""),
            ))

        return items


class TwitterSource:
    """Placeholder for Twitter/X data.

    X API v2 requires elevated access. snscrape stopped working after X
    locked down its endpoints. This class provides the interface so the
    pipeline can integrate Twitter data when access is available.
    """

    def __init__(self, bearer_token: str | None = None) -> None:
        self.bearer_token = bearer_token or os.environ.get("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            raise EnvironmentError(
                "Set TWITTER_BEARER_TOKEN env var. X API v2 requires a developer account "
                "with at least Basic tier access ($100/mo as of 2024)."
            )

    def fetch(
        self,
        symbol: str | None = None,
        lookback_hours: float = 24,
        limit: int = 100,
    ) -> list[TextItem]:
        if _requests is None:
            raise ImportError("pip install requests — required for TwitterSource")

        cutoff = _cutoff(lookback_hours)
        query = f"${symbol}" if symbol else "stock OR market OR crypto"
        query += " -is:retweet lang:en"

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": query,
            "max_results": min(limit, 100),
            "start_time": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tweet.fields": "created_at,author_id",
        }

        resp = _requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        items: list[TextItem] = []
        for tweet in data.get("data", []):
            ts = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
            items.append(TextItem(
                text=tweet["text"],
                source="twitter",
                symbol=symbol,
                timestamp=ts,
                url=f"https://twitter.com/i/status/{tweet['id']}",
            ))

        return items
