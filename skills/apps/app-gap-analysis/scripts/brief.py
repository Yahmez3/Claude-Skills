"""OpportunityBrief — the structured output of the pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class Competitor:
    name: str
    platform: str
    app_id: str
    category: str
    price: str
    rating_avg: float | None = None
    rating_count: int | None = None
    url: str = ""


@dataclass
class OpportunityBrief:
    title: str
    thesis: str
    generated_at: str
    incumbent: Competitor
    target_user: dict                    # {persona, unmet_need, coping_strategy}
    gaps: list[dict]                     # unified gaps from reconcile()
    incumbent_strengths: list[str]
    mvp_features: list[str]
    nice_to_haves: list[str]
    non_goals: list[str]
    monetization: dict                   # {model, rationale}
    risks: dict                          # {market, execution, legal}
    next_steps: list[str]
    recommended_stack: dict              # {web/mobile/backend choices}
    recommended_scaffold: str            # which scaffold skill to invoke

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    def to_markdown(self, path: str | Path | None = None) -> str:
        md = _render_markdown(self)
        if path:
            Path(path).write_text(md)
        return md


def _render_markdown(b: OpportunityBrief) -> str:
    lines: list[str] = []
    lines.append(f"# {b.title}\n")
    lines.append(f"_{b.thesis}_\n")
    lines.append(f"Generated: {b.generated_at}\n")

    lines.append("## Incumbent")
    inc = b.incumbent
    lines.append(f"**{inc.name}** — {inc.category}, {inc.platform}, {inc.price}")
    if inc.rating_avg is not None:
        lines.append(f"Rating: {inc.rating_avg:.2f} ({inc.rating_count:,} ratings)")
    if inc.url:
        lines.append(f"[Store listing]({inc.url})")
    lines.append("")

    lines.append("## Target user")
    for k, v in b.target_user.items():
        lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
    lines.append("")

    lines.append("## Gap analysis")
    for i, g in enumerate(b.gaps, start=1):
        freq_stat = g.get("frequency_stat_pct")
        freq_llm = g.get("frequency_llm_pct")
        freq_parts = []
        if freq_stat is not None:
            freq_parts.append(f"stat={freq_stat:.1f}%")
        if freq_llm is not None:
            freq_parts.append(f"llm={freq_llm:.0f}%")
        freq_str = f" ({', '.join(freq_parts)})" if freq_parts else ""
        conf = " [high-confidence]" if g.get("high_confidence") else ""
        lines.append(f"### {i}. {g.get('name', 'gap')}{conf}{freq_str}")
        lines.append(g.get("description", ""))
        if g.get("tags"):
            lines.append(f"Tags: `{', '.join(g['tags'])}`")
        if g.get("opportunity"):
            lines.append(f"**Opportunity:** {g['opportunity']}")
        quotes = (g.get("quotes_llm") or []) + (g.get("quotes_stat") or [])
        for q in quotes[:3]:
            lines.append(f"> {q}")
        lines.append("")

    if b.incumbent_strengths:
        lines.append("## Incumbent strengths (don't attack head-on)")
        for s in b.incumbent_strengths:
            lines.append(f"- {s}")
        lines.append("")

    lines.append("## MVP scope")
    lines.append("### Must-have")
    for f in b.mvp_features:
        lines.append(f"- {f}")
    lines.append("### Nice-to-have")
    for f in b.nice_to_haves:
        lines.append(f"- {f}")
    lines.append("### Non-goals")
    for f in b.non_goals:
        lines.append(f"- {f}")
    lines.append("")

    lines.append("## Monetization")
    lines.append(f"**Model:** {b.monetization.get('model', '')}")
    lines.append(f"**Rationale:** {b.monetization.get('rationale', '')}\n")

    lines.append("## Risks")
    for k in ("market", "execution", "legal"):
        v = b.risks.get(k)
        if v:
            lines.append(f"- **{k.title()}:** {v}")
    lines.append("")

    lines.append("## Recommended stack")
    for k, v in b.recommended_stack.items():
        lines.append(f"- **{k}:** {v}")
    lines.append(f"\nScaffold skill: `{b.recommended_scaffold}`\n")

    lines.append("## Next steps")
    for s in b.next_steps:
        lines.append(f"- {s}")

    return "\n".join(lines) + "\n"


def build_brief(
    incumbent: Competitor,
    unified_gaps: list[dict],
    llm_report,
    incumbent_description: str = "",
) -> OpportunityBrief:
    """Synthesize brief pieces from pipeline outputs. Pure function — no I/O."""
    top_gaps = unified_gaps[:5]

    mvp = [g.get("opportunity") or g.get("description", "") for g in top_gaps[:3] if g]
    mvp = [m for m in mvp if m]
    nice = [g.get("opportunity") or g.get("description", "") for g in unified_gaps[3:7]]
    nice = [n for n in nice if n]

    # Non-goals = incumbent strengths
    non_goals = [f"Do not try to out-polish {incumbent.name} on: {s}"
                 for s in (llm_report.incumbent_strengths[:3] if llm_report else [])]

    # Monetization inference: if "pricing" gap is top, flip the model
    monetization = {
        "model": "freemium with one-time unlock",
        "rationale": "Default — adjust based on gap evidence",
    }
    for g in top_gaps:
        if "pricing" in g.get("tags", []):
            monetization = {
                "model": "one-time purchase (no subscription)",
                "rationale": f"Pricing friction is a top-ranked complaint for {incumbent.name}; "
                             "a pay-once model directly removes that pain",
            }
            break

    target_user = {
        "persona": (llm_report.underserved_segments[0].get("segment")
                    if llm_report and llm_report.underserved_segments
                    else f"Dissatisfied {incumbent.category.lower()} power user"),
        "unmet_need": top_gaps[0].get("description", "") if top_gaps else "",
        "coping_strategy": "Currently tolerates the incumbent or uses ad-hoc workarounds",
    }

    # Stack recommendation — defaults conservative
    rec_stack = {
        "mobile": "React Native + Expo (iOS + Android from one codebase)",
        "backend": "FastAPI + Postgres",
        "web": "Next.js (App Router, TypeScript, Tailwind)",
    }

    scaffold = "trading-app-scaffold" if "finance" in incumbent.category.lower() else "trading-app-scaffold"

    thesis = (llm_report.differentiation_thesis if llm_report else
              f"Underserved needs in {incumbent.name} create room for a focused competitor.")

    return OpportunityBrief(
        title=f"Opportunity: beat {incumbent.name}",
        thesis=thesis,
        generated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        incumbent=incumbent,
        target_user=target_user,
        gaps=top_gaps,
        incumbent_strengths=(llm_report.incumbent_strengths if llm_report else []),
        mvp_features=mvp,
        nice_to_haves=nice,
        non_goals=non_goals,
        monetization=monetization,
        risks={
            "market": "Validate that complaints represent addressable demand (5-interview test).",
            "execution": "Parity on incumbent's core strength is table-stakes — scope MVP tightly.",
            "legal": "Avoid trademarked names/icons; review incumbent patents on core mechanics.",
        },
        next_steps=[
            "5 user interviews with people who've churned from the incumbent",
            "Landing page A/B test on the top-1 gap positioning",
            "3-week prototype targeting only the top-2 gaps",
            f"Invoke scaffold: {scaffold}",
        ],
        recommended_stack=rec_stack,
        recommended_scaffold=scaffold,
    )
