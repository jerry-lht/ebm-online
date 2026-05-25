from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from screening.config import load_experiment_defaults, load_provider_configs
from screening.paths import config_root


def test_load_provider_configs_example() -> None:
    providers = load_provider_configs(config_root / "llm_providers.example.yaml")
    assert len(providers) == 2
    assert providers[0].provider == "openai"
    assert providers[0].temperature == 0.0
    assert providers[0].max_tokens == 1200
    assert providers[0].max_retries == 2
    assert providers[0].api_key_env or providers[0].api_key


def test_load_experiment_defaults_example() -> None:
    defaults = load_experiment_defaults(config_root / "experiment_defaults.yaml")
    assert defaults.default_provider == "openai"
    assert defaults.prompt_version == "v0"
    assert defaults.output_root == "results"
    assert defaults.high_confidence_threshold == 0.8
    assert defaults.default_temperature == 0.0
    assert defaults.default_max_tokens == 1200
    assert defaults.default_max_retries == 2


def test_provider_configs_require_top_level_providers_key(tmp_path: Path) -> None:
    path = tmp_path / "bad_providers.yaml"
    path.write_text(yaml.safe_dump({"items": []}), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_provider_configs(path)


def test_experiment_defaults_fail_on_missing_required_fields(tmp_path: Path) -> None:
    path = tmp_path / "bad_defaults.yaml"
    path.write_text(yaml.safe_dump({"prompt_version": "v0"}), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_experiment_defaults(path)


def test_malformed_yaml_raises_yaml_error(tmp_path: Path) -> None:
    path = tmp_path / "malformed.yaml"
    path.write_text("providers: [\n", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_provider_configs(path)
