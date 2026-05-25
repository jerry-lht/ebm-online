from __future__ import annotations

import subprocess
import sys


def _run_module_help(module_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module_name, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_inventory_data_help() -> None:
    result = _run_module_help("screening.cli.inventory_data")
    assert result.returncode == 0
    assert "Inventory available screening datasets" in result.stdout
    assert "--dataset" in result.stdout
    assert "--output-dir" in result.stdout


def test_prepare_q2crbench_help() -> None:
    result = _run_module_help("screening.cli.prepare_q2crbench")
    assert result.returncode == 0
    assert "Prepare Q2CRBench-3 examples" in result.stdout
    assert "--source-dataset" in result.stdout
    assert "--settings" in result.stdout


def test_evaluate_predictions_help() -> None:
    result = _run_module_help("screening.cli.evaluate_predictions")
    assert result.returncode == 0
    assert "Evaluate screening predictions" in result.stdout
    assert "--predictions" in result.stdout
    assert "--gold" in result.stdout
    assert "--output" in result.stdout
    assert "--method" in result.stdout
    assert "--run-id" in result.stdout
    assert "--readiness-profile" in result.stdout
    assert "--reference-metrics" in result.stdout


def test_run_direct_llm_help() -> None:
    result = _run_module_help("screening.cli.run_direct_llm")
    assert result.returncode == 0
    assert "Run the direct LLM baseline" in result.stdout
    assert "--examples" in result.stdout
    assert "--provider-config" in result.stdout
    assert "--defaults-config" in result.stdout
    assert "--resume" in result.stdout


def test_run_criterion_wise_help() -> None:
    result = _run_module_help("screening.cli.run_criterion_wise")
    assert result.returncode == 0
    assert "Run the criterion-wise evidence-grounded screening method" in result.stdout
    assert "--examples" in result.stdout
    assert "--criteria-mode" in result.stdout
    assert "fixed_specs" in result.stdout
    assert "hybrid_specs_raw" in result.stdout


def test_run_two_stage_help() -> None:
    result = _run_module_help("screening.cli.run_two_stage")
    assert result.returncode == 0
    assert "Compose abstract-only stage1 predictions" in result.stdout
    assert "--stage1-examples" in result.stdout
    assert "--stage2-predictions" in result.stdout
    assert "--reference-metrics" in result.stdout
