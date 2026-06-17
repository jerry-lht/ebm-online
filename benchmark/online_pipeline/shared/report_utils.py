"""Report helpers for benchmark runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: str | Path, value: Any) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_summary_markdown(path: str | Path, *, title: str, summary: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in summary.items():
        if isinstance(value, float):
            display = f"{value:.4f}"
        else:
            display = str(value)
        lines.append(f"- {key}: {display}")
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")
