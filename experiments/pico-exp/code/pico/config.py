"""Configuration loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML config file.

    YAML support uses PyYAML when it is installed in the experiment environment.
    """
    config_path = Path(path)
    suffix = config_path.suffix.lower()
    with config_path.open("r", encoding="utf-8") as handle:
        if suffix == ".json":
            data = json.load(handle)
        elif suffix in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise RuntimeError("PyYAML is required to load YAML config files") from exc
            data = yaml.safe_load(handle)
        else:
            raise ValueError(f"Unsupported config extension: {config_path.suffix}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level config object in {config_path}")
    return data


def get_provider_config(config: dict[str, Any], provider: str) -> dict[str, Any]:
    providers = config.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("Config field 'providers' must be an object")
    provider_config = providers.get(provider)
    if not isinstance(provider_config, dict):
        raise KeyError(f"Provider {provider!r} is not configured")
    return provider_config
