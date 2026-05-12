"""StatsEngine main class integrating all statistical modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .corrections import apply_zero_cell_correction
from .derivation import (
    ci_to_sd,
    median_iqr_to_mean_sd,
    median_range_to_mean_sd,
    p_to_se,
    se_to_sd,
)
from .effects import (
    StudyData,
    StudyEffect,
    compute_generic_iv,
    compute_log_or,
    compute_log_rr,
    compute_md,
    compute_smd,
)
from .heterogeneity import HeterogeneityResult, compute_heterogeneity
from .pooling import AnalysisModel, PoolingMethod, PooledResult, pool_effects


class EffectMeasure(Enum):
    MD = "Mean Difference"
    SMD = "Standardized Mean Difference (Hedges' g)"
    RR = "Risk Ratio"
    OR = "Odds Ratio"
    HR = "Hazard Ratio"
    GIV = "Generic Inverse Variance"


class DerivationType(Enum):
    CI_TO_SD = "95% CI → SD"
    SE_TO_SD = "SE → SD"
    P_TO_SE = "p-value → SE"
    MEDIAN_IQR_TO_MEAN_SD = "Median + IQR → Mean + SD (Wan 2014)"
    MEDIAN_RANGE_TO_MEAN_SD = "Median + Range → Mean + SD (Hozo 2005)"


@dataclass(frozen=True)
class DerivedFields:
    mean: float | None = None
    sd: float | None = None
    se: float | None = None


class StatsEngine:
    def compute_study_effect(self, data: StudyData, effect_measure: EffectMeasure) -> StudyEffect:
        if effect_measure == EffectMeasure.MD:
            return compute_md(data)
        if effect_measure == EffectMeasure.SMD:
            return compute_smd(data)
        if effect_measure == EffectMeasure.RR:
            return compute_log_rr(data)
        if effect_measure == EffectMeasure.OR:
            return compute_log_or(data)
        if effect_measure == EffectMeasure.GIV or effect_measure == EffectMeasure.HR:
            return compute_generic_iv(data)
        raise ValueError(f"Unsupported effect measure: {effect_measure}")

    def pool_effects(
        self,
        effects: list[StudyEffect],
        method: PoolingMethod,
        model: AnalysisModel,
    ) -> PooledResult:
        return pool_effects(effects, method, model)

    def compute_heterogeneity(
        self,
        effects: list[StudyEffect],
        pooled: PooledResult,
    ) -> HeterogeneityResult:
        return compute_heterogeneity(effects, tau2=pooled.tau2)

    def derive_missing_stats(self, observed: dict, derivation_type: DerivationType) -> DerivedFields:
        if derivation_type == DerivationType.CI_TO_SD:
            return DerivedFields(sd=ci_to_sd(observed["mean"], observed["ci_low"], observed["ci_high"], observed["n"]))
        if derivation_type == DerivationType.SE_TO_SD:
            return DerivedFields(sd=se_to_sd(observed["se"], observed["n"]))
        if derivation_type == DerivationType.P_TO_SE:
            return DerivedFields(se=p_to_se(observed["effect"], observed["p_value"]))
        if derivation_type == DerivationType.MEDIAN_IQR_TO_MEAN_SD:
            mean, sd = median_iqr_to_mean_sd(observed["median"], observed["q1"], observed["q3"], observed["n"])
            return DerivedFields(mean=mean, sd=sd)
        if derivation_type == DerivationType.MEDIAN_RANGE_TO_MEAN_SD:
            mean, sd = median_range_to_mean_sd(
                observed["median"], observed["min"], observed["max"], observed["n"]
            )
            return DerivedFields(mean=mean, sd=sd)
        raise ValueError(f"Unsupported derivation type: {derivation_type}")
