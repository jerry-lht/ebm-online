"""JSON and JSONL helpers for PICO experiment artifacts."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, TypeVar

from pico.schemas import DocumentExample, RunMetadata, Span, dataclass_to_dict

T = TypeVar("T")


def ensure_parent_dir(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def write_json(path: str | Path, data: Any) -> None:
    output_path = ensure_parent_dir(path)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(dataclass_to_dict(data), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    output_path = ensure_parent_dir(path)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dataclass_to_dict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def append_jsonl(path: str | Path, rows: Iterable[Any]) -> None:
    output_path = ensure_parent_dir(path)
    with output_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dataclass_to_dict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object on line {line_number} of {path}")
            yield value


def write_document_examples(path: str | Path, examples: Iterable[DocumentExample]) -> None:
    write_jsonl(path, (example.to_dict() for example in examples))


def read_document_examples(path: str | Path) -> list[DocumentExample]:
    return [DocumentExample.from_dict(row) for row in read_jsonl(path)]


def write_span_predictions(path: str | Path, spans: Iterable[Span]) -> None:
    write_jsonl(path, (span.to_dict() for span in spans))


def read_span_predictions(path: str | Path) -> list[Span]:
    return [Span.from_dict(row) for row in read_jsonl(path)]


def write_run_metadata(path: str | Path, metadata: RunMetadata) -> None:
    write_json(path, metadata.to_dict())


def read_run_metadata(path: str | Path) -> RunMetadata:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected run metadata JSON object in {path}")
    return RunMetadata.from_dict(data)


def write_metrics(path: str | Path, metrics: dict[str, Any]) -> None:
    write_json(path, metrics)


def read_metrics(path: str | Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Expected metrics JSON object in {path}")
    return data
