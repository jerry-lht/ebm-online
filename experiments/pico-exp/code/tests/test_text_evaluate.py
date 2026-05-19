from __future__ import annotations

import json

import pytest

from pico.cli.evaluate_text_predictions import main
from pico.io_utils import write_document_examples, write_jsonl
from pico.schemas import DocumentExample, Span
from pico.text_evaluate import evaluate_text_predictions, normalize_text


def _example(doc_id: str = "d1") -> DocumentExample:
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract="alpha beta gamma",
        tokens=["alpha", "beta", "gamma"],
        token_offsets=[(0, 5), (6, 10), (11, 16)],
        gold_spans=[
            Span(doc_id=doc_id, label="P", text="Alpha beta", start_token=0, end_token=2, char_start=0, char_end=10),
            Span(doc_id=doc_id, label="O", text="gamma", start_token=2, end_token=3, char_start=11, char_end=16),
        ],
        bio_labels=["I-PAR", "I-PAR", "I-OUT"],
    )


def _raw(doc_id: str, items: object) -> dict[str, object]:
    return {"doc_id": doc_id, "response": json.dumps(items), "metadata": {}}


def test_normalize_text_is_conservative() -> None:
    assert normalize_text(" Alpha\tBeta ") == "alpha beta"
    assert normalize_text("alpha\u2013beta") == "alpha-beta"


def test_text_exact_and_normalized_metrics() -> None:
    metrics = evaluate_text_predictions(
        [_example()],
        [_raw("d1", [{"label": "P", "text": "alpha  beta"}, {"label": "O", "text": "gamma"}])],
    )

    assert metrics["text_exact"]["tp"] == 1
    assert metrics["text_exact"]["fp"] == 1
    assert metrics["text_exact"]["fn"] == 1
    assert metrics["text_normalized"]["f1"] == 1
    assert metrics["pio_completeness"]["pio_complete_document_rate"] == 1


def test_wrong_label_counts_fp_and_fn() -> None:
    metrics = evaluate_text_predictions([_example()], [_raw("d1", [{"label": "I", "text": "Alpha beta"}])])

    assert metrics["text_exact"]["tp"] == 0
    assert metrics["text_exact"]["fp"] == 1
    assert metrics["text_exact"]["fn"] == 2
    assert metrics["text_exact"]["per_label"]["P"]["fn"] == 1
    assert metrics["text_exact"]["per_label"]["I"]["fp"] == 1


def test_duplicate_prediction_uses_multiset_counts() -> None:
    metrics = evaluate_text_predictions(
        [_example()],
        [_raw("d1", [{"label": "O", "text": "gamma"}, {"label": "O", "text": "gamma"}])],
    )

    assert metrics["text_exact"]["tp"] == 1
    assert metrics["text_exact"]["fp"] == 1
    assert metrics["text_exact"]["fn"] == 1


def test_cli_writes_text_tables(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "text_metrics.json"
    tables_dir = tmp_path / "tables"
    write_document_examples(gold_path, [_example()])
    write_jsonl(raw_path, [_raw("d1", [{"label": "P", "text": "Alpha beta"}, {"label": "O", "text": "gamma"}])])

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--output",
                str(output_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
        == 0
    )

    metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert metrics["text_normalized"]["f1"] == 1
    assert (tables_dir / "llm_text_f1.csv").exists()
    assert (tables_dir / "llm_pio_completeness.csv").exists()
    with pytest.raises(ValueError, match="pass --force"):
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--output",
                str(output_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test",
            ]
        )
