#!/usr/bin/env python3
"""
Compare baseline vs optimized predictions using the project's official
evaluation logic from evaluate.py.

Usage:
    python compare_results.py
    python compare_results.py --baseline results/predictions_test_baseline \
                              --optimized results/predictions_test_optimized
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from domain_specs import SPECS
from evaluate import evaluate_one_gt_record


def evaluate_dir(dataset_dir: Path, pred_dir: Path) -> tuple[dict, dict, list]:
    """Run the official evaluator over a prediction directory.

    Returns (slot_correct, slot_total, per_record_rows) where the rows include
    the per-domain GT/pred for each evaluated GT record (so we can do
    transition analysis later).
    """
    slot_correct: dict[str, int] = defaultdict(int)
    slot_total: dict[str, int] = defaultdict(int)
    rows: list[dict] = []

    pred_files = sorted(pred_dir.glob("*.json"))
    for pred_path in pred_files:
        gt_path = dataset_dir / pred_path.name
        if not gt_path.exists():
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

            slot_results = evaluate_one_gt_record(gt_rob, prediction)
            for slot_id, res in slot_results.items():
                slot_total[slot_id] += 1
                if res["match"]:
                    slot_correct[slot_id] += 1
                rows.append({
                    "pmid": prediction.get("pmid", pred_path.stem),
                    "gt_record_idx": gt_idx,
                    "slot_id": slot_id,
                    "gt": res["gt"],
                    "pred": res["pred"],
                    "match": res["match"],
                })

    return dict(slot_correct), dict(slot_total), rows


def fmt_pct(c: int, n: int) -> str:
    if n == 0:
        return "n/a"
    return f"{c}/{n} = {c/n:.2%}"


def print_comparison(
    baseline_correct: dict,
    baseline_total: dict,
    optimized_correct: dict,
    optimized_total: dict,
) -> None:
    print("\n" + "=" * 100)
    print("RESULTS COMPARISON: Baseline vs Optimized")
    print("=" * 100)
    print(f"{'Domain':<50} {'Baseline':<22} {'Optimized':<22} {'Change':<12}")
    print("-" * 100)

    total_b_c = total_b_n = total_o_c = total_o_n = 0

    for spec in SPECS:
        slot = spec.slot_id
        b_c = baseline_correct.get(slot, 0)
        b_n = baseline_total.get(slot, 0)
        o_c = optimized_correct.get(slot, 0)
        o_n = optimized_total.get(slot, 0)

        b_acc = b_c / b_n if b_n > 0 else 0
        o_acc = o_c / o_n if o_n > 0 else 0
        change = o_acc - b_acc

        marker = ""
        if change > 0.01:
            marker = " UP"
        elif change < -0.01:
            marker = " DOWN"

        print(
            f"  {spec.domain_label[:48]:<48} "
            f"{fmt_pct(b_c, b_n):<22} "
            f"{fmt_pct(o_c, o_n):<22} "
            f"{change:+.2%}{marker}"
        )

        total_b_c += b_c
        total_b_n += b_n
        total_o_c += o_c
        total_o_n += o_n

    print("-" * 100)
    overall_b = total_b_c / total_b_n if total_b_n > 0 else 0
    overall_o = total_o_c / total_o_n if total_o_n > 0 else 0
    overall_change = overall_o - overall_b
    marker = ""
    if overall_change > 0.01:
        marker = " UP"
    elif overall_change < -0.01:
        marker = " DOWN"

    print(
        f"  {'OVERALL':<48} "
        f"{fmt_pct(total_b_c, total_b_n):<22} "
        f"{fmt_pct(total_o_c, total_o_n):<22} "
        f"{overall_change:+.2%}{marker}"
    )
    print("=" * 100)


def transition_table(baseline_rows: list[dict], optimized_rows: list[dict]) -> None:
    """Show how predictions changed between the two versions, per domain."""
    # Index by (pmid, gt_record_idx, slot_id)
    b_idx = {(r["pmid"], r["gt_record_idx"], r["slot_id"]): r for r in baseline_rows}
    o_idx = {(r["pmid"], r["gt_record_idx"], r["slot_id"]): r for r in optimized_rows}

    common_keys = sorted(set(b_idx) & set(o_idx))
    by_slot = defaultdict(lambda: {"fixed": [], "broken": [], "still_wrong": [], "still_right": []})

    for k in common_keys:
        b = b_idx[k]
        o = o_idx[k]
        slot = k[2]
        if b["match"] and o["match"]:
            by_slot[slot]["still_right"].append((b, o))
        elif not b["match"] and o["match"]:
            by_slot[slot]["fixed"].append((b, o))
        elif b["match"] and not o["match"]:
            by_slot[slot]["broken"].append((b, o))
        else:
            by_slot[slot]["still_wrong"].append((b, o))

    print("\n" + "=" * 100)
    print("PREDICTION TRANSITIONS (Baseline -> Optimized)")
    print("=" * 100)

    for spec in SPECS:
        slot = spec.slot_id
        s = by_slot.get(slot, {"fixed": [], "broken": [], "still_wrong": [], "still_right": []})
        fixed = len(s["fixed"])
        broken = len(s["broken"])
        net = fixed - broken

        print(f"\n  {spec.domain_label}:")
        print(f"    Fixed   (wrong -> right): {fixed}")
        print(f"    Broken  (right -> wrong): {broken}")
        print(f"    Still wrong:              {len(s['still_wrong'])}")
        print(f"    Still right:              {len(s['still_right'])}")
        print(f"    Net change:               {net:+d}")

        if fixed:
            print("    Examples FIXED:")
            for b, o in s["fixed"][:3]:
                print(f"      pmid={b['pmid']}  GT={b['gt']!r}  baseline={b['pred']!r}  optimized={o['pred']!r}")
        if broken:
            print("    Examples BROKEN:")
            for b, o in s["broken"][:3]:
                print(f"      pmid={b['pmid']}  GT={b['gt']!r}  baseline={b['pred']!r}  optimized={o['pred']!r}")

    print("\n" + "=" * 100)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baseline vs optimized RoB predictions")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--baseline", default="results/predictions")
    parser.add_argument("--optimized", default="results/predictions_optimized")
    parser.add_argument("--show_transitions", action="store_true",
                        help="Show per-domain prediction transition analysis")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    baseline_dir = Path(args.baseline)
    optimized_dir = Path(args.optimized)

    if not dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {dataset_dir}")
        return
    if not baseline_dir.exists():
        print(f"ERROR: Baseline predictions not found: {baseline_dir}")
        return
    if not optimized_dir.exists():
        print(f"ERROR: Optimized predictions not found: {optimized_dir}")
        return

    print(f"Dataset:   {dataset_dir}")
    print(f"Baseline:  {baseline_dir}")
    print(f"Optimized: {optimized_dir}\n")

    print("Evaluating baseline...")
    b_correct, b_total, b_rows = evaluate_dir(dataset_dir, baseline_dir)
    print(f"  -> {sum(b_total.values())} domain records across "
          f"{len(set((r['pmid'], r['gt_record_idx']) for r in b_rows))} GT records")

    print("Evaluating optimized...")
    o_correct, o_total, o_rows = evaluate_dir(dataset_dir, optimized_dir)
    print(f"  -> {sum(o_total.values())} domain records across "
          f"{len(set((r['pmid'], r['gt_record_idx']) for r in o_rows))} GT records")

    print_comparison(b_correct, b_total, o_correct, o_total)

    if args.show_transitions:
        transition_table(b_rows, o_rows)


if __name__ == "__main__":
    main()
