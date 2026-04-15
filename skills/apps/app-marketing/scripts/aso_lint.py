"""Lint an App Store / Play Store listing against rules and common mistakes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


PROHIBITED_TERMS = {
    "best", "top", "free", "sale", "new", "cheap", "deal",     # puffery / Apple flags
    "#1", "no.1", "no 1",
}

# Well-known brands you usually can't reference in ASO fields
BRAND_TRAPS = {
    "apple", "iphone", "ipad", "ios", "android", "google", "microsoft",
    "facebook", "instagram", "tiktok", "youtube", "spotify", "netflix",
    "uber", "airbnb",
}


@dataclass
class Finding:
    severity: Literal["error", "warn", "info"]
    field: str
    message: str


@dataclass
class IosListing:
    app_name: str               # <= 30 chars
    subtitle: str               # <= 30 chars
    keywords: str               # comma-separated, <= 100 chars
    promo_text: str = ""        # <= 170 chars
    description: str = ""       # <= 4000 chars


@dataclass
class AndroidListing:
    title: str                  # <= 30 chars
    short_description: str      # <= 80 chars
    full_description: str       # <= 4000 chars


def _length_check(value: str, limit: int, field: str, findings: list[Finding]):
    if len(value) > limit:
        findings.append(Finding("error", field,
                                f"{len(value)} chars — exceeds {limit}-char limit"))
    elif len(value) > limit * 0.95:
        findings.append(Finding("warn", field,
                                f"{len(value)}/{limit} — near limit, little room for future edits"))
    elif len(value) < limit * 0.4 and limit <= 30:
        findings.append(Finding("info", field,
                                f"{len(value)}/{limit} — under-using the field; more keyword room available"))


def _check_prohibited(value: str, field: str, findings: list[Finding]):
    toks = set(re.findall(r"[a-z0-9#]+", value.lower()))
    bad = toks & PROHIBITED_TERMS
    if bad:
        findings.append(Finding("warn", field,
                                f"contains promo/puffery terms Apple may reject: {sorted(bad)}"))
    brand = toks & BRAND_TRAPS
    if brand:
        findings.append(Finding("warn", field,
                                f"references third-party brand(s) — verify you have rights: {sorted(brand)}"))


def _check_repetition_across(name: str, subtitle: str, keywords: str,
                             findings: list[Finding]):
    def words(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", s.lower())) - {"and", "the", "for", "with", "a", "to", "in", "of"}
    n, s = words(name), words(subtitle)
    k = set(t.strip().lower() for t in keywords.split(",") if t.strip())
    overlap_n_k = n & k
    overlap_s_k = s & k
    if overlap_n_k:
        findings.append(Finding("warn", "keywords",
                                f"words duplicated in App Name — waste of 100-char budget: {sorted(overlap_n_k)}"))
    if overlap_s_k:
        findings.append(Finding("warn", "keywords",
                                f"words duplicated in Subtitle — waste of 100-char budget: {sorted(overlap_s_k)}"))


def _check_keywords_format(keywords: str, findings: list[Finding]):
    if " ," in keywords or ", " in keywords:
        findings.append(Finding("warn", "keywords",
                                "spaces around commas waste characters — use `a,b,c` with no spaces"))
    tokens = [t.strip() for t in keywords.split(",") if t.strip()]
    dupes = [t for t in tokens if tokens.count(t) > 1]
    if dupes:
        findings.append(Finding("error", "keywords",
                                f"duplicate tokens in keywords: {sorted(set(dupes))}"))
    for t in tokens:
        if " " in t:
            findings.append(Finding("info", "keywords",
                                    f"multi-word token `{t}` — Apple recommends single words "
                                    "(it auto-combines with Name/Subtitle)"))


def lint_ios(listing: IosListing) -> list[Finding]:
    f: list[Finding] = []
    _length_check(listing.app_name, 30, "app_name", f)
    _length_check(listing.subtitle, 30, "subtitle", f)
    _length_check(listing.keywords, 100, "keywords", f)
    _length_check(listing.promo_text, 170, "promo_text", f)
    _length_check(listing.description, 4000, "description", f)
    _check_prohibited(listing.app_name, "app_name", f)
    _check_prohibited(listing.subtitle, "subtitle", f)
    _check_keywords_format(listing.keywords, f)
    _check_repetition_across(listing.app_name, listing.subtitle, listing.keywords, f)
    if not listing.description.strip():
        f.append(Finding("warn", "description", "empty — still useful for web SEO of the App Store page"))
    return f


def lint_android(listing: AndroidListing) -> list[Finding]:
    f: list[Finding] = []
    _length_check(listing.title, 30, "title", f)
    _length_check(listing.short_description, 80, "short_description", f)
    _length_check(listing.full_description, 4000, "full_description", f)
    _check_prohibited(listing.title, "title", f)
    _check_prohibited(listing.short_description, "short_description", f)
    # Keyword density sanity — Play indexes full description
    words = re.findall(r"[a-z]+", listing.full_description.lower())
    if words:
        from collections import Counter
        most = Counter(words).most_common(3)
        for w, n in most:
            if len(w) > 3 and n / len(words) > 0.05:
                f.append(Finding("warn", "full_description",
                                 f"keyword stuffing risk: `{w}` appears {n}x ({n/len(words):.1%})"))
    return f


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return "OK — no issues found."
    order = {"error": 0, "warn": 1, "info": 2}
    findings = sorted(findings, key=lambda x: order[x.severity])
    lines = []
    icons = {"error": "[ERR] ", "warn": "[WARN]", "info": "[INFO]"}
    for x in findings:
        lines.append(f"{icons[x.severity]} {x.field}: {x.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Demo
    listing = IosListing(
        app_name="Budget Buddy — Money Tracker",
        subtitle="Track spending, save money",
        keywords="budget, spending, money, track, save, expense, budget, planner",
        promo_text="New: shared household budgets!",
        description="Budget Buddy helps you track your money..." * 10,
    )
    print(format_report(lint_ios(listing)))
