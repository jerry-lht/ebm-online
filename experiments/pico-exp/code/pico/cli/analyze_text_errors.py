"""Analyze TP/FP/FN text extraction errors for LLM PICO runs."""

from __future__ import annotations

import argparse

from pico.error_analysis import analyze_text_errors
from pico.io_utils import read_document_examples, read_jsonl, write_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze text-level TP/FP/FN errors for LLM PICO extraction.")
    parser.add_argument("--gold", required=True, help="Gold document examples JSONL.")
    parser.add_argument("--raw", required=True, help="Raw LLM response JSONL.")
    parser.add_argument("--output", required=True, help="Error analysis JSON output path.")
    parser.add_argument("--sample-limit-per-label", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    examples = read_document_examples(args.gold)
    raw_rows = list(read_jsonl(args.raw))
    analysis = analyze_text_errors(
        examples=examples,
        raw_rows=raw_rows,
        sample_limit_per_label=args.sample_limit_per_label,
    )
    analysis["inputs"] = {"gold_path": args.gold, "raw_path": args.raw}
    write_metrics(args.output, analysis)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
