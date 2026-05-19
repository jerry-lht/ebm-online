from __future__ import annotations

import json

import pytest

from q2pico.cli.validate_predictions import main
from q2pico.io_utils import read_slot_predictions, write_jsonl, write_question_examples
from q2pico.schemas import QuestionPICOExample
from q2pico.slot_validate import LLM_VALIDATOR_VERSION, validate_slot_predictions


def _example(question_id: str = "q1") -> QuestionPICOExample:
    return QuestionPICOExample(
        question_id=question_id,
        split="test59",
        question_text="In adults with hypertension, does drug A versus placebo reduce stroke?",
        gold_slots={"P": ["adults with hypertension"], "I": ["drug A"], "C": ["placebo"], "O": ["stroke"]},
    )


def _raw(question_id: str, payload: object) -> dict[str, object]:
    return {"question_id": question_id, "response": json.dumps(payload), "metadata": {}}


def test_valid_canonical_payload_is_written() -> None:
    rows, quality = validate_slot_predictions([_example()], [_raw("q1", {"P": [" x "], "I": [], "C": [], "O": []})])
    assert len(rows) == 1
    assert rows[0].slots["P"] == ["x"]
    assert rows[0].metadata["validator_version"] == LLM_VALIDATOR_VERSION
    assert quality["counts"]["written_values"] == 1


def test_invalid_json_and_unknown_keys_are_counted() -> None:
    rows, quality = validate_slot_predictions(
        [_example()],
        [
            {"question_id": "q1", "response": "[not json]"},
            _raw("q1", {"X": []}),
        ],
    )
    assert rows == []
    assert quality["counts"]["invalid_json_rows"] == 1
    assert quality["counts"]["schema_invalid_rows"] == 1


def test_keyed_single_label_payload_is_accepted() -> None:
    rows, quality = validate_slot_predictions([_example()], [_raw("q1", {"participants": ["adults"]})])
    assert len(rows) == 1
    assert rows[0].slots["P"] == ["adults"]
    assert rows[0].slots["I"] == []
    assert quality["counts"]["written_values"] == 1


def test_pi_only_scope_accepts_pi_canonical_payload_without_co() -> None:
    rows, quality = validate_slot_predictions(
        [_example()],
        [_raw("q1", {"P": ["adults"], "I": ["drug a"]})],
        labels=("P", "I"),
    )
    assert len(rows) == 1
    assert rows[0].slots["P"] == ["adults"]
    assert rows[0].slots["I"] == ["drug a"]
    assert rows[0].slots["C"] == []
    assert rows[0].slots["O"] == []
    assert quality["counts"]["written_values"] == 2


def test_non_list_and_non_string_values_raise_schema_errors() -> None:
    rows, quality = validate_slot_predictions(
        [_example()],
        [
            _raw("q1", {"P": "bad", "I": [], "C": [], "O": []}),
            _raw("q1", {"P": [1], "I": [], "C": [], "O": []}),
        ],
    )
    assert rows == []
    assert quality["counts"]["non_list_slot_rows"] == 1
    assert quality["counts"]["non_string_items"] == 1


def test_cli_writes_validated_slots_quality_json_and_quality_csv(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    valid_path = tmp_path / "validated.slots.jsonl"
    quality_path = tmp_path / "quality.json"
    tables_dir = tmp_path / "tables"
    write_question_examples(examples_path, [_example()])
    write_jsonl(raw_path, [_raw("q1", {"P": ["adults"], "I": [], "C": [], "O": []})])

    assert (
        main(
            [
                "--examples",
                str(examples_path),
                "--raw",
                str(raw_path),
                "--valid-output",
                str(valid_path),
                "--quality-output",
                str(quality_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test59",
            ]
        )
        == 0
    )

    rows = read_slot_predictions(valid_path)
    assert len(rows) == 1
    assert json.loads(quality_path.read_text(encoding="utf-8"))["validator_version"] == LLM_VALIDATOR_VERSION
    assert "invalid_json_rate" in (tables_dir / "llm_quality.csv").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="pass --force"):
        main(
            [
                "--examples",
                str(examples_path),
                "--raw",
                str(raw_path),
                "--valid-output",
                str(valid_path),
                "--quality-output",
                str(quality_path),
                "--tables-dir",
                str(tables_dir),
                "--method",
                "m",
                "--setting",
                "s",
                "--split",
                "test59",
            ]
        )
