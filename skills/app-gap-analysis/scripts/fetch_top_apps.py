"""Fetch top app charts from Apple RSS and Google Play.

Apple RSS Marketing Tools:
    https://rss.applemarketingtools.com/api/v2/{country}/apps/{chart}/{limit}/apps.json
    charts: most-downloaded-free, most-downloaded-paid, top-free, top-paid, new-apps-we-love
    (top-grossing requires the legacy RSS endpoint below)

Legacy Apple RSS (top-grossing, genre filter, still served):
    https://itunes.apple.com/{country}/rss/topgrossingapplications/limit={limit}/genre={id}/json

Google Play: uses the `google-play-scraper` package if installed. Graceful degradation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CHART_MAP_MODERN = {
    "top-free": "most-downloaded-free",
    "top-paid": "most-downloaded-paid",
    "top-new": "new-apps-we-love",
}

# Apple genre IDs (partial) — https://developer.apple.com/documentation/appstoreconnectapi/appstoreversion
IOS_GENRE_IDS: dict[str, int] = {
    "all": 0,
    "business": 6000, "weather": 6001, "utilities": 6002, "travel": 6003,
    "sports": 6004, "social-networking": 6005, "reference": 6006,
    "productivity": 6007, "photo-video": 6008, "news": 6009, "navigation": 6010,
    "music": 6011, "lifestyle": 6012, "health-fitness": 6013, "games": 6014,
    "finance": 6015, "entertainment": 6016, "education": 6017, "book": 6018,
    "medical": 6020, "food-drink": 6023, "shopping": 6024,
}


@dataclass
class AppEntry:
    platform: str
    chart: str
    country: str
    rank: int
    app_id: str
    name: str
    developer: str
    category: str
    price: str
    url: str
    icon: str

    def dict(self) -> dict:
        return asdict(self)


def _get_json(url: str, timeout: float = 10.0) -> dict:
    req = Request(url, headers={"User-Agent": "app-gap-analysis/0.1"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------------- Apple ----------------

def fetch_apple_modern(
    chart: str = "top-free",
    country: str = "us",
    limit: int = 25,
) -> list[AppEntry]:
    """Hit the modern marketing-tools RSS. No genre filter — returns overall chart."""
    feed_chart = CHART_MAP_MODERN.get(chart, chart)
    url = (f"https://rss.applemarketingtools.com/api/v2/{country}/apps/"
           f"{feed_chart}/{limit}/apps.json")
    data = _get_json(url)
    out: list[AppEntry] = []
    for i, item in enumerate(data["feed"]["results"], start=1):
        out.append(AppEntry(
            platform="ios", chart=chart, country=country, rank=i,
            app_id=item["id"], name=item["name"], developer=item["artistName"],
            category=item.get("genres", [{}])[0].get("name", ""),
            price="free" if chart.endswith("free") else item.get("artworkUrl100", ""),
            url=item["url"], icon=item.get("artworkUrl100", ""),
        ))
    return out


def fetch_apple_legacy(
    chart: Literal["topgrossingapplications", "topfreeapplications",
                   "toppaidapplications"] = "topgrossingapplications",
    country: str = "us",
    genre: str = "all",
    limit: int = 25,
) -> list[AppEntry]:
    """Legacy iTunes RSS — supports top-grossing and genre filtering."""
    genre_id = IOS_GENRE_IDS.get(genre, 0)
    parts = [f"limit={limit}"]
    if genre_id:
        parts.append(f"genre={genre_id}")
    url = f"https://itunes.apple.com/{country}/rss/{chart}/" + "/".join(parts) + "/json"
    data = _get_json(url)
    entries = data["feed"].get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    out: list[AppEntry] = []
    for i, item in enumerate(entries, start=1):
        out.append(AppEntry(
            platform="ios", chart=chart, country=country, rank=i,
            app_id=item["id"]["attributes"]["im:id"],
            name=item["im:name"]["label"],
            developer=item["im:artist"]["label"],
            category=item.get("category", {}).get("attributes", {}).get("label", genre),
            price=item.get("im:price", {}).get("label", ""),
            url=item["link"][0]["attributes"]["href"] if isinstance(item.get("link"), list)
                 else item.get("link", {}).get("attributes", {}).get("href", ""),
            icon=item["im:image"][-1]["label"] if item.get("im:image") else "",
        ))
    return out


def fetch_apple_lookup(app_id: str, country: str = "us") -> dict:
    """Full metadata for a single app via iTunes lookup API."""
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    data = _get_json(url)
    results = data.get("results") or []
    return results[0] if results else {}


# ---------------- Google Play ----------------

def fetch_play_chart(
    category: str = "APPLICATION",
    collection: str = "TOP_FREE",
    country: str = "us",
    limit: int = 25,
) -> list[AppEntry]:
    """Use google-play-scraper if available; return [] with a hint otherwise."""
    try:
        from google_play_scraper import app as gp_app  # noqa: F401
        from google_play_scraper.features.top_charts import top_charts  # type: ignore
    except Exception:
        return []

    rows = top_charts(category=category, collection=collection, country=country,
                      lang="en", count=limit)
    out: list[AppEntry] = []
    for i, r in enumerate(rows, start=1):
        out.append(AppEntry(
            platform="android", chart=collection.lower(), country=country, rank=i,
            app_id=r["appId"], name=r["title"],
            developer=r.get("developer", ""),
            category=r.get("genre", category),
            price="free" if r.get("free", True) else str(r.get("priceText", "")),
            url=r.get("url", ""),
            icon=r.get("icon", ""),
        ))
    return out


# ---------------- unified ----------------

def fetch_top(
    platform: Literal["ios", "android", "both"] = "ios",
    chart: str = "top-grossing",
    country: str = "us",
    category: str = "all",
    limit: int = 10,
) -> list[AppEntry]:
    out: list[AppEntry] = []
    if platform in ("ios", "both"):
        if chart == "top-grossing":
            out += fetch_apple_legacy("topgrossingapplications", country, category, limit)
        elif chart == "top-paid":
            if category == "all":
                out += fetch_apple_modern("top-paid", country, limit)
            else:
                out += fetch_apple_legacy("toppaidapplications", country, category, limit)
        else:
            if category == "all":
                out += fetch_apple_modern("top-free", country, limit)
            else:
                out += fetch_apple_legacy("topfreeapplications", country, category, limit)
    if platform in ("android", "both"):
        collection = {
            "top-free": "TOP_FREE",
            "top-paid": "TOP_PAID",
            "top-grossing": "GROSSING",
        }.get(chart, "TOP_FREE")
        out += fetch_play_chart(collection=collection, country=country, limit=limit)
    return out
