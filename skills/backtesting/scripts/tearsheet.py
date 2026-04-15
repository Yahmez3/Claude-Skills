"""Single-file HTML tear sheet generator."""
from __future__ import annotations

import base64
import io

import pandas as pd

from .vector_backtest import BacktestResult


def _fig_to_b64() -> str:
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close()
    return base64.b64encode(buf.getvalue()).decode()


def tearsheet(result: BacktestResult, benchmark: pd.Series | None = None,
              out_path: str = "tearsheet.html") -> str:
    import matplotlib.pyplot as plt

    # Equity curve
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(result.equity.index, result.equity.values, label="strategy", linewidth=1.5)
    if benchmark is not None:
        bm = benchmark.reindex(result.equity.index).ffill()
        bm_eq = result.equity.iloc[0] * (bm / bm.iloc[0])
        ax.plot(bm_eq.index, bm_eq.values, label="buy & hold", linewidth=1, alpha=0.7)
    ax.set_title("Equity Curve")
    ax.legend()
    ax.grid(alpha=0.3)
    equity_img = _fig_to_b64()

    # Drawdown
    dd = result.equity / result.equity.cummax() - 1
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(dd.index, dd.values, 0, color="red", alpha=0.3)
    ax.set_title("Drawdown")
    ax.grid(alpha=0.3)
    dd_img = _fig_to_b64()

    # Monthly heatmap
    monthly = result.returns.resample("M").apply(lambda x: (1 + x).prod() - 1)
    pivot = monthly.groupby([monthly.index.year, monthly.index.month]).sum().unstack()
    fig, ax = plt.subplots(figsize=(10, max(3, 0.4 * len(pivot))))
    ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", vmin=-0.1, vmax=0.1)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xticks(range(12))
    ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"])
    ax.set_title("Monthly returns")
    heat_img = _fig_to_b64()

    metrics_rows = "".join(
        f"<tr><td>{k}</td><td>{v:.4f}</td></tr>" if isinstance(v, float)
        else f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in result.metrics.items()
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Backtest Tear Sheet</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse}}td,th{{padding:4px 12px;border-bottom:1px solid #eee}}
img{{max-width:100%;margin:1rem 0}}
</style></head><body>
<h1>Backtest Tear Sheet</h1>
<h2>Metrics</h2>
<table>{metrics_rows}</table>
<h2>Equity</h2><img src="data:image/png;base64,{equity_img}">
<h2>Drawdown</h2><img src="data:image/png;base64,{dd_img}">
<h2>Monthly Returns</h2><img src="data:image/png;base64,{heat_img}">
</body></html>"""
    with open(out_path, "w") as f:
        f.write(html)
    return out_path
