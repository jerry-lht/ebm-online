"""Dispatch dataset builds to module-owned builders."""

from __future__ import annotations

from typing import Any

from benchmark.online_pipeline.shared.building import DEFAULT_SEED, ROOT


def build_dataset(
    *,
    module: str,
    source: str,
    dataset_name: str,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    source_url: str | None = None,
    allow_deterministic_fallback: bool = False,
) -> dict[str, Any]:
    source = _resolve_source(module=module, source=source)
    if module == "q2pico":
        from benchmark.online_pipeline.q2pico.builder import build_dataset as build_q2pico_dataset

        return build_q2pico_dataset(
            source=source,
            dataset_name=dataset_name,
            sample_size=sample_size,
            seed=seed,
            source_url=source_url,
        )
    if module == "study_screening":
        from benchmark.online_pipeline.study_screening.builder import build_dataset as build_study_screening_dataset

        return build_study_screening_dataset(
            source=source,
            dataset_name=dataset_name,
            sample_size=sample_size,
            seed=seed,
            source_url=source_url,
        )
    if module == "study_pio":
        from benchmark.online_pipeline.study_pio.builder import build_dataset as build_study_pio_dataset

        return build_study_pio_dataset(
            source=source,
            dataset_name=dataset_name,
            sample_size=sample_size,
            seed=seed,
            source_url=source_url,
        )
    if module == "risk_of_bias":
        from benchmark.online_pipeline.risk_of_bias.builder import build_dataset as build_risk_of_bias_dataset

        return build_risk_of_bias_dataset(
            source=source,
            dataset_name=dataset_name,
            sample_size=sample_size,
            seed=seed,
            source_url=source_url,
        )
    if module == "meta_analysis":
        from benchmark.online_pipeline.meta_analysis.builder import build_dataset as build_meta_analysis_dataset

        return build_meta_analysis_dataset(
            source=source,
            dataset_name=dataset_name,
            sample_size=sample_size,
            seed=seed,
            source_url=source_url,
            allow_deterministic_fallback=allow_deterministic_fallback,
        )
    if module == "grade":
        from pathlib import Path

        from benchmark.online_pipeline.grade.builder import build_dataset_v3 as build_grade_dataset
        from benchmark.online_pipeline.shared.building import RAW_DATA_DIR

        if source not in {"grade_v3", "cochrane_grade_v3"}:
            raise ValueError("Reproducible grade build supports source 'grade_v3'")
        return build_grade_dataset(
            dataset_name=dataset_name,
            raw_root=Path(source_url) if source_url else RAW_DATA_DIR / "grade",
            sample_size=sample_size,
            seed=seed,
        )
    raise ValueError("Reproducible build currently supports q2pico, study_screening, study_pio, risk_of_bias, meta_analysis, and grade")


def _resolve_source(*, module: str, source: str) -> str:
    if source != "builtin_smoke":
        return source
    return {
        "q2pico": "builtin_smoke",
        "study_screening": "builtin_smoke",
        "study_pio": "cochrane_study_pio",
        "risk_of_bias": "cochrane_rob1",
        "meta_analysis": "cochrane_meta_v1",
        "grade": "grade_v3",
    }.get(module, source)
