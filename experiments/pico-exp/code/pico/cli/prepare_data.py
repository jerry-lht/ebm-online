"""Prepare standardized EBM-NLP examples."""

from __future__ import annotations

import argparse
import sys

from pico.ebm_data import EBMDataError, prepare_ebm_nlp_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare standardized EBM-NLP PICO examples.")
    parser.add_argument("--ebm-tar", default="data/EBM-NLP/ebm_nlp_2_00.tar.gz")
    parser.add_argument("--output-dir", default="results/data")
    parser.add_argument("--force", action="store_true", help="Overwrite existing prepared outputs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = prepare_ebm_nlp_data(args.ebm_tar, args.output_dir, force=args.force)
    except EBMDataError as exc:
        parser.exit(status=1, message=f"prepare_data failed: {exc}\n")
    train = summary["splits"]["train"]
    test = summary["splits"]["test"]
    print(
        "Prepared EBM-NLP examples: "
        f"train_docs={train['doc_count']} test_docs={test['doc_count']} "
        f"train_spans={train['p_span_count'] + train['i_span_count'] + train['o_span_count']} "
        f"test_spans={test['p_span_count'] + test['i_span_count'] + test['o_span_count']} "
        f"offset_failures={summary['offset_failure_count']}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
