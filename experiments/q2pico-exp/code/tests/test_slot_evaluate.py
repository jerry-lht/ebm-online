from __future__ import annotations

import json

from q2pico.cli.evaluate_predictions import main
from q2pico.io_utils import write_question_examples, write_slot_predictions
from q2pico.schemas import QuestionPICOExample, SlotPrediction
from q2pico.slot_evaluate import evaluate_slot_predictions


def _example(question_id: str = "q1") -> QuestionPICOExample:
    return QuestionPICOExample(
        question_id=question_id,
        split="test59",
        question_text="Question",
        gold_slots={"P": ["Adults"], "I": ["Drug-A"], "C": ["Placebo"], "O": ["Stroke reduction"]},
    )


def _pred(question_id: str = "q1", **slots: list[str]) -> SlotPrediction:
    payload = {label: [] for label in ("P", "I", "C", "O")}
    payload.update(slots)
    return SlotPrediction(question_id=question_id, slots=payload)


def test_exact_vs_normalized_matching() -> None:
    metrics = evaluate_slot_predictions([_example()], [_pred(P=[" adults "], I=["drug-a"], C=["placebo"], O=["stroke reduction"])])
    assert metrics["slot_exact"]["f1"] < 1
    assert metrics["slot_normalized"]["f1"] == 1


def test_c_label_is_included_and_partial_completeness_is_counted() -> None:
    metrics = evaluate_slot_predictions([_example()], [_pred(P=["Adults"], I=["Drug-A"], O=["Stroke reduction"])])
    assert metrics["slot_exact"]["per_label"]["C"]["fn"] == 1
    assert metrics["pico_completeness"]["pico_complete_question_rate"] == 0


def test_pi_only_scope_ignores_c_and_o() -> None:
    metrics = evaluate_slot_predictions(
        [_example()],
        [_pred(P=["Adults"], I=["Drug-A"])],
        labels=("P", "I"),
    )
    assert set(metrics["slot_exact"]["per_label"]) == {"P", "I"}
    assert metrics["slot_exact"]["f1"] == 1
    assert metrics["pico_completeness"]["pico_complete_question_rate"] == 1


def test_cli_writes_metrics_and_tables(tmp_path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    pred_path = tmp_path / "pred.jsonl"
    output_path = tmp_path / "metrics.json"
    tables_dir = tmp_path / "tables"
    write_question_examples(gold_path, [_example()])
    write_slot_predictions(pred_path, [_pred(P=["Adults"], I=["Drug-A"], C=["Placebo"], O=["Stroke reduction"])])

    assert (
        main(
            [
                "--gold",
                str(gold_path),
                "--pred",
                str(pred_path),
                "--output",
                str(output_path),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test59",
                "--tables-dir",
                str(tables_dir),
            ]
        )
        == 0
    )

    metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert metrics["slot_exact"]["f1"] == 1
    assert (tables_dir / "llm_slot_f1.csv").exists()
    assert (tables_dir / "llm_slot_completeness.csv").exists()
    assert (tables_dir / "run_index.csv").exists()
