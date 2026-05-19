"""CLI for preparing Q2CRBench-3 screening examples."""

from __future__ import annotations

import argparse

from screening.datasets.q2crbench import (
    DEFAULT_SOURCE_DATASET,
    SETTINGS,
    prepare_q2crbench,
    write_q2crbench_artifacts,
)
from screening.paths import data_root, results_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.prepare_q2crbench",
        description="Prepare Q2CRBench-3 examples and data quality artifacts.",
    )
    parser.add_argument(
        "--data-root",
        default=str(data_root),
        help="Root directory containing the Q2CRBench-3 folder. Defaults to results/../data.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(results_root),
        help="Directory for prepared artifacts. Defaults to results.",
    )
    parser.add_argument(
        "--source-dataset",
        default=DEFAULT_SOURCE_DATASET,
        help=f"Q2CRBench source dataset to prepare. Defaults to {DEFAULT_SOURCE_DATASET}.",
    )
    parser.add_argument(
        "--settings",
        default=",".join(SETTINGS),
        help="Comma-separated settings to generate: abstract_only,evidence_profile.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing Q2CRBench artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = tuple(part.strip() for part in args.settings.split(",") if part.strip())

    prepared = prepare_q2crbench(
        args.data_root,
        source_dataset=args.source_dataset,
        settings=settings,
    )
    artifacts = write_q2crbench_artifacts(prepared, args.output_dir, force=args.force)

    print(f"Prepared Q2CRBench source dataset: {prepared.source_dataset}")
    print(f"abstract_only examples: {len(prepared.abstract_only_examples)}")
    print(f"evidence_profile examples: {len(prepared.evidence_profile_examples)}")
    for name, path in artifacts.__dict__.items():
        if path:
            print(f"{name}: {path}")
    blockers = prepared.data_quality.get("blockers", [])
    if blockers:
        print(f"Dataset-level blockers: {len(blockers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
