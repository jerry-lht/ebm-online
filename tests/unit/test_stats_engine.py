"""Tests for the Phase 1 stats engine."""

from __future__ import annotations

import math

from ebm_backend.shared.statistics.engine import AnalysisModel, EffectMeasure, StatsEngine
from ebm_backend.shared.statistics.effects import StudyData
from ebm_backend.shared.statistics.pooling import PoolingMethod


def test_compute_md():
    engine = StatsEngine()
    data = StudyData(
        study_id="s1",
        outcome_type="continuous",
        exp_mean=10.0,
        exp_sd=2.0,
        exp_n=50,
        ctrl_mean=8.0,
        ctrl_sd=2.0,
        ctrl_n=50,
    )
    effect = engine.compute_study_effect(data, EffectMeasure.MD)
    assert effect.effect == 2.0
    assert effect.weight > 0


def test_pool_iv_fixed():
    engine = StatsEngine()
    effects = [
        engine.compute_study_effect(
            StudyData(
                study_id="s1",
                outcome_type="continuous",
                exp_mean=10.0,
                exp_sd=2.0,
                exp_n=50,
                ctrl_mean=8.0,
                ctrl_sd=2.0,
                ctrl_n=50,
            ),
            EffectMeasure.MD,
        ),
        engine.compute_study_effect(
            StudyData(
                study_id="s2",
                outcome_type="continuous",
                exp_mean=11.0,
                exp_sd=2.0,
                exp_n=50,
                ctrl_mean=9.0,
                ctrl_sd=2.0,
                ctrl_n=50,
            ),
            EffectMeasure.MD,
        ),
    ]
    pooled = engine.pool_effects(effects, PoolingMethod.IV, AnalysisModel.FIXED)
    assert math.isfinite(pooled.effect)
    assert pooled.study_count == 2


def test_heterogeneity_single_group():
    engine = StatsEngine()
    effect = engine.compute_study_effect(
        StudyData(
            study_id="s1",
            outcome_type="continuous",
            exp_mean=10.0,
            exp_sd=2.0,
            exp_n=50,
            ctrl_mean=8.0,
            ctrl_sd=2.0,
            ctrl_n=50,
        ),
        EffectMeasure.MD,
    )
    pooled = engine.pool_effects([effect], PoolingMethod.IV, AnalysisModel.FIXED)
    heterogeneity = engine.compute_heterogeneity([effect], pooled)
    assert heterogeneity.q == 0.0
    assert heterogeneity.i2 == 0.0
