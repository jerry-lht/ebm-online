"""LLM-assisted study result extraction for Meta Analysis Subtask 2."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from ebm_backend.online_pipeline.infrastructure.llm import call_llm_json
from benchmark.online_pipeline.meta_analysis.evaluation_common.article_store import load_articles_for_instance
from benchmark.online_pipeline.meta_analysis.evaluation_common.io import load_dataset
from benchmark.online_pipeline.q2pico.evaluation.judge import load_llm_config
from benchmark.online_pipeline.shared.jsonl import append_jsonl, read_jsonl, write_jsonl
from benchmark.online_pipeline.shared.prompts import render_prompt_template


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
EXTRACTION_PROMPT = PROMPT_DIR / "study_result_extraction_v1.txt"


def run_llm_extraction(
    *,
    dataset: str | Path,
    llm_config: str | Path,
    output_path: str | Path,
    failure_output_path: str | Path,
    limit: int | None = None,
    workers: int = 1,
    resume: bool = False,
) -> list[dict[str, Any]]:
    if workers <= 0:
        raise ValueError("workers must be positive")
    instances, _ = load_dataset(dataset)
    if limit is not None:
        instances = instances[:limit]
    config = load_llm_config(llm_config)
    existing_rows = _completed_rows(output_path) if resume else []
    completed = {str(row.get("instance_id") or "") for row in existing_rows}
    if resume:
        write_jsonl(output_path, existing_rows, sort_keys=False)
    else:
        Path(output_path).unlink(missing_ok=True)
        Path(failure_output_path).unlink(missing_ok=True)
    pending = [instance for instance in instances if str(instance["instance_id"]) not in completed]
    rows = list(existing_rows)

    def extract_one(instance: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "instance_id": instance["instance_id"],
            "review_id": instance.get("review_id"),
            "analysis_setting": instance.get("analysis_setting"),
            "included_studies": instance.get("included_studies") or [],
            "article_study_links": instance.get("article_study_links") or [],
            "articles": load_articles_for_instance(dataset_dir=dataset, instance=instance),
        }
        prompt = render_prompt_template(EXTRACTION_PROMPT, {"input_json": json.dumps(payload, ensure_ascii=False)})
        parsed = _call_llm_json(config=config, prompt=prompt)
        return _coerce_prediction(instance=instance, parsed=parsed)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, max(1, len(pending)))) as executor:
        future_to_instance = {executor.submit(extract_one, instance): str(instance["instance_id"]) for instance in pending}
        for future in concurrent.futures.as_completed(future_to_instance):
            instance_id = future_to_instance[future]
            try:
                row = future.result()
            except Exception as exc:
                append_jsonl(
                    failure_output_path,
                    [{"instance_id": instance_id, "error_type": type(exc).__name__, "message": str(exc)}],
                    sort_keys=False,
                )
                continue
            rows.append(row)
            append_jsonl(output_path, [row], sort_keys=False)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--llm-config", default="llm.local.json")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--failure-output-path", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run_llm_extraction(
        dataset=args.dataset,
        llm_config=args.llm_config,
        output_path=args.output_path,
        failure_output_path=args.failure_output_path,
        limit=args.limit,
        workers=args.workers,
        resume=args.resume,
    )
    print(args.output_path)


def _completed_rows(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path)
    if not resolved.exists():
        return []
    return read_jsonl(resolved)


def _coerce_prediction(*, instance: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    setting = instance.get("analysis_setting") or {}
    comparison = setting.get("comparison") or {}
    outcome = setting.get("outcome") or {}
    subgroup = setting.get("subgroup") or {}
    data_type = setting.get("data_type")
    rows = []
    for item in parsed.get("study_result_rows") or []:
        if not isinstance(item, dict):
            continue
        result_data = item.get("result_data") if isinstance(item.get("result_data"), dict) else {}
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        if data_type == "Dichotomous":
            coerced = {
                "experimental_events": _optional_int(result_data.get("experimental_events")),
                "experimental_total": _optional_int(result_data.get("experimental_total")),
                "control_events": _optional_int(result_data.get("control_events")),
                "control_total": _optional_int(result_data.get("control_total")),
            }
        else:
            coerced = {
                "experimental_mean": _optional_float(result_data.get("experimental_mean")),
                "experimental_sd": _optional_float(result_data.get("experimental_sd")),
                "experimental_total": _optional_int(result_data.get("experimental_total")),
                "control_mean": _optional_float(result_data.get("control_mean")),
                "control_sd": _optional_float(result_data.get("control_sd")),
                "control_total": _optional_int(result_data.get("control_total")),
            }
        if any(value is None for value in coerced.values()):
            continue
        study_id = str(item.get("study_id") or "")
        if not study_id:
            continue
        rows.append(
            {
                "row_id": f"llm-row::{instance['instance_id']}::{_slug(study_id)}",
                "setting_id": setting.get("setting_id"),
                "study_id": study_id,
                "study_year": _nullable_text(item.get("study_year")),
                "footnote": None,
                "extraction_status": "extracted",
                "data_type": data_type,
                "comparison": {
                    "experimental_arm": comparison.get("experimental"),
                    "control_arm": comparison.get("comparator"),
                },
                "outcome": {
                    "label": outcome.get("label"),
                    "timepoint": (setting.get("timepoint") or {}).get("label"),
                },
                "subgroup": subgroup,
                "result_data": coerced,
                "source": {
                    "method": "study_results_llm_extract_v1",
                    "article_id": _nullable_text(source.get("article_id")),
                    "table_id": _nullable_text(source.get("table_id")),
                    "reason": _nullable_text(source.get("reason")),
                },
            }
        )
    return {
        "instance_id": instance["instance_id"],
        "review_id": instance.get("review_id"),
        "study_result_rows": rows,
        "warnings": [str(item) for item in parsed.get("warnings") or []],
    }


def _call_llm_json(*, config: dict[str, str], prompt: str) -> dict[str, Any]:
    return call_llm_json(
        config=config,
        system="You are a strict study-result extractor. Return only valid JSON.",
        prompt=prompt,
    )


def _optional_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return cleaned or "study"


if __name__ == "__main__":
    main()
