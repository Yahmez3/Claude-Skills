"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries, ISeriesApi, IChartApi } from "lightweight-charts";

type Bar = { time: number; open: number; high: number; low: number; close: number };

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("SPY");
  const [bars, setBars] = useState<Bar[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
    fetch(`${backend}/bars?symbol=${symbol}&timeframe=1d`)
      .then((r) => r.json())
      .then((j) => {
        const mapped = j.bars.map((b: any) => ({
          time: Math.floor(new Date(b.ts).getTime() / 1000),
          open: b.o, high: b.h, low: b.l, close: b.c,
        }));
        setBars(mapped);
      })
      .catch(() => setBars([]));
  }, [symbol]);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0a0a0a" }, textColor: "#e5e5e5" },
      grid: { vertLines: { color: "#1f1f1f" }, horzLines: { color: "#1f1f1f" } },
      height: 500,
    });
    const series = chart.addSeries(CandlestickSeries);
    chartRef.current = chart;
    seriesRef.current = series;
    return () => chart.remove();
  }, []);

  useEffect(() => {
    seriesRef.current?.setData(bars as any);
  }, [bars]);

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="flex items-center gap-4 mb-4">
        <input
          className="bg-neutral-900 px-3 py-2 rounded border border-neutral-800"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
        />
        <span className="text-neutral-400">{bars.length} bars</span>
      </div>
      <div ref={containerRef} className="w-full rounded border border-neutral-800" />
    </main>
  );
}
