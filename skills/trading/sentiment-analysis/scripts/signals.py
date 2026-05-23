"""Generate trading signals from sentiment snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .aggregator import SentimentSnapshot, time_series


@dataclass
class SentimentSignal:
    symbol: str
    timestamp: datetime
    signal: int        # -1 (sell/short), 0 (flat), +1 (buy/long)
    mode: str          # "momentum" | "contrarian"
    z_score: float
    confidence: float  # 0.0 to 1.0 based on volume and z-score magnitude


def generate_signal(
    snapshots: list[SentimentSnapshot],
    mode: str = "momentum",
    z_threshold: float = 1.5,
) -> SentimentSignal:
    if not snapshots:
        return SentimentSignal(
            symbol="UNKNOWN",
            timestamp=datetime.now(timezone.utc),
            signal=0,
            mode=mode,
            z_score=0.0,
            confidence=0.0,
        )

    enriched = time_series(snapshots)
    latest = enriched[-1]
    z = latest.z_score or 0.0

    if mode == "momentum":
        if z >= z_threshold:
            raw_signal = 1
        elif z <= -z_threshold:
            raw_signal = -1
        else:
            raw_signal = 0
    elif mode == "contrarian":
        if z >= z_threshold:
            raw_signal = -1
        elif z <= -z_threshold:
            raw_signal = 1
        else:
            raw_signal = 0
    else:
        raise ValueError(f"Unknown mode: {mode}. Choose 'momentum' or 'contrarian'.")

    # Confidence scales with z-score magnitude and mention volume
    z_confidence = min(1.0, abs(z) / (z_threshold * 2))
    vol_confidence = min(1.0, latest.volume / 50)
    confidence = (z_confidence + vol_confidence) / 2

    return SentimentSignal(
        symbol=latest.symbol,
        timestamp=latest.timestamp,
        signal=raw_signal,
        mode=mode,
        z_score=z,
        confidence=round(confidence, 3),
    )


def bulk_signals(
    symbols: list[str],
    snapshots_map: dict[str, list[SentimentSnapshot]],
    mode: str = "momentum",
    z_threshold: float = 1.5,
) -> list[SentimentSignal]:
    signals: list[SentimentSignal] = []
    for symbol in symbols:
        snaps = snapshots_map.get(symbol, [])
        sig = generate_signal(snaps, mode=mode, z_threshold=z_threshold)
        signals.append(sig)
    return signals
