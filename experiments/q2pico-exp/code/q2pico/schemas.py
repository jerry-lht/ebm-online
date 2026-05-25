"""Shared schemas for Question-to-PICO experiment artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Any, ClassVar

PICO_LABELS: tuple[str, ...] = ("P", "I", "C", "O")
LABEL_TO_OUTPUT_KEY: dict[str, str] = {
    "P": "participants",
    "I": "interventions",
    "C": "comparators",
    "O": "outcomes",
}
OUTPUT_KEY_TO_LABEL: dict[str, str] = {value: key for key, value in LABEL_TO_OUTPUT_KEY.items()}


def parse_label_scope(value: str | None) -> tuple[str, ...]:
    if value is None:
        return PICO_LABELS
    raw_items = [item.strip() for item in value.split(",")]
    labels = [item for item in raw_items if item]
    if not labels:
        raise ValueError("Label scope must include at least one label")
    unknown = [label for label in labels if label not in PICO_LABELS]
    if unknown:
        raise ValueError(f"Unsupported labels in scope: {unknown}")
    deduped: list[str] = []
    for label in labels:
        if label not in deduped:
            deduped.append(label)
    return tuple(deduped)


def _drop_unknown_keys(cls: type[Any], data: dict[str, Any]) -> dict[str, Any]:
    valid = {item.name for item in fields(cls)}
    return {key: value for key, value in data.items() if key in valid}


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def normalize_slot_values(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"Slot values must be strings; got {type(value).__name__}")
        clean = value.strip()
        if not clean or clean in seen:
            continue
        normalized.append(clean)
        seen.add(clean)
    return normalized


def coerce_slot_dict(
    slots: dict[str, Any],
    *,
    allow_partial: bool = False,
    labels: tuple[str, ...] = PICO_LABELS,
) -> dict[str, list[str]]:
    if not isinstance(slots, dict):
        raise TypeError("Slots must be an object")
    allowed_labels = set(labels)
    unknown = sorted(set(slots) - allowed_labels)
    if unknown:
        raise ValueError(f"Unsupported PICO slot keys: {unknown}")
    if not allow_partial:
        missing = [label for label in labels if label not in slots]
        if missing:
            raise ValueError(f"Missing PICO slot keys: {missing}")
    normalized: dict[str, list[str]] = {}
    for label in labels:
        raw_values = slots.get(label, [])
        if not isinstance(raw_values, list):
            raise TypeError(f"Slot {label} must be a list")
        normalized[label] = normalize_slot_values(raw_values)
    return normalized


@dataclass
class QuestionPICOExample:
    """One clinical question and its gold P/I/C/O slot values."""

    question_id: str
    split: str
    question_text: str
    gold_slots: dict[str, list[str]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.gold_slots = coerce_slot_dict(self.gold_slots)

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionPICOExample":
        return cls(**_drop_unknown_keys(cls, data))


@dataclass
class SlotPrediction:
    """Validated slot prediction for one question."""

    question_id: str
    slots: dict[str, list[str]]
    metadata: dict[str, Any] = field(default_factory=dict)

    allowed_labels: ClassVar[set[str]] = set(PICO_LABELS)

    def __post_init__(self) -> None:
        self.slots = coerce_slot_dict(self.slots)

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlotPrediction":
        return cls(**_drop_unknown_keys(cls, data))


@dataclass
class RunMetadata:
    """Metadata required to reproduce an experiment run."""

    run_id: str
    method: str
    setting: str
    timestamp: str
    config: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    input_data_version: str | None = None
    evaluator_version: str | None = None
    command: list[str] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)
    runtime_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunMetadata":
        return cls(**_drop_unknown_keys(cls, data))
