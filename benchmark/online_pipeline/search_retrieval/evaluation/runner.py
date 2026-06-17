"""Run the search retrieval scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from benchmark.online_pipeline.shared.run_utils import run_structural_module_benchmark


MODULE_NAME = "search_retrieval"
MODULE_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    result = run_structural_module_benchmark(
        module_name=MODULE_NAME,
        dataset=args.dataset,
        method=args.method,
        run_id=args.run_id,
        module_dir=MODULE_DIR,
    )
    print(result["run_dir"])


if __name__ == "__main__":
    main()
