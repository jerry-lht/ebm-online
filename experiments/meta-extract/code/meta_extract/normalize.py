"""Normalization utilities for benchmark2-v2 tasks."""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, InvalidOperation
from typing import Iterable

SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[-_/]+")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return SPACE_RE.sub(" ", text)


def normalize_text_loose(value: object) -> str:
    return normalize_text(value).casefold()


def normalize_phrase(value: object) -> str:
    text = normalize_text_loose(value)
    text = PUNCT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def canonical_numeric_string(value: object) -> str | None:
    text = normalize_text(value)
    if text == "":
        return None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized == "-0":
        normalized = "0"
    return normalized


def normalize_value(value: object) -> str:
    numeric = canonical_numeric_string(value)
    if numeric is not None:
        return numeric
    return normalize_text(value)


def normalize_value_loose(value: object) -> str:
    numeric = canonical_numeric_string(value)
    if numeric is not None:
        return numeric
    return normalize_phrase(value)


def normalize_subgroup(value: object) -> str | None:
    text = normalize_phrase(value)
    if text in {"", "none", "null"}:
        return None
    return text


def normalize_timepoint_value(value: object) -> str:
    text = normalize_phrase(value)
    if text.startswith("at "):
        text = text[3:]
    text = text.replace("post intervention", "post intervention")
    text = text.replace("post intervention", "post intervention")
    return SPACE_RE.sub(" ", text).strip()


def normalize_timepoints(values: Iterable[object]) -> tuple[str, ...]:
    normalized = []
    for value in values or []:
        text = normalize_timepoint_value(value)
        if text:
            normalized.append(text)
    return tuple(sorted(dict.fromkeys(normalized)))


def item_key(item: dict) -> tuple[str | None, tuple[str, ...]]:
    return normalize_subgroup(item.get("subgroup")), normalize_timepoints(item.get("timepoints") or [])


def structured_item_key(item: dict) -> tuple[str | None, tuple[str, ...]]:
    return item_key(item)


def field_key(field: dict) -> tuple[str, str]:
    return normalize_text(field.get("field")), normalize_value_loose(field.get("value"))


def row_key(row: dict) -> tuple[tuple[str, str], ...]:
    direct_fields = row.get("direct_extraction_fields") or []
    return tuple(sorted(field_key(field) for field in direct_fields))


def stable_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()
