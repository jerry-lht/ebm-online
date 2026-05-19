"""Shared schemas for PICO experiment data and results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Any, ClassVar

PICO_LABELS: tuple[str, ...] = ("P", "I", "O")

LABEL_MAPPING: dict[str, str] = {
    "participants": "P",
    "interventions": "I",
    "outcomes": "O",
}


def _drop_unknown_keys(cls: type[Any], data: dict[str, Any]) -> dict[str, Any]:
    valid = {item.name for item in fields(cls)}
    return {key: value for key, value in data.items() if key in valid}


def dataclass_to_dict(value: Any) -> Any:
    """Convert nested dataclasses to JSON-serializable dictionaries."""
    if is_dataclass(value):
        return asdict(value)
    return value


@dataclass(frozen=True)
class Span:
    """A P/I/O span in official EBM-NLP token space.

    `end_token` and `char_end` are exclusive offsets.
    """

    doc_id: str
    label: str
    text: str
    start_token: int
    end_token: int
    char_start: int | None = None
    char_end: int | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    allowed_labels: ClassVar[set[str]] = set(PICO_LABELS)

    def __post_init__(self) -> None:
        if self.label not in self.allowed_labels:
            raise ValueError(f"Unsupported PICO label: {self.label!r}")
        if self.start_token < 0 or self.end_token < self.start_token:
            raise ValueError("Span token offsets must satisfy 0 <= start_token <= end_token")
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("char_start and char_end must either both be set or both be None")
        if self.char_start is not None:
            if self.char_start < 0 or self.char_end is None or self.char_end < self.char_start:
                raise ValueError("Span character offsets must satisfy 0 <= char_start <= char_end")

    def to_dict(self) -> dict[str, Any]:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Span":
        return cls(**_drop_unknown_keys(cls, data))


@dataclass
class DocumentExample:
    """One abstract with official tokens and experiment annotations."""

    doc_id: str
    split: str
    abstract: str
    tokens: list[str]
    token_offsets: list[tuple[int, int]] = field(default_factory=list)
    gold_spans: list[Span] = field(default_factory=list)
    bio_labels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.gold_spans = [
            span if isinstance(span, Span) else Span.from_dict(span)
            for span in self.gold_spans
        ]
        self.token_offsets = [tuple(offset) for offset in self.token_offsets]

    def to_dict(self) -> dict[str, Any]:
        data = dataclass_to_dict(self)
        data["token_offsets"] = [list(offset) for offset in self.token_offsets]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentExample":
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
