"""Prepare Clinical_Questions splits for q2pico."""

from __future__ import annotations

import argparse

from q2pico.io_utils import write_json
from q2pico.question_data import DEFAULT_SPLIT_SEED, prepare_question_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Clinical_Questions splits for q2pico.")
    parser.add_argument("--dataset-dir", default="data/Q2CRBench-3/Clinical_Questions")
    parser.add_argument("--output-dir", default="results/data")
    parser.add_argument("--seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = prepare_question_data(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        seed=args.seed,
        force=args.force,
    )
    write_json(f"{args.output_dir}/prepare_summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
