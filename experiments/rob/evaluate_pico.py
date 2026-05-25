#!/usr/bin/env python3
"""
Evaluate PICO consistency judgements.

Reads results/pico_judgements/ and prints per-slot distribution of
consistent / inconsistent / unclear.

Usage:
    python evaluate_pico.py
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

SLOTS = ["participants", "interventions", "outcomes"]
JUDGEMENTS = ["consistent", "inconsistent", "unclear"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judgements_dir", default="results/pico_judgements")
    parser.add_argument("--output_dir", default="results/pico_evaluation")
    args = parser.parse_args()

    judge_dir = Path(args.judgements_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(judge_dir.glob("*.json"))
    if not files:
        print(f"No files in {judge_dir}")
        return

    counts: dict[str, dict[str, int]] = {s: defaultdict(int) for s in SLOTS}
    flipped: dict[str, int] = defaultdict(int)
    per_study_rows: list[dict] = []

    for path in files:
        d = json.loads(path.read_text(encoding="utf-8"))
        judgements = d.get("judgements", {})
        for slot in SLOTS:
            entry = judgements.get(slot, {})
            if entry.get("_error"):
                key = "_error"
            else:
                key = (entry.get("judgement") or "missing").lower()
            counts[slot][key] += 1
            if entry.get("judgement_raw"):
                flipped[slot] += 1
            per_study_rows.append({
                "pmid": d.get("pmid", path.stem),
                "study_id": d.get("study_id", ""),
                "extraction_model": d.get("extraction_model", ""),
                "judge_model": d.get("judge_model", ""),
                "slot": slot,
                "judgement": key,
                "judgement_raw": entry.get("judgement_raw") or "",
                "reasoning": entry.get("reasoning", ""),
            })

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'Slot':<16} " + "  ".join(f"{j:<18}" for j in JUDGEMENTS) + "  errors  flipped  total")
    print("=" * 100)
    summary_rows = []
    for slot in SLOTS:
        c = counts[slot]
        total = sum(c.values())
        row = {"slot": slot, "total": total}
        line = f"{slot:<16} "
        for j in JUDGEMENTS:
            n = c.get(j, 0)
            pct = n / total * 100 if total else 0
            line += f"{n:>3} ({pct:5.1f}%)     "
            row[j] = n
            row[f"{j}_pct"] = round(pct, 1)
        err = c.get("_error", 0) + c.get("missing", 0)
        line += f"{err:>4}    {flipped[slot]:>4}    {total}"
        row["errors"] = err
        row["flipped_by_sanity_check"] = flipped[slot]
        print(line)
        summary_rows.append(row)
    print(f"\nFiles: {len(files)}")

    # ── CSVs ─────────────────────────────────────────────────────────────────
    summary_path = output_dir / "slot_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    study_path = output_dir / "per_study_results.csv"
    with open(study_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["pmid", "study_id", "extraction_model", "judge_model",
                        "slot", "judgement", "judgement_raw", "reasoning"],
        )
        writer.writeheader()
        writer.writerows(per_study_rows)

    print(f"\nSaved:\n  {summary_path}\n  {study_path}")


if __name__ == "__main__":
    main()
