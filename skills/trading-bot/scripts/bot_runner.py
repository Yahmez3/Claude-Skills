"""Resilient bot loop harness.

Provides a main loop with kill switch, exponential backoff on transient errors,
and structured JSON logging. Pass in a `tick` callable that implements your
strategy for one iteration.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable


def stop_requested(stop_path: str = "./STOP") -> bool:
    return Path(stop_path).exists()


class JsonLineHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        payload = {"ts": record.created, "level": record.levelname,
                   "event": record.getMessage(), **getattr(record, "extra", {})}
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()


def get_logger(name: str = "bot") -> logging.Logger:
    lg = logging.getLogger(name)
    if not lg.handlers:
        lg.setLevel(logging.INFO)
        lg.addHandler(JsonLineHandler())
    return lg


def run_loop(
    tick: Callable[[], None],
    interval_s: float = 60.0,
    stop_path: str = "./STOP",
    max_transient_retries: int = 5,
    on_error: Callable[[Exception], bool] | None = None,
) -> None:
    """Run `tick` every `interval_s` seconds until STOP file appears.

    `on_error` is called with the exception; return True to keep running,
    False to re-raise. Default classifies network-ish errors as transient.
    """
    log = get_logger()
    retries = 0
    while not stop_requested(stop_path):
        t0 = time.time()
        try:
            tick()
            retries = 0
        except KeyboardInterrupt:
            log.info("interrupted")
            break
        except Exception as e:  # noqa: BLE001
            keep_going = (on_error or _default_on_error)(e)
            if not keep_going:
                log.exception("fatal")
                raise
            retries += 1
            if retries > max_transient_retries:
                log.error(f"max retries exceeded: {e}")
                raise
            backoff = min(2 ** retries, 60)
            log.warning(f"transient error, retrying in {backoff}s: {e}")
            time.sleep(backoff)
            continue

        elapsed = time.time() - t0
        time.sleep(max(0.0, interval_s - elapsed))
    log.info("stopped")


def _default_on_error(e: Exception) -> bool:
    msg = str(e).lower()
    transient = any(k in msg for k in ("timeout", "connection", "429", "500", "502", "503", "504"))
    return transient
