"""Trading CLI — Typer subcommands for fetch, backtest, signal, bot."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich import print
from rich.table import Table

app = typer.Typer(help="Trading CLI — fetch data, backtest, run bots.")


@app.command()
def fetch(
    symbol: str = typer.Argument(..., help="Ticker, e.g. SPY or BTC/USDT"),
    timeframe: str = typer.Option("1d"),
    days: int = typer.Option(365, help="Lookback"),
    out: Path = typer.Option(None, help="Parquet output path"),
):
    """Fetch OHLCV and optionally save to Parquet."""
    import yfinance as yf

    start = (date.today() - timedelta(days=days)).isoformat()
    interval = {"1d": "1d", "1h": "60m", "15m": "15m"}.get(timeframe, "1d")
    df = yf.download(symbol, start=start, interval=interval,
                     auto_adjust=True, progress=False).rename(columns=str.lower)
    print(f"[green]Fetched {len(df)} bars[/green] for {symbol}")
    table = Table(title=f"{symbol} last 5")
    for c in ["open", "high", "low", "close", "volume"]:
        table.add_column(c, justify="right")
    for _, r in df.tail(5).iterrows():
        table.add_row(*[f"{r[c]:,.2f}" for c in ["open", "high", "low", "close", "volume"]])
    print(table)
    if out:
        df.to_parquet(out)
        print(f"[cyan]Wrote {out}[/cyan]")


@app.command()
def backtest(
    symbol: str,
    fast: int = 20,
    slow: int = 50,
    days: int = typer.Option(365 * 3),
):
    """Quick SMA-crossover backtest. Replace with the `backtesting` skill for real work."""
    import numpy as np
    import pandas as pd
    import yfinance as yf

    start = (date.today() - timedelta(days=days)).isoformat()
    df = yf.download(symbol, start=start, interval="1d",
                     auto_adjust=True, progress=False).rename(columns=str.lower)
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    sig = pd.Series(np.where(f > s, 1, 0), index=df.index).shift(1).fillna(0)
    ret = df["close"].pct_change().fillna(0)
    strat = sig * ret
    equity = (1 + strat).cumprod()
    print(f"[bold]{symbol}[/bold] SMA({fast}/{slow})")
    print(f"  total return : {(equity.iloc[-1] - 1) * 100:+.2f}%")
    print(f"  sharpe       : {(strat.mean() / (strat.std() or 1e-9)) * 252 ** 0.5:.2f}")
    print(f"  max drawdown : {(equity / equity.cummax() - 1).min() * 100:.2f}%")


@app.command()
def signal(symbol: str, strategy: str = "sma_crossover"):
    """Print the latest signal for a symbol."""
    import numpy as np
    import pandas as pd
    import yfinance as yf

    df = yf.download(symbol, period="6mo", interval="1d",
                     auto_adjust=True, progress=False).rename(columns=str.lower)
    if strategy == "sma_crossover":
        f = df["close"].rolling(20).mean()
        s = df["close"].rolling(50).mean()
        latest = int(np.sign(f.iloc[-1] - s.iloc[-1]))
        print(f"{symbol} {strategy}: {'LONG' if latest > 0 else 'FLAT/SHORT'} "
              f"(close {df['close'].iloc[-1]:.2f})")
    else:
        print(f"[red]Unknown strategy {strategy}[/red]")


@app.command()
def bot(config: Path = typer.Argument(..., help="bot config YAML")):
    """Run a live/paper bot driven by a config file."""
    print(f"[yellow]Bot runner would read {config} and start a loop (stub).[/yellow]")
    print("Wire to the `trading-bot` skill's bot_runner.run_loop().")


if __name__ == "__main__":
    app()
