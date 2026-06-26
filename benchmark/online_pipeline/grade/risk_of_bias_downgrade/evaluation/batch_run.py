"""Batch runner and error analysis for the GRADE risk-of-bias domain."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from benchmark.online_pipeline.grade.risk_of_bias_downgrade.evaluation.runner import run_benchmark
from benchmark.online_pipeline.shared.jsonl import read_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json


DOMAIN_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = DOMAIN_DIR / "datasets" / "grade_v3"
DEFAULT_RUNS_ROOT = DOMAIN_DIR / "runs"
FIELDS = ("downgraded", "severity", "levels", "level_evaluable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run and summarize GRADE risk-of-bias benchmark batches.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET_ROOT))
    parser.add_argument("--split", default="dev", choices=("all", "smoke", "dev", "test"))
    parser.add_argument("--method", default="method_test")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--run-id-prefix", default="grade-rob-downgrade-batch")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--llm-config", default=None, help="Recorded for LLM-backed methods; method_test does not consume it.")
    parser.add_argument("--skip-gold", action="store_true", help="Skip the gold plumbing check.")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    dataset = dataset_root if args.split == "all" else dataset_root / "splits" / args.split
    _assert_real_jsonl(dataset / "instances.jsonl")
    _assert_real_jsonl(dataset / "gold.jsonl")
    llm_config_info = _llm_config_info(args.llm_config)
    if args.llm_config:
        os.environ["LLM_CONFIG_PATH"] = str(Path(args.llm_config).resolve())

    gold_result = None
    if not args.skip_gold:
        gold_result = run_benchmark(
            dataset=dataset,
            method="gold",
            run_id=f"{args.run_id_prefix}-gold-{_sample_suffix(args.split, args.offset, args.limit)}",
            runs_root=args.runs_root,
            offset=args.offset,
            limit=args.limit,
        )

    method_result = run_benchmark(
        dataset=dataset,
        method=args.method,
        run_id=f"{args.run_id_prefix}-{_slug(args.method)}-{_sample_suffix(args.split, args.offset, args.limit)}",
        runs_root=args.runs_root,
        offset=args.offset,
        limit=args.limit,
    )
    run_dir = Path(method_result["run_dir"])
    analysis = analyze_run(run_dir=run_dir, dataset=dataset, offset=args.offset, limit=args.limit)
    summary = {
        "dataset": str(dataset),
        "split": args.split,
        "offset": args.offset,
        "limit": args.limit,
        "method": args.method,
        "method_run_dir": str(run_dir),
        "gold_run_dir": gold_result["run_dir"] if gold_result else None,
        "gold_metrics": gold_result["metrics"] if gold_result else None,
        "method_metrics": method_result["metrics"],
        "llm_config": llm_config_info,
        "analysis": analysis,
    }
    write_json(run_dir / "batch_summary.json", summary)
    _write_markdown(run_dir / "batch_summary.md", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def analyze_run(*, run_dir: Path, dataset: Path, offset: int = 0, limit: int | None = None) -> dict[str, Any]:
    comparisons = read_jsonl(run_dir / "comparisons.jsonl")
    predictions = read_jsonl(run_dir / "predictions.jsonl")
    gold_rows = read_jsonl(dataset / "gold.jsonl")
    if offset or limit is not None:
        start = max(0, int(offset or 0))
        stop = None if limit is None else start + max(0, int(limit))
        gold_rows = gold_rows[start:stop]

    mismatches = [row for row in comparisons if not row.get("exact_match")]
    by_instance: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comparisons:
        by_instance[str(row.get("instance_id") or "")].append(row)
    failed_instances = [
        instance_id
        for instance_id, rows in by_instance.items()
        if not all(bool(row.get("exact_match")) for row in rows)
    ]

    return {
        "mismatch_count_by_field": dict(Counter(str(row.get("field") or "") for row in mismatches)),
        "confusions_by_field": _confusions(comparisons),
        "gold_distribution": _judgement_distribution([row.get("judgement") or {} for row in gold_rows]),
        "prediction_distribution": _judgement_distribution([_prediction_judgement(row) for row in predictions]),
        "failed_instance_count": len(failed_instances),
        "failed_instance_examples": _failed_examples(failed_instances, by_instance, limit=20),
    }


def _confusions(comparisons: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for field in FIELDS:
        pairs = Counter(
            f"gold={row.get('gold')!r} -> pred={row.get('prediction')!r}"
            for row in comparisons
            if row.get("field") == field and not row.get("exact_match")
        )
        result[field] = dict(pairs.most_common())
    return result


def _judgement_distribution(judgements: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        field: dict(Counter(str(row.get(field)) for row in judgements))
        for field in ("downgraded", "severity", "levels", "level_evaluable")
    }


def _failed_examples(
    failed_instances: list[str],
    by_instance: dict[str, list[dict[str, Any]]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    examples = []
    for instance_id in failed_instances[:limit]:
        rows = [
            {
                "field": row.get("field"),
                "gold": row.get("gold"),
                "prediction": row.get("prediction"),
            }
            for row in by_instance[instance_id]
            if not row.get("exact_match")
        ]
        examples.append({"instance_id": instance_id, "mismatches": rows})
    return examples


def _prediction_judgement(prediction: dict[str, Any]) -> dict[str, Any]:
    if isinstance(prediction.get("judgement"), dict):
        return prediction["judgement"]
    payload = prediction.get("prediction")
    if isinstance(payload, dict) and isinstance(payload.get("judgement"), dict):
        return payload["judgement"]
    return {}


def _llm_config_info(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "status": "not_requested"}
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    if not resolved.exists():
        return {"path": str(resolved), "status": "missing"}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(resolved), "status": "invalid_json", "error": str(exc)}
    return {
        "path": str(resolved),
        "status": "loaded",
        "model": payload.get("model") or payload.get("model_id"),
        "base_url": payload.get("base_url"),
        "api_mode": payload.get("api_mode") or payload.get("mode"),
    }


def _assert_real_jsonl(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    head = path.read_text(encoding="utf-8", errors="replace")[:128]
    if head.startswith("version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            f"{path} is still a Git LFS pointer. Run: git lfs pull --include=\"benchmark/online_pipeline/grade/risk_of_bias_downgrade/**\""
        )


def _write_markdown(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary["method_metrics"]
    analysis = summary["analysis"]
    lines = [
        "# GRADE Risk-of-Bias Downgrade Batch Summary",
        "",
        f"- method: {summary['method']}",
        f"- dataset: {summary['dataset']}",
        f"- offset: {summary['offset']}",
        f"- limit: {summary['limit']}",
        f"- run_dir: {summary['method_run_dir']}",
        "",
        "## Metrics",
        "",
    ]
    for key in (
        "instance_count",
        "judgement_join_rate",
        "downgraded_exact_rate",
        "severity_exact_rate",
        "levels_exact_rate",
        "evaluable_exact_rate",
        "all_fields_exact_rate",
    ):
        value = metrics.get(key)
        display = f"{value:.4f}" if isinstance(value, float) else str(value)
        lines.append(f"- {key}: {display}")
    lines.extend(["", "## Mismatches", ""])
    for field, count in analysis["mismatch_count_by_field"].items():
        lines.append(f"- {field}: {count}")
    lines.extend(["", "## Top Confusions", ""])
    for field in FIELDS:
        lines.append(f"### {field}")
        confusions = analysis["confusions_by_field"].get(field) or {}
        if not confusions:
            lines.append("- none")
            continue
        for label, count in list(confusions.items())[:10]:
            lines.append(f"- {label}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value).strip("-").lower() or "method"


def _sample_suffix(split: str, offset: int, limit: int | None) -> str:
    limit_label = "all" if limit is None else str(limit)
    if offset:
        return f"{split}-offset-{offset}-limit-{limit_label}"
    return f"{split}-{limit_label}"


if __name__ == "__main__":
    main()
