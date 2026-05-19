#!/usr/bin/env python3
"""
RoB Evaluation Script — 5-domain version (Plan A).

Compares 5-domain model predictions against ground-truth `risk_of_bias` arrays.

Domains evaluated:
    1. Random sequence generation
    2. Allocation concealment
    3. Blinding of participants and personnel
    4. Blinding of outcome assessment
    5. Incomplete outcome data

When a GT file has multiple entries for the same domain (e.g. split by
outcome class), they are merged into a single worst-case judgement
(High > Unclear > Low).

Handles dataset variants:
- List-top-level files: same paper assessed in multiple SRs (each scored separately)
- Merged Blinding entry "Blinding (performance bias and detection bias)" → both blinding domains
- Non-Cochrane entries (QUADAS-2, prognostic-tool checklists) → skipped

Usage:
    python evaluate.py
    python evaluate.py --predictions_dir results/predictions --output_dir results/evaluation
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from domain_specs import SPECS

JUDGEMENTS = ["Low risk", "High risk", "Unclear risk"]
_SEVERITY = {"High risk": 0, "Unclear risk": 1, "Low risk": 2}

SLOT_TO_CANON = {
    "random_sequence_generation": "random_sequence",
    "allocation_concealment": "allocation_concealment",
    "blinding_participants": "blinding_participants",
    "blinding_outcome": "blinding_outcome",
    "incomplete_outcome": "incomplete_outcome",
}


def gt_canonical_domains(domain_text: str) -> list[str]:
    """Map a GT domain string to one or more canonical keys.

    Returns empty list for Selective reporting, Other bias, QUADAS-2,
    prognostic-tool checklists, etc. The merged "Blinding (performance
    bias and detection bias)" entry maps to both blinding domains.
    """
    d = domain_text.lower()

    # Merged blinding entry — applies to BOTH blinding domains
    if "blinding" in d and "performance" in d and "detection" in d:
        return ["blinding_participants", "blinding_outcome"]

    if "random sequence" in d or "sequence generation" in d:
        return ["random_sequence"]
    if "allocation concealment" in d:
        return ["allocation_concealment"]
    if "blinding of participants" in d or "performance bias" in d:
        return ["blinding_participants"]
    if "blinding of outcome" in d or "detection bias" in d:
        return ["blinding_outcome"]
    if "incomplete outcome" in d or "attrition" in d:
        return ["incomplete_outcome"]
    return []


def _worst(entries: list[dict]) -> dict:
    """Return the entry with the most severe judgement (High > Unclear > Low)."""
    return min(
        entries,
        key=lambda e: _SEVERITY.get(e.get("judgement", "Unclear risk"), 1),
    )


def evaluate_one_gt_record(gt_rob: list[dict], prediction: dict) -> dict[str, dict]:
    """Score the prediction against a single GT `risk_of_bias` array."""
    gt_by_canon: dict[str, list[dict]] = defaultdict(list)
    for entry in gt_rob:
        if not isinstance(entry, dict):
            continue
        for c in gt_canonical_domains(entry.get("domain", "")):
            gt_by_canon[c].append(entry)

    pred_entries = prediction.get("prediction", {}).get("risk_of_bias", []) or []
    pred_by_slot: dict[str, dict] = {}
    for i, spec in enumerate(SPECS):
        if i < len(pred_entries):
            pred_by_slot[spec.slot_id] = pred_entries[i]

    results: dict[str, dict] = {}
    for spec in SPECS:
        canon = SLOT_TO_CANON[spec.slot_id]
        gt_entries = gt_by_canon.get(canon, [])
        if not gt_entries:
            continue
        gt_entry = _worst(gt_entries) if len(gt_entries) > 1 else gt_entries[0]

        gt_j = gt_entry.get("judgement")
        pred_entry = pred_by_slot.get(spec.slot_id)
        pred_j = pred_entry.get("judgement") if pred_entry else None

        results[spec.slot_id] = {
            "gt": gt_j,
            "pred": pred_j,
            "match": gt_j == pred_j,
            "domain_label": spec.domain_label,
            "gt_domain_str": gt_entry.get("domain", ""),
        }
    return results


def print_confusion_matrix(confusion: dict, label: str, file=None) -> None:
    all_preds = sorted(
        {p for gt_dict in confusion.values() for p in gt_dict},
        key=lambda j: _SEVERITY.get(j, 99),
    )
    if not all_preds:
        return
    header = f"\n{'GT \\ Pred':<18}" + "".join(f"{p:<18}" for p in all_preds)
    lines = [f"=== {label} ===", header]
    for gt_j in JUDGEMENTS:
        row = f"{gt_j:<18}" + "".join(
            f"{confusion[gt_j].get(p, 0):<18}" for p in all_preds
        )
        lines.append(row)
    text = "\n".join(lines)
    print(text)
    if file:
        file.write(text + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate 5-domain RoB predictions")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--predictions_dir", default="results/predictions")
    parser.add_argument("--output_dir", default="results/evaluation")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    pred_dir = Path(args.predictions_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pred_files = sorted(pred_dir.glob("*.json"))
    if not pred_files:
        print(f"No prediction files found in {pred_dir}")
        return

    print(f"Evaluating {len(pred_files)} prediction files...\n")

    slot_correct: dict[str, int] = defaultdict(int)
    slot_total: dict[str, int] = defaultdict(int)
    confusion: dict[str, dict[str, dict[str, int]]] = {
        s.slot_id: defaultdict(lambda: defaultdict(int)) for s in SPECS
    }

    per_study_rows: list[dict] = []
    n_gt_records = 0

    for pred_path in pred_files:
        gt_path = dataset_dir / pred_path.name
        if not gt_path.exists():
            print(f"  Warning: no ground-truth for {pred_path.name}, skipping")
            continue

        prediction = json.loads(pred_path.read_text(encoding="utf-8"))
        gt_raw = json.loads(gt_path.read_text(encoding="utf-8"))

        gt_records = gt_raw if isinstance(gt_raw, list) else [gt_raw]

        for gt_idx, gt_rec in enumerate(gt_records):
            if not isinstance(gt_rec, dict):
                continue
            gt_rob = gt_rec.get("risk_of_bias", []) or []
            if not gt_rob:
                continue
            n_gt_records += 1

            slot_results = evaluate_one_gt_record(gt_rob, prediction)

            for slot_id, res in slot_results.items():
                slot_total[slot_id] += 1
                if res["match"]:
                    slot_correct[slot_id] += 1

                gt_j = res["gt"] or "Missing"
                pred_j = res["pred"] or "Missing"
                confusion[slot_id][gt_j][pred_j] += 1

                per_study_rows.append({
                    "pmid": prediction.get("pmid", pred_path.stem),
                    "study_id": gt_rec.get("study_id", prediction.get("study_id", "")),
                    "gt_record_idx": gt_idx,
                    "model": prediction.get("model", ""),
                    "slot_id": slot_id,
                    "domain": res["domain_label"],
                    "gt_domain_str": res.get("gt_domain_str", ""),
                    "gt": gt_j,
                    "pred": pred_j,
                    "match": int(res["match"]),
                })

    # ── Per-domain accuracy ───────────────────────────────────────────────────
    print(f"\nGT records evaluated: {n_gt_records} (across {len(pred_files)} prediction files)")
    print("=" * 92)
    print(f"{'Domain':<60} {'Correct':>8}  {'Total':>6}  {'Accuracy':>9}")
    print("=" * 92)

    summary_rows = []
    total_correct = total_total = 0

    for spec in SPECS:
        slot_id = spec.slot_id
        n = slot_total[slot_id]
        c = slot_correct[slot_id]
        acc = c / n if n > 0 else 0.0
        total_correct += c
        total_total += n
        print(f"  {spec.domain_label[:58]:<58} {c:>8}  {n:>6}  {acc:>8.1%}")
        summary_rows.append({
            "slot_id": slot_id,
            "domain": spec.domain_label,
            "correct": c,
            "total": n,
            "accuracy": round(acc, 4),
        })

    print("-" * 92)
    overall = total_correct / total_total if total_total > 0 else 0.0
    print(f"  {'OVERALL (5-domain)':<58} {total_correct:>8}  {total_total:>6}  {overall:>8.1%}")
    print("=" * 92)
    summary_rows.append({
        "slot_id": "OVERALL",
        "domain": "OVERALL",
        "correct": total_correct,
        "total": total_total,
        "accuracy": round(overall, 4),
    })

    # ── Confusion matrices ────────────────────────────────────────────────────
    cm_path = output_dir / "confusion_matrices.txt"
    with open(cm_path, "w", encoding="utf-8") as f:
        for spec in SPECS:
            print_confusion_matrix(confusion[spec.slot_id], spec.domain_label, file=f)

    # ── CSVs ──────────────────────────────────────────────────────────────────
    acc_path = output_dir / "domain_accuracy.csv"
    with open(acc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["slot_id", "domain", "correct", "total", "accuracy"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    study_path = output_dir / "per_study_results.csv"
    with open(study_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["pmid", "study_id", "gt_record_idx", "model", "slot_id",
                        "domain", "gt_domain_str", "gt", "pred", "match"],
        )
        writer.writeheader()
        writer.writerows(per_study_rows)

    print(f"\nSaved:")
    print(f"  {acc_path}")
    print(f"  {study_path}")
    print(f"  {cm_path}")


if __name__ == "__main__":
    main()
