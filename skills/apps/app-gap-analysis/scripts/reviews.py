"""Pull and normalize app reviews from both stores.

Apple reviews: public RSS at
    https://itunes.apple.com/{country}/rss/customerreviews/page={n}/id={app_id}/sortBy=mostRecent/json

Google Play: via `google-play-scraper.reviews`.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from urllib.request import Request, urlopen


@dataclass
class Review:
    platform: str
    app_id: str
    author: str
    stars: int
    title: str
    body: str
    version: str
    posted_at: Optional[str]     # ISO8601 string or None
    helpful: int = 0

    def dict(self) -> dict:
        return asdict(self)


def _get_json(url: str, timeout: float = 10.0) -> dict:
    req = Request(url, headers={"User-Agent": "app-gap-analysis/0.1"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------------- Apple ----------------

def fetch_apple_reviews(
    app_id: str,
    country: str = "us",
    max_pages: int = 10,
    sleep_s: float = 0.5,
) -> list[Review]:
    """Paginate the customer-reviews RSS. Apple caps around 10 pages / 500 reviews."""
    out: list[Review] = []
    for page in range(1, max_pages + 1):
        url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
               f"page={page}/id={app_id}/sortby=mostrecent/json")
        try:
            data = _get_json(url)
        except Exception:
            break
        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break
        # First entry is the app metadata — skip if it lacks "im:rating"
        for e in entries:
            if "im:rating" not in e:
                continue
            out.append(Review(
                platform="ios",
                app_id=app_id,
                author=e.get("author", {}).get("name", {}).get("label", ""),
                stars=int(e["im:rating"]["label"]),
                title=e.get("title", {}).get("label", ""),
                body=e.get("content", {}).get("label", ""),
                version=e.get("im:version", {}).get("label", ""),
                posted_at=e.get("updated", {}).get("label"),
                helpful=int(e.get("im:voteSum", {}).get("label", "0") or 0),
            ))
        time.sleep(sleep_s)
    return out


# ---------------- Google Play ----------------

def fetch_play_reviews(app_id: str, country: str = "us", limit: int = 500) -> list[Review]:
    try:
        from google_play_scraper import Sort, reviews
    except Exception:
        return []
    rows, _ = reviews(app_id, lang="en", country=country,
                      sort=Sort.NEWEST, count=limit)
    out: list[Review] = []
    for r in rows:
        out.append(Review(
            platform="android",
            app_id=app_id,
            author=r.get("userName", ""),
            stars=int(r.get("score", 0)),
            title="",
            body=r.get("content", "") or "",
            version=r.get("reviewCreatedVersion") or "",
            posted_at=r["at"].isoformat() if isinstance(r.get("at"), datetime) else None,
            helpful=int(r.get("thumbsUpCount", 0) or 0),
        ))
    return out


def fetch_reviews(platform: str, app_id: str, country: str = "us",
                  limit: int = 500) -> list[Review]:
    if platform == "ios":
        return fetch_apple_reviews(app_id, country, max_pages=max(1, limit // 50))
    if platform == "android":
        return fetch_play_reviews(app_id, country, limit)
    raise ValueError(f"unknown platform: {platform}")


def rating_distribution(reviews: list[Review]) -> dict[int, int]:
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        if 1 <= r.stars <= 5:
            dist[r.stars] += 1
    return dist


def split_by_sentiment(reviews: list[Review]) -> tuple[list[Review], list[Review]]:
    """Return (negative, positive). 1-2 stars = negative, 4-5 = positive, 3 ignored."""
    neg = [r for r in reviews if r.stars <= 2]
    pos = [r for r in reviews if r.stars >= 4]
    return neg, pos
