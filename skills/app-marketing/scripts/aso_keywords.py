"""ASO keyword research via iTunes search + competitor usage.

Public endpoints used (no auth):
- https://itunes.apple.com/search?term=...&entity=software&country=us
- https://itunes.apple.com/WebObjects/MZStoreServices.woa/wa/wsSearch?...
- Search suggestions: https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?clientApplication=Software&term={q}

Volume proxy is crude (count of suggestions + top-results breadth); for real volumes
buy data.ai / Sensor Tower. This module is for directional guidance only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from urllib.parse import quote
from urllib.request import Request, urlopen


SEARCH_URL = "https://itunes.apple.com/search?term={q}&entity=software&country={c}&limit=25"
HINTS_URL = ("https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/"
             "wa/hints?clientApplication=Software&term={q}")


@dataclass
class KeywordScore:
    term: str
    relevance: float        # 0..1 subjective (caller tunes)
    difficulty: int         # competitor-usage count in top results
    volume_proxy: int       # # of autocomplete suggestions containing term
    score: float            # relevance * volume / (1 + difficulty)

    def dict(self) -> dict:
        return asdict(self)


def _get(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "app-marketing-aso/0.1"})
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def search_top(term: str, country: str = "us") -> list[dict]:
    data = _get(SEARCH_URL.format(q=quote(term), c=country))
    return data.get("results", [])


def suggestions(term: str) -> list[str]:
    """Autocomplete hints — mirrors App Store search box."""
    try:
        data = _get(HINTS_URL.format(q=quote(term)))
    except Exception:
        return []
    hints = data.get("hints", [])
    return [h.get("term", "") for h in hints if h.get("term")]


def expand_seeds(seeds: list[str]) -> list[str]:
    """Build a long-tail candidate list from each seed via autocomplete."""
    out: set[str] = set()
    for s in seeds:
        out.add(s.lower().strip())
        for h in suggestions(s):
            out.add(h.lower().strip())
    # Drop pure single-char and overly-long tails
    return [t for t in out if 2 < len(t) <= 40]


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def competitor_usage(term: str, country: str = "us", top_n: int = 15) -> int:
    """How many of the top-N results for `term` actually use the term in title/subtitle?"""
    tokens = set(_normalize(term).split())
    if not tokens:
        return 0
    results = search_top(term, country)[:top_n]
    hits = 0
    for r in results:
        blob = _normalize(f"{r.get('trackName','')} {r.get('trackCensoredName','')} "
                          f"{r.get('description','')[:300]}")
        blob_tokens = set(blob.split())
        if tokens.issubset(blob_tokens):
            hits += 1
    return hits


def score_keyword(term: str, relevance: float = 0.8, country: str = "us") -> KeywordScore:
    """Per-term score. `relevance` is caller-provided (how relevant is term to MY app)."""
    hints = suggestions(term)
    volume_proxy = len([h for h in hints if term.lower() in h.lower()])
    diff = competitor_usage(term, country)
    score = (relevance * (1 + volume_proxy)) / (1 + diff)
    return KeywordScore(term=term, relevance=relevance, difficulty=diff,
                        volume_proxy=volume_proxy, score=score)


def research(seeds: list[str], country: str = "us",
             relevance_lookup: dict[str, float] | None = None) -> list[KeywordScore]:
    """Expand seeds, score each, return ranked list."""
    candidates = expand_seeds(seeds)
    rel = relevance_lookup or {}
    scored: list[KeywordScore] = []
    for c in candidates:
        r = rel.get(c, 0.6)  # default moderate relevance
        scored.append(score_keyword(c, relevance=r, country=country))
    scored.sort(key=lambda k: k.score, reverse=True)
    return scored


# ---------- packing ----------

def pack_keywords_field(terms: list[str], max_chars: int = 100) -> str:
    """Pack into Apple's 100-char keywords field. Dedupe words, use commas, no spaces after.

    Apple indexes each comma-separated token and also combinatorially joins them with
    words from Name/Subtitle, so minimize duplication across fields.
    """
    seen_words: set[str] = set()
    ordered: list[str] = []
    for t in terms:
        words = [w for w in re.split(r"[\s,]+", t.strip().lower()) if w]
        new_words = [w for w in words if w not in seen_words]
        if not new_words:
            continue
        seen_words.update(new_words)
        # Emit individual words (Apple best practice — not phrases)
        for w in new_words:
            ordered.append(w)

    # Fit into 100 chars, comma-separated, no spaces
    out_parts: list[str] = []
    total = 0
    for w in ordered:
        add = len(w) + (1 if out_parts else 0)  # comma
        if total + add > max_chars:
            break
        out_parts.append(w)
        total += add
    return ",".join(out_parts)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("seeds", nargs="+", help="Seed keywords/phrases")
    ap.add_argument("--country", default="us")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()
    ranked = research(args.seeds, country=args.country)
    for k in ranked[:args.top]:
        print(f"{k.score:6.2f}  rel={k.relevance:.2f}  diff={k.difficulty:2d}  "
              f"vol={k.volume_proxy:2d}  {k.term}")
    print("\nPacked keywords field (100 chars):")
    print(pack_keywords_field([k.term for k in ranked[:args.top]]))
