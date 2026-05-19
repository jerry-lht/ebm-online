from __future__ import annotations

import json

import pytest

from q2pico.cli.run_llm import SCHEMA_VERSION, main
from q2pico.io_utils import read_question_examples, write_question_examples
from q2pico.schemas import QuestionPICOExample


def _example(question_id: str = "q1") -> QuestionPICOExample:
    return QuestionPICOExample(
        question_id=question_id,
        split="test59",
        question_text="In adults with hypertension, does drug A versus placebo reduce stroke?",
        gold_slots={"P": ["adults with hypertension"], "I": ["drug A"], "C": ["placebo"], "O": ["stroke"]},
    )


def _manifest(path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "question_split_v1",
                "splits": {
                    "fewshot20": {"question_ids": ["shot1"]},
                    "dev20": {"question_ids": []},
                    "test59": {"question_ids": ["q1"]},
                },
            }
        ),
        encoding="utf-8",
    )


def test_dry_run_writes_split_label_prompts_and_config(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "llm"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    top_prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    p_prompt = json.loads((output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert top_prompt["question_id"] == "q1"
    assert p_prompt["question_id"] == "q1"
    assert "Clinical question" in p_prompt["messages"][1]["content"]
    assert '"participants"' in p_prompt["messages"][1]["content"]
    assert p_prompt["metadata"]["few_shot_doc_ids"] == ["shot1"]
    assert p_prompt["metadata"]["schema_version"] == SCHEMA_VERSION
    assert run_config["task"] == "question_pico"
    assert run_config["split_manifest_path"] == str(manifest_path)


def test_non_dry_run_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "llm"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)

    with pytest.raises(RuntimeError, match="OpenAI API key is required"):
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
            ]
        )


def test_resume_skips_completed_label_subrequests_only(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "llm"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)
    label_dir = output_dir / "labels" / "P"
    label_dir.mkdir(parents=True)
    (label_dir / "raw.jsonl").write_text(
        json.dumps({"question_id": "q1", "response": json.dumps({"participants": ["adults"]})}) + "\n",
        encoding="utf-8",
    )
    (label_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
                "--resume",
            ]
        )
        == 0
    )

    p_prompts = (output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8").strip()
    i_prompts = (output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8").strip()
    assert p_prompts == ""
    assert i_prompts != ""


def test_pi_only_dry_run_writes_only_p_and_i_label_dirs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "llm"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
                "--labels",
                "P,I",
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["labels"] == ["P", "I"]
    assert (output_dir / "labels" / "P" / "prompts.jsonl").exists()
    assert (output_dir / "labels" / "I" / "prompts.jsonl").exists()
    assert not (output_dir / "labels" / "C").exists()
    assert not (output_dir / "labels" / "O").exists()


def test_pi_only_output_check_ignores_existing_unrequested_label_dirs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "llm"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)
    stale_c_dir = output_dir / "labels" / "C"
    stale_c_dir.mkdir(parents=True)
    (stale_c_dir / "prompts.jsonl").write_text("stale\n", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
                "--labels",
                "P,I",
                "--dry-run",
            ]
        )
        == 0
    )

    assert (output_dir / "labels" / "P" / "prompts.jsonl").exists()
    assert (output_dir / "labels" / "I" / "prompts.jsonl").exists()
    assert (stale_c_dir / "prompts.jsonl").read_text(encoding="utf-8") == "stale\n"


@pytest.mark.parametrize(
    ("variant", "expected_i_prompt_version", "expected_text"),
    [
        ("baseline", "question_slot_split_v1_i_only", "active option being asked about"),
        ("official_only", "question_slot_split_v1_i_official_only", "Do not force the first mentioned"),
        (
            "official_plus_order_heuristic",
            "question_slot_split_v1_i_official_plus_order_heuristic",
            "Dataset-alignment heuristic",
        ),
    ],
)
def test_pi_prompt_variant_selects_enhanced_p_and_i_variant(
    tmp_path,
    monkeypatch,
    variant: str,
    expected_i_prompt_version: str,
    expected_text: str,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / f"llm-{variant}"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example("shot1")])
    _manifest(manifest_path)

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--split-manifest",
                str(manifest_path),
                "--few-shot-examples",
                str(shots_path),
                "--output-dir",
                str(output_dir),
                "--labels",
                "P,I",
                "--pi-prompt-variant",
                variant,
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    p_prompt = json.loads((output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    i_prompt = json.loads((output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert run_config["pi_prompt_variant"] == variant
    assert run_config["label_prompt_versions"] == {
        "P": "question_slot_split_v1_p_pi_enhanced",
        "I": expected_i_prompt_version,
    }
    assert p_prompt["metadata"]["prompt_version"] == "question_slot_split_v1_p_pi_enhanced"
    assert i_prompt["metadata"]["prompt_version"] == expected_i_prompt_version
    assert "treatment status, response status" in p_prompt["messages"][1]["content"]
    assert expected_text in i_prompt["messages"][1]["content"]


def test_few_shot_count_uses_first_n_examples_from_same_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    manifest_path = tmp_path / "manifest.json"
    write_question_examples(examples_path, [_example("q1")])
    write_question_examples(shots_path, [_example(f"shot{index}") for index in range(1, 6)])
    _manifest(manifest_path)

    for count in (3, 5):
        output_dir = tmp_path / f"llm-{count}"
        assert (
            main(
                [
                    "--provider",
                    "openai",
                    "--model-id",
                    "test-model",
                    "--examples",
                    str(examples_path),
                    "--split-manifest",
                    str(manifest_path),
                    "--few-shot-examples",
                    str(shots_path),
                    "--few-shot-count",
                    str(count),
                    "--output-dir",
                    str(output_dir),
                    "--labels",
                    "P,I",
                    "--pi-prompt-variant",
                    "official_only",
                    "--dry-run",
                ]
            )
            == 0
        )
        run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
        expected_ids = [f"shot{index}" for index in range(1, count + 1)]
        assert run_config["label_few_shot_paths"] == {"P": str(shots_path), "I": str(shots_path)}
        assert run_config["few_shot_doc_ids"] == {"P": expected_ids, "I": expected_ids}


def test_pi_fewshot_file_has_expected_order_and_count() -> None:
    examples = read_question_examples("results/data/questions.pi_fewshot5.examples.jsonl")

    assert [example.question_id for example in examples] == [
        "2020 EAN Dementia::1",
        "2021 ACR RA::61",
        "2021 ACR RA::17b",
        "2021 ACR RA::21b",
        "2024 KDIGO CKD::b6",
    ]
