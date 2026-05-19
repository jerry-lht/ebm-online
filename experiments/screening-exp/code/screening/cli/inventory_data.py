"""CLI for local dataset inventory and validation artifacts."""

from __future__ import annotations

import argparse

from screening.datasets.inventory import inventory_datasets, write_inventory_artifacts
from screening.paths import data_root, results_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m screening.cli.inventory_data",
        description="Inventory available screening datasets and validate basic inputs.",
    )
    parser.add_argument(
        "--dataset",
        choices=("all", "q2crbench", "csmed_ft"),
        default="all",
        help="Dataset to inventory. Defaults to all local datasets.",
    )
    parser.add_argument(
        "--data-root",
        default=str(data_root),
        help="Root directory containing local dataset folders.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(results_root),
        help="Directory for inventory artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    inventory = inventory_datasets(args.data_root, dataset=args.dataset)
    artifacts = write_inventory_artifacts(inventory, args.output_dir)

    print(f"Inventoried {len(inventory.rows)} dataset rows and {len(inventory.manifest)} documents.")
    for name, path in artifacts.items():
        print(f"{name}: {path}")
    if inventory.blockers:
        print(f"Blockers: {len(inventory.blockers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
