"""Infrastructure adapter for resolving online pipeline module methods."""

from __future__ import annotations

from dataclasses import dataclass

from ebm_backend.online_pipeline.infrastructure.methods.registry import get_module_method


@dataclass(frozen=True)
class RegistryModuleMethodResolver:
    def resolve(self, *, module_name: str, method_name: str):
        return get_module_method(module_name, method_name)
