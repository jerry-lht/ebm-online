#!/usr/bin/env python3
"""
RoB Evaluation Script — 5-domain version.

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
    python evaluate.py --binary    # Low/Unclear merged; report High-risk precision/recall/F1
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from domain_specs import SPECS

JUDGEMENTS = ["Low risk", "High risk", "Unclear risk"]
JUDGEMENTS_BINARY = ["High risk", "Not high"]
_SEVERITY = {"High risk": 0, "Unclear risk": 1, "Low risk": 2}
_SEVERITY_BINARY = {"High risk": 0, "Not high": 1}

SLOT_TO_CANON = {
    "random_sequence_generation": "random_sequence",
    "allocation_concealment": "allocation_concealment",
    "blinding_participants": "blinding_participants",
    "blinding_outcome": "blinding_outcome",
    "incomplete_outcome": "incomplete_outcome",
}


def to_binary(j: str | None) -> str | None:
    """Collapse Low/Unclear into 'Not high'; keep High as 'High risk'."""
    if not j:
        return None
    s = j.lower()
    if "high" in s:
        return "High risk"
    if "low" in s or "unclear" in s:
        return "Not high"
    return None


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


def print_confusion_matrix(confusion: dict, label: str, binary: bool = False, file=None) -> None:
    judgements = JUDGEMENTS_BINARY if binary else JUDGEMENTS
    severity = _SEVERITY_BINARY if binary else _SEVERITY
    all_preds = sorted(
        {p for gt_dict in confusion.values() for p in gt_dict},
        key=lambda j: severity.get(j, 99),
    )
    if not all_preds:
        return
    header = f"\n{'GT \\ Pred':<18}" + "".join(f"{p:<18}" for p in all_preds)
    lines = [f"=== {label} ===", header]
    for gt_j in judgements:
        row = f"{gt_j:<18}" + "".join(
            f"{confusion[gt_j].get(p, 0):<18}" for p in all_preds
        )
        lines.append(row)
    text = "\n".join(lines)
    print(text)
    if file:
        file.write(text + "\n")


SHORT_LABELS = {
    "random_sequence_generation": "Random sequence",
    "allocation_concealment":     "Allocation concealment",
    "blinding_participants":      "Blinding (participants)",
    "blinding_outcome":           "Blinding (outcome)",
    "incomplete_outcome":         "Incomplete outcome",
}


def binary_metrics(confusion: dict) -> dict:
    """Compute precision/recall/F1 for the High-risk class."""
    tp = confusion.get("High risk", {}).get("High risk", 0)
    fn = confusion.get("High risk", {}).get("Not high", 0)
    fp = confusion.get("Not high", {}).get("High risk", 0)
    tn = confusion.get("Not high", {}).get("Not high", 0)

    n = tp + fp + fn + tn
    n_pos = tp + fn  # actual positives
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / n if n > 0 else 0.0
    prevalence = n_pos / n if n > 0 else 0.0
    # Trivial baseline: predict "Not high" for everything → accuracy = 1 - prevalence
    baseline_acc = (tn + fn) / n if n > 0 else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "n": n, "n_pos": n_pos,
        "precision": precision, "recall": recall, "f1": f1,
        "accuracy": accuracy, "prevalence": prevalence,
        "baseline_acc": baseline_acc,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate 5-domain RoB predictions")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--predictions_dir", default="results/predictions")
    parser.add_argument("--output_dir", default="results/evaluation")
    parser.add_argument("--binary", action="store_true",
                        help="Collapse Low/Unclear into one class; "
                             "report High-risk precision/recall/F1.")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    pred_dir = Path(args.predictions_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pred_files = sorted(pred_dir.glob("*.json"))
    if not pred_files:
        print(f"No prediction files found in {pred_dir}")
        return

    mode = "BINARY (High vs Not-high)" if args.binary else "3-class (Low / High / Unclear)"
    print(f"Evaluating {len(pred_files)} prediction files...  Mode: {mode}\n")

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
                gt_j_raw = res["gt"]
                pred_j_raw = res["pred"]

                if args.binary:
                    gt_j = to_binary(gt_j_raw)
                    pred_j = to_binary(pred_j_raw)
                    match = (gt_j is not None and gt_j == pred_j)
                else:
                    gt_j = gt_j_raw
                    pred_j = pred_j_raw
                    match = res["match"]

                slot_total[slot_id] += 1
                if match:
                    slot_correct[slot_id] += 1

                gt_key = gt_j or "Missing"
                pred_key = pred_j or "Missing"
                confusion[slot_id][gt_key][pred_key] += 1

                per_study_rows.append({
                    "pmid": prediction.get("pmid", pred_path.stem),
                    "study_id": gt_rec.get("study_id", prediction.get("study_id", "")),
                    "gt_record_idx": gt_idx,
                    "model": prediction.get("model", ""),
                    "slot_id": slot_id,
                    "domain": res["domain_label"],
                    "gt_domain_str": res.get("gt_domain_str", ""),
                    "gt": gt_key,
                    "pred": pred_key,
                    "match": int(match),
                })

    # ── Per-domain accuracy (or binary metrics) ──────────────────────────────
    print(f"\nGT records evaluated: {n_gt_records} (across {len(pred_files)} prediction files)")

    summary_rows: list[dict] = []
    total_correct = total_total = 0

    if args.binary:
        # Aggregate confusion across all 5 domains for OVERALL metrics
        overall_conf: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        print("=" * 110)
        print(f"{'Domain':<50} {'Accuracy':>9}  {'Precision':>10}  {'Recall':>8}  {'F1':>6}  "
              f"{'TP':>4}  {'FP':>4}  {'FN':>4}  {'TN':>4}")
        print("=" * 110)

        for spec in SPECS:
            slot_id = spec.slot_id
            m = binary_metrics(confusion[slot_id])
            n = slot_total[slot_id]
            c = slot_correct[slot_id]
            total_correct += c
            total_total += n

            for gt_k, preds in confusion[slot_id].items():
                for pred_k, cnt in preds.items():
                    overall_conf[gt_k][pred_k] += cnt

            print(f"  {spec.domain_label[:48]:<48} {m['accuracy']:>8.1%}  "
                  f"{m['precision']:>9.1%}  {m['recall']:>7.1%}  {m['f1']:>5.2f}  "
                  f"{m['tp']:>4}  {m['fp']:>4}  {m['fn']:>4}  {m['tn']:>4}")
            summary_rows.append({
                "slot_id": slot_id,
                "domain": spec.domain_label,
                "correct": c,
                "total": n,
                "accuracy": round(m["accuracy"], 4),
                "precision_high": round(m["precision"], 4),
                "recall_high": round(m["recall"], 4),
                "f1_high": round(m["f1"], 4),
                "tp_high": m["tp"],
                "fp_high": m["fp"],
                "fn_high": m["fn"],
                "tn_high": m["tn"],
            })

        print("-" * 110)
        ov = binary_metrics(overall_conf)
        print(f"  {'OVERALL (5-domain, micro-avg)':<48} {ov['accuracy']:>8.1%}  "
              f"{ov['precision']:>9.1%}  {ov['recall']:>7.1%}  {ov['f1']:>5.2f}  "
              f"{ov['tp']:>4}  {ov['fp']:>4}  {ov['fn']:>4}  {ov['tn']:>4}")
        print("=" * 110)
        summary_rows.append({
            "slot_id": "OVERALL",
            "domain": "OVERALL",
            "correct": total_correct,
            "total": total_total,
            "accuracy": round(ov["accuracy"], 4),
            "precision_high": round(ov["precision"], 4),
            "recall_high": round(ov["recall"], 4),
            "f1_high": round(ov["f1"], 4),
            "tp_high": ov["tp"],
            "fp_high": ov["fp"],
            "fn_high": ov["fn"],
            "tn_high": ov["tn"],
        })
    else:
        print("=" * 92)
        print(f"{'Domain':<60} {'Correct':>8}  {'Total':>6}  {'Accuracy':>9}")
        print("=" * 92)

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
    cm_name = "confusion_matrices_binary.txt" if args.binary else "confusion_matrices.txt"
    cm_path = output_dir / cm_name
    with open(cm_path, "w", encoding="utf-8") as f:
        for spec in SPECS:
            print_confusion_matrix(confusion[spec.slot_id], spec.domain_label,
                                   binary=args.binary, file=f)

    # ── CSVs ──────────────────────────────────────────────────────────────────
    acc_name = "domain_accuracy_binary.csv" if args.binary else "domain_accuracy.csv"
    study_name = "per_study_results_binary.csv" if args.binary else "per_study_results.csv"

    acc_path = output_dir / acc_name
    fieldnames = list(summary_rows[0].keys()) if summary_rows else \
        ["slot_id", "domain", "correct", "total", "accuracy"]
    with open(acc_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    study_path = output_dir / study_name
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
