#!/usr/bin/env python3
"""
Enhanced comparison with detailed analysis and visualizations.

Usage:
    python detailed_analysis.py
    python detailed_analysis.py --baseline results/predictions --optimized results/predictions_optimized
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter


def load_ground_truth(dataset_dir: Path) -> dict:
    """Load ground truth from dataset files."""
    gt = {}
    for path in dataset_dir.glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        study = raw[0] if isinstance(raw, list) else raw
        study_id = study.get("study_id") or path.stem

        rob_data = study.get("risk_of_bias", {})
        if isinstance(rob_data, list):
            rob_data = rob_data[0] if rob_data else {}

        gt[study_id] = {
            "random_sequence_generation": rob_data.get("random_sequence_generation"),
            "allocation_concealment": rob_data.get("allocation_concealment"),
            "blinding_participants": rob_data.get("blinding_of_participants_and_personnel"),
            "blinding_outcome": rob_data.get("blinding_of_outcome_assessment"),
            "incomplete_outcome": rob_data.get("incomplete_outcome_data"),
        }
    return gt


def load_predictions(pred_dir: Path) -> dict:
    """Load predictions from results directory."""
    preds = {}
    for path in pred_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        study_id = data.get("study_id") or path.stem
        preds[study_id] = data.get("slot_map", {})
    return preds


def normalize_judgement(j: str | None) -> str | None:
    """Normalize judgement strings."""
    if not j:
        return None
    j = j.strip().lower()
    if "low" in j:
        return "Low risk"
    if "high" in j:
        return "High risk"
    if "unclear" in j:
        return "Unclear risk"
    return None


def analyze_transitions(ground_truth: dict, baseline_preds: dict, optimized_preds: dict) -> dict:
    """Analyze how predictions changed from baseline to optimized."""
    domains = [
        "random_sequence_generation",
        "allocation_concealment",
        "blinding_participants",
        "blinding_outcome",
        "incomplete_outcome",
    ]

    transitions = defaultdict(lambda: defaultdict(lambda: {"count": 0, "studies": []}))

    for study_id, gt_judgements in ground_truth.items():
        if study_id not in baseline_preds or study_id not in optimized_preds:
            continue

        baseline_j = baseline_preds[study_id]
        optimized_j = optimized_preds[study_id]

        for domain in domains:
            gt = normalize_judgement(gt_judgements.get(domain))
            base = normalize_judgement(baseline_j.get(domain))
            opt = normalize_judgement(optimized_j.get(domain))

            if gt is None or base is None or opt is None:
                continue

            if base != opt:
                key = f"{base} → {opt}"
                was_correct = (base == gt)
                now_correct = (opt == gt)

                if not was_correct and now_correct:
                    category = "fixed"
                elif was_correct and not now_correct:
                    category = "broken"
                else:
                    category = "changed"

                transitions[domain][category]["count"] += 1
                transitions[domain][category]["studies"].append({
                    "study_id": study_id,
                    "gt": gt,
                    "baseline": base,
                    "optimized": opt,
                })

    return dict(transitions)


def analyze_confusion_matrix(ground_truth: dict, predictions: dict, domain: str) -> dict:
    """Generate confusion matrix for a domain."""
    matrix = defaultdict(lambda: defaultdict(int))

    for study_id, gt_judgements in ground_truth.items():
        if study_id not in predictions:
            continue

        gt = normalize_judgement(gt_judgements.get(domain))
        pred = normalize_judgement(predictions[study_id].get(domain))

        if gt is None or pred is None:
            continue

        matrix[gt][pred] += 1

    return dict(matrix)


def print_detailed_comparison(ground_truth: dict, baseline_preds: dict, optimized_preds: dict):
    """Print detailed comparison with transition analysis."""

    domain_labels = {
        "random_sequence_generation": "Random sequence generation",
        "allocation_concealment": "Allocation concealment",
        "blinding_participants": "Blinding of participants",
        "blinding_outcome": "Blinding of outcome assessment",
        "incomplete_outcome": "Incomplete outcome data",
    }

    print("\n" + "="*100)
    print("DETAILED RESULTS ANALYSIS")
    print("="*100)

    # Overall comparison
    print("\n" + "─"*100)
    print("OVERALL ACCURACY COMPARISON")
    print("─"*100)

    for domain_id, domain_label in domain_labels.items():
        print(f"\n{domain_label}:")

        # Baseline stats
        b_correct = 0
        b_total = 0
        for study_id, gt_j in ground_truth.items():
            if study_id not in baseline_preds:
                continue
            gt = normalize_judgement(gt_j.get(domain_id))
            pred = normalize_judgement(baseline_preds[study_id].get(domain_id))
            if gt is None or pred is None:
                continue
            b_total += 1
            if gt == pred:
                b_correct += 1

        # Optimized stats
        o_correct = 0
        o_total = 0
        for study_id, gt_j in ground_truth.items():
            if study_id not in optimized_preds:
                continue
            gt = normalize_judgement(gt_j.get(domain_id))
            pred = normalize_judgement(optimized_preds[study_id].get(domain_id))
            if gt is None or pred is None:
                continue
            o_total += 1
            if gt == pred:
                o_correct += 1

        b_acc = b_correct / b_total if b_total > 0 else 0
        o_acc = o_correct / o_total if o_total > 0 else 0
        change = o_acc - b_acc

        print(f"  Baseline:  {b_correct}/{b_total} = {b_acc:.2%}")
        print(f"  Optimized: {o_correct}/{o_total} = {o_acc:.2%}")
        print(f"  Change:    {change:+.2%}", end="")
        if change > 0.01:
            print(" ✅ IMPROVED")
        elif change < -0.01:
            print(" ⚠️ DECLINED")
        else:
            print(" ≈ STABLE")

    # Transition analysis
    print("\n" + "─"*100)
    print("PREDICTION TRANSITIONS (Baseline → Optimized)")
    print("─"*100)

    transitions = analyze_transitions(ground_truth, baseline_preds, optimized_preds)

    for domain_id, domain_label in domain_labels.items():
        if domain_id not in transitions:
            continue

        domain_trans = transitions[domain_id]
        fixed = domain_trans.get("fixed", {}).get("count", 0)
        broken = domain_trans.get("broken", {}).get("count", 0)
        changed = domain_trans.get("changed", {}).get("count", 0)

        if fixed + broken + changed == 0:
            continue

        print(f"\n{domain_label}:")
        print(f"  ✅ Fixed (wrong → correct):  {fixed}")
        print(f"  ⚠️  Broken (correct → wrong): {broken}")
        print(f"  ↔️  Changed (wrong → wrong):  {changed}")
        print(f"  Net improvement: {fixed - broken:+d}")

        # Show examples of fixed cases
        if fixed > 0:
            examples = domain_trans["fixed"]["studies"][:3]
            print(f"\n  Examples of fixed predictions:")
            for ex in examples:
                print(f"    • {ex['study_id']}: {ex['baseline']} → {ex['optimized']} (GT: {ex['gt']})")

        # Show examples of broken cases
        if broken > 0:
            examples = domain_trans["broken"]["studies"][:3]
            print(f"\n  Examples of broken predictions:")
            for ex in examples:
                print(f"    • {ex['study_id']}: {ex['baseline']} → {ex['optimized']} (GT: {ex['gt']})")

    # Confusion matrices for key domains
    print("\n" + "─"*100)
    print("CONFUSION MATRICES (Optimized Version)")
    print("─"*100)

    key_domains = ["random_sequence_generation", "allocation_concealment", "incomplete_outcome"]

    for domain_id in key_domains:
        domain_label = domain_labels[domain_id]
        matrix = analyze_confusion_matrix(ground_truth, optimized_preds, domain_id)

        if not matrix:
            continue

        print(f"\n{domain_label}:")
        print(f"{'':>20} {'Pred: Low':>15} {'Pred: High':>15} {'Pred: Unclear':>15}")
        print("  " + "-"*65)

        for gt_label in ["Low risk", "High risk", "Unclear risk"]:
            if gt_label not in matrix:
                continue
            row = matrix[gt_label]
            print(f"  GT: {gt_label:<13} {row.get('Low risk', 0):>15} "
                  f"{row.get('High risk', 0):>15} {row.get('Unclear risk', 0):>15}")

    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)

    total_b_correct = 0
    total_b_total = 0
    total_o_correct = 0
    total_o_total = 0

    for domain_id in domain_labels.keys():
        for study_id, gt_j in ground_truth.items():
            if study_id in baseline_preds:
                gt = normalize_judgement(gt_j.get(domain_id))
                pred = normalize_judgement(baseline_preds[study_id].get(domain_id))
                if gt is not None and pred is not None:
                    total_b_total += 1
                    if gt == pred:
                        total_b_correct += 1

            if study_id in optimized_preds:
                gt = normalize_judgement(gt_j.get(domain_id))
                pred = normalize_judgement(optimized_preds[study_id].get(domain_id))
                if gt is not None and pred is not None:
                    total_o_total += 1
                    if gt == pred:
                        total_o_correct += 1

    overall_b_acc = total_b_correct / total_b_total if total_b_total > 0 else 0
    overall_o_acc = total_o_correct / total_o_total if total_o_total > 0 else 0
    overall_change = overall_o_acc - overall_b_acc

    print(f"\nOverall Accuracy:")
    print(f"  Baseline:  {total_b_correct}/{total_b_total} = {overall_b_acc:.2%}")
    print(f"  Optimized: {total_o_correct}/{total_o_total} = {overall_o_acc:.2%}")
    print(f"  Change:    {overall_change:+.2%}", end="")
    if overall_change > 0.01:
        print(" ✅ IMPROVED")
    elif overall_change < -0.01:
        print(" ⚠️ DECLINED")
    else:
        print(" ≈ STABLE")

    print("\nTarget Goals:")
    print("  • Random sequence generation: ~80% (was 72%)")
    print("  • Allocation concealment: ~69% (was 68%)")
    print("  • Incomplete outcome: maintain ~63%")
    print("  • Blinding outcome: maintain ~54%")
    print("  • Overall: 65%+ (was 62.67%)")

    print("\n" + "="*100)


def main():
    parser = argparse.ArgumentParser(description="Detailed analysis of baseline vs optimized")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--baseline", default="results/predictions")
    parser.add_argument("--optimized", default="results/predictions_optimized")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    baseline_dir = Path(args.baseline)
    optimized_dir = Path(args.optimized)

    if not dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {dataset_dir}")
        return 1

    if not baseline_dir.exists():
        print(f"ERROR: Baseline predictions not found: {baseline_dir}")
        return 1

    if not optimized_dir.exists():
        print(f"ERROR: Optimized predictions not found: {optimized_dir}")
        return 1

    print("Loading data...")
    ground_truth = load_ground_truth(dataset_dir)
    baseline_preds = load_predictions(baseline_dir)
    optimized_preds = load_predictions(optimized_dir)

    print(f"Loaded {len(ground_truth)} ground truth studies")
    print(f"Loaded {len(baseline_preds)} baseline predictions")
    print(f"Loaded {len(optimized_preds)} optimized predictions")

    print_detailed_comparison(ground_truth, baseline_preds, optimized_preds)

    return 0


if __name__ == "__main__":
    exit(main())
