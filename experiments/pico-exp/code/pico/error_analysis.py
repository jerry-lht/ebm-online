"""Error analysis helpers for LLM PICO extraction."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from pico.schemas import DocumentExample, PICO_LABELS
from pico.text_evaluate import normalize_text


def analyze_text_errors(
    examples: list[DocumentExample],
    raw_rows: list[dict[str, Any]],
    sample_limit_per_label: int = 20,
) -> dict[str, Any]:
    """Build TP/FP/FN text-match samples aligned with normalized text metrics."""
    gold_by_doc = {example.doc_id: example for example in examples}
    pred_by_doc = _prediction_items_by_doc(raw_rows)

    totals = {
        label: {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tp_samples": [],
            "fp_samples": [],
            "fn_samples": [],
        }
        for label in PICO_LABELS
    }

    for example in examples:
        pred_items = pred_by_doc.get(example.doc_id, [])
        pred_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        gold_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for item in pred_items:
            pred_by_label[item["label"]].append(item)
        for span in example.gold_spans:
            gold_by_label[span.label].append(
                {
                    "text": span.text,
                    "normalized_text": normalize_text(span.text),
                    "char_start": span.char_start,
                    "char_end": span.char_end,
                }
            )

        for label in PICO_LABELS:
            label_totals = totals[label]
            gold_counter = Counter(item["normalized_text"] for item in gold_by_label[label])
            pred_counter = Counter(item["normalized_text"] for item in pred_by_label[label])
            all_texts = sorted(set(gold_counter) | set(pred_counter))

            for text_key in all_texts:
                tp = min(gold_counter[text_key], pred_counter[text_key])
                fp = max(0, pred_counter[text_key] - gold_counter[text_key])
                fn = max(0, gold_counter[text_key] - pred_counter[text_key])
                label_totals["tp"] += tp
                label_totals["fp"] += fp
                label_totals["fn"] += fn

                if tp and len(label_totals["tp_samples"]) < sample_limit_per_label:
                    label_totals["tp_samples"].append(
                        _sample_record(
                            doc_id=example.doc_id,
                            label=label,
                            normalized_text=text_key,
                            gold_items=gold_by_label[label],
                            pred_items=pred_by_label[label],
                            kind="tp",
                        )
                    )
                if fp and len(label_totals["fp_samples"]) < sample_limit_per_label:
                    label_totals["fp_samples"].append(
                        _sample_record(
                            doc_id=example.doc_id,
                            label=label,
                            normalized_text=text_key,
                            gold_items=gold_by_label[label],
                            pred_items=pred_by_label[label],
                            kind="fp",
                        )
                    )
                if fn and len(label_totals["fn_samples"]) < sample_limit_per_label:
                    label_totals["fn_samples"].append(
                        _sample_record(
                            doc_id=example.doc_id,
                            label=label,
                            normalized_text=text_key,
                            gold_items=gold_by_label[label],
                            pred_items=pred_by_label[label],
                            kind="fn",
                        )
                    )

    return {
        "sample_limit_per_label": sample_limit_per_label,
        "labels": {
            label: {
                "tp": totals[label]["tp"],
                "fp": totals[label]["fp"],
                "fn": totals[label]["fn"],
                "tp_samples": totals[label]["tp_samples"],
                "fp_samples": totals[label]["fp_samples"],
                "fn_samples": totals[label]["fn_samples"],
            }
            for label in PICO_LABELS
        },
    }


def _prediction_items_by_doc(raw_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        doc_id = row.get("doc_id")
        response = row.get("response")
        if not isinstance(doc_id, str) or not isinstance(response, str):
            continue
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, list):
            continue
        for item in parsed:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            text = item.get("text")
            if not isinstance(label, str) or not isinstance(text, str):
                continue
            if label not in PICO_LABELS:
                continue
            by_doc[doc_id].append(
                {
                    "label": label,
                    "text": text,
                    "normalized_text": normalize_text(text),
                }
            )
    return by_doc


def _sample_record(
    doc_id: str,
    label: str,
    normalized_text: str,
    gold_items: list[dict[str, Any]],
    pred_items: list[dict[str, Any]],
    kind: str,
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "label": label,
        "kind": kind,
        "normalized_text": normalized_text,
        "gold_texts": [item["text"] for item in gold_items if item["normalized_text"] == normalized_text],
        "pred_texts": [item["text"] for item in pred_items if item["normalized_text"] == normalized_text],
    }
