"""Conversions between EBM-NLP token labels, spans, and BLURB labels."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pico.schemas import PICO_LABELS, Span

PICO_TO_BLURB: dict[str, str] = {
    "P": "I-PAR",
    "I": "I-INT",
    "O": "I-OUT",
}

BLURB_TO_PICO: dict[str, str] = {value: key for key, value in PICO_TO_BLURB.items()}
BLURB_OVERWRITE_ORDER: tuple[str, ...] = ("P", "I", "O")
BLURB_POLICY: dict[str, Any] = {
    "label_scheme": "O/I-PAR/I-INT/I-OUT",
    "overwrite_order": list(BLURB_OVERWRITE_ORDER),
    "conflict_priority": "OUT > INT > PAR",
}


def binary_token_labels_to_spans(
    doc_id: str,
    label_sets: dict[str, list[int]],
    tokens: list[str],
    token_offsets: list[tuple[int, int]] | None = None,
    abstract: str = "",
) -> list[Span]:
    """Convert official binary P/I/O token labels to contiguous positive spans."""
    token_count = len(tokens)
    offsets = token_offsets or []
    spans: list[Span] = []

    for label in PICO_LABELS:
        labels = label_sets.get(label, [0] * token_count)
        if len(labels) != token_count:
            raise ValueError(f"{label} label length {len(labels)} does not match {token_count} tokens")

        start: int | None = None
        for index, value in enumerate([*labels, 0]):
            if value == 1 and start is None:
                start = index
            elif value == 0 and start is not None:
                spans.append(
                    _make_span(
                        doc_id=doc_id,
                        label=label,
                        start_token=start,
                        end_token=index,
                        tokens=tokens,
                        token_offsets=offsets,
                        abstract=abstract,
                    )
                )
                start = None
            elif value not in {0, 1}:
                raise ValueError(f"{label} labels must be binary; got {value!r} at token {index}")

    return spans


def spans_to_multi_label_token_coverage(
    spans: list[Span],
    token_count: int,
) -> dict[str, list[int]]:
    """Convert a span list to P/I/O binary token coverage."""
    coverage = {label: [0] * token_count for label in PICO_LABELS}
    for span in spans:
        if span.label not in coverage:
            raise ValueError(f"Unsupported PICO label: {span.label!r}")
        if span.start_token < 0 or span.end_token > token_count:
            raise ValueError(
                f"Span {span.doc_id}:{span.start_token}-{span.end_token} exceeds {token_count} tokens"
            )
        for index in range(span.start_token, span.end_token):
            coverage[span.label][index] = 1
    return coverage


def spans_to_blurb_bio_labels(spans: list[Span], token_count: int) -> list[str]:
    """Convert spans to BLURB-compatible single-sequence labels.

    The assignment order intentionally matches BLURB sample preprocessing:
    participants, then interventions, then outcomes. Later labels overwrite
    earlier labels on overlapping tokens.
    """
    labels = ["O"] * token_count
    for pico_label in BLURB_OVERWRITE_ORDER:
        blurb_label = PICO_TO_BLURB[pico_label]
        for span in spans:
            if span.label != pico_label:
                continue
            if span.start_token < 0 or span.end_token > token_count:
                raise ValueError(
                    f"Span {span.doc_id}:{span.start_token}-{span.end_token} exceeds {token_count} tokens"
                )
            for index in range(span.start_token, span.end_token):
                labels[index] = blurb_label
    return labels


def blurb_bio_labels_to_spans(
    doc_id: str,
    bio_labels: list[str],
    tokens: list[str],
    token_offsets: list[tuple[int, int]] | None = None,
    abstract: str = "",
) -> list[Span]:
    """Convert a BLURB single-sequence label list back to P/I/O spans."""
    offsets = token_offsets or []
    spans: list[Span] = []
    start: int | None = None
    current_label: str | None = None

    for index, blurb_label in enumerate([*bio_labels, "O"]):
        if blurb_label == "O":
            next_label = None
        else:
            try:
                next_label = BLURB_TO_PICO[blurb_label]
            except KeyError as exc:
                raise ValueError(f"Unsupported BLURB label: {blurb_label!r}") from exc

        if next_label != current_label:
            if start is not None and current_label is not None:
                spans.append(
                    _make_span(
                        doc_id=doc_id,
                        label=current_label,
                        start_token=start,
                        end_token=index,
                        tokens=tokens,
                        token_offsets=offsets,
                        abstract=abstract,
                    )
                )
            start = index if next_label is not None else None
            current_label = next_label

    return spans


def describe_overlap_conflicts(coverage: dict[str, list[int]]) -> dict[str, Any]:
    """Summarize tokens covered by multiple P/I/O labels."""
    if not coverage:
        conflict_count = 0
        combinations: Counter[str] = Counter()
    else:
        token_count = len(next(iter(coverage.values())))
        combinations = Counter()
        for index in range(token_count):
            active = [label for label in PICO_LABELS if coverage.get(label, [])[index] == 1]
            if len(active) > 1:
                combinations["+".join(active)] += 1
        conflict_count = sum(combinations.values())

    return {
        "has_conflict": conflict_count > 0,
        "conflict_token_count": conflict_count,
        "label_combinations": dict(sorted(combinations.items())),
        "blurb_policy": BLURB_POLICY,
    }


def _make_span(
    doc_id: str,
    label: str,
    start_token: int,
    end_token: int,
    tokens: list[str],
    token_offsets: list[tuple[int, int]],
    abstract: str,
) -> Span:
    if token_offsets and len(token_offsets) >= end_token:
        char_start = token_offsets[start_token][0]
        char_end = token_offsets[end_token - 1][1]
        text = abstract[char_start:char_end]
    else:
        char_start = None
        char_end = None
        text = " ".join(tokens[start_token:end_token])

    return Span(
        doc_id=doc_id,
        label=label,
        text=text,
        start_token=start_token,
        end_token=end_token,
        char_start=char_start,
        char_end=char_end,
    )
