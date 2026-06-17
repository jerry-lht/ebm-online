"""API dependency construction."""

from __future__ import annotations

from ebm_backend.online_pipeline.application.module_runner import ModuleRunner
from ebm_backend.online_pipeline.infrastructure.methods.resolver import RegistryModuleMethodResolver


def get_module_runner_for_api() -> ModuleRunner:
    return ModuleRunner(resolver=RegistryModuleMethodResolver())
