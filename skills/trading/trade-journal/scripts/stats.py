"""Per-strategy and per-symbol performance statistics."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .models import JournalDB, Trade


@dataclass
class TradeStats:
    strategy: str
    symbol: str
    total_trades: int
    winners: int
    losers: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_pnl: float
    max_win: float
    max_loss: float
    avg_hold_time: Optional[timedelta]
    expectancy: float
    sharpe: Optional[float]


def compute(trades: list[Trade]) -> TradeStats:
    closed = [t for t in trades if t.pnl is not None]
    total = len(closed)

    if total == 0:
        return TradeStats(
            strategy="ALL",
            symbol="ALL",
            total_trades=0,
            winners=0,
            losers=0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            total_pnl=0.0,
            max_win=0.0,
            max_loss=0.0,
            avg_hold_time=None,
            expectancy=0.0,
            sharpe=None,
        )

    pnls = [t.pnl for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    hold_times: list[timedelta] = []
    for t in closed:
        if t.closed_at and t.timestamp:
            hold_times.append(t.closed_at - t.timestamp)

    avg_hold = (
        sum(hold_times, timedelta()) / len(hold_times) if hold_times else None
    )

    mean_pnl = total_pnl / total
    sharpe = None
    if total > 30:
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / total
        std = math.sqrt(variance)
        if std > 0:
            sharpe = (mean_pnl / std) * math.sqrt(252)

    strategies = {t.strategy for t in closed}
    symbols = {t.symbol for t in closed}

    return TradeStats(
        strategy=next(iter(strategies)) if len(strategies) == 1 else "ALL",
        symbol=next(iter(symbols)) if len(symbols) == 1 else "ALL",
        total_trades=total,
        winners=len(wins),
        losers=len(losses),
        win_rate=len(wins) / total if total else 0.0,
        avg_win=sum(wins) / len(wins) if wins else 0.0,
        avg_loss=sum(losses) / len(losses) if losses else 0.0,
        profit_factor=gross_win / gross_loss if gross_loss > 0 else float("inf"),
        total_pnl=total_pnl,
        max_win=max(pnls),
        max_loss=min(pnls),
        avg_hold_time=avg_hold,
        expectancy=mean_pnl,
        sharpe=sharpe,
    )


def by_strategy(db: JournalDB) -> dict[str, TradeStats]:
    results: dict[str, TradeStats] = {}
    for strategy in db.all_strategies():
        trades = db.query(strategy=strategy)
        stats = compute(trades)
        stats.strategy = strategy
        results[strategy] = stats
    return results


def by_symbol(db: JournalDB) -> dict[str, TradeStats]:
    results: dict[str, TradeStats] = {}
    for symbol in db.all_symbols():
        trades = db.query(symbol=symbol)
        stats = compute(trades)
        stats.symbol = symbol
        results[symbol] = stats
    return results


def by_period(db: JournalDB, period: str = "month") -> dict[str, TradeStats]:
    """Group trades by time period and compute stats for each.

    period: "day", "week", or "month"
    """
    all_trades = db.query()
    buckets: dict[str, list[Trade]] = defaultdict(list)

    for t in all_trades:
        if period == "day":
            key = t.timestamp.strftime("%Y-%m-%d")
        elif period == "week":
            iso = t.timestamp.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        else:
            key = t.timestamp.strftime("%Y-%m")
        buckets[key].append(t)

    results: dict[str, TradeStats] = {}
    for key in sorted(buckets):
        stats = compute(buckets[key])
        stats.strategy = key
        results[key] = stats
    return results


def equity_curve(trades: list[Trade]) -> list[tuple[datetime, float]]:
    """Cumulative P&L over time from closed trades."""
    closed = sorted(
        [t for t in trades if t.pnl is not None and t.closed_at is not None],
        key=lambda t: t.closed_at,
    )
    curve: list[tuple[datetime, float]] = []
    cumulative = 0.0
    for t in closed:
        cumulative += t.pnl
        curve.append((t.closed_at, cumulative))
    return curve
