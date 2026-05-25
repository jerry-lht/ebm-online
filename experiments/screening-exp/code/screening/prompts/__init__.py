"""Prompt modules for screening experiments."""

from screening.prompts.direct import build_direct_prompt
from screening.prompts.criterion_wise import build_criterion_wise_prompt

__all__ = ["build_direct_prompt", "build_criterion_wise_prompt"]
