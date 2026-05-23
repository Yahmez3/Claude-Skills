"""Performance report generation with Markdown tables and equity curve charts."""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional

from .models import JournalDB
from .stats import TradeStats, by_period, by_strategy, by_symbol, compute, equity_curve


def render_markdown(stats: TradeStats) -> str:
    hold_str = _format_timedelta(stats.avg_hold_time) if stats.avg_hold_time else "N/A"
    sharpe_str = f"{stats.sharpe:.2f}" if stats.sharpe is not None else "N/A"

    rows = [
        ("Total Trades", str(stats.total_trades)),
        ("Winners / Losers", f"{stats.winners} / {stats.losers}"),
        ("Win Rate", f"{stats.win_rate:.1%}"),
        ("Avg Win", f"{stats.avg_win:+.2f}"),
        ("Avg Loss", f"{stats.avg_loss:+.2f}"),
        ("Profit Factor", f"{stats.profit_factor:.2f}"),
        ("Total P&L", f"{stats.total_pnl:+.2f}"),
        ("Max Win", f"{stats.max_win:+.2f}"),
        ("Max Loss", f"{stats.max_loss:+.2f}"),
        ("Expectancy", f"{stats.expectancy:+.2f}"),
        ("Sharpe", sharpe_str),
        ("Avg Hold Time", hold_str),
    ]

    lines = [
        f"### {stats.strategy} — {stats.symbol}",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for label, value in rows:
        lines.append(f"| {label} | {value} |")
    return "\n".join(lines)


def _format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def render_equity_curve(
    trades: list,
    output_path: Path,
    title: str = "Equity Curve",
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        sys.stderr.write("matplotlib not installed — skipping equity curve chart\n")
        return

    curve = equity_curve(trades)
    if not curve:
        return

    dates = [c[0] for c in curve]
    pnls = [c[1] for c in curve]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates, pnls, linewidth=1.5, color="#2196F3")
    ax.fill_between(dates, pnls, alpha=0.1, color="#2196F3")
    ax.axhline(y=0, color="#666", linewidth=0.5, linestyle="--")
    ax.set_title(title)
    ax.set_ylabel("Cumulative P&L")
    ax.set_xlabel("Date")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)


def full_report(
    db: JournalDB,
    output_dir: Path,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    period: Optional[str] = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    all_trades = db.query(strategy=strategy, symbol=symbol)
    overall = compute(all_trades)
    overall.strategy = strategy or "ALL"
    overall.symbol = symbol or "ALL"

    sections: list[str] = [
        "# Trade Journal Report",
        "",
        "## Overall Performance",
        "",
        render_markdown(overall),
    ]

    strat_stats = by_strategy(db)
    if len(strat_stats) > 1 and strategy is None:
        sections.extend(["", "## By Strategy", ""])
        for name, stats in sorted(strat_stats.items()):
            sections.extend([render_markdown(stats), ""])

    sym_stats = by_symbol(db)
    if len(sym_stats) > 1 and symbol is None:
        sections.extend(["", "## By Symbol", ""])
        for name, stats in sorted(sym_stats.items()):
            sections.extend([render_markdown(stats), ""])

    if period:
        period_stats = by_period(db, period=period)
        if period_stats:
            sections.extend(["", f"## By Period ({period})", ""])
            for name, stats in sorted(period_stats.items()):
                sections.extend([render_markdown(stats), ""])

    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(sections) + "\n")

    render_equity_curve(all_trades, output_dir / "equity.png")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a trade journal performance report"
    )
    parser.add_argument("--db", default="trades.db", help="Path to SQLite database")
    parser.add_argument("--strategy", default=None, help="Filter by strategy")
    parser.add_argument("--symbol", default=None, help="Filter by symbol")
    parser.add_argument(
        "--period",
        default=None,
        choices=["day", "week", "month"],
        help="Group stats by time period",
    )
    parser.add_argument("--output", default="./report", help="Output directory")
    args = parser.parse_args(argv)

    with JournalDB(args.db) as db:
        full_report(
            db,
            output_dir=Path(args.output),
            strategy=args.strategy,
            symbol=args.symbol,
            period=args.period,
        )
    print(f"Report written to {args.output}/")


if __name__ == "__main__":
    main()
