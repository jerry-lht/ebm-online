from __future__ import annotations

import json
import time

import pytest

import pico.cli.run_llm as run_llm
from pico.cli.run_llm import SCHEMA_VERSION, main
from pico.io_utils import write_document_examples, write_jsonl
from pico.prompt_registry import resolve_prompt_path
from pico.schemas import DocumentExample, Span


def _example(doc_id: str = "d1") -> DocumentExample:
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract="alpha beta gamma",
        tokens=["alpha", "beta", "gamma"],
        token_offsets=[(0, 5), (6, 10), (11, 16)],
        gold_spans=[
            Span(
                doc_id=doc_id,
                label="P",
                text="alpha",
                start_token=0,
                end_token=1,
                char_start=0,
                char_end=5,
            )
        ],
        bio_labels=["I-PAR", "O", "O"],
    )


def _split_example(doc_id: str = "d1") -> DocumentExample:
    return DocumentExample(
        doc_id=doc_id,
        split="test",
        abstract="participants intervention outcome",
        tokens=["participants", "intervention", "outcome"],
        token_offsets=[(0, 12), (13, 25), (26, 33)],
        gold_spans=[
            Span(doc_id=doc_id, label="P", text="participants", start_token=0, end_token=1),
            Span(doc_id=doc_id, label="I", text="intervention", start_token=1, end_token=2),
            Span(doc_id=doc_id, label="O", text="outcome", start_token=2, end_token=3),
        ],
        bio_labels=["I-PAR", "I-INT", "I-OUT"],
    )


def test_dry_run_writes_prompts_and_config_without_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    prompt_rows = [
        json.loads(line)
        for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert len(prompt_rows) == 1
    assert prompt_rows[0]["doc_id"] == "d1"
    assert "alpha beta gamma" in prompt_rows[0]["messages"][1]["content"]
    assert "Do not return character offsets" in prompt_rows[0]["messages"][1]["content"]
    assert "model_version" in prompt_rows[0]["metadata"]
    assert prompt_rows[0]["metadata"]["schema_version"] == SCHEMA_VERSION
    assert prompt_rows[0]["metadata"]["prompt_schema"] == "text"
    assert run_config["dry_run"] is True
    assert run_config["model_id"] == "test-model"
    assert run_config["workers"] == 16
    assert not (output_dir / "raw.jsonl").exists()


def test_non_dry_run_requires_api_key_before_calling_openai(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    with pytest.raises(RuntimeError, match="OpenAI API key is required"):
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert (output_dir / "prompts.jsonl").exists()
    assert (output_dir / "run_config.json").exists()
    assert not (output_dir / "raw.jsonl").exists()


def test_model_id_can_come_from_provider_config(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    config_path = tmp_path / "llm.yaml"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])
    config_path.write_text(
        "\n".join(
            [
                "providers:",
                "  openai:",
                "    model_id: configured-model",
                "    model_version: 2026-05-14",
                "    base_url: https://api.openai.com/v1",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--provider",
                "openai",
                "--provider-config",
                str(config_path),
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["model_id"] == "configured-model"
    assert run_config["model_version"] == "2026-05-14"
    assert run_config["api_mode"] == "responses"


def test_non_openai_base_url_defaults_to_chat_completions_mode(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    config_path = tmp_path / "llm.yaml"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])
    config_path.write_text(
        "\n".join(
            [
                "providers:",
                "  openai:",
                "    model_id: configured-model",
                "    base_url: https://api.deepseek.com",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--provider",
                "openai",
                "--provider-config",
                str(config_path),
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["api_mode"] == "chat_completions"


def test_configured_api_mode_overrides_default(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    config_path = tmp_path / "llm.yaml"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])
    config_path.write_text(
        "\n".join(
            [
                "providers:",
                "  openai:",
                "    model_id: configured-model",
                "    base_url: https://api.deepseek.com",
                "    api_mode: responses",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--provider",
                "openai",
                "--provider-config",
                str(config_path),
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["api_mode"] == "responses"


def test_few_shot_prompt_requires_and_renders_examples(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("target")])
    write_document_examples(shots_path, [_example("shot1")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot",
                "--few-shot-examples",
                str(shots_path),
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert "Example doc_id: shot1" in prompt["messages"][1]["content"]
    assert '"label": "P"' in prompt["messages"][1]["content"]
    assert "char_start" not in prompt["messages"][1]["content"]
    assert prompt["metadata"]["few_shot_doc_ids"] == ["shot1"]
    assert run_config["few_shot_doc_ids"] == ["shot1"]


def test_offsets_prompt_mode_keeps_offset_schema_for_ablation(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-offsets",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert "Character offsets are zero-based" in prompt["messages"][1]["content"]
    assert prompt["metadata"]["prompt_schema"] == "offsets"
    assert run_config["schema_version"] == "llm_pico_spans_offsets_v1"


def test_v2_text_prompt_includes_pio_definitions(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v2",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert "P = participants or study population" in prompt["messages"][1]["content"]
    assert "I = interventions, treatments, comparators, or controls" in prompt["messages"][1]["content"]
    assert "O = outcomes, endpoints, measurements, or adverse events" in prompt["messages"][1]["content"]


def test_v3_text_prompt_includes_multiple_mentions_guidance(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v3",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert "include each exact mention separately" in prompt["messages"][1]["content"]
    assert "extract the specific local mention" in prompt["messages"][1]["content"]


def test_v3_i_only_prompt_changes_i_definition(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v3-i-only",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert "I = interventions or treatments" in prompt["messages"][1]["content"]
    assert "comparators, or controls" not in prompt["messages"][1]["content"]


def test_bestof_split_i_only_prompt_uses_new_structure_and_hides_example_doc_id(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("target")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--dry-run",
            ]
        )
        == 0
    )

    i_prompt = json.loads((output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8"))
    content = i_prompt["messages"][1]["content"]
    assert "Task definition:" in content
    assert "I definition and scope:" in content
    assert "Rules:" in content
    assert "Example:" in content
    assert "Document id:" not in content
    assert "Example doc_id:" not in content
    assert "Extract intervention spans from the randomized controlled trial abstract below." in content
    assert "I means the exact span(s) that name what participants received, what they were compared against, or the care/assignment condition of a trial arm." in content
    assert "If both intervention arms and comparator/control arms are mentioned, extract both." in content
    assert 'Return only JSON in this exact format: `{"interventions":["..."]}`' in content
    assert 'Example with one span: `{"interventions":["placebo"]}`' in content
    assert 'Example with multiple spans: `{"interventions":["acupuncture","usual care"]}`' in content
    assert '"label": "I"' not in content
    assert '"interventions"' in content


def test_bestof_split_v2_i_only_prompt_adds_representative_mention_guidance(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("target")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v2",
                "--label-target",
                "I",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    content = prompt["messages"][1]["content"]
    assert "Representative mention guidance:" in content
    assert "Prefer one representative exact mention per intervention arm" in content
    assert "Avoid returning repeated long and short variants of the same arm" in content
    assert 'Return only JSON in this exact format: `{"interventions":["..."]}`' in content
    assert "Document id:" not in content
    assert "Example doc_id:" not in content
    assert '"label": "I"' not in content


def test_label_target_is_valid_only_with_bestof_split_mode(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    with pytest.raises(
        ValueError,
        match="--label-target is valid only with --prompt-mode few-shot-text-bestof-split-v1 or few-shot-text-bestof-split-v2",
    ):
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--label-target",
                "P",
                "--dry-run",
            ]
        )


def test_v4_text_prompt_keeps_multiple_mentions_guidance_without_local_mention_rule(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v4",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert "include each exact mention separately" in prompt["messages"][1]["content"]
    assert "Use exact text copied from the abstract. Do not paraphrase." in prompt["messages"][1]["content"]
    assert "extract the specific local mention" not in prompt["messages"][1]["content"]


def test_v4_i_only_prompt_changes_i_definition_without_local_mention_rule(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v4-i-only",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert "I = interventions or treatments" in prompt["messages"][1]["content"]
    assert "comparators, or controls" not in prompt["messages"][1]["content"]
    assert "extract the specific local mention" not in prompt["messages"][1]["content"]


def test_v5_text_prompt_tightens_o_definition_and_keeps_text_only_contract(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "zero-shot-text-v5",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    content = prompt["messages"][1]["content"]
    assert "Do not return character offsets or token offsets." in content
    assert "Extract `pain score`, not `pain score was lower`." in content
    assert "If a sentence only expresses efficacy, superiority, significance" in content
    assert "char_start" not in content
    assert "char_end" not in content
    assert run_config["prompt_mode"] == "zero-shot-text-v5"
    assert run_config["prompt_version"] == "zero_shot_text_v5"


def test_few_shot_v5_uses_dedicated_examples_and_records_prompt_version(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    shots_path = tmp_path / "shots.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("target")])
    shots = [
        DocumentExample(
            doc_id="shot-pain",
            split="train",
            abstract="Pain score was lower. Hospital stay was shorter.",
            tokens=[],
            gold_spans=[
                Span(doc_id="shot-pain", label="O", text="Pain score", start_token=0, end_token=0),
                Span(doc_id="shot-pain", label="O", text="Hospital stay", start_token=0, end_token=0),
            ],
            bio_labels=[],
        ),
        DocumentExample(
            doc_id="shot-lab",
            split="train",
            abstract="Complement factor C3a was reduced.",
            tokens=[],
            gold_spans=[
                Span(doc_id="shot-lab", label="O", text="Complement factor C3a", start_token=0, end_token=0),
            ],
            bio_labels=[],
        ),
    ]
    write_document_examples(shots_path, shots)

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-v5",
                "--few-shot-examples",
                str(shots_path),
                "--few-shot-count",
                "2",
                "--dry-run",
            ]
        )
        == 0
    )

    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    content = prompt["messages"][1]["content"]
    assert "Example doc_id: shot-pain" in content
    assert "Example doc_id: shot-lab" in content
    assert '"text": "Pain score"' in content
    assert '"text": "Complement factor C3a"' in content
    assert "char_start" not in content
    assert "char_end" not in content
    assert prompt["metadata"]["few_shot_doc_ids"] == ["shot-pain", "shot-lab"]
    assert prompt["metadata"]["prompt_version"] == "few_shot_text_v5"
    assert run_config["prompt_mode"] == "few-shot-text-v5"
    assert run_config["prompt_version"] == "few_shot_text_v5"
    assert run_config["few_shot_doc_ids"] == ["shot-pain", "shot-lab"]


def test_dry_run_refuses_to_replace_existing_outputs_without_force(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])
    args = [
        "--provider",
        "openai",
        "--model-id",
        "test-model",
        "--examples",
        str(examples_path),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    ]
    assert main(args) == 0
    with pytest.raises(FileExistsError, match="pass --force"):
        main(args)
    assert main([*args, "--force"]) == 0


def test_workers_can_be_overridden_and_must_be_positive(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--workers",
                "4",
                "--dry-run",
            ]
        )
        == 0
    )
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["workers"] == 4

    with pytest.raises(ValueError, match="workers must be positive"):
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--workers",
                "0",
                "--force",
                "--dry-run",
            ]
        )


def test_resume_skips_existing_raw_rows(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("d1"), _example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d1", "response": "[]", "metadata": {}}])
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--force",
                "--dry-run",
            ]
        )
        == 0
    )

    prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in prompts] == ["d2"]
    assert run_config["existing_raw_rows"] == 1
    assert run_config["existing_error_rows"] == 0
    assert run_config["pending_prompt_rows"] == 1


def test_resume_allows_existing_prompt_and_config_outputs_without_force(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("d1"), _example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d1", "response": "[]", "metadata": {}}])
    write_jsonl(output_dir / "prompts.jsonl", [{"doc_id": "stale"}])
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--dry-run",
            ]
        )
        == 0
    )

    prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in prompts] == ["d2"]
    assert run_config["existing_raw_rows"] == 1


def test_resume_rejects_orphan_raw_without_run_config(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example()])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d1", "response": "[]", "metadata": {}}])

    with pytest.raises(FileExistsError, match="raw output exists without run_config"):
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--dry-run",
            ]
        )


def test_resume_does_not_skip_existing_error_rows(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("d1"), _example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "errors.jsonl", [{"doc_id": "d1", "error_type": "Timeout", "message": "boom"}])
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--force",
                "--dry-run",
            ]
        )
        == 0
    )

    prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in prompts] == ["d1", "d2"]
    assert run_config["existing_error_rows"] == 1


def test_resume_retries_docs_from_existing_error_rows(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("d1"), _example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d1", "response": "[]", "metadata": {}}])
    write_jsonl(output_dir / "errors.jsonl", [{"doc_id": "d2", "error_type": "Timeout", "message": "boom"}])
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--force",
                "--dry-run",
            ]
        )
        == 0
    )

    prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in prompts] == ["d2"]
    assert run_config["existing_raw_rows"] == 1
    assert run_config["existing_error_rows"] == 1


def test_resume_clears_recovered_error_rows_and_failed_count(tmp_path, monkeypatch) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_example("d1"), _example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d1", "response": "[]", "metadata": {}}])
    write_jsonl(output_dir / "errors.jsonl", [{"doc_id": "d2", "error_type": "Timeout", "message": "boom"}])
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    def _fake_call_openai(**kwargs: object) -> dict[str, int]:
        write_jsonl(output_dir / "raw.jsonl", [{"doc_id": "d2", "response": "[]", "metadata": {}}])
        return {"written_rows": 1, "failed_rows": 0}

    monkeypatch.setattr(run_llm, "_call_openai", _fake_call_openai)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--resume",
                "--force",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    errors = [json.loads(line) for line in (output_dir / "errors.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert run_config["completed_raw_rows"] == 2
    assert run_config["failed_rows"] == 0
    assert errors == []


def test_bestof_split_dry_run_writes_label_subdirs_and_split_config(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert run_config["split_extraction"] is True
    assert run_config["split_strategy"] == "bestof_pio_v1"
    assert run_config["label_prompt_versions"]["P"] == "few_shot_text_bestof_split_v1_p_only"
    assert run_config["label_few_shot_paths"]["I"].endswith("few_shot_text_bestof_split_i.examples.jsonl")
    assert run_config["label_schema_versions"]["O"] == SCHEMA_VERSION

    top_prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert top_prompts[0]["doc_id"] == "d1"
    assert top_prompts[0]["split_extraction"] is True

    p_prompt = json.loads((output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8"))
    i_prompt = json.loads((output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8"))
    o_prompt = json.loads((output_dir / "labels" / "O" / "prompts.jsonl").read_text(encoding="utf-8"))
    assert p_prompt["metadata"]["label_filter"] == "P"
    assert i_prompt["metadata"]["label_filter"] == "I"
    assert o_prompt["metadata"]["label_filter"] == "O"
    assert p_prompt["metadata"]["keyed_output_key"] == "participants"
    assert i_prompt["metadata"]["keyed_output_key"] == "interventions"
    assert o_prompt["metadata"]["keyed_output_key"] == "outcomes"
    assert "Task definition:" in p_prompt["messages"][1]["content"]
    assert "P definition and scope:" in p_prompt["messages"][1]["content"]
    assert 'Return only JSON in this exact format: `{"participants":["..."]}`' in p_prompt["messages"][1]["content"]
    assert "Task definition:" in i_prompt["messages"][1]["content"]
    assert "I definition and scope:" in i_prompt["messages"][1]["content"]
    assert 'Return only JSON in this exact format: `{"interventions":["..."]}`' in i_prompt["messages"][1]["content"]
    assert "Task definition:" in o_prompt["messages"][1]["content"]
    assert "O definition and scope:" in o_prompt["messages"][1]["content"]
    assert 'Return only JSON in this exact format: `{"outcomes":["..."]}`' in o_prompt["messages"][1]["content"]
    assert "Document id:" not in i_prompt["messages"][1]["content"]
    assert "Example doc_id:" not in i_prompt["messages"][1]["content"]
    assert "Hard rules for O" in o_prompt["messages"][1]["content"]
    assert "Document id:" in p_prompt["messages"][1]["content"]
    assert "Document id:" in o_prompt["messages"][1]["content"]
    assert "Example doc_id:" in p_prompt["messages"][1]["content"]
    assert "Example doc_id:" in o_prompt["messages"][1]["content"]


def test_bestof_split_few_shot_examples_are_label_filtered(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--dry-run",
            ]
        )
        == 0
    )

    p_prompt = json.loads((output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8"))
    i_prompt = json.loads((output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8"))
    o_prompt = json.loads((output_dir / "labels" / "O" / "prompts.jsonl").read_text(encoding="utf-8"))
    assert '"participants"' in p_prompt["messages"][1]["content"]
    assert '"label": "P"' not in p_prompt["messages"][1]["content"]
    assert '"label": "I"' not in p_prompt["messages"][1]["content"]
    assert '"label": "O"' not in p_prompt["messages"][1]["content"]
    assert '"interventions"' in i_prompt["messages"][1]["content"]
    assert '"label": "I"' not in i_prompt["messages"][1]["content"]
    assert '"label": "P"' not in i_prompt["messages"][1]["content"]
    assert '"label": "O"' not in i_prompt["messages"][1]["content"]
    assert '"outcomes"' in o_prompt["messages"][1]["content"]
    assert '"label": "O"' not in o_prompt["messages"][1]["content"]
    assert '"label": "P"' not in o_prompt["messages"][1]["content"]
    assert '"label": "I"' not in o_prompt["messages"][1]["content"]


def test_bestof_split_resume_skips_existing_subrequests_only(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1"), _split_example("d2")])
    (output_dir / "labels" / "P").mkdir(parents=True, exist_ok=True)
    write_jsonl(
        output_dir / "labels" / "P" / "raw.jsonl",
        [{"doc_id": "d1", "response": '[{"label":"P","text":"participants"}]', "metadata": {}}],
    )
    (output_dir / "labels" / "P" / "run_config.json").write_text("{}", encoding="utf-8")
    (output_dir / "labels" / "I").mkdir(parents=True, exist_ok=True)
    (output_dir / "labels" / "I" / "run_config.json").write_text("{}", encoding="utf-8")
    (output_dir / "labels" / "O").mkdir(parents=True, exist_ok=True)
    (output_dir / "labels" / "O" / "run_config.json").write_text("{}", encoding="utf-8")
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--resume",
                "--dry-run",
            ]
        )
        == 0
    )

    p_prompts = [json.loads(line) for line in (output_dir / "labels" / "P" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    i_prompts = [json.loads(line) for line in (output_dir / "labels" / "I" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    o_prompts = [json.loads(line) for line in (output_dir / "labels" / "O" / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["doc_id"] for row in p_prompts] == ["d2"]
    assert [row["doc_id"] for row in i_prompts] == ["d1", "d2"]
    assert [row["doc_id"] for row in o_prompts] == ["d1", "d2"]


@pytest.mark.parametrize(
    ("prompt_mode", "override_examples", "expected_prompt_version", "expected_doc_ids"),
    [
        ("few-shot-text-bestof-split-v1", False, "few_shot_text_bestof_split_v1_i_only", ["10078672", "9951491", "9987969"]),
        ("few-shot-text-bestof-split-v1", True, "few_shot_text_bestof_split_v1_i_only", ["shot-a", "shot-b", "shot-c"]),
        ("few-shot-text-bestof-split-v2", False, "few_shot_text_bestof_split_v2_i_only", ["10078672", "9951491", "9987969"]),
        ("few-shot-text-bestof-split-v2", True, "few_shot_text_bestof_split_v2_i_only", ["shot-a", "shot-b", "shot-c"]),
    ],
)
def test_bestof_split_i_single_label_ablation_configs_record_prompt_and_few_shot_selection(
    tmp_path,
    prompt_mode: str,
    override_examples: bool,
    expected_prompt_version: str,
    expected_doc_ids: list[str],
) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1")])

    shots_path = tmp_path / "shots.jsonl"
    if override_examples:
        shots = [
            DocumentExample(
                doc_id="shot-a",
                split="train",
                abstract="arm alpha versus placebo",
                tokens=[],
                gold_spans=[
                    Span(doc_id="shot-a", label="I", text="arm alpha", start_token=0, end_token=0),
                    Span(doc_id="shot-a", label="I", text="placebo", start_token=0, end_token=0),
                ],
                bio_labels=[],
            ),
            DocumentExample(
                doc_id="shot-b",
                split="train",
                abstract="usual care and exercise therapy",
                tokens=[],
                gold_spans=[
                    Span(doc_id="shot-b", label="I", text="usual care", start_token=0, end_token=0),
                    Span(doc_id="shot-b", label="I", text="exercise therapy", start_token=0, end_token=0),
                ],
                bio_labels=[],
            ),
            DocumentExample(
                doc_id="shot-c",
                split="train",
                abstract="diet counseling only",
                tokens=[],
                gold_spans=[
                    Span(doc_id="shot-c", label="I", text="diet counseling only", start_token=0, end_token=0),
                ],
                bio_labels=[],
            ),
        ]
        write_document_examples(shots_path, shots)

    args = [
        "--provider",
        "openai",
        "--model-id",
        "test-model",
        "--examples",
        str(examples_path),
        "--output-dir",
        str(output_dir),
        "--prompt-mode",
        prompt_mode,
        "--label-target",
        "I",
        "--dry-run",
    ]
    if override_examples:
        args.extend(["--few-shot-examples", str(shots_path)])

    assert main(args) == 0

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    assert run_config["prompt_mode"] == prompt_mode
    assert run_config["prompt_version"] == expected_prompt_version
    assert run_config["label_prompt_versions"]["I"] == expected_prompt_version
    assert run_config["few_shot_doc_ids"] == expected_doc_ids
    assert prompt["metadata"]["prompt_version"] == expected_prompt_version
    assert prompt["metadata"]["few_shot_doc_ids"] == expected_doc_ids
    expected_path = str(shots_path) if override_examples else "results/data/few_shot_text_bestof_split_i.examples.jsonl"
    assert run_config["input_paths"]["few_shot_examples"] == expected_path
    assert run_config["label_few_shot_paths"]["I"] == expected_path


def test_bestof_split_single_label_dry_run_writes_only_target_outputs(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1")])

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--label-target",
                "P",
                "--dry-run",
            ]
        )
        == 0
    )

    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    prompt = json.loads((output_dir / "prompts.jsonl").read_text(encoding="utf-8"))
    content = prompt["messages"][1]["content"]
    assert run_config["split_extraction"] is True
    assert run_config["label"] == "P"
    assert run_config["label_output_key"] == "participants"
    assert run_config["prompt_version"] == "few_shot_text_bestof_split_v1_p_only"
    assert run_config["input_paths"]["few_shot_examples"].endswith("few_shot_text_bestof_split_p.examples.jsonl")
    assert prompt["metadata"]["label_filter"] == "P"
    assert prompt["metadata"]["keyed_output_key"] == "participants"
    assert 'Return only JSON in this exact format: `{"participants":["..."]}`' in content
    assert not (output_dir / "labels").exists()
    assert not (output_dir / "raw.jsonl").exists()
    assert not (output_dir / "errors.jsonl").exists()


def test_bestof_split_single_label_resume_stays_within_top_level_output_dir(tmp_path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    output_dir = tmp_path / "llm"
    write_document_examples(examples_path, [_split_example("d1"), _split_example("d2")])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        output_dir / "raw.jsonl",
        [{"doc_id": "d1", "response": '[{"label":"P","text":"participants"}]', "metadata": {}}],
    )
    (output_dir / "run_config.json").write_text("{}", encoding="utf-8")

    assert (
        main(
            [
                "--provider",
                "openai",
                "--model-id",
                "test-model",
                "--examples",
                str(examples_path),
                "--output-dir",
                str(output_dir),
                "--prompt-mode",
                "few-shot-text-bestof-split-v1",
                "--label-target",
                "P",
                "--resume",
                "--dry-run",
            ]
        )
        == 0
    )

    prompts = [json.loads(line) for line in (output_dir / "prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    run_config = json.loads((output_dir / "run_config.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in prompts] == ["d2"]
    assert run_config["existing_raw_rows"] == 1
    assert run_config["existing_error_rows"] == 0
    assert run_config["pending_prompt_rows"] == 1
    assert run_config["label"] == "P"


def test_prompt_versions_resolve_from_staged_directories() -> None:
    assert resolve_prompt_path("few_shot_text_v1").parts[-2] == "stage_v1"
    assert resolve_prompt_path("zero_shot_text_v5").parts[-2] == "stage_v5"
    assert resolve_prompt_path("few_shot_text_bestof_split_v1_i_only").parts[-2] == "stage_bestof_split_v1"
    assert resolve_prompt_path("few_shot_text_bestof_split_v2_i_only").parts[-2] == "stage_bestof_split_v2"


def test_call_single_prompt_retries_retryable_503_then_succeeds(monkeypatch) -> None:
    class _Retryable503(Exception):
        status_code = 503

    attempts = {"count": 0}

    def _fake_once(**_: object) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise _Retryable503("Service temporarily unavailable")
        return {"doc_id": "d1", "response": "[]", "metadata": {}}

    sleep_calls: list[float] = []

    def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(run_llm, "_call_single_prompt_once", _fake_once)
    monkeypatch.setattr(run_llm.random, "uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr(time, "sleep", _fake_sleep)

    row = run_llm._call_single_prompt(
        prompt_row={"doc_id": "d1", "messages": [], "metadata": {}},
        api_key="k",
        base_url="https://example.com/v1",
        model_id="m",
        temperature=0.0,
        timeout_seconds=10.0,
        prompt_schema="text",
        api_mode="chat_completions",
        max_retries=3,
    )
    assert row["doc_id"] == "d1"
    assert attempts["count"] == 3
    assert sleep_calls == [2.0, 4.0]


def test_call_single_prompt_does_not_retry_non_retryable_400(monkeypatch) -> None:
    class _BadRequest400(Exception):
        status_code = 400

    attempts = {"count": 0}

    def _fake_once(**_: object) -> dict[str, object]:
        attempts["count"] += 1
        raise _BadRequest400("invalid request")

    monkeypatch.setattr(run_llm, "_call_single_prompt_once", _fake_once)

    with pytest.raises(_BadRequest400):
        run_llm._call_single_prompt(
            prompt_row={"doc_id": "d1", "messages": [], "metadata": {}},
            api_key="k",
            base_url="https://example.com/v1",
            model_id="m",
            temperature=0.0,
            timeout_seconds=10.0,
            prompt_schema="text",
            api_mode="chat_completions",
            max_retries=5,
        )
    assert attempts["count"] == 1


def test_response_format_error_detection_covers_text_format_missing_name() -> None:
    class _CompatError(Exception):
        pass

    exc = _CompatError(
        "Error code: 400 - {'error': {'message': \"Missing required parameter: '***.***.name'.\", "
        "'param': 'text.format.name', 'code': 'missing_required_parameter'}}"
    )
    assert run_llm._is_response_format_error(exc) is True


def test_parse_response_text_accepts_markdown_json_fence() -> None:
    parsed = run_llm._parse_response_text(
        """```json
{"spans":[{"label":"I","text":"placebo"}]}
```"""
    )
    assert parsed == {"spans": [{"label": "I", "text": "placebo"}]}


def test_parse_response_text_extracts_json_when_surrounded_by_text() -> None:
    parsed = run_llm._parse_response_text(
        'Here is the result:\n{"spans":[{"label":"P","text":"participants"}]}\nDone.'
    )
    assert parsed == {"spans": [{"label": "P", "text": "participants"}]}


def test_parse_response_text_accepts_top_level_spans_array() -> None:
    parsed = run_llm._parse_response_text('[{"label":"O","text":"pain score"}]')
    assert parsed == {"spans": [{"label": "O", "text": "pain score"}]}


def test_normalize_response_items_injects_label_for_interventions_key_mode() -> None:
    normalized = run_llm._normalize_response_items(["acupuncture", "usual care"], "I", "interventions")
    assert normalized == [
        {"label": "I", "text": "acupuncture"},
        {"label": "I", "text": "usual care"},
    ]


@pytest.mark.parametrize(
    ("payload", "key", "expected"),
    [
        ('{"participants":["adults","healthy controls"]}', "participants", ["adults", "healthy controls"]),
        ('{"interventions":["acupuncture","usual care"]}', "interventions", ["acupuncture", "usual care"]),
        ('{"outcomes":["pain score","hospital stay"]}', "outcomes", ["pain score", "hospital stay"]),
    ],
)
def test_parse_response_text_accepts_label_specific_keyed_objects(payload: str, key: str, expected: list[str]) -> None:
    parsed = run_llm._parse_response_text(payload, keyed_output_key=key)
    assert parsed == {"spans": expected}


def test_parse_response_text_accepts_fenced_keyed_json() -> None:
    parsed = run_llm._parse_response_text(
        """```json
{"participants":["adults with hypertension"]}
```""",
        keyed_output_key="participants",
    )
    assert parsed == {"spans": ["adults with hypertension"]}


def test_parse_response_text_extracts_wrapped_keyed_json() -> None:
    parsed = run_llm._parse_response_text(
        'Answer:\n{"outcomes":["pain score"]}\nDone.',
        keyed_output_key="outcomes",
    )
    assert parsed == {"spans": ["pain score"]}


def test_parse_response_text_rejects_wrong_key_for_single_label_mode() -> None:
    with pytest.raises(ValueError, match="must use the 'participants' key"):
        run_llm._parse_response_text('{"interventions":["acupuncture"]}', keyed_output_key="participants")


def test_normalize_response_items_injects_label_for_participants_key_mode() -> None:
    normalized = run_llm._normalize_response_items(["adults", "healthy controls"], "P", "participants")
    assert normalized == [
        {"label": "P", "text": "adults"},
        {"label": "P", "text": "healthy controls"},
    ]


def test_normalize_response_items_injects_label_for_outcomes_key_mode() -> None:
    normalized = run_llm._normalize_response_items(["pain score", "hospital stay"], "O", "outcomes")
    assert normalized == [
        {"label": "O", "text": "pain score"},
        {"label": "O", "text": "hospital stay"},
    ]


def test_validate_llm_can_consume_normalized_single_label_raw_output() -> None:
    example = _split_example("d1")
    from pico.validate_llm import validate_llm_predictions

    validated_spans, quality = validate_llm_predictions(
        [example],
        [
            {
                "doc_id": "d1",
                "response": json.dumps(
                    run_llm._normalize_response_items(["participants"], "P", "participants"),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "metadata": {"label_filter": "P", "keyed_output_key": "participants"},
            }
        ],
    )
    assert [(span.label, span.text) for span in validated_spans] == [("P", "participants")]
    assert quality["counts"]["written_spans"] == 1
