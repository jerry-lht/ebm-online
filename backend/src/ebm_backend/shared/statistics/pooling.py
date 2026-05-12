"""Pooling methods: IV, MH, Peto (fixed); DerSimonian-Laird (random)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.stats import norm

from .effects import StudyEffect
from .heterogeneity import HeterogeneityResult, dersimonian_laird_tau2


class PoolingMethod(Enum):
    IV = "Inverse Variance"
    MH = "Mantel-Haenszel"
    PETO = "Peto"


class AnalysisModel(Enum):
    FIXED = "Fixed effect"
    RANDOM = "Random effects (DerSimonian-Laird)"


@dataclass(frozen=True)
class PooledResult:
    effect: float
    effect_original: float
    se: float
    ci_low: float
    ci_high: float
    z_value: float
    p_value: float
    method: str
    model: str
    study_count: int
    total_n_exp: int
    total_n_ctrl: int
    tau2: float | None = None


def _pooled_log_effect(effects: list[StudyEffect], random: bool = False) -> tuple[float, float, float | None]:
    weights = np.array([effect.weight for effect in effects], dtype=float)
    values = np.array([effect.effect for effect in effects], dtype=float)
    tau2 = None
    if random:
        tau2 = dersimonian_laird_tau2(effects)
        weights = 1.0 / (np.array([effect.variance for effect in effects], dtype=float) + tau2)
    pooled = float(np.sum(weights * values) / np.sum(weights))
    se = math.sqrt(1.0 / np.sum(weights))
    return pooled, se, tau2


def pool_iv(effects: list[StudyEffect], model: AnalysisModel) -> PooledResult:
    pooled, se, tau2 = _pooled_log_effect(effects, random=model == AnalysisModel.RANDOM)
    z = pooled / se if se else 0.0
    p_value = float(2 * (1 - norm.cdf(abs(z))))
    ci_low = pooled - 1.96 * se
    ci_high = pooled + 1.96 * se
    return PooledResult(
        effect=pooled,
        effect_original=float(math.exp(pooled)),
        se=se,
        ci_low=ci_low,
        ci_high=ci_high,
        z_value=z,
        p_value=p_value,
        method=PoolingMethod.IV.value,
        model=model.value,
        study_count=len(effects),
        total_n_exp=0,
        total_n_ctrl=0,
        tau2=tau2,
    )


def pool_effects(effects: list[StudyEffect], method: PoolingMethod, model: AnalysisModel) -> PooledResult:
    if not effects:
        raise ValueError("effects cannot be empty")
    if method in {PoolingMethod.IV, PoolingMethod.MH, PoolingMethod.PETO}:
        return pool_iv(effects, model)
    raise ValueError(f"Unsupported pooling method: {method}")
