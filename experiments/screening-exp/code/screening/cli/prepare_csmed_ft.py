"""CLI for preparing CSMeD-FT screening examples."""

from __future__ import annotations

import argparse

from screening.datasets.csmed_ft import SETTINGS, prepare_csmed_ft, write_csmed_ft_artifacts
from screening.paths import data_root, results_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.prepare_csmed_ft",
        description="Prepare CSMeD-FT examples and data quality artifacts.",
    )
    parser.add_argument(
        "--data-root",
        default=str(data_root),
        help="Root directory containing the CSMeD-FT folder. Defaults to results/../data.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(results_root),
        help="Directory for prepared artifacts. Defaults to results.",
    )
    parser.add_argument(
        "--settings",
        default=",".join(SETTINGS),
        help="Comma-separated settings to generate: abstract_only,full_text_only,abstract_plus_full_text.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CSMeD-FT artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = tuple(part.strip() for part in args.settings.split(",") if part.strip())

    prepared = prepare_csmed_ft(args.data_root, settings=settings)
    artifacts = write_csmed_ft_artifacts(prepared, args.output_dir, force=args.force)

    for split, by_setting in sorted(prepared.examples_by_split_setting.items()):
        counts = ", ".join(f"{setting}={len(examples)}" for setting, examples in sorted(by_setting.items()))
        print(f"{split}: {counts}")
    for key, path in artifacts.examples_by_split_setting.items():
        print(f"{key}: {path}")
    print(f"manifest_csv: {artifacts.manifest_csv}")
    print(f"data_quality_json: {artifacts.data_quality_json}")
    print(f"data_quality_md: {artifacts.data_quality_md}")
    print(f"dataset_summary_csv: {artifacts.dataset_summary_csv}")
    blockers = prepared.data_quality.get("blockers", [])
    if blockers:
        print(f"Dataset-level blockers: {len(blockers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
