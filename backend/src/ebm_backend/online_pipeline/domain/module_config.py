"""Shared runtime configuration for independently executed modules."""

from __future__ import annotations

from dataclasses import dataclass, field

from ebm_backend.online_pipeline.domain.common import WorkflowConstraints


@dataclass(frozen=True)
class ModuleRunConfig:
    max_results: int = 20
    constraints: WorkflowConstraints = field(default_factory=WorkflowConstraints)
