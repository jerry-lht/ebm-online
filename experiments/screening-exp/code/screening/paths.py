"""Path helpers derived from the package location."""

from __future__ import annotations

from pathlib import Path

code_root = Path(__file__).resolve().parents[1]
experiment_root = code_root.parent
data_root = experiment_root / "data"
results_root = experiment_root / "results"
config_root = code_root / "config"


def ensure_results_subdir(name: str) -> Path:
    """Create and return a named subdirectory under the results root."""
    if not name or not name.strip():
        raise ValueError("results subdirectory name must be a non-empty string")

    target = results_root / name
    target.mkdir(parents=True, exist_ok=True)
    return target
