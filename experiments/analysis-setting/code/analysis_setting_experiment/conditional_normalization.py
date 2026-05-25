from __future__ import annotations

import hashlib
import re
import string
from typing import Any

_PUNCT_TRANSLATION = str.maketrans("", "", string.punctuation.replace("/", ""))
_MULTISPACE_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_COMPARISON_CONNECTOR_REPLACEMENTS = (
    (re.compile(r"\bversus\b", re.IGNORECASE), " vs "),
    (re.compile(r"\bvs\.?\b", re.IGNORECASE), " vs "),
    (re.compile(r"\bcompared with\b", re.IGNORECASE), " vs "),
    (re.compile(r"\bcompared to\b", re.IGNORECASE), " vs "),
)
_COMPARISON_SURFACE_ALIASES = (
    (re.compile(r"\bplacebo control\b"), "placebo"),
    (re.compile(r"\bstandard care\b"), "usual care"),
    (re.compile(r"\broutine care\b"), "usual care"),
    (re.compile(r"\bcare as usual\b"), "usual care"),
    (re.compile(r"\bactive comparators\b"), "active comparator"),
    (re.compile(r"\bactive controls\b"), "active control"),
    (re.compile(r"\binactive controls\b"), "inactive control"),
    (re.compile(r"\binactive control group\b"), "inactive control"),
    (re.compile(r"\binactive comparator\b"), "inactive control"),
)
_EFFECT_MEASURE_ALIASES = {
    "rr": "risk ratio",
    "risk ratio rr": "risk ratio",
    "md": "mean difference",
    "mean difference md": "mean difference",
    "standardized mean difference": "std mean difference",
    "standardised mean difference": "std mean difference",
    "smd": "std mean difference",
    "std standardized mean difference": "std mean difference",
    "incidence rate ratio": "rate ratio",
    "irr": "rate ratio",
}


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def normalize_text(value: Any) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        return ""
    normalized = cleaned
    for pattern, replacement in _COMPARISON_CONNECTOR_REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)
    lowered = normalized.lower().translate(_PUNCT_TRANSLATION)
    lowered = lowered.replace(" vs ", " versus ")
    return _MULTISPACE_RE.sub(" ", lowered).strip()


def normalize_effect_measure(value: Any) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    return _EFFECT_MEASURE_ALIASES.get(normalized, normalized)


def normalize_comparison_text(value: Any) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    for pattern, replacement in _COMPARISON_SURFACE_ALIASES:
        normalized = pattern.sub(replacement, normalized)
    return _MULTISPACE_RE.sub(" ", normalized).strip()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        key = normalize_text(cleaned)
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def normalize_string_list(values: list[str]) -> list[str]:
    normalized = [normalize_text(value) for value in values]
    return sorted({value for value in normalized if value})


def normalize_comparison_list(values: list[str]) -> list[str]:
    normalized = [normalize_comparison_text(value) for value in values]
    return sorted({value for value in normalized if value})


def normalize_arm_pair(pair: dict[str, Any]) -> dict[str, str]:
    return {
        "experimental_arm": clean_text(pair.get("experimental_arm")),
        "control_arm": clean_text(pair.get("control_arm")),
    }


def normalize_arm_pair_fields(pair: dict[str, Any]) -> dict[str, str]:
    return {
        "experimental_arm": normalize_text(pair.get("experimental_arm")),
        "control_arm": normalize_text(pair.get("control_arm")),
    }


def arm_pair_key(pair: dict[str, Any]) -> tuple[str, str]:
    normalized = normalize_arm_pair_fields(pair)
    return normalized["experimental_arm"], normalized["control_arm"]


def unordered_arm_pair_key(pair: dict[str, Any]) -> tuple[str, str]:
    left, right = arm_pair_key(pair)
    return tuple(sorted((left, right)))


def dedupe_arm_pairs(values: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for value in values:
        pair = normalize_arm_pair(value)
        key = arm_pair_key(pair)
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(pair)
    return deduped


def normalize_arm_pairs(values: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        pair = normalize_arm_pair_fields(value)
        key = (pair["experimental_arm"], pair["control_arm"])
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        normalized.append(pair)
    normalized.sort(key=lambda item: (item["experimental_arm"], item["control_arm"]))
    return normalized


def slugify(value: str, *, fallback: str = "item") -> str:
    normalized = normalize_text(value)
    if not normalized:
        return fallback
    slug = _SLUG_RE.sub("-", normalized).strip("-")
    return slug or fallback


def stable_digest(parts: list[str], *, length: int = 10) -> str:
    joined = "||".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:length]
