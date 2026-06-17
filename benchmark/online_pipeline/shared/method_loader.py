"""Load online pipeline methods for benchmark runners."""

from __future__ import annotations

from ebm_backend.online_pipeline.infrastructure.methods.registry import get_module_method


def load_method(method_spec: str, *, default_module: str | None = None):
    if "." in method_spec:
        module_name, method_name = method_spec.split(".", 1)
    else:
        if default_module is None:
            raise ValueError("A module name is required when method_spec does not include one")
        module_name = default_module
        method_name = method_spec
    return get_module_method(module_name, method_name)
