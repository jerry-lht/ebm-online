from __future__ import annotations

import csv

from screening.run_index import update_run_index


def test_update_run_index_upserts_by_run_id(tmp_path) -> None:
    path = tmp_path / "run_index.csv"
    update_run_index(
        path,
        {
            "run_id": "run-1",
            "method": "direct_criteria_aware",
            "benchmark": "csmed_ft",
            "split": "test-small",
            "input_setting": "abstract_only",
            "provider": "openai",
            "model": "gpt-test",
            "prompt_version": "v7",
            "sample_count": 10,
            "success_count": 9,
            "error_count": 1,
            "is_real_llm_run": True,
        },
    )
    update_run_index(
        path,
        {
            "run_id": "run-1",
            "method": "direct_criteria_aware",
            "benchmark": "csmed_ft",
            "split": "test-small",
            "input_setting": "abstract_only",
            "provider": "openai",
            "model": "gpt-test-v2",
            "prompt_version": "v8",
            "sample_count": 10,
            "success_count": 10,
            "error_count": 0,
            "is_real_llm_run": True,
        },
    )

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["model"] == "gpt-test-v2"
    assert rows[0]["success_count"] == "10"
