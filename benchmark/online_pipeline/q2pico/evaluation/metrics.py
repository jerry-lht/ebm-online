"""Q2PICO smoke benchmark metrics."""

from __future__ import annotations

from typing import Any


SLOTS = ("P", "I", "C", "O")


def evaluate(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from benchmark.online_pipeline.q2pico.evaluation.judge import normalized_match_judge

    instances = [
        {"instance_id": row["instance_id"], "question_text": ""}
        for row in predictions
    ]
    match_rows = normalized_match_judge(instances=instances, predictions=predictions, gold_by_id=gold_by_id)
    metrics = evaluate_match_rows(match_rows)
    metrics["exact_all_slots"] = _exact_all_slots(predictions, gold_by_id)
    return metrics


def evaluate_match_rows(match_rows: list[dict[str, Any]]) -> dict[str, Any]:
    slot_metrics: dict[str, dict[str, float | int]] = {}
    total_tp = total_fp = total_fn = 0
    rows_by_instance: dict[str, list[dict[str, Any]]] = {}
    for row in match_rows:
        rows_by_instance.setdefault(str(row["instance_id"]), []).append(row)

    for slot in SLOTS:
        tp = fp = fn = exact = 0
        for row in match_rows:
            if row["slot"] != slot:
                continue
            row_tp = len(row.get("matches") or [])
            row_fp = len(row.get("unmatched_predicted_indices") or [])
            row_fn = len(row.get("unmatched_gold_indices") or [])
            tp += row_tp
            fp += row_fp
            fn += row_fn
            if row_fp == 0 and row_fn == 0:
                exact += 1
        precision, recall, f1 = _prf(tp, fp, fn)
        slot_row_count = sum(1 for row in match_rows if row["slot"] == slot)
        slot_metrics[slot] = {
            "exact_match": exact / slot_row_count if slot_row_count else 0.0,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    micro_precision, micro_recall, micro_f1 = _prf(total_tp, total_fp, total_fn)
    macro_f1 = _macro_question_f1(rows_by_instance)
    complete_questions = sum(1 for rows in rows_by_instance.values() if all(not row.get("unmatched_gold_indices") for row in rows))
    return {
        "instance_count": len(rows_by_instance),
        "slot_metrics": slot_metrics,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "macro_f1": macro_f1,
        "pico_complete_question_rate": complete_questions / len(rows_by_instance) if rows_by_instance else 0.0,
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
    }


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _macro_question_f1(rows_by_instance: dict[str, list[dict[str, Any]]]) -> float:
    if not rows_by_instance:
        return 0.0
    f1_values: list[float] = []
    for rows in rows_by_instance.values():
        tp = sum(len(row.get("matches") or []) for row in rows)
        fp = sum(len(row.get("unmatched_predicted_indices") or []) for row in rows)
        fn = sum(len(row.get("unmatched_gold_indices") or []) for row in rows)
        _precision, _recall, f1 = _prf(tp, fp, fn)
        f1_values.append(f1)
    return sum(f1_values) / len(f1_values)


def _exact_all_slots(predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]]) -> float:
    if not predictions:
        return 0.0
    from benchmark.online_pipeline.q2pico.evaluation.judge import normalized_match_judge

    rows = normalized_match_judge(
        instances=[{"instance_id": row["instance_id"], "question_text": ""} for row in predictions],
        predictions=predictions,
        gold_by_id=gold_by_id,
    )
    by_instance: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_instance.setdefault(str(row["instance_id"]), []).append(row)
    exact = sum(
        1
        for instance_rows in by_instance.values()
        if all(not row.get("unmatched_gold_indices") and not row.get("unmatched_predicted_indices") for row in instance_rows)
    )
    return exact / len(predictions)
