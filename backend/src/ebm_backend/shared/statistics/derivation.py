"""Statistical derivation: CI->SD, SE->SD, p->SE, median/IQR->mean/SD."""

from __future__ import annotations

import math

from scipy.stats import norm


def ci_to_sd(mean: float, ci_low: float, ci_high: float, n: int, confidence: float = 0.95) -> float:
    z = norm.ppf(1 - (1 - confidence) / 2)
    se = (ci_high - ci_low) / (2 * z)
    return se * math.sqrt(n)


def se_to_sd(se: float, n: int) -> float:
    return se * math.sqrt(n)


def p_to_se(effect: float, p_value: float) -> float:
    p_value = max(min(p_value, 1 - 1e-16), 1e-16)
    z = norm.ppf(1 - p_value / 2)
    return abs(effect) / z if z else float("inf")


def median_iqr_to_mean_sd(median: float, q1: float, q3: float, n: int) -> tuple[float, float]:
    mean = median
    sd = (q3 - q1) / 1.35 if q3 >= q1 else 0.0
    return mean, sd


def median_range_to_mean_sd(median: float, min_value: float, max_value: float, n: int) -> tuple[float, float]:
    mean = median
    sd = (max_value - min_value) / 4 if max_value >= min_value else 0.0
    return mean, sd
