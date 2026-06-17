"""Load meta-analysis subtask methods."""

from __future__ import annotations

from importlib import import_module
from typing import Any


SUBTASK_PACKAGES = {
    "study_results": "subtask2_study_results",
    "analysis_methods": "subtask3_analysis_methods",
    "subgroup_analysis": "subtask4_subgroup_analysis",
    "overall_estimates": "subtask5_overall_estimates",
}


def get_meta_analysis_subtask_method(subtask: str, method_name: str) -> Any:
    package = SUBTASK_PACKAGES.get(subtask)
    if package is None:
        valid = ", ".join(sorted(SUBTASK_PACKAGES))
        raise ValueError(f"Unknown meta-analysis subtask '{subtask}'. Valid subtasks: {valid}")
    module_path = f"ebm_backend.online_pipeline.infrastructure.methods.meta_analysis.{package}.{method_name}"
    try:
        module = import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(f"Unknown meta-analysis subtask method '{method_name}' for subtask '{subtask}'") from exc
    if hasattr(module, "build_method"):
        return module.build_method()
    raise ValueError(f"Meta-analysis subtask method module '{module_path}' must define build_method()")
