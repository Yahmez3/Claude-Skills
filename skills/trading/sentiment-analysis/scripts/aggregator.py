"""Aggregate sentiment results into time-windowed snapshots with z-scores."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .sentiment import SentimentResult


@dataclass
class SentimentSnapshot:
    symbol: str
    timestamp: datetime
    mean_score: float
    median_score: float
    volume: int
    std_dev: float
    source_breakdown: dict[str, float] = field(default_factory=dict)
    z_score: float | None = None


def aggregate(
    results: list[SentimentResult],
    symbol: str,
    window_minutes: int = 60,
    reference_time: datetime | None = None,
) -> SentimentSnapshot:
    ref = reference_time or datetime.now(timezone.utc)
    cutoff = ref - timedelta(minutes=window_minutes)

    seen_ids: set[str] = set()
    filtered: list[SentimentResult] = []
    for r in results:
        if r.text_id in seen_ids:
            continue
        seen_ids.add(r.text_id)
        if r.symbol and r.symbol.upper() != symbol.upper():
            continue
        filtered.append(r)

    if not filtered:
        return SentimentSnapshot(
            symbol=symbol,
            timestamp=ref,
            mean_score=0.0,
            median_score=0.0,
            volume=0,
            std_dev=0.0,
        )

    scores = [r.score for r in filtered]
    mean_score = statistics.mean(scores)
    median_score = statistics.median(scores)
    std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0

    source_groups: dict[str, list[float]] = {}
    for r in filtered:
        source_key = r.method
        source_groups.setdefault(source_key, []).append(r.score)
    source_breakdown = {k: statistics.mean(v) for k, v in source_groups.items()}

    return SentimentSnapshot(
        symbol=symbol,
        timestamp=ref,
        mean_score=mean_score,
        median_score=median_score,
        volume=len(filtered),
        std_dev=std_dev,
        source_breakdown=source_breakdown,
    )


def time_series(
    snapshots: list[SentimentSnapshot],
    lookback: int = 20,
) -> list[SentimentSnapshot]:
    """Add rolling z-scores to a chronologically ordered list of snapshots.

    Z-score = (current mean_score - rolling mean) / rolling std.
    Uses the last `lookback` snapshots for the rolling window.
    """
    if not snapshots:
        return []

    sorted_snaps = sorted(snapshots, key=lambda s: s.timestamp)

    for i, snap in enumerate(sorted_snaps):
        window_start = max(0, i - lookback + 1)
        window = sorted_snaps[window_start:i + 1]
        window_scores = [s.mean_score for s in window]

        if len(window_scores) < 2:
            snap.z_score = 0.0
            continue

        mu = statistics.mean(window_scores)
        sigma = statistics.stdev(window_scores)
        if sigma == 0:
            snap.z_score = 0.0
        else:
            snap.z_score = (snap.mean_score - mu) / sigma

    return sorted_snaps
