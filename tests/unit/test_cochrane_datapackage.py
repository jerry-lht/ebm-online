"""Regression tests against a real Cochrane SR datapackage sample."""

from __future__ import annotations

import csv
import io
import math
import zipfile
from pathlib import Path

from ebm_backend.shared.statistics.effects import StudyData, compute_log_or, compute_smd


def _load_rows():
    zip_path = Path("data/Cochrane/original-data/data-package/CD015064-dataPackage.zip")
    with zipfile.ZipFile(zip_path) as z:
        with z.open("CD015064-analysis-data/CD015064-data-rows.csv") as f:
            return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))


def test_continuous_sample_matches_cochrane():
    rows = _load_rows()
    row = next(r for r in rows if r["Analysis number"] == "1" and r["Study"] == "EUCTR2004-002688-25-GB")
    effect = compute_smd(
        StudyData(
            study_id=row["Study"],
            outcome_type="continuous",
            exp_mean=float(row["Experimental mean"]),
            exp_sd=float(row["Experimental SD"]),
            exp_n=int(row["Experimental N"]),
            ctrl_mean=float(row["Control mean"]),
            ctrl_sd=float(row["Control SD"]),
            ctrl_n=int(row["Control N"]),
        )
    )

    assert math.isclose(effect.effect, float(row["Mean"]), abs_tol=1e-4)
    assert math.isclose(effect.ci_low, float(row["CI start"]), abs_tol=1e-4)
    assert math.isclose(effect.ci_high, float(row["CI end"]), abs_tol=1e-4)


def test_binary_sample_matches_cochrane():
    rows = _load_rows()
    row = next(r for r in rows if r["Analysis number"] == "1" and r["Study"] == "Wahn 2002")
    effect = compute_log_or(
        StudyData(
            study_id=row["Study"],
            outcome_type="binary",
            exp_events=int(row["Experimental cases"]),
            exp_n=int(row["Experimental N"]),
            ctrl_events=int(row["Control cases"]),
            ctrl_n=int(row["Control N"]),
        )
    )

    assert math.isclose(math.exp(effect.effect), float(row["Mean"]), abs_tol=1e-4)
    assert math.isclose(math.exp(effect.ci_low), float(row["CI start"]), abs_tol=1e-4)
    assert math.isclose(math.exp(effect.ci_high), float(row["CI end"]), abs_tol=1e-4)
