from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Dict, List

from common import ACT_I_STATS, DIMENSION_LABELS, MATRIX_DIMENSIONS, utc_now_iso
from competitors import DB_PATH, _connect, ensure_schema, get_act_i_profile, init_and_seed, load_competitors

REPORT_PATH = Path("report.md")
MATRIX_PATH = Path("matrix.md")
BENCHMARK_PATH = Path("benchmark_results.json")


def _read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _score_summary(act_scores: Dict[str, int], competitors: List[Dict[str, object]]) -> List[str]:
    lines: List[str] = []
    for dimension in MATRIX_DIMENSIONS:
        comp_avg = round(mean(int(c["scores"][dimension]) for c in competitors), 2)
        act = int(act_scores[dimension])
        lines.append(
            f"- **{DIMENSION_LABELS[dimension]}**: ACT-I {act}/5 vs competitor average {comp_avg}/5"
        )
    return lines


def _top_competitors(competitors: List[Dict[str, object]], n: int = 5) -> List[Dict[str, object]]:
    ranked = []
    for comp in competitors:
        total = sum(int(comp["scores"][d]) for d in MATRIX_DIMENSIONS)
        ranked.append({"company": comp["company_name"], "total": total, "category": comp["category"]})
    ranked.sort(key=lambda x: x["total"], reverse=True)
    return ranked[:n]


def _gather_sources(competitors: List[Dict[str, object]]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for comp in competitors:
        for source in comp["sources"]:
            if source not in seen:
                seen.add(source)
                ordered.append(source)
    return ordered


def generate_report(
    out_path: Path = REPORT_PATH,
    db_path: Path = DB_PATH,
    matrix_path: Path = MATRIX_PATH,
    benchmark_path: Path = BENCHMARK_PATH,
) -> str:
    if not db_path.exists():
        init_and_seed(db_path)

    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        act_profile = get_act_i_profile(conn)
        competitors = load_competitors(conn, include_act_i=False)
    finally:
        conn.close()

    if not matrix_path.exists():
        raise FileNotFoundError(f"Missing matrix file: {matrix_path}")
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Missing benchmark file: {benchmark_path}")

    benchmark = _read_json(benchmark_path)

    act_scores = {k: int(v) for k, v in act_profile["scores"].items()}
    top_companies = _top_competitors(competitors)
    score_lines = _score_summary(act_scores, competitors)
    sources = _gather_sources(competitors)

    lines: List[str] = [
        "# Prove We're Ahead: ACT-I Competitive Analysis",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Executive Summary",
        "",
        "ACT-I leads this benchmarked set on core influence dimensions that matter for conversion quality: emotional rapport, formula-driven guidance, persistent context, and measurable outcomes. "
        "Across the capability matrix, ACT-I is strongest in influence-centric categories and remains competitive on integration breadth and scale, where large platform vendors are traditionally strongest.",
        "",
        f"Head-to-head benchmark result: **{benchmark['summary']['winner']}** by **{benchmark['summary']['weighted_gap']}** weighted points under the Colosseum rubric.",
        "",
        "## Competitive Landscape",
        "",
        f"Registry size: **{len(competitors)}** competitor records spanning voice AI platforms, sales engagement, conversational marketing, and support AI.",
        "",
        "Top competitors by aggregate capability score:",
    ]

    for item in top_companies:
        lines.append(f"- **{item['company']}** ({item['category']}) - total matrix score {item['total']}")

    lines.extend(
        [
            "",
            "ACT-I vs market averages:",
            *score_lines,
            "",
            "## Head-to-Head Results",
            "",
            f"Scenario: **{benchmark['scenario']['name']}**",
            "",
            f"- ACT-I weighted score: **{benchmark['scores']['act_i']['weighted_total']} / 10**",
            f"- Generic AI weighted score: **{benchmark['scores']['generic']['weighted_total']} / 10**",
            f"- Gap: **{benchmark['summary']['weighted_gap']}**",
            "",
            "Colosseum criteria used:",
            "- Rapport and empathy",
            "- Strategic structure",
            "- Contextual memory",
            "- Integrity-based influence",
            "- Next-step clarity",
            "",
            "## ACT-I Advantages",
            "",
            f"- **{ACT_I_STATS['calls_made']} calls made**",
            f"- **{ACT_I_STATS['pathways']} pathways**",
            f"- **{ACT_I_STATS['users']} users** with **{ACT_I_STATS['interactions']}**",
            f"- **{ACT_I_STATS['live_agents']} live agents**",
            "- **The Unblinded Formula** with **39 components**",
            "- **Integrity-based influence** aligned to long-term trust, not manipulative urgency",
            "- **27-year-proven formulaic approach** applied to modern AI interaction design",
            "",
            "What no one else in this set clearly matches:",
            "- A named, structured influence formula with 39 explicit components",
            "- A combined live-agent + AI ecosystem anchored in one persuasion methodology",
            "- Pathway-level operationalization (128 pathways) mapped to outcomes",
            "",
            "## Market Position",
            "",
            "ACT-I should be positioned as a premium influence-intelligence layer rather than just another voice bot or sales automation tool. "
            "The closest alternatives are strong at infrastructure (API telephony, contact-center scale, CRM integration), but weaker in rapport-centric influence methodology and formulaic conversational governance.",
            "",
            "Recommended narrative for leadership and prospects:",
            "- Competitors automate conversations",
            "- ACT-I operationalizes trustworthy influence",
            "- The result is higher-conviction conversion behavior, not just lower handling time",
            "",
            "## Sources",
            "",
        ]
    )

    for url in sources:
        lines.append(f"- {url}")

    report = "\n".join(lines) + "\n"
    out_path.write_text(report, encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate final competitive proof report")
    parser.add_argument("--out", default=str(REPORT_PATH), help="Output markdown path")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to competitor SQLite DB")
    parser.add_argument("--matrix", default=str(MATRIX_PATH), help="Path to matrix markdown")
    parser.add_argument("--benchmark", default=str(BENCHMARK_PATH), help="Path to benchmark JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_report(
        out_path=Path(args.out),
        db_path=Path(args.db),
        matrix_path=Path(args.matrix),
        benchmark_path=Path(args.benchmark),
    )


if __name__ == "__main__":
    main()
