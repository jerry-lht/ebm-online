from __future__ import annotations

from pathlib import Path

from analysis_setting_experiment.constants import PROMPT_VERSION
from analysis_setting_experiment.prompt_specs import PROMPT_SPECS, discover_prompt_specs
from analysis_setting_experiment.prompting import build_prompt


def test_build_prompt_includes_canonicalization_guidance() -> None:
    prompt = build_prompt(
        {
            "sr_title": "Example review",
            "sr_pico": {"intervention": ["drug"], "comparison": ["placebo"]},
            "studies": [{"title": "Study 1", "abstract": "Example abstract"}],
        }
    )
    assert "canonical settings that a review author would meta-analyze" in prompt
    assert "Few-shot canonicalization examples" in prompt
    assert "reported_outcome_measures: this is the place to preserve abstract surface forms" in prompt
    assert PROMPT_VERSION in prompt


def test_build_prompt_supports_version_override() -> None:
    prompt = build_prompt(
        {
            "sr_title": "Example review",
            "sr_pico": {},
            "studies": [],
        },
        prompt_version="abstract_sr_direct_generation_v1",
    )
    assert "Prompt version: abstract_sr_direct_generation_v1." in prompt
    assert "Few-shot canonicalization examples" not in prompt
    assert "Return a JSON array only." in prompt


def test_current_prompt_version_has_registered_spec() -> None:
    assert PROMPT_VERSION in PROMPT_SPECS
    assert PROMPT_SPECS[PROMPT_VERSION].prompt_template_path.exists()


def test_discover_prompt_specs_from_directory(tmp_path: Path) -> None:
    prompts_root = tmp_path / "prompts"
    v1_dir = prompts_root / "v1"
    v2_dir = prompts_root / "v2"
    ignored_dir = prompts_root / "ignored"
    v1_dir.mkdir(parents=True)
    v2_dir.mkdir(parents=True)
    ignored_dir.mkdir(parents=True)
    (v1_dir / "prompt.txt").write_text("Prompt version: {prompt_version}.", encoding="utf-8")
    (v2_dir / "prompt.txt").write_text("Prompt version: {prompt_version}.\n{few_shots_section}", encoding="utf-8")
    (v2_dir / "few_shots.txt").write_text("few shots", encoding="utf-8")

    specs = discover_prompt_specs(prompts_root)

    assert set(specs) == {"v1", "v2"}
    assert specs["v1"].few_shots_path is None
    assert specs["v2"].few_shots_path == v2_dir / "few_shots.txt"
