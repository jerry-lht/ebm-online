"""Effect size calculations (MD, SMD, log RR, log OR)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm

from .corrections import apply_zero_cell_correction


@dataclass(frozen=True)
class StudyData:
    study_id: str
    outcome_type: str
    exp_mean: float | None = None
    exp_sd: float | None = None
    exp_n: int | None = None
    ctrl_mean: float | None = None
    ctrl_sd: float | None = None
    ctrl_n: int | None = None
    exp_events: int | None = None
    ctrl_events: int | None = None
    giv_effect: float | None = None
    giv_se: float | None = None
    o_e: float | None = None
    variance: float | None = None


@dataclass(frozen=True)
class StudyEffect:
    study_id: str
    effect: float
    se: float
    variance: float
    weight: float
    ci_low: float
    ci_high: float


def _ci(effect: float, se: float) -> tuple[float, float]:
    z = norm.ppf(0.975)
    return effect - z * se, effect + z * se


def compute_md(data: StudyData) -> StudyEffect:
    assert data.exp_mean is not None and data.ctrl_mean is not None
    assert data.exp_sd is not None and data.ctrl_sd is not None
    assert data.exp_n is not None and data.ctrl_n is not None
    effect = data.exp_mean - data.ctrl_mean
    variance = (data.exp_sd**2 / data.exp_n) + (data.ctrl_sd**2 / data.ctrl_n)
    se = math.sqrt(variance)
    ci_low, ci_high = _ci(effect, se)
    return StudyEffect(data.study_id, effect, se, variance, 1 / variance if variance else 0.0, ci_low, ci_high)


def compute_smd(data: StudyData) -> StudyEffect:
    assert data.exp_mean is not None and data.ctrl_mean is not None
    assert data.exp_sd is not None and data.ctrl_sd is not None
    assert data.exp_n is not None and data.ctrl_n is not None
    pooled_sd = math.sqrt(
        ((data.exp_n - 1) * data.exp_sd**2 + (data.ctrl_n - 1) * data.ctrl_sd**2)
        / (data.exp_n + data.ctrl_n - 2)
    )
    d = (data.exp_mean - data.ctrl_mean) / pooled_sd
    j = 1 - (3 / (4 * (data.exp_n + data.ctrl_n) - 9))
    effect = j * d
    variance = (data.exp_n + data.ctrl_n) / (data.exp_n * data.ctrl_n) + effect**2 / (2 * (data.exp_n + data.ctrl_n - 2))
    se = math.sqrt(variance)
    ci_low, ci_high = _ci(effect, se)
    return StudyEffect(data.study_id, effect, se, variance, 1 / variance if variance else 0.0, ci_low, ci_high)


def compute_log_rr(data: StudyData) -> StudyEffect:
    assert data.exp_events is not None and data.ctrl_events is not None
    assert data.exp_n is not None and data.ctrl_n is not None
    exp_events, exp_n, ctrl_events, ctrl_n = apply_zero_cell_correction(
        data.exp_events, data.exp_n, data.ctrl_events, data.ctrl_n
    )
    risk_e = exp_events / exp_n
    risk_c = ctrl_events / ctrl_n
    effect = math.log(risk_e / risk_c)
    variance = (1 / exp_events) - (1 / exp_n) + (1 / ctrl_events) - (1 / ctrl_n)
    se = math.sqrt(variance)
    ci_low, ci_high = _ci(effect, se)
    return StudyEffect(data.study_id, effect, se, variance, 1 / variance if variance else 0.0, ci_low, ci_high)


def compute_log_or(data: StudyData) -> StudyEffect:
    assert data.exp_events is not None and data.ctrl_events is not None
    assert data.exp_n is not None and data.ctrl_n is not None
    exp_events, exp_n, ctrl_events, ctrl_n = apply_zero_cell_correction(
        data.exp_events, data.exp_n, data.ctrl_events, data.ctrl_n
    )
    exp_non = exp_n - exp_events
    ctrl_non = ctrl_n - ctrl_events
    effect = math.log((exp_events / exp_non) / (ctrl_events / ctrl_non))
    variance = 1 / exp_events + 1 / exp_non + 1 / ctrl_events + 1 / ctrl_non
    se = math.sqrt(variance)
    ci_low, ci_high = _ci(effect, se)
    return StudyEffect(data.study_id, effect, se, variance, 1 / variance if variance else 0.0, ci_low, ci_high)


def compute_generic_iv(data: StudyData) -> StudyEffect:
    assert data.giv_effect is not None and data.giv_se is not None
    variance = data.giv_se**2
    ci_low, ci_high = _ci(data.giv_effect, data.giv_se)
    return StudyEffect(
        data.study_id,
        data.giv_effect,
        data.giv_se,
        variance,
        1 / variance if variance else 0.0,
        ci_low,
        ci_high,
    )
