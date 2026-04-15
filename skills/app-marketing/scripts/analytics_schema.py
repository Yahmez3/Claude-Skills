"""Canonical analytics event schema with emitters for PostHog, Mixpanel, GA4.

Goals:
- Consistent event names across platforms/warehouses
- Type-checked properties
- One place to evolve the schema
- Same call on web, iOS, Android (adapters translate)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Literal


# ---------------- schema ----------------

EventName = Literal[
    "install",
    "signup_started",
    "signup_completed",
    "activation",
    "key_action",
    "paywall_shown",
    "subscribe_started",
    "subscribe_completed",
    "subscribe_canceled",
    "feature_used",
    "error",
    "session_start",
    "session_end",
]

REQUIRED_PROPS: dict[str, set[str]] = {
    "install": {"source"},
    "signup_completed": {"method"},
    "activation": {"time_to_activation_s"},
    "paywall_shown": {"offer", "context"},
    "subscribe_started": {"offer"},
    "subscribe_completed": {"offer", "price_usd"},
    "feature_used": {"feature"},
}


@dataclass
class Event:
    name: EventName
    user_id: str | None = None
    anon_id: str | None = None
    ts: float = field(default_factory=time.time)
    props: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.user_id is None and self.anon_id is None:
            errs.append("need user_id or anon_id")
        missing = REQUIRED_PROPS.get(self.name, set()) - set(self.props.keys())
        if missing:
            errs.append(f"missing required props for {self.name}: {sorted(missing)}")
        return errs

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------- emitters ----------------

class Emitter:
    def send(self, e: Event) -> None:
        raise NotImplementedError


class PostHogEmitter(Emitter):
    def __init__(self, api_key: str | None = None, host: str = "https://us.i.posthog.com"):
        self.api_key = api_key or os.environ.get("POSTHOG_API_KEY")
        self.host = host

    def send(self, e: Event) -> None:
        if not self.api_key:
            raise RuntimeError("POSTHOG_API_KEY not set")
        import urllib.request
        payload = {
            "api_key": self.api_key,
            "event": e.name,
            "distinct_id": e.user_id or e.anon_id,
            "properties": {**e.props, "$timestamp": e.ts},
        }
        req = urllib.request.Request(
            f"{self.host}/capture/",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()


class MixpanelEmitter(Emitter):
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("MIXPANEL_TOKEN")

    def send(self, e: Event) -> None:
        if not self.token:
            raise RuntimeError("MIXPANEL_TOKEN not set")
        import base64, urllib.request
        payload = {
            "event": e.name,
            "properties": {
                **e.props,
                "token": self.token,
                "time": int(e.ts),
                "distinct_id": e.user_id or e.anon_id,
            },
        }
        data = base64.b64encode(json.dumps(payload).encode())
        req = urllib.request.Request(
            "https://api.mixpanel.com/track",
            data=b"data=" + data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        urllib.request.urlopen(req, timeout=5).read()


class GA4Emitter(Emitter):
    def __init__(self, measurement_id: str | None = None, api_secret: str | None = None):
        self.mid = measurement_id or os.environ.get("GA4_MEASUREMENT_ID")
        self.secret = api_secret or os.environ.get("GA4_API_SECRET")

    def send(self, e: Event) -> None:
        if not (self.mid and self.secret):
            raise RuntimeError("GA4_MEASUREMENT_ID / GA4_API_SECRET not set")
        import urllib.request
        url = (f"https://www.google-analytics.com/mp/collect"
               f"?measurement_id={self.mid}&api_secret={self.secret}")
        payload = {
            "client_id": e.anon_id or e.user_id or "unknown",
            "events": [{"name": e.name, "params": e.props}],
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()


class MultiEmitter(Emitter):
    """Fan out to many emitters; swallow individual failures so one dead vendor
    doesn't break the event pipeline."""

    def __init__(self, *emitters: Emitter):
        self.emitters = emitters

    def send(self, e: Event) -> None:
        for em in self.emitters:
            try:
                em.send(e)
            except Exception as err:  # noqa: BLE001
                print(f"[analytics] {type(em).__name__} failed: {err}")


# ---------------- example schema init ----------------

def example_schema_doc() -> str:
    """Print a markdown schema reference for the team wiki."""
    lines = ["# Analytics schema\n"]
    descriptions = {
        "install": "First open of the app on a device.",
        "signup_started": "Auth UI shown to the user.",
        "signup_completed": "Account exists on the server.",
        "activation": "User performed the app's core aha-moment action.",
        "key_action": "Repeat core action; one per occurrence.",
        "paywall_shown": "Paywall view impression.",
        "subscribe_started": "User tapped the purchase CTA.",
        "subscribe_completed": "Receipt verified.",
        "subscribe_canceled": "User or system canceled the sub.",
        "feature_used": "A named feature was used.",
        "error": "Client-side error surfaced to the user.",
        "session_start": "Foreground after >30m background.",
        "session_end": "Background or close.",
    }
    for n, desc in descriptions.items():
        req = REQUIRED_PROPS.get(n, set())
        req_str = ", ".join(sorted(req)) if req else "-"
        lines.append(f"### `{n}`\n{desc}\n\n**Required props:** {req_str}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    print(example_schema_doc())
