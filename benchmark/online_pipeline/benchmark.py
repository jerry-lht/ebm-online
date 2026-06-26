"""Unified CLI for online pipeline benchmark build and evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmark.online_pipeline.builders import DEFAULT_SEED, ROOT, build_dataset
from benchmark.online_pipeline.q2pico.evaluation.runner import run_benchmark as run_q2pico
from benchmark.online_pipeline.risk_of_bias.evaluation.runner import run_benchmark as run_risk_of_bias
from benchmark.online_pipeline.shared.report_utils import write_json
from benchmark.online_pipeline.study_pio.evaluation.runner import run_benchmark as run_study_pio
from benchmark.online_pipeline.study_screening.evaluation.runner import run_benchmark as run_study_screening


GRADE_DOMAIN_DIRS = {
    "risk_of_bias": "risk_of_bias_downgrade",
    "risk_of_bias_downgrade": "risk_of_bias_downgrade",
    "inconsistency": "inconsistency",
    "indirectness": "indirectness",
    "imprecision": "imprecision",
}

METRICS_INDEX_FIELDS = [
    "timestamp",
    "run_id",
    "source",
    "dataset_name",
    "split",
    "sample_size",
    "seed",
    "limit",
    "method",
    "judge_mode",
    "completed_count",
    "primary_metric",
    "micro_f1",
    "macro_f1",
    "population_f1",
    "intervention_comparator_f1",
    "outcomes_f1",
    "critical_fields_complete_rate",
    "include_precision",
    "include_recall",
    "include_f1",
    "accuracy",
    "false_negative_count",
    "all_fields_exact",
    "field_completion_rate",
    "subtask2_exact_row_rate",
    "subtask2_numeric_close_rate",
    "subtask3_method_exact_rate",
    "subtask4_subgroup_join_rate",
    "subtask4_estimate_exact_or_close_rate",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and run online pipeline benchmarks.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_build_args(subparsers.add_parser("build"))
    _add_run_args(subparsers.add_parser("run"))
    _add_all_args(subparsers.add_parser("all"))
    _add_index_args(subparsers.add_parser("index"))
    args = parser.parse_args()

    if args.command == "build":
        result = _build_from_args(args)
        print(_format_build_output(result))
    elif args.command == "run":
        result = _run_from_args(args)
        print(result["run_dir"])
    elif args.command == "all":
        build_result = _build_from_args(args)
        result = _run_from_args(args, dataset_dir=_dataset_split_dir(_dataset_root_from_build_result(args, build_result), args.split))
        print(result["run_dir"])
    elif args.command == "index":
        print(_metrics_index_csv_from_args(args))


def _add_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--module", required=True, choices=("q2pico", "study_screening", "study_pio", "risk_of_bias", "meta_analysis", "grade"))
    parser.add_argument("--source", default="builtin_smoke")
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--seed", default=DEFAULT_SEED)


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--module", required=True, choices=("q2pico", "study_screening", "study_pio", "risk_of_bias", "meta_analysis", "grade"))
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--subtask", default=None, help="Required for meta_analysis runs.")
    parser.add_argument("--domain", default=None, help="Required for grade runs.")
    parser.add_argument("--split", default="smoke", choices=("all", "smoke", "dev", "test"))
    parser.add_argument("--method", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--judge-mode", choices=("llm", "normalized"), default="normalized")
    parser.add_argument("--llm-config", default="llm.local.json")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--section-policy", choices=("abstract_only", "abstract_plus_fulltext"), default="abstract_plus_fulltext")
    parser.add_argument("--max-abstract-chars", type=int, default=None)
    parser.add_argument("--max-full-text-chars", type=int, default=12000)


def _add_all_args(parser: argparse.ArgumentParser) -> None:
    _add_build_args(parser)
    parser.add_argument("--subtask", default=None, help="Required for meta_analysis runs.")
    parser.add_argument("--domain", default=None, help="Required for grade runs.")
    parser.add_argument("--split", default="smoke", choices=("all", "smoke", "dev", "test"))
    parser.add_argument("--method", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--judge-mode", choices=("llm", "normalized"), default="normalized")
    parser.add_argument("--llm-config", default="llm.local.json")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--section-policy", choices=("abstract_only", "abstract_plus_fulltext"), default="abstract_plus_fulltext")
    parser.add_argument("--max-abstract-chars", type=int, default=None)
    parser.add_argument("--max-full-text-chars", type=int, default=12000)


def _add_index_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--module", required=True, choices=("q2pico", "study_screening", "study_pio", "risk_of_bias", "meta_analysis", "grade"))
    parser.add_argument("--subtask", default=None, help="Required for meta_analysis indexes.")
    parser.add_argument("--domain", default=None, help="Required for grade indexes.")


def _build_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return build_dataset(
        module=args.module,
        source=args.source,
        dataset_name=args.dataset_name,
        sample_size=args.sample_size,
        seed=args.seed,
        source_url=args.source_url,
    )


def _format_build_output(result: dict[str, Any]) -> str:
    if result.get("dataset_dir"):
        return str(result["dataset_dir"])
    if result.get("dataset_dirs"):
        return json.dumps(result["dataset_dirs"], ensure_ascii=False, sort_keys=True)
    raise ValueError("Build result did not include dataset_dir or dataset_dirs")


def _dataset_root_from_build_result(args: argparse.Namespace, result: dict[str, Any]) -> Path:
    if result.get("dataset_dir"):
        return Path(result["dataset_dir"])
    dataset_dirs = result.get("dataset_dirs") or {}
    if args.module == "meta_analysis":
        if not args.subtask:
            raise ValueError("--subtask is required for meta_analysis all")
        return Path(dataset_dirs[args.subtask])
    if args.module == "grade":
        if not args.domain:
            raise ValueError("--domain is required for grade all")
        return Path(dataset_dirs[_grade_domain_name(args.domain)])
    raise ValueError(f"Build result for {args.module} did not include a runnable dataset_dir")


def _run_from_args(args: argparse.Namespace, dataset_dir: Path | None = None) -> dict[str, Any]:
    dataset_root = _dataset_root_from_args(args)
    dataset = dataset_dir or _dataset_split_dir(dataset_root, args.split)
    if args.module == "q2pico":
        result = run_q2pico(
            dataset=dataset,
            method=args.method,
            run_id=args.run_id,
            judge_mode=args.judge_mode,
            llm_config=args.llm_config,
            limit=args.limit,
            resume=args.resume,
            workers=args.workers,
        )
    elif args.module == "study_screening":
        result = run_study_screening(
            dataset=dataset,
            method=args.method,
            run_id=args.run_id,
            limit=args.limit,
            section_policy=args.section_policy,
            max_abstract_chars=args.max_abstract_chars,
            max_full_text_chars=args.max_full_text_chars,
        )
    elif args.module == "study_pio":
        result = run_study_pio(
            dataset=dataset,
            method=args.method,
            run_id=args.run_id,
            limit=args.limit,
            judge_mode=args.judge_mode,
            llm_config=args.llm_config,
            resume=args.resume,
            workers=args.workers,
        )
    elif args.module == "risk_of_bias":
        result = run_risk_of_bias(
            dataset=dataset,
            method=args.method,
            run_id=args.run_id,
            limit=args.limit,
            llm_config=args.llm_config,
            resume=args.resume,
            workers=args.workers,
        )
    elif args.module == "meta_analysis":
        run_meta_analysis = _load_meta_analysis_runner(args.subtask)
        kwargs: dict[str, Any] = {
            "dataset": dataset,
            "method": args.method,
            "run_id": args.run_id,
            "limit": args.limit,
        }
        if args.subtask == "subtask2_study_results":
            kwargs["llm_config"] = args.llm_config
        result = run_meta_analysis(
            **kwargs,
        )
    elif args.module == "grade":
        run_grade = _load_grade_runner(args.domain)

        result = run_grade(
            dataset=dataset,
            method=args.method,
            run_id=args.run_id,
            limit=args.limit,
        )
    else:
        raise ValueError(f"Unsupported module: {args.module}")
    if args.module in {"risk_of_bias", "meta_analysis", "grade"}:
        return result
    index_row = _index_row(args=args, dataset=dataset, result=result)
    _append_metrics_index(index_row)
    write_json(Path(result["run_dir"]) / "metrics_index_row.json", index_row)
    return result


def _index_row(*, args: argparse.Namespace, dataset: Path, result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    dataset_root = _dataset_root_from_split(dataset)
    source_manifest = _read_optional_json(dataset_root / "source_manifest.json")
    split = getattr(args, "split", "smoke")
    if args.module == "q2pico":
        primary_metric = metrics.get("micro_f1")
    elif args.module == "study_pio":
        primary_metric = metrics.get("macro_f1")
    elif args.module == "study_screening":
        primary_metric = metrics.get("include_f1")
    elif args.module == "meta_analysis":
        primary_metric = metrics.get("subtask2_numeric_close_rate")
    else:
        primary_metric = metrics.get("domain_macro_f1")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": args.module,
        "source": getattr(args, "source", source_manifest.get("source", "")),
        "dataset_name": args.dataset_name,
        "split": split,
        "sample_size": _split_sample_size(dataset_root=dataset_root, split=split, dataset=dataset),
        "seed": getattr(args, "seed", _read_optional_json(dataset_root / "build_manifest.json").get("seed", "")),
        "run_id": args.run_id,
        "method": args.method,
        "judge_mode": getattr(args, "judge_mode", ""),
        "limit": args.limit,
        "completed_count": metrics.get("instance_count", ""),
        "primary_metric": primary_metric,
        "micro_f1": metrics.get("micro_f1", ""),
        "macro_f1": metrics.get("macro_f1", ""),
        "population_f1": metrics.get("population_f1", ""),
        "intervention_comparator_f1": metrics.get("intervention_comparator_f1", ""),
        "outcomes_f1": metrics.get("outcomes_f1", ""),
        "critical_fields_complete_rate": metrics.get("critical_fields_complete_rate", ""),
        "include_precision": metrics.get("include_precision", ""),
        "include_recall": metrics.get("include_recall", ""),
        "include_f1": metrics.get("include_f1", ""),
        "accuracy": metrics.get("accuracy", ""),
        "false_negative_count": metrics.get("false_negative_count", ""),
        "all_fields_exact": metrics.get("all_fields_exact", ""),
        "field_completion_rate": metrics.get("field_completion_rate", ""),
        "high_risk_recall": metrics.get("high_risk_recall", ""),
        "domain_macro_f1": metrics.get("domain_macro_f1", ""),
        "domain_coverage_rate": metrics.get("domain_coverage_rate", ""),
        "subtask2_exact_row_rate": metrics.get("subtask2_exact_row_rate", ""),
        "subtask2_numeric_close_rate": metrics.get("subtask2_numeric_close_rate", ""),
        "subtask3_method_exact_rate": metrics.get("subtask3_method_exact_rate", ""),
        "subtask4_subgroup_join_rate": metrics.get("subtask4_subgroup_join_rate", ""),
        "subtask4_estimate_exact_or_close_rate": metrics.get("subtask4_estimate_exact_or_close_rate", ""),
    }


def _append_metrics_index(row: dict[str, Any]) -> None:
    module = str(row.get("module") or "")
    index_csv = _module_metrics_index_csv(module)
    index_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = [_compact_index_row(existing) for existing in _read_metrics_index_rows(module)]
    key = _metrics_row_key(row, module=module)
    rows = [existing for existing in rows if _metrics_row_key(existing, module=module) != key]
    rows.append(_compact_index_row(row))
    fieldnames = [field for field in METRICS_INDEX_FIELDS if any(field in item for item in rows)]
    with index_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_metrics_index_rows(module: str) -> list[dict[str, Any]]:
    module_index = _module_metrics_index_csv(module)
    if not module_index.exists():
        return []
    rows: list[dict[str, Any]] = []
    with module_index.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["module"] = module
            rows.append(row)
    return rows


def _compact_index_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field, "") for field in METRICS_INDEX_FIELDS if field in row}


def _metrics_row_key(row: dict[str, Any], *, module: str | None = None) -> tuple[str, str, str, str]:
    return (
        str(row.get("module") or module or ""),
        str(row.get("dataset_name") or ""),
        str(row.get("split") or ""),
        str(row.get("run_id") or ""),
    )


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _split_sample_size(*, dataset_root: Path, split: str, dataset: Path) -> Any:
    split_manifest = _read_optional_json(dataset_root / "split_manifest.json")
    split_info = (split_manifest.get("splits") or {}).get(split)
    if isinstance(split_info, dict) and "count" in split_info:
        return split_info["count"]
    instances_path = dataset / "instances.jsonl"
    if instances_path.exists():
        return sum(1 for line in instances_path.read_text(encoding="utf-8").splitlines() if line.strip())
    return ""


def _dataset_split_dir(dataset_root: Path, split: str) -> Path:
    if split == "all":
        return dataset_root
    return dataset_root / "splits" / split


def _dataset_root_from_args(args: argparse.Namespace) -> Path:
    if args.module == "meta_analysis":
        if not args.subtask:
            raise ValueError("--subtask is required for meta_analysis runs")
        return ROOT / "meta_analysis" / args.subtask / "datasets" / args.dataset_name
    if args.module == "grade":
        if not args.domain:
            raise ValueError("--domain is required for grade runs")
        return ROOT / "grade" / _grade_domain_dir(args.domain) / "datasets" / args.dataset_name
    return ROOT / args.module / "datasets" / args.dataset_name


def _load_meta_analysis_runner(subtask: str | None) -> Any:
    if subtask == "subtask2_study_results":
        from benchmark.online_pipeline.meta_analysis.subtask2_study_results.evaluation.runner import run_benchmark
    elif subtask == "subtask3_analysis_methods":
        from benchmark.online_pipeline.meta_analysis.subtask3_analysis_methods.evaluation.runner import run_benchmark
    elif subtask == "subtask4_subgroup_analysis":
        from benchmark.online_pipeline.meta_analysis.subtask4_subgroup_analysis.evaluation.runner import run_benchmark
    elif subtask == "subtask5_overall_estimates":
        from benchmark.online_pipeline.meta_analysis.subtask5_overall_estimates.evaluation.runner import run_benchmark
    else:
        raise ValueError(f"Unsupported meta_analysis subtask: {subtask}")
    return run_benchmark


def _load_grade_runner(domain: str | None) -> Any:
    normalized = _grade_domain_name(domain)
    if normalized == "risk_of_bias":
        from benchmark.online_pipeline.grade.risk_of_bias_downgrade.evaluation.runner import run_benchmark
    elif normalized == "inconsistency":
        from benchmark.online_pipeline.grade.inconsistency.evaluation.runner import run_benchmark
    elif normalized == "indirectness":
        from benchmark.online_pipeline.grade.indirectness.evaluation.runner import run_benchmark
    elif normalized == "imprecision":
        from benchmark.online_pipeline.grade.imprecision.evaluation.runner import run_benchmark
    else:
        raise ValueError(f"Unsupported grade domain: {domain}")
    return run_benchmark


def _dataset_root_from_split(dataset: Path) -> Path:
    if dataset.parent.name == "splits":
        return dataset.parent.parent
    return dataset


def _module_metrics_index_csv(module: str) -> Path:
    return ROOT / module / "runs" / "metrics_index.csv"


def _metrics_index_csv_from_args(args: argparse.Namespace) -> Path:
    if args.module == "meta_analysis":
        if not args.subtask:
            raise ValueError("--subtask is required for meta_analysis indexes")
        return ROOT / "meta_analysis" / args.subtask / "runs" / "metrics_index.csv"
    if args.module == "grade":
        if not args.domain:
            raise ValueError("--domain is required for grade indexes")
        return ROOT / "grade" / _grade_domain_dir(args.domain) / "runs" / "metrics_index.csv"
    return _module_metrics_index_csv(args.module)


def _grade_domain_name(domain: str | None) -> str:
    if domain == "risk_of_bias_downgrade":
        return "risk_of_bias"
    if domain in {"risk_of_bias", "inconsistency", "indirectness", "imprecision"}:
        return str(domain)
    raise ValueError(f"Unsupported grade domain: {domain}")


def _grade_domain_dir(domain: str | None) -> str:
    normalized = _grade_domain_name(domain)
    return GRADE_DOMAIN_DIRS[normalized]


if __name__ == "__main__":
    main()
