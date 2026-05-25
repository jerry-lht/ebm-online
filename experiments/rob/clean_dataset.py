#!/usr/bin/env python3
"""
Drop dataset files that contain empty fields, so they are not evaluated.

A file is dropped if ANY of these are empty (None / "" / [] / {}):
    sr_pico.population
    sr_pico.intervention
    sr_pico.comparison
    sr_pico.outcome
    characteristics.participants
    characteristics.interventions
    characteristics.outcomes
    characteristics.notes

For list-top-level files (same study assessed in multiple SRs), the file is
dropped if ANY record fails. Matching prediction file at the same path under
--predictions_dir is also removed so evaluation skips the study cleanly.

Usage:
    python clean_dataset.py --dry_run        # preview only
    python clean_dataset.py                  # actually delete
    python clean_dataset.py --no_predictions # only drop dataset files
"""

import argparse
import json
from pathlib import Path


PICO_KEYS = ("population", "intervention", "comparison", "outcome")
CHAR_REQUIRED_KEYS = ("participants", "interventions", "outcomes", "notes")


def is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        return True
    return False


def record_has_empty(rec: dict) -> list[str]:
    """Return the list of empty field paths in this record (empty if clean)."""
    bad: list[str] = []

    pico = rec.get("sr_pico")
    if not isinstance(pico, dict):
        bad.append("sr_pico (missing)")
    else:
        for k in PICO_KEYS:
            if k not in pico or is_empty(pico[k]):
                bad.append(f"sr_pico.{k}")

    chars = rec.get("characteristics")
    if not isinstance(chars, dict):
        bad.append("characteristics (missing)")
    else:
        for k in CHAR_REQUIRED_KEYS:
            if k not in chars or is_empty(chars[k]):
                bad.append(f"characteristics.{k}")

    return bad


def file_has_empty(path: Path) -> list[str]:
    """Return list of empty fields across all records in the file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw if isinstance(raw, list) else [raw]
    bad: list[str] = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        for f in record_has_empty(rec):
            bad.append(f"[record {i}] {f}" if isinstance(raw, list) else f)
    return bad


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop files with any empty sr_pico / characteristics field")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--predictions_dir", default="results/predictions",
                        help="Also delete matching prediction files here.")
    parser.add_argument("--no_predictions", action="store_true",
                        help="Only delete dataset files; leave predictions alone.")
    parser.add_argument("--dry_run", action="store_true",
                        help="Show what would be deleted; do not delete anything.")
    parser.add_argument("--show_reasons", action="store_true",
                        help="List the empty fields for each dropped file.")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    pred_dir = Path(args.predictions_dir)
    files = sorted(p for p in dataset_dir.glob("*.json") if p.suffix == ".json")

    if not files:
        print(f"No JSON files in {dataset_dir}")
        return

    mode = "DRY RUN" if args.dry_run else "DELETE"
    print(f"Mode: {mode}   Files scanned: {len(files)}")
    print(f"Dataset dir:     {dataset_dir}")
    if not args.no_predictions:
        print(f"Predictions dir: {pred_dir}\n")
    else:
        print()

    to_drop: list[tuple[Path, list[str]]] = []
    for path in files:
        bad = file_has_empty(path)
        if bad:
            to_drop.append((path, bad))

    print(f"Files to drop: {len(to_drop)} / {len(files)}")
    print(f"Files to keep: {len(files) - len(to_drop)}\n")

    if args.show_reasons and to_drop:
        for path, bad in to_drop[:20]:
            print(f"  {path.name}: {', '.join(bad[:5])}{' ...' if len(bad) > 5 else ''}")
        if len(to_drop) > 20:
            print(f"  ... and {len(to_drop) - 20} more")
        print()

    if args.dry_run:
        print("(dry run — nothing deleted)")
        return

    deleted_data = 0
    deleted_pred = 0
    for path, _ in to_drop:
        path.unlink()
        deleted_data += 1
        if not args.no_predictions:
            pred_path = pred_dir / path.name
            if pred_path.exists():
                pred_path.unlink()
                deleted_pred += 1

    print(f"Deleted dataset files:     {deleted_data}")
    if not args.no_predictions:
        print(f"Deleted prediction files:  {deleted_pred}")


if __name__ == "__main__":
    main()
