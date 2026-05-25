from __future__ import annotations

import json

import pytest

from pico.cli.evaluate_predictions import main
from pico.evaluate import evaluate_all
from pico.io_utils import write_document_examples, write_span_predictions
from pico.schemas import DocumentExample, Span


def _span(doc_id: str, label: str, start: int, end: int) -> Span:
    return Span(doc_id=doc_id, label=label, text=" ".join(["t"] * (end - start)), start_token=start, end_token=end)


def _example(
    doc_id: str = "d1",
    spans: list[Span] | None = None,
    bio_labels: list[str] | None = None,
    has_overlap: bool = False,
) -> DocumentExample:
    tokens = ["a", "b", "c", "d"]
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract="a b c d",
        tokens=tokens,
        token_offsets=[(0, 1), (2, 3), (4, 5), (6, 7)],
        gold_spans=spans if spans is not None else [_span(doc_id, "P", 0, 2)],
        bio_labels=bio_labels if bio_labels is not None else ["I-PAR", "I-PAR", "O", "O"],
        metadata={"has_overlap": has_overlap},
    )


def test_perfect_prediction_scores_one() -> None:
    example = _example()
    metrics = evaluate_all([example], [_span("d1", "P", 0, 2)], {"d1": example.bio_labels})

    assert metrics["exact_span"]["f1"] == 1
    assert metrics["relaxed_span"]["f1"] == 1
    assert metrics["blurb_token"]["f1"] == 1


def test_missing_span_adds_fn_and_lowers_recall() -> None:
    metrics = evaluate_all([_example()], [], {"d1": ["O", "O", "O", "O"]})

    assert metrics["exact_span"]["tp"] == 0
    assert metrics["exact_span"]["fn"] == 1
    assert metrics["exact_span"]["recall"] == 0


def test_extra_span_adds_fp_and_lowers_precision() -> None:
    metrics = evaluate_all([_example()], [_span("d1", "P", 0, 2), _span("d1", "I", 2, 3)])

    assert metrics["exact_span"]["tp"] == 1
    assert metrics["exact_span"]["fp"] == 1
    assert metrics["exact_span"]["precision"] == 0.5


def test_wrong_label_counts_fp_and_fn() -> None:
    metrics = evaluate_all([_example()], [_span("d1", "I", 0, 2)])

    assert metrics["exact_span"]["tp"] == 0
    assert metrics["exact_span"]["fp"] == 1
    assert metrics["exact_span"]["fn"] == 1


def test_boundary_mismatch_fails_exact_but_matches_relaxed() -> None:
    metrics = evaluate_all([_example()], [_span("d1", "P", 0, 1)])

    assert metrics["exact_span"]["f1"] == 0
    assert metrics["relaxed_span"]["f1"] == 1


def test_duplicate_predictions_first_matches_rest_are_fp() -> None:
    metrics = evaluate_all([_example()], [_span("d1", "P", 0, 2), _span("d1", "P", 0, 2)])

    assert metrics["exact_span"]["tp"] == 1
    assert metrics["exact_span"]["fp"] == 1
    assert metrics["exact_span"]["duplicates"]["count"] == 1
    assert metrics["exact_span"]["duplicates"]["rate"] == 0.5


def test_overlapping_gold_spans_can_all_match_span_evaluator() -> None:
    spans = [_span("d1", "P", 0, 2), _span("d1", "I", 1, 3), _span("d1", "O", 2, 4)]
    example = _example(spans=spans, bio_labels=["I-PAR", "I-INT", "I-OUT", "I-OUT"], has_overlap=True)
    metrics = evaluate_all([example], spans, {"d1": example.bio_labels})

    assert metrics["exact_span"]["f1"] == 1
    assert metrics["overlap_subset"]["f1"] == 1
    assert metrics["blurb_token"]["f1"] == 1


def test_bio_cli_rejects_bad_length_illegal_label_and_unknown_doc(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    output_path = tmp_path / "metrics.json"
    tables_dir = tmp_path / "tables"
    write_document_examples(gold_path, [_example()])

    cases = [
        {"doc_id": "d1", "bio_labels": ["O"]},
        {"doc_id": "d1", "bio_labels": ["O", "BAD", "O", "O"]},
        {"doc_id": "unknown", "bio_labels": ["O", "O", "O", "O"]},
    ]
    for row in cases:
        pred_path = tmp_path / f"{row['doc_id']}_{len(row['bio_labels'])}.jsonl"
        pred_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            main(
                [
                    "--gold",
                    str(gold_path),
                    "--pred",
                    str(pred_path),
                    "--pred-format",
                    "bio",
                    "--output",
                    str(output_path),
                    "--tables-dir",
                    str(tables_dir),
                ]
            )


def test_cli_writes_metrics_and_tables_for_span_predictions(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    pred_path = tmp_path / "pred.jsonl"
    output_path = tmp_path / "metrics.json"
    tables_dir = tmp_path / "tables"
    prediction = _span("d1", "P", 0, 2)
    write_document_examples(gold_path, [_example()])
    write_span_predictions(pred_path, [prediction])

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--pred",
                str(pred_path),
                "--pred-format",
                "spans",
                "--output",
                str(output_path),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
                "--tables-dir",
                str(tables_dir),
            ]
        )
        == 0
    )

    metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert metrics["exact_span"]["f1"] == 1
    assert (tables_dir / "main_blurb_token_f1.csv").exists()
    assert (tables_dir / "main_span_f1.csv").exists()
    assert (tables_dir / "per_label_f1.csv").exists()
    assert (tables_dir / "run_index.csv").exists()
