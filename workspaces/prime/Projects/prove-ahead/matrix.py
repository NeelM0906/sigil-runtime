from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table

from common import DIMENSION_LABELS, MATRIX_DIMENSIONS, utc_now_iso
from competitors import DB_PATH, _connect, ensure_schema, get_act_i_profile, load_competitors

OUTPUT_PATH = Path("matrix.md")


def score_label(score: int) -> str:
    labels = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Very High"}
    return labels.get(score, "Unknown")


def compute_rows(act_scores: Dict[str, int], competitors: List[Dict[str, object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for comp in competitors:
        scores = {k: int(v) for k, v in comp["scores"].items()}
        total = sum(scores.values())
        gap_vs_act = sum(act_scores[d] - scores[d] for d in MATRIX_DIMENSIONS)
        rows.append(
            {
                "company": comp["company_name"],
                "scores": scores,
                "total": total,
                "gap_vs_act": gap_vs_act,
                "pricing_model": comp["pricing_model"],
            }
        )
    rows.sort(key=lambda x: (x["total"], x["company"]), reverse=True)
    return rows


def generate_markdown(
    act_profile: Dict[str, object],
    competitor_rows: List[Dict[str, object]],
    out_path: Path = OUTPUT_PATH,
) -> str:
    header_cols = ["Company"] + [DIMENSION_LABELS[d] for d in MATRIX_DIMENSIONS] + ["Total", "Gap vs ACT-I"]
    markdown_lines = [
        "# ACT-I Competitive Capability Matrix",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "Scoring: 1 (Very Low) to 5 (Very High)",
        "",
        "| " + " | ".join(header_cols) + " |",
        "| " + " | ".join(["---"] * len(header_cols)) + " |",
    ]

    act_scores = {k: int(v) for k, v in act_profile["scores"].items()}
    act_total = sum(act_scores.values())
    act_row = ["ACT-I"] + [str(act_scores[d]) for d in MATRIX_DIMENSIONS] + [str(act_total), "0"]
    markdown_lines.append("| " + " | ".join(act_row) + " |")

    for row in competitor_rows:
        values = [row["company"]] + [str(row["scores"][d]) for d in MATRIX_DIMENSIONS] + [
            str(row["total"]),
            str(row["gap_vs_act"]),
        ]
        markdown_lines.append("| " + " | ".join(values) + " |")

    top_gaps = sorted(competitor_rows, key=lambda r: r["gap_vs_act"], reverse=True)[:5]
    markdown_lines.extend(
        [
            "",
            "## Key Gaps Favoring ACT-I",
            "",
        ]
    )
    for row in top_gaps:
        markdown_lines.append(f"- **{row['company']}** trails ACT-I by **{row['gap_vs_act']}** total points.")

    markdown = "\n".join(markdown_lines) + "\n"
    out_path.write_text(markdown, encoding="utf-8")
    return markdown


def show_console(act_profile: Dict[str, object], competitor_rows: List[Dict[str, object]]) -> None:
    console = Console()
    table = Table(title="ACT-I vs Competitors (Capability Totals)")
    table.add_column("Company", style="bold")
    table.add_column("Total Score")
    table.add_column("Gap vs ACT-I")
    table.add_column("Pricing Model")

    act_total = sum(int(act_profile["scores"][d]) for d in MATRIX_DIMENSIONS)
    table.add_row("ACT-I", str(act_total), "0", act_profile["pricing_model"])

    for row in competitor_rows:
        table.add_row(row["company"], str(row["total"]), str(row["gap_vs_act"]), row["pricing_model"])

    console.print(table)


def build_matrix(db_path: Path = DB_PATH, out_path: Path = OUTPUT_PATH) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    conn = _connect(db_path)
    try:
        ensure_schema(conn)
        act_profile = get_act_i_profile(conn)
        competitors = load_competitors(conn, include_act_i=False)
    finally:
        conn.close()

    act_scores = {k: int(v) for k, v in act_profile["scores"].items()}
    rows = compute_rows(act_scores, competitors)
    generate_markdown(act_profile, rows, out_path=out_path)
    return act_profile, rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ACT-I capability matrix")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    parser.add_argument("--out", default=str(OUTPUT_PATH), help="Output markdown path")
    parser.add_argument("--no-console", action="store_true", help="Skip Rich CLI table output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    act_profile, rows = build_matrix(Path(args.db), Path(args.out))
    if not args.no_console:
        show_console(act_profile, rows)


if __name__ == "__main__":
    main()
