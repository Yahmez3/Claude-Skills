"""Streamlit trading dashboard — single-file starter."""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# Expect the market-data skill installed at ~/.claude/skills/trading/skills/market-data
# Or vendor its fetchers here. For the template we implement a minimal yfinance fetch.

st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("Trading Dashboard")

# ---------- sidebar ----------
with st.sidebar:
    symbol = st.text_input("Symbol", value="SPY")
    tf = st.selectbox("Timeframe", ["1d", "1h", "15m"], index=0)
    lookback_days = st.slider("Lookback (days)", 30, 365 * 3, 365)
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()

@st.cache_data(ttl=300)
def load(symbol: str, tf: str, lookback_days: int) -> pd.DataFrame:
    import yfinance as yf
    end = date.today()
    start = end - timedelta(days=lookback_days)
    interval = {"1d": "1d", "1h": "60m", "15m": "15m"}[tf]
    df = yf.download(symbol, start=start, end=end, interval=interval,
                     auto_adjust=True, progress=False)
    df = df.rename(columns=str.lower)
    return df

df = load(symbol, tf, lookback_days)
if df.empty:
    st.error(f"No data for {symbol}")
    st.stop()

# ---------- metrics ----------
col1, col2, col3, col4 = st.columns(4)
last = df["close"].iloc[-1]
prev = df["close"].iloc[-2]
col1.metric("Last", f"${last:,.2f}", f"{(last / prev - 1) * 100:+.2f}%")
col2.metric("Range (period)", f"${df['low'].min():,.2f} – ${df['high'].max():,.2f}")
col3.metric("Avg Volume", f"{df['volume'].mean():,.0f}")
ret = df["close"].pct_change().dropna()
col4.metric("Vol (ann.)", f"{ret.std() * (252 ** 0.5) * 100:.1f}%")

# ---------- chart ----------
import plotly.graph_objects as go
fig = go.Figure(data=[go.Candlestick(
    x=df.index, open=df["open"], high=df["high"],
    low=df["low"], close=df["close"], name=symbol,
)])
fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(t=20))
st.plotly_chart(fig, use_container_width=True)

# ---------- table ----------
with st.expander("Raw data"):
    st.dataframe(df.tail(250), use_container_width=True)
