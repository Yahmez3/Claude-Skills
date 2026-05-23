"""End-to-end sentiment analysis pipeline with CLI entrypoint."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from .aggregator import SentimentSnapshot, aggregate
from .sentiment import (
    SentimentResult,
    ensemble_score,
    llm_score,
    textblob_score,
    vader_score,
)
from .signals import SentimentSignal, generate_signal
from .sources import NewsSource, RedditSource, TextItem, TwitterSource


def _score_items(
    items: list[TextItem],
    methods: list[str],
) -> list[SentimentResult]:
    results: list[SentimentResult] = []

    non_llm = [m for m in methods if m != "llm"]
    use_llm = "llm" in methods

    for item in items:
        if len(methods) > 1 and not use_llm:
            r = ensemble_score(item.text, methods=non_llm, symbol=item.symbol)
            results.append(r)
        else:
            for m in non_llm:
                if m == "vader":
                    results.append(vader_score(item.text, symbol=item.symbol))
                elif m == "textblob":
                    results.append(textblob_score(item.text, symbol=item.symbol))

    if use_llm and items:
        batch_size = 20
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            texts = [it.text for it in batch]
            symbols = [it.symbol for it in batch]
            llm_results = llm_score(texts, symbols=symbols)
            results.extend(llm_results)

    return results


def _fetch_items(
    symbols: list[str],
    source_names: list[str],
    lookback_hours: float,
) -> list[TextItem]:
    all_items: list[TextItem] = []

    for source_name in source_names:
        for symbol in symbols:
            try:
                if source_name == "reddit":
                    src = RedditSource()
                    all_items.extend(src.fetch(symbol=symbol, lookback_hours=lookback_hours))
                elif source_name == "news":
                    src_news = NewsSource()
                    all_items.extend(src_news.fetch(symbol=symbol, lookback_hours=lookback_hours))
                elif source_name == "twitter":
                    src_tw = TwitterSource()
                    all_items.extend(src_tw.fetch(symbol=symbol, lookback_hours=lookback_hours))
            except (ImportError, EnvironmentError) as e:
                print(f"Warning: {source_name} unavailable for {symbol}: {e}", file=sys.stderr)

    return all_items


def run(
    symbols: list[str],
    sources: list[str] | None = None,
    methods: list[str] | None = None,
    mode: str = "momentum",
    lookback_hours: float = 24,
    z_threshold: float = 1.5,
) -> dict[str, SentimentSignal]:
    sources = sources or ["news"]
    methods = methods or ["vader"]

    items = _fetch_items(symbols, sources, lookback_hours)

    results = _score_items(items, methods)

    signals: dict[str, SentimentSignal] = {}
    for symbol in symbols:
        symbol_results = [r for r in results if r.symbol and r.symbol.upper() == symbol.upper()]
        snapshot = aggregate(symbol_results, symbol)
        signal = generate_signal([snapshot], mode=mode, z_threshold=z_threshold)
        signals[symbol] = signal

    return signals


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sentiment-based trading signal generator",
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="Ticker symbols to analyze (e.g. AAPL TSLA BTC)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["news"],
        choices=["reddit", "news", "twitter"],
        help="Data sources to scrape",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["vader"],
        choices=["vader", "textblob", "llm"],
        help="Sentiment scoring methods",
    )
    parser.add_argument(
        "--mode",
        default="momentum",
        choices=["momentum", "contrarian"],
        help="Signal generation mode",
    )
    parser.add_argument(
        "--lookback",
        type=float,
        default=24,
        help="Lookback window in hours (default: 24)",
    )
    parser.add_argument(
        "--z-threshold",
        type=float,
        default=1.5,
        help="Z-score threshold for signal generation (default: 1.5)",
    )

    args = parser.parse_args()

    signals = run(
        symbols=args.symbols,
        sources=args.sources,
        methods=args.methods,
        mode=args.mode,
        lookback_hours=args.lookback,
        z_threshold=args.z_threshold,
    )

    for symbol, signal in signals.items():
        direction = {1: "BUY", -1: "SELL", 0: "FLAT"}[signal.signal]
        print(
            f"{symbol:>6s} | {direction:>4s} | "
            f"z={signal.z_score:+.2f} | "
            f"conf={signal.confidence:.1%} | "
            f"mode={signal.mode}"
        )


if __name__ == "__main__":
    main()
