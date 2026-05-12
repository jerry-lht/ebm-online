"""Heterogeneity tests: Cochran's Q, I-squared, tau-squared."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2

from .effects import StudyEffect


@dataclass(frozen=True)
class HeterogeneityResult:
    q: float
    df: int
    p_value: float
    i2: float
    tau2: float | None


def cochran_q(effects: list[StudyEffect]) -> float:
    if len(effects) <= 1:
        return 0.0
    weights = np.array([effect.weight for effect in effects], dtype=float)
    values = np.array([effect.effect for effect in effects], dtype=float)
    pooled = float(np.sum(weights * values) / np.sum(weights))
    return float(np.sum(weights * (values - pooled) ** 2))


def dersimonian_laird_tau2(effects: list[StudyEffect], q: float | None = None) -> float:
    if len(effects) <= 1:
        return 0.0
    q = cochran_q(effects) if q is None else q
    weights = np.array([effect.weight for effect in effects], dtype=float)
    df = len(effects) - 1
    c = float(np.sum(weights) - np.sum(weights**2) / np.sum(weights))
    return max(0.0, (q - df) / c) if c > 0 else 0.0


def compute_heterogeneity(effects: list[StudyEffect], tau2: float | None = None) -> HeterogeneityResult:
    if len(effects) <= 1:
        return HeterogeneityResult(q=0.0, df=0, p_value=1.0, i2=0.0, tau2=tau2)
    q = cochran_q(effects)
    df = len(effects) - 1
    p_value = float(chi2.sf(q, df))
    i2 = max(0.0, ((q - df) / q) * 100) if q > 0 else 0.0
    return HeterogeneityResult(q=q, df=df, p_value=p_value, i2=i2, tau2=tau2)
