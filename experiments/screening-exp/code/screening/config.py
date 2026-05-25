"""Configuration models and YAML loaders for screening experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ProviderConfig(BaseModel):
    """Configuration for a single model provider."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    api_key: str | None = None
    timeout_seconds: int | float | None = Field(default=None, gt=0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=1.0, ge=0.0)


class ExperimentDefaults(BaseModel):
    """Shared default settings for experiment runs."""

    model_config = ConfigDict(extra="forbid")

    default_provider: str
    prompt_version: str
    output_root: str
    high_confidence_threshold: float = Field(ge=0.0, le=1.0)
    default_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=1200, gt=0)
    default_max_retries: int = Field(default=2, ge=0)


def _load_yaml(path: str | Path) -> Any:
    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data


def load_provider_configs(path: str | Path) -> list[ProviderConfig]:
    """Load provider configs from YAML."""
    data = _load_yaml(path)
    if not isinstance(data, dict) or "providers" not in data:
        raise ValidationError.from_exception_data(
            "ProviderConfigDocument",
            [
                {
                    "type": "missing",
                    "loc": ("providers",),
                    "msg": "Field required",
                    "input": data,
                }
            ],
        )

    providers = data["providers"]
    if not isinstance(providers, list):
        raise ValidationError.from_exception_data(
            "ProviderConfigDocument",
            [
                {
                    "type": "list_type",
                    "loc": ("providers",),
                    "msg": "Input should be a valid list",
                    "input": providers,
                }
            ],
        )

    return [ProviderConfig.model_validate(item) for item in providers]


def load_experiment_defaults(path: str | Path) -> ExperimentDefaults:
    """Load experiment defaults from YAML."""
    data = _load_yaml(path)
    return ExperimentDefaults.model_validate(data)
