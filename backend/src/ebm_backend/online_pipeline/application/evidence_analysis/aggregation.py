"""Meta-analysis aggregation and pooling."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ebm_backend.online_pipeline.application.evidence_analysis.models import (
    AggregationResult,
    AnalysisAggregation,
    AnalysisSpec,
    ExtractedDataRow,
    StudyAggregation,
)
from ebm_backend.shared.statistics.effects import StudyData
from ebm_backend.shared.statistics.engine import AnalysisModel, EffectMeasure, StatsEngine
from ebm_backend.shared.statistics.pooling import PoolingMethod


class MetaAnalysisAggregator:
    """Convert extracted rows to StudyData and aggregate with StatsEngine."""

    def __init__(self, stats_engine: StatsEngine | None = None):
        self.stats_engine = stats_engine or StatsEngine()

    def aggregate(self, *, analyses: list[AnalysisSpec], rows: list[ExtractedDataRow]) -> AggregationResult:
        outputs: list[AnalysisAggregation] = []
        warnings: list[str] = []
        by_analysis = {analysis.analysis_id: [] for analysis in analyses}
        for row in rows:
            by_analysis.setdefault(row.analysis_id, []).append(row)

        for analysis in analyses:
            analysis_rows = by_analysis.get(analysis.analysis_id, [])
            study_effects: list[StudyAggregation] = []
            excluded_rows: list[ExtractedDataRow] = []
            valid_effects = []
            for row in analysis_rows:
                if row.extraction_status != "included":
                    excluded_rows.append(row)
                    study_effects.append(
                        StudyAggregation(
                            study_id=row.study_id,
                            analysis_id=row.analysis_id,
                            included=False,
                            excluded_reason=row.missing_reason or row.extraction_status,
                        )
                    )
                    continue
                try:
                    data = self._to_study_data(row)
                    effect = self.stats_engine.compute_study_effect(data, _effect_measure(row.effect_measure))
                    valid_effects.append(effect)
                    study_effects.append(
                        StudyAggregation(
                            study_id=row.study_id,
                            analysis_id=row.analysis_id,
                            included=True,
                            effect=effect.effect,
                            se=effect.se,
                            variance=effect.variance,
                            weight=effect.weight,
                            ci_low=effect.ci_low,
                            ci_high=effect.ci_high,
                        )
                    )
                except Exception as exc:
                    excluded_rows.append(row)
                    reason = f"Could not compute study effect: {exc}"
                    study_effects.append(
                        StudyAggregation(
                            study_id=row.study_id,
                            analysis_id=row.analysis_id,
                            included=False,
                            excluded_reason=reason,
                        )
                    )
            pooled_result: dict[str, Any] | None = None
            heterogeneity: dict[str, Any] | None = None
            local_warnings: list[str] = []
            if valid_effects:
                try:
                    pooled = self.stats_engine.pool_effects(
                        valid_effects,
                        _pooling_method(analysis.pooling_method),
                        _analysis_model(analysis.model),
                    )
                    pooled_result = asdict(pooled)
                    heterogeneity = asdict(self.stats_engine.compute_heterogeneity(valid_effects, pooled))
                except Exception as exc:
                    local_warnings.append(f"Pooling failed for {analysis.analysis_id}: {exc}")
            else:
                local_warnings.append(f"No computable extracted rows for {analysis.analysis_id}.")
            warnings.extend(local_warnings)
            outputs.append(
                AnalysisAggregation(
                    analysis_id=analysis.analysis_id,
                    outcome=analysis.outcome,
                    effect_measure=analysis.effect_measure,
                    study_effects=study_effects,
                    pooled_result=pooled_result,
                    heterogeneity=heterogeneity,
                    excluded_rows=excluded_rows,
                    warnings=local_warnings,
                )
            )
        return AggregationResult(analyses=outputs, warnings=warnings)

    def _to_study_data(self, row: ExtractedDataRow) -> StudyData:
        return StudyData(
            study_id=row.study_id,
            outcome_type=row.outcome_type,
            exp_mean=row.exp_mean,
            exp_sd=row.exp_sd,
            exp_n=row.exp_n,
            ctrl_mean=row.ctrl_mean,
            ctrl_sd=row.ctrl_sd,
            ctrl_n=row.ctrl_n,
            exp_events=row.exp_events,
            ctrl_events=row.ctrl_events,
            giv_effect=row.giv_effect,
            giv_se=row.giv_se,
        )


def _effect_measure(value: str) -> EffectMeasure:
    text = value.upper()
    if text == "MD":
        return EffectMeasure.MD
    if text == "SMD":
        return EffectMeasure.SMD
    if text == "OR":
        return EffectMeasure.OR
    if text == "HR":
        return EffectMeasure.HR
    if text == "GIV":
        return EffectMeasure.GIV
    return EffectMeasure.RR


def _pooling_method(value: str) -> PoolingMethod:
    text = value.upper()
    if text == "MH":
        return PoolingMethod.MH
    if text == "PETO":
        return PoolingMethod.PETO
    return PoolingMethod.IV


def _analysis_model(value: str) -> AnalysisModel:
    text = value.lower()
    if "random" in text:
        return AnalysisModel.RANDOM
    return AnalysisModel.FIXED
