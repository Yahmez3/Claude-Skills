"""End-to-end driver: chart -> top app -> reviews -> gaps -> brief."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import extract_gaps
from .brief import Competitor, build_brief
from .fetch_top_apps import fetch_apple_lookup, fetch_top
from .llm_analysis import LLMReport, analyze as llm_analyze, reconcile
from .reviews import fetch_reviews, rating_distribution, split_by_sentiment


def run(
    platform: str = "ios",
    chart: str = "top-grossing",
    country: str = "us",
    category: str = "all",
    rank: int = 1,
    review_limit: int = 400,
    use_llm: bool = True,
    out_dir: str = "./gap_analysis_output",
) -> dict:
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    # 1. Top chart
    charts = fetch_top(platform=platform, chart=chart, country=country,
                       category=category, limit=max(rank, 5))
    if not charts or rank > len(charts):
        raise RuntimeError(f"Could not fetch rank {rank} from {platform}/{chart}")
    entry = charts[rank - 1]
    print(f"[1/5] Top app: #{entry.rank} {entry.name} by {entry.developer} ({entry.platform})")

    # 2. Metadata
    description = ""
    rating_avg = None
    rating_count = None
    if entry.platform == "ios":
        meta = fetch_apple_lookup(entry.app_id, country=country)
        description = meta.get("description", "")
        rating_avg = meta.get("averageUserRating")
        rating_count = meta.get("userRatingCount")
    print(f"[2/5] Fetched metadata (rating {rating_avg}, {rating_count} ratings)")

    # 3. Reviews
    reviews = fetch_reviews(entry.platform, entry.app_id, country=country, limit=review_limit)
    dist = rating_distribution(reviews)
    negative, positive = split_by_sentiment(reviews)
    print(f"[3/5] Reviews: {len(reviews)} total ({len(negative)} negative, "
          f"{len(positive)} positive). Distribution: {dist}")

    # 4. Gap extraction — statistical + optionally LLM
    stat_gaps = extract_gaps(negative, positive) if len(negative) >= 20 else []
    llm_report: LLMReport | None = None
    if use_llm and negative:
        try:
            llm_report = llm_analyze(entry.name, entry.category, description, negative)
        except Exception as e:
            print(f"      LLM analysis skipped: {e}")
            llm_report = None
    unified = reconcile(stat_gaps, llm_report) if llm_report else [
        {
            "name": f"cluster-{g.cluster_id}",
            "description": " / ".join(g.keywords) or "Unlabeled theme",
            "severity_llm": None, "frequency_llm_pct": None,
            "frequency_stat_pct": g.frequency_pct,
            "tags": g.tags, "quotes_llm": [], "quotes_stat": g.examples,
            "keywords_stat": g.keywords, "opportunity": "",
            "high_confidence": False,
        } for g in stat_gaps
    ]
    # Sort unified by best-available frequency * severity
    def _rank(g):
        f = g.get("frequency_stat_pct") or g.get("frequency_llm_pct") or 0
        s = g.get("severity_llm") or 3
        return f * s
    unified.sort(key=_rank, reverse=True)
    print(f"[4/5] Extracted {len(unified)} gap themes")

    # 5. Brief
    incumbent = Competitor(
        name=entry.name, platform=entry.platform, app_id=entry.app_id,
        category=entry.category, price=entry.price,
        rating_avg=rating_avg, rating_count=rating_count, url=entry.url,
    )
    brief = build_brief(incumbent, unified, llm_report, description)
    md_path = outp / "opportunity_brief.md"
    json_path = outp / "opportunity_brief.json"
    reviews_path = outp / "reviews.json"
    brief.to_markdown(md_path)
    brief.to_json(json_path)
    reviews_path.write_text(json.dumps([r.dict() for r in reviews], indent=2))
    print(f"[5/5] Wrote {md_path}, {json_path}, {reviews_path}")

    return {"brief_path": str(md_path), "json_path": str(json_path),
            "reviews_path": str(reviews_path), "n_gaps": len(unified)}


def main():
    ap = argparse.ArgumentParser(description="App gap analysis pipeline")
    ap.add_argument("--platform", default="ios", choices=["ios", "android", "both"])
    ap.add_argument("--chart", default="top-grossing",
                    choices=["top-grossing", "top-free", "top-paid", "top-new"])
    ap.add_argument("--country", default="us")
    ap.add_argument("--category", default="all")
    ap.add_argument("--rank", type=int, default=1)
    ap.add_argument("--reviews", type=int, default=400, dest="review_limit")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--out", default="./gap_analysis_output", dest="out_dir")
    args = ap.parse_args()
    run(platform=args.platform, chart=args.chart, country=args.country,
        category=args.category, rank=args.rank, review_limit=args.review_limit,
        use_llm=not args.no_llm, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
