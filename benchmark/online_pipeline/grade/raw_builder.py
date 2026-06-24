"""CLI for freezing and building the GRADE benchmark raw data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmark.online_pipeline.grade.builder import (
    DEFAULT_SEED,
    DEFAULT_V2_REVIEWS,
    MODULE,
    SOURCE_V2,
    SOURCE_V3,
    build_alignment_v3,
    build_alignment_v2,
    build_dataset_v3,
    build_dataset_v2,
    freeze_raw_snapshot,
)
from benchmark.online_pipeline.q2pico.evaluation.judge import load_llm_config
from benchmark.online_pipeline.shared.building import RAW_DATA_DIR
from benchmark.online_pipeline.shared.analysis_settings.builder import (
    DEFAULT_OUTPUT_ROOT as DEFAULT_SHARED_SETTING_ROOT,
    build_grade_required_settings,
)


DEFAULT_RAW_ROOT = RAW_DATA_DIR / MODULE
DEFAULT_DATASET_NAME = SOURCE_V3


def _format_dataset_result(result: dict[str, object]) -> str:
    return str(result.get("dataset_dir") or result.get("dataset_dirs"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GRADE raw data and benchmark datasets.")
    parser.add_argument(
        "command",
        choices=(
            "freeze-source",
            "build-shared-settings",
            "build-alignment-v2",
            "build-dataset-v2",
            "all-v2",
            "smoke-v2",
            "build-alignment-v3",
            "build-dataset-v3",
            "all-v3",
            "smoke-v3",
            "report",
        ),
    )
    parser.add_argument("--raw-root", default=str(DEFAULT_RAW_ROOT))
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--config", default=None, help="Deprecated alias for --llm-config.")
    parser.add_argument("--llm-config", default=None, help="JSON config with api_key, base_url, model, and optional API settings.")
    parser.add_argument("--shared-settings-root", default=str(DEFAULT_SHARED_SETTING_ROOT))
    parser.add_argument("--reviews", nargs="*", default=None)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default="https://api.openai.com")
    parser.add_argument("--api-mode", choices=("responses", "chat"), default=None)
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--alignment-name", default="alignment_v3")
    parser.add_argument("--setting-limit", type=int, default=None)
    parser.add_argument("--max-setting-failures", type=int, default=50)
    parser.add_argument("--limit-tables", type=int, default=None)
    parser.add_argument("--limit-rows", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    raw_root = Path(args.raw_root)
    llm_config_path = args.llm_config or args.config
    llm_config = _load_llm_config(llm_config_path)
    api_key = args.api_key or llm_config.get("api_key")
    base_url = args.base_url if args.base_url != "https://api.openai.com" else llm_config.get("base_url", args.base_url)
    model = args.model if args.model != "gpt-4.1-mini" else llm_config.get("model", args.model)
    api_mode = args.api_mode or llm_config.get("api_mode", "responses")
    if args.command in {"build-alignment-v3", "all-v3"} and args.alignment_name == "alignment_v3" and not args.use_llm:
        raise RuntimeError(
            "alignment_v3 is the formal grade_v4 alignment and requires --use-llm. "
            "For structural dry-run smoke, pass a non-default --alignment-name."
        )
    if args.command == "freeze-source":
        freeze_raw_snapshot(raw_root=raw_root)
        print(raw_root / "source_manifest.json")
    elif args.command == "build-shared-settings":
        build_grade_required_settings(
            output_root=Path(args.shared_settings_root),
            meta_raw_root=RAW_DATA_DIR / "meta_analysis",
            grade_raw_root=raw_root,
            llm_config=llm_config_path,
            use_llm=args.use_llm,
            workers=args.workers,
            resume=args.resume,
            reviews=args.reviews,
            limit=args.setting_limit,
            max_failures=args.max_setting_failures,
        )
        print(Path(args.shared_settings_root) / "cleaning_report.json")
    elif args.command == "build-alignment-v2":
        summary = build_alignment_v2(
            raw_root=raw_root,
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
        )
        print(raw_root / "intermediate" / "alignment_v2" / "alignment_summary.json")
        print(summary)
    elif args.command == "build-dataset-v2":
        result = build_dataset_v2(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else SOURCE_V2,
            raw_root=raw_root,
            sample_size=args.sample_size,
            seed=args.seed,
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
        )
        print(_format_dataset_result(result))
    elif args.command == "build-alignment-v3":
        summary = build_alignment_v3(
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
            alignment_name=args.alignment_name,
        )
        print(raw_root / "intermediate" / args.alignment_name / "alignment_summary.json")
        print(summary)
    elif args.command == "build-dataset-v3":
        result = build_dataset_v3(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else SOURCE_V3,
            source=SOURCE_V3,
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            sample_size=args.sample_size,
            seed=args.seed,
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
            alignment_name=args.alignment_name,
        )
        print(_format_dataset_result(result))
    elif args.command == "all-v2":
        freeze_raw_snapshot(raw_root=raw_root)
        build_alignment_v2(
            raw_root=raw_root,
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
        )
        result = build_dataset_v2(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else SOURCE_V2,
            raw_root=raw_root,
            sample_size=args.sample_size,
            seed=args.seed,
        )
        print(_format_dataset_result(result))
    elif args.command == "smoke-v2":
        freeze_raw_snapshot(raw_root=raw_root)
        build_alignment_v2(
            raw_root=raw_root,
            reviews=args.reviews or list(DEFAULT_V2_REVIEWS),
            use_llm=True,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables if args.limit_tables is not None else 3,
            limit_rows=args.limit_rows if args.limit_rows is not None else 12,
            timeout=args.timeout,
            retries=args.retries,
        )
        result = build_dataset_v2(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else "grade_v2_smoke",
            raw_root=raw_root,
            sample_size=args.sample_size,
            seed=args.seed,
        )
        print(_format_dataset_result(result))
    elif args.command == "all-v3":
        freeze_raw_snapshot(raw_root=raw_root)
        build_grade_required_settings(
            output_root=Path(args.shared_settings_root),
            meta_raw_root=RAW_DATA_DIR / "meta_analysis",
            grade_raw_root=raw_root,
            llm_config=llm_config_path,
            use_llm=args.use_llm,
            workers=args.workers,
            resume=args.resume,
            reviews=args.reviews,
            limit=args.setting_limit,
            max_failures=args.max_setting_failures,
        )
        build_alignment_v3(
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            reviews=args.reviews,
            use_llm=args.use_llm,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables,
            limit_rows=args.limit_rows,
            timeout=args.timeout,
            retries=args.retries,
            alignment_name=args.alignment_name,
        )
        result = build_dataset_v3(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else SOURCE_V3,
            source=SOURCE_V3,
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            sample_size=args.sample_size,
            seed=args.seed,
            alignment_name=args.alignment_name,
        )
        print(_format_dataset_result(result))
    elif args.command == "smoke-v3":
        smoke_reviews = args.reviews or ["CD000031", "CD014498", "CD013830"]
        freeze_raw_snapshot(raw_root=raw_root)
        build_grade_required_settings(
            output_root=Path(args.shared_settings_root),
            meta_raw_root=RAW_DATA_DIR / "meta_analysis",
            grade_raw_root=raw_root,
            llm_config=llm_config_path,
            use_llm=True,
            workers=args.workers,
            resume=True,
            reviews=smoke_reviews,
            limit=args.setting_limit,
            max_failures=args.max_setting_failures,
        )
        build_alignment_v3(
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            reviews=smoke_reviews,
            use_llm=True,
            api_key=api_key,
            base_url=base_url,
            api_mode=api_mode,
            model=model,
            workers=args.workers,
            resume=args.resume,
            limit_tables=args.limit_tables if args.limit_tables is not None else 3,
            limit_rows=args.limit_rows if args.limit_rows is not None else 12,
            timeout=args.timeout,
            retries=args.retries,
            alignment_name=args.alignment_name,
        )
        result = build_dataset_v3(
            dataset_name=args.dataset_name if args.dataset_name != DEFAULT_DATASET_NAME else "grade_v4_smoke",
            source=SOURCE_V3,
            raw_root=raw_root,
            shared_settings_root=Path(args.shared_settings_root),
            sample_size=args.sample_size,
            seed=args.seed,
            alignment_name=args.alignment_name,
        )
        print(_format_dataset_result(result))
    else:
        report_path = raw_root / "intermediate" / args.alignment_name / "alignment_summary.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Missing alignment report: {report_path}")
        print(report_path)


def _load_llm_config(path: str | None) -> dict[str, str]:
    resolved = path or "llm.local.json"
    if not Path(resolved).exists() and not path:
        return {}
    return load_llm_config(resolved)


if __name__ == "__main__":
    main()
