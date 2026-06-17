"""JSON-safe serialization for workflow domain objects."""

from __future__ import annotations

import json
import types
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def from_jsonable(value: Any, target_type: type | Any, *, path: str = "$") -> Any:
    """Parse JSON-safe values into domain dataclasses and value objects."""

    if target_type is Any:
        return value

    origin = get_origin(target_type)
    args = get_args(target_type)

    if origin in (Union, types.UnionType):
        return _parse_union(value, args, path=path)

    if origin in (list, tuple, set):
        if not isinstance(value, list):
            raise ValueError(f"{path} must be a list")
        item_type = args[0] if args else Any
        parsed = [from_jsonable(item, item_type, path=f"{path}[{index}]") for index, item in enumerate(value)]
        if origin is tuple:
            return tuple(parsed)
        if origin is set:
            return set(parsed)
        return parsed

    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        key_type = args[0] if args else str
        value_type = args[1] if len(args) > 1 else Any
        return {
            from_jsonable(key, key_type, path=f"{path}.<key>"): from_jsonable(item, value_type, path=f"{path}.{key}")
            for key, item in value.items()
        }

    if isinstance(target_type, type) and issubclass(target_type, Enum):
        try:
            return target_type(value)
        except ValueError as exc:
            valid = ", ".join(str(item.value) for item in target_type)
            raise ValueError(f"{path} must be one of: {valid}") from exc

    if isinstance(target_type, type) and is_dataclass(target_type):
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        return _parse_dataclass(value, target_type, path=path)

    if target_type is str:
        return "" if value is None else str(value)
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)

    return value


def _parse_dataclass(value: dict[str, Any], target_type: type, *, path: str) -> Any:
    hints = get_type_hints(target_type)
    kwargs: dict[str, Any] = {}
    for field in fields(target_type):
        if field.name not in value:
            continue
        field_type = hints.get(field.name, Any)
        kwargs[field.name] = from_jsonable(value[field.name], field_type, path=f"{path}.{field.name}")
    try:
        return target_type(**kwargs)
    except TypeError as exc:
        raise ValueError(f"{path} is missing required fields for {target_type.__name__}: {exc}") from exc


def _parse_union(value: Any, args: tuple[Any, ...], *, path: str) -> Any:
    if value is None and type(None) in args:
        return None
    errors = []
    for candidate in args:
        if candidate is type(None):
            continue
        try:
            return from_jsonable(value, candidate, path=path)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
    expected = " | ".join(getattr(candidate, "__name__", str(candidate)) for candidate in args)
    raise ValueError(f"{path} must match one of: {expected}. {'; '.join(errors[:3])}")
