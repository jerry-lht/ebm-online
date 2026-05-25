from __future__ import annotations

import json

from pico.cli.analyze_text_errors import main
from pico.error_analysis import analyze_text_errors
from pico.io_utils import write_document_examples, write_jsonl
from pico.schemas import DocumentExample, Span


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


def test_analyze_text_errors_collects_tp_fp_fn_samples() -> None:
    analysis = analyze_text_errors(
        examples=[_example()],
        raw_rows=[
            _raw(
                "d1",
                [
                    {"label": "P", "text": "Alpha beta"},
                    {"label": "P", "text": "alpha beta extra"},
                    {"label": "I", "text": "gamma"},
                ],
            )
        ],
        sample_limit_per_label=5,
    )

    assert analysis["labels"]["P"]["tp"] == 1
    assert analysis["labels"]["P"]["fp"] == 1
    assert analysis["labels"]["P"]["fn"] == 0
    assert analysis["labels"]["O"]["fn"] == 1
    assert analysis["labels"]["P"]["tp_samples"][0]["doc_id"] == "d1"
    assert analysis["labels"]["P"]["fp_samples"][0]["pred_texts"] == ["alpha beta extra"]
    assert analysis["labels"]["O"]["fn_samples"][0]["gold_texts"] == ["gamma"]


def test_error_analysis_cli_writes_json(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "analysis.json"
    write_document_examples(gold_path, [_example()])
    write_jsonl(raw_path, [_raw("d1", [{"label": "P", "text": "Alpha beta"}])])

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--raw",
                str(raw_path),
                "--output",
                str(output_path),
                "--sample-limit-per-label",
                "3",
            ]
        )
        == 0
    )

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["sample_limit_per_label"] == 3
    assert data["labels"]["P"]["tp"] == 1
    assert data["labels"]["O"]["fn"] == 1
