"""Generate a dated launch checklist from config.

Usage:
    python launch_checklist.py --launch 2026-05-05 --channels ph,hn,twitter,email \
        --timezone America/Los_Angeles
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal


@dataclass
class ChecklistItem:
    when: date
    channel: str
    task: str
    owner: str = "founder"
    est_time: str = "30m"


STATIC_PRELAUNCH = [
    ("-14d", "product",  "Finalize positioning doc (1-page)", "founder", "2h"),
    ("-14d", "product",  "Instrument activation + retention events", "eng", "1d"),
    ("-14d", "web",      "Deploy landing page with waitlist capture", "eng", "1d"),
    ("-14d", "support",  "Route support@ email; publish FAQ", "founder", "2h"),
    ("-10d", "product",  "Ship to 10 friendly beta users; gather feedback", "founder", "ongoing"),
    ("-7d",  "asset",    "Record 30-second demo video; export 5 screenshots + GIF", "founder", "4h"),
    ("-7d",  "press",    "Draft 5-10 personalized press pitches", "founder", "3h"),
    ("-7d",  "social",   "Draft launch tweet thread + LinkedIn post", "founder", "2h"),
    ("-5d",  "ph",       "Create Product Hunt teaser page, schedule launch", "founder", "1h"),
    ("-3d",  "qa",       "Regression pass on onboarding + purchase flow", "eng", "4h"),
    ("-2d",  "ph",       "Confirm PH hunter / maker coordination", "founder", "30m"),
    ("-1d",  "email",    "Prep launch-day email broadcast to waitlist", "founder", "1h"),
    ("-1d",  "ops",      "Clear calendar for launch day; have phone nearby", "founder", "-"),
]

STATIC_LAUNCH_DAY = [
    ("00:01 PT", "ph",      "PH post goes live; verify maker comment posts"),
    ("06:00",    "email",   "Send launch email to waitlist"),
    ("09:00 ET", "social",  "Post tweet thread + LinkedIn + personal profiles"),
    ("10:00",    "comm",    "Post in 3-5 relevant communities you're active in (NOT cold)"),
    ("all day",  "ph",      "Reply to every PH comment within 2h — this ranks you"),
    ("all day",  "support", "Triage bug reports; have hotfix ready"),
    ("18:00",    "social",  "Retrospective tweet with #s so far; thank upvoters"),
]

STATIC_POSTLAUNCH = [
    ("+1d",  "hn",      "Submit `Show HN:` post (if app fits) — Tue-Thu morning ET", "founder", "1h"),
    ("+1d",  "press",   "Follow up with any journalist who didn't reply", "founder", "1h"),
    ("+3d",  "review",  "First pass responding to App Store reviews", "founder", "2h"),
    ("+7d",  "content", "Public launch retrospective — real numbers", "founder", "3h"),
    ("+7d",  "ph",      "DM the top-10 PH commenters with a personal thank-you", "founder", "1h"),
    ("+14d", "metrics", "Review D7 retention; identify activation drop-offs", "founder", "2h"),
    ("+30d", "iter",    "ASO refresh based on 30d keyword performance", "founder", "3h"),
]


def _offset(base: date, s: str) -> date:
    """Parse '-14d' / '+1d' offsets."""
    sign = 1 if s.startswith("+") else -1
    n = int(s.strip("+-d"))
    return base + timedelta(days=sign * n)


def generate(launch_date: date, channels: set[str] | None = None) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []

    def _keep(channel: str) -> bool:
        return channels is None or channel in channels or channel in {
            "product", "web", "support", "qa", "asset", "ops", "email", "metrics", "iter", "comm"
        }

    for off, ch, task, owner, et in STATIC_PRELAUNCH:
        if _keep(ch):
            items.append(ChecklistItem(_offset(launch_date, off), ch, task, owner, et))
    for t, ch, task in STATIC_LAUNCH_DAY:
        if _keep(ch):
            items.append(ChecklistItem(launch_date, ch, f"[{t}] {task}"))
    for off, ch, task, owner, et in STATIC_POSTLAUNCH:
        if _keep(ch):
            items.append(ChecklistItem(_offset(launch_date, off), ch, task, owner, et))

    items.sort(key=lambda x: (x.when, x.channel))
    return items


def render_markdown(items: list[ChecklistItem], launch_date: date) -> str:
    lines = [f"# Launch checklist — {launch_date.isoformat()}\n"]
    by_date: dict[date, list[ChecklistItem]] = {}
    for it in items:
        by_date.setdefault(it.when, []).append(it)
    for d in sorted(by_date):
        rel = (d - launch_date).days
        tag = "launch day" if rel == 0 else f"T{rel:+d}d"
        lines.append(f"## {d.isoformat()} — {tag}")
        for it in by_date[d]:
            lines.append(f"- [ ] **{it.channel}** — {it.task}  _({it.owner}, ~{it.est_time})_")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--launch", required=True, help="YYYY-MM-DD launch date")
    ap.add_argument("--channels", default="", help="Comma-separated channels to include")
    args = ap.parse_args()
    launch = datetime.strptime(args.launch, "%Y-%m-%d").date()
    channels = set(c.strip() for c in args.channels.split(",") if c.strip()) or None
    items = generate(launch, channels)
    print(render_markdown(items, launch))


if __name__ == "__main__":
    main()
