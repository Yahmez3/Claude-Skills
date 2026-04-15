"""Options chain fetching and filtering."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def fetch_chain(symbol: str, expiration: str | None = None) -> pd.DataFrame:
    """Fetch an options chain from yfinance.

    Returns a DataFrame with columns:
        contract, type (C/P), strike, expiration, bid, ask, mid,
        last, volume, open_interest, iv, delta(nan), underlying
    """
    import yfinance as yf

    tk = yf.Ticker(symbol)
    expirations = tk.options
    if not expirations:
        raise ValueError(f"No options for {symbol}")
    if expiration is None:
        expiration = expirations[0]

    chain = tk.option_chain(expiration)
    underlying = tk.fast_info.get("last_price") or tk.history(period="1d")["Close"].iloc[-1]

    def _frame(df: pd.DataFrame, typ: str) -> pd.DataFrame:
        out = pd.DataFrame({
            "contract": df["contractSymbol"],
            "type": typ,
            "strike": df["strike"],
            "expiration": pd.Timestamp(expiration),
            "bid": df["bid"],
            "ask": df["ask"],
            "mid": (df["bid"] + df["ask"]) / 2,
            "last": df["lastPrice"],
            "volume": df["volume"].fillna(0).astype(int),
            "open_interest": df["openInterest"].fillna(0).astype(int),
            "iv": df["impliedVolatility"],
        })
        out["underlying"] = underlying
        return out

    calls = _frame(chain.calls, "C")
    puts = _frame(chain.puts, "P")
    return pd.concat([calls, puts], ignore_index=True)


def atm_strikes(chain: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Return the n strikes closest to spot for each side."""
    spot = chain["underlying"].iloc[0]
    chain = chain.assign(abs_moneyness=(chain["strike"] - spot).abs())
    return (chain.sort_values("abs_moneyness")
                 .groupby("type", group_keys=False)
                 .head(n)
                 .drop(columns="abs_moneyness")
                 .sort_values(["type", "strike"]))
