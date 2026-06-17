"""JSONL helpers for benchmark fixtures and outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path)
    rows: list[dict[str, Any]] = []
    with resolved.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"{resolved}:{line_number} must contain a JSON object")
            rows.append(value)
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]], *, sort_keys: bool = True) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=sort_keys) + "\n")


def append_jsonl(path: str | Path, rows: list[dict[str, Any]], *, sort_keys: bool = True) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=sort_keys) + "\n")
        handle.flush()
