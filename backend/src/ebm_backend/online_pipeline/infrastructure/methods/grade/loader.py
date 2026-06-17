"""Load GRADE domain methods."""

from __future__ import annotations

from importlib import import_module
from typing import Any


GRADE_DOMAIN_NAMES = {"risk_of_bias", "inconsistency", "indirectness", "imprecision"}


def get_grade_domain_method(domain: str, method_name: str) -> Any:
    if domain not in GRADE_DOMAIN_NAMES:
        valid = ", ".join(sorted(GRADE_DOMAIN_NAMES))
        raise ValueError(f"Unknown GRADE domain '{domain}'. Valid domains: {valid}")
    module_path = f"ebm_backend.online_pipeline.infrastructure.methods.grade.{domain}.{method_name}"
    try:
        module = import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(f"Unknown GRADE domain method '{method_name}' for domain '{domain}'") from exc
    if hasattr(module, "build_method"):
        return module.build_method()
    raise ValueError(f"GRADE domain method module '{module_path}' must define build_method()")
