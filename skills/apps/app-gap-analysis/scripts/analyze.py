"""Statistical pain-point extraction from negative reviews.

Approach:
1. Corpus = negative reviews (<=2 stars). Comparison corpus = positive (>=4).
2. TF-IDF of both; surface terms distinctive to negatives (log-odds / ratio).
3. Cluster negative reviews (MiniBatchKMeans) over TF-IDF vectors.
4. For each cluster: centroid keywords + 3 representative reviews.
5. Heuristic tag each cluster against a pain-point taxonomy.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .reviews import Review


TAXONOMY: dict[str, list[str]] = {
    "missing_feature": [
        "missing", "wish", "would love", "add", "please add", "need", "should have",
        "lacks", "no way to", "can't", "cannot", "doesn't support", "feature request",
    ],
    "ux_friction": [
        "confusing", "hard to", "too many taps", "not intuitive", "clunky", "ugly",
        "buried", "unclear", "frustrating", "complicated", "annoying",
    ],
    "performance": [
        "slow", "laggy", "freeze", "crash", "battery", "hot", "unresponsive",
        "takes forever", "loading", "buffering",
    ],
    "pricing": [
        "paywall", "subscription", "too expensive", "overpriced", "rip off", "ripoff",
        "greedy", "used to be free", "hidden cost", "in-app purchase", "refund",
    ],
    "reliability": [
        "sync", "lost", "deleted", "gone", "corrupt", "bug", "error", "broken",
        "doesn't work", "data loss", "reset",
    ],
    "privacy": [
        "tracking", "privacy", "data", "spying", "ads everywhere", "sold my",
        "permissions", "creepy",
    ],
    "platform_gap": [
        "android", "ipad", "tablet", "web", "desktop", "mac", "windows", "wear",
        "watch", "apple watch", "browser",
    ],
    "support": [
        "support", "no response", "customer service", "ignored", "unhelpful",
        "still waiting",
    ],
}


@dataclass
class Gap:
    cluster_id: int
    n_reviews: int
    frequency_pct: float                  # of negative corpus
    keywords: list[str]
    tags: list[str]                       # taxonomy tags
    examples: list[str]                   # 3 short excerpts
    severity: float = 0.0                 # avg helpful-weighted severity


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z' ]", " ", (text or "").lower())).strip()


def _tag_cluster(keywords: list[str], examples: list[str]) -> list[str]:
    blob = " ".join(keywords + [e.lower() for e in examples])
    hits = []
    for tag, markers in TAXONOMY.items():
        if any(m in blob for m in markers):
            hits.append(tag)
    return hits or ["other"]


def extract_gaps(negative: list[Review], positive: list[Review],
                 n_clusters: int = 6, min_reviews: int = 20) -> list[Gap]:
    """Return ranked gaps from negative reviews."""
    if len(negative) < min_reviews:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import MiniBatchKMeans
    except ImportError as e:
        raise RuntimeError("app-gap-analysis requires scikit-learn for statistical mode") from e

    texts = [_clean(f"{r.title} {r.body}") for r in negative]
    pos_texts = [_clean(f"{r.title} {r.body}") for r in positive] or [""]

    vec = TfidfVectorizer(max_features=3000, stop_words="english",
                          ngram_range=(1, 2), min_df=2, max_df=0.8)
    X = vec.fit_transform(texts)
    X_pos = vec.transform(pos_texts)

    k = min(n_clusters, max(2, len(negative) // 10))
    km = MiniBatchKMeans(n_clusters=k, n_init=5, random_state=42)
    labels = km.fit_predict(X)

    terms = vec.get_feature_names_out()
    pos_mean = X_pos.mean(axis=0).A1 if X_pos.shape[0] else None

    gaps: list[Gap] = []
    for cid in range(k):
        idx = [i for i, lbl in enumerate(labels) if lbl == cid]
        if not idx:
            continue
        centroid = km.cluster_centers_[cid]
        # Keyword score: cluster centroid - positive mean (distinctiveness)
        if pos_mean is not None:
            score = centroid - pos_mean
        else:
            score = centroid
        top_term_idx = score.argsort()[-8:][::-1]
        keywords = [terms[i] for i in top_term_idx if score[i] > 0][:6]

        # Pick the 3 reviews closest to the centroid
        sims = (X[idx] @ centroid.reshape(-1, 1)).A1
        order = sims.argsort()[::-1]
        examples = []
        for o in order[:5]:
            r = negative[idx[o]]
            excerpt = (r.body or r.title).strip().replace("\n", " ")
            if len(excerpt) > 280:
                excerpt = excerpt[:277] + "..."
            if excerpt:
                examples.append(excerpt)
            if len(examples) >= 3:
                break

        # Severity = mean (1/stars) weighted by 1+log(1+helpful)
        import math
        sev = 0.0
        tot_w = 0.0
        for i in idx:
            r = negative[i]
            w = 1 + math.log1p(r.helpful)
            sev += (6 - r.stars) * w
            tot_w += w
        severity = sev / tot_w if tot_w else 0.0

        gaps.append(Gap(
            cluster_id=cid,
            n_reviews=len(idx),
            frequency_pct=100 * len(idx) / len(negative),
            keywords=keywords,
            tags=_tag_cluster(keywords, examples),
            examples=examples,
            severity=severity,
        ))

    # Rank by frequency * severity
    gaps.sort(key=lambda g: g.frequency_pct * g.severity, reverse=True)
    return gaps


def top_terms_distinctive_to_negatives(
    negative: list[Review], positive: list[Review], top_k: int = 25,
) -> list[tuple[str, float]]:
    """Log-odds-ratio of terms in negative vs positive reviews."""
    import math

    def bag(revs: list[Review]) -> Counter:
        c: Counter = Counter()
        for r in revs:
            for tok in _clean(f"{r.title} {r.body}").split():
                if len(tok) > 2:
                    c[tok] += 1
        return c

    neg_bag, pos_bag = bag(negative), bag(positive)
    n_neg = sum(neg_bag.values()) or 1
    n_pos = sum(pos_bag.values()) or 1
    scores: list[tuple[str, float]] = []
    vocab = set(neg_bag) | set(pos_bag)
    for w in vocab:
        if neg_bag[w] + pos_bag[w] < 5:
            continue
        p_neg = (neg_bag[w] + 0.5) / n_neg
        p_pos = (pos_bag[w] + 0.5) / n_pos
        scores.append((w, math.log(p_neg / p_pos)))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
