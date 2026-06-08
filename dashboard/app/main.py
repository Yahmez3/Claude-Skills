"""FastAPI app for the TradingAgents dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from .memory import load_memory_entries, load_run_artifacts
from .runner import RunManager
from .runs import RunRegistry


load_dotenv()

logging.basicConfig(level=os.getenv("DASHBOARD_LOG_LEVEL", "INFO"))


HERE = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(HERE / "templates"))


def _detect_providers() -> list[str]:
    mapping = {
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
        "glm": "ZHIPU_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    return [name for name, env in mapping.items() if os.getenv(env)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.getenv("DASHBOARD_DB_PATH", "./runs.db")
    registry = RunRegistry(db_path)
    loop = asyncio.get_running_loop()
    manager = RunManager(registry=registry, loop=loop)
    app.state.registry = registry
    app.state.manager = manager
    yield


app = FastAPI(title="TradingAgents Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    runs = request.app.state.registry.list(limit=25)
    decisions = load_memory_entries()
    decisions_recent = list(reversed(decisions))[:10]
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "runs": runs,
            "decisions": decisions_recent,
            "providers": _detect_providers(),
            "today": date.today().isoformat(),
        },
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: str):
    run = request.app.state.registry.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    artifacts = load_run_artifacts(run.ticker, run.trade_date)
    return TEMPLATES.TemplateResponse(
        request,
        "run.html",
        {"run": run, "artifacts": artifacts},
    )


@app.get("/decisions", response_class=HTMLResponse)
async def decisions_page(request: Request):
    entries = list(reversed(load_memory_entries()))
    return TEMPLATES.TemplateResponse(
        request,
        "decisions.html",
        {"entries": entries},
    )


# ---------- API ----------

@app.post("/api/runs")
async def api_start_run(
    request: Request,
    ticker: str = Form(...),
    trade_date: str = Form(...),
    llm_provider: str = Form("openai"),
    deep_think_llm: str = Form("gpt-5.4"),
    quick_think_llm: str = Form("gpt-5.4-mini"),
    max_debate_rounds: int = Form(1),
    max_risk_discuss_rounds: int = Form(1),
    analysts: list[str] = Form(["market", "social", "news", "fundamentals"]),
):
    ticker = ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    if not analysts:
        raise HTTPException(status_code=400, detail="select at least one analyst")

    config_overrides = {
        "llm_provider": llm_provider,
        "deep_think_llm": deep_think_llm,
        "quick_think_llm": quick_think_llm,
        "max_debate_rounds": int(max_debate_rounds),
        "max_risk_discuss_rounds": int(max_risk_discuss_rounds),
    }

    manager: RunManager = request.app.state.manager
    run_id = manager.start(ticker, trade_date, config_overrides, analysts)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


@app.get("/api/runs")
async def api_list_runs(request: Request):
    runs = request.app.state.registry.list(limit=100)
    return JSONResponse([r.to_dict() for r in runs])


@app.get("/api/runs/{run_id}")
async def api_get_run(request: Request, run_id: str):
    run = request.app.state.registry.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    artifacts = load_run_artifacts(run.ticker, run.trade_date)
    return JSONResponse({"run": run.to_dict(), "artifacts": artifacts})


@app.get("/api/runs/{run_id}/events")
async def api_run_events(request: Request, run_id: str):
    """SSE: replay the session log, then stream live events until the run ends."""
    manager: RunManager = request.app.state.manager
    run = request.app.state.registry.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    session = manager.get_session(run_id)

    async def event_gen():
        # If the session is still alive, hook up a live subscriber first so
        # we don't drop events that arrive between the snapshot and the
        # subscribe call.
        live_q: Optional[asyncio.Queue] = None
        if session is not None:
            live_q = asyncio.Queue(maxsize=512)
            session.add_subscriber(live_q)

        try:
            # Replay everything that already happened.
            backlog = session.snapshot() if session else []
            for event in backlog:
                if await request.is_disconnected():
                    return
                yield {"event": event["type"], "data": json.dumps(event)}

            # If there's no live session (process restart, run already
            # finished long ago), end the stream after replay.
            if session is None or session.done:
                yield {"event": "_eof", "data": "{}"}
                return

            # Stream live events.
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(live_q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # Heartbeat to keep proxies happy.
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": event["type"], "data": json.dumps(event)}
                if event["type"] == "_eof":
                    return
        finally:
            if session is not None and live_q is not None:
                session.remove_subscriber(live_q)

    return EventSourceResponse(event_gen())
