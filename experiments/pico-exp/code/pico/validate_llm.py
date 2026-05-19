"""Validate raw LLM PICO JSON responses into official token-space spans."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from pico.schemas import DocumentExample, PICO_LABELS, Span

LLM_VALIDATOR_VERSION = "phase6-v1"


@dataclass
class _DocCounts:
    raw_rows: int = 0
    invalid_json_responses: int = 0
    non_array_responses: int = 0
    response_items: int = 0
    schema_invalid_items: int = 0
    unknown_doc_items: int = 0
    missing_offset_items: int = 0
    unambiguous_text_only_items: int = 0
    ambiguous_match_items: int = 0
    invalid_offset_items: int = 0
    non_extractive_items: int = 0
    token_boundary_invalid_items: int = 0
    duplicate_spans: int = 0
    valid_spans: int = 0
    written_spans: int = 0
    overlap_conflict_tokens: int = 0
    overlap_conflict_documents: int = 0
    token_count: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


def validate_llm_predictions(
    examples: list[DocumentExample],
    raw_rows: list[dict[str, Any]],
) -> tuple[list[Span], dict[str, Any]]:
    """Validate raw per-document LLM responses.

    `raw_rows` must contain objects with a string `doc_id` and a string
    `response`. The response string must decode to a JSON array of objects with
    `label` and `text`. Items may optionally include `char_start` and
    `char_end`; text-only items are normalized only when the text occurs exactly
    once in the abstract.
    """
    examples_by_doc = _index_examples(examples)
    doc_counts: dict[str, _DocCounts] = {
        doc_id: _DocCounts(token_count=len(example.tokens))
        for doc_id, example in examples_by_doc.items()
    }
    unknown_counts: dict[str, _DocCounts] = defaultdict(_DocCounts)
    valid_spans: list[Span] = []
    seen_keys_by_doc: dict[str, set[tuple[str, int, int]]] = defaultdict(set)

    for row_index, row in enumerate(raw_rows, start=1):
        doc_id = row.get("doc_id")
        response = row.get("response")
        count_key = doc_id if isinstance(doc_id, str) else f"__row_{row_index}__"
        counts = doc_counts.get(count_key)
        if counts is None:
            counts = unknown_counts[count_key]
        counts.raw_rows += 1

        if not isinstance(doc_id, str) or not isinstance(response, str):
            counts.schema_invalid_items += 1
            counts.response_items += 1
            _record_error(counts, row_index, "row_schema_invalid", "raw row requires string doc_id and response")
            continue

        example = examples_by_doc.get(doc_id)
        if example is None:
            parsed = _parse_response(response, counts, row_index)
            if isinstance(parsed, list):
                item_count = len(parsed)
                counts.response_items += item_count
                counts.schema_invalid_items += item_count
                counts.unknown_doc_items += item_count
                _record_error(counts, row_index, "unknown_doc_id", f"unknown doc_id: {doc_id!r}")
            continue

        parsed = _parse_response(response, counts, row_index)
        if parsed is None:
            continue
        if not isinstance(parsed, list):
            counts.non_array_responses += 1
            counts.response_items += 1
            counts.schema_invalid_items += 1
            _record_error(counts, row_index, "response_not_array", "response JSON must be an array")
            continue

        for item_index, item in enumerate(parsed):
            counts.response_items += 1
            if not isinstance(item, dict):
                counts.schema_invalid_items += 1
                _record_error(counts, row_index, "item_schema_invalid", "array item must be an object", item_index)
                continue

            schema_error = _schema_error(item)
            if schema_error is not None:
                counts.schema_invalid_items += 1
                _record_error(counts, row_index, "item_schema_invalid", schema_error, item_index)
                continue

            label = item["label"]
            text = item["text"]
            has_start = "char_start" in item
            has_end = "char_end" in item
            if not has_start or not has_end:
                counts.missing_offset_items += 1
                char_span = _unique_text_match(example.abstract, text)
                if char_span is None:
                    match_count = _text_match_count(example.abstract, text)
                    if match_count == 0:
                        counts.non_extractive_items += 1
                        _record_error(counts, row_index, "non_extractive", "text is not an exact substring", item_index)
                    else:
                        counts.ambiguous_match_items += 1
                        _record_error(
                            counts,
                            row_index,
                            "ambiguous_match",
                            f"text occurs {match_count} times in abstract",
                            item_index,
                        )
                    continue
                counts.unambiguous_text_only_items += 1
                char_start, char_end = char_span
                token_span = _char_offsets_to_token_span(example.token_offsets, char_start, char_end)
                if token_span is None:
                    counts.invalid_offset_items += 1
                    counts.token_boundary_invalid_items += 1
                    _record_error(
                        counts,
                        row_index,
                        "token_boundary_invalid",
                        "matched character offsets do not align to official token boundaries",
                        item_index,
                    )
                    continue
                start_token, end_token = token_span
                _append_valid_span(
                    valid_spans=valid_spans,
                    seen_keys_by_doc=seen_keys_by_doc,
                    counts=counts,
                    doc_id=doc_id,
                    label=label,
                    text=text,
                    start_token=start_token,
                    end_token=end_token,
                    char_start=char_start,
                    char_end=char_end,
                    validation_mode="text_unique_match",
                )
                continue

            char_start = item["char_start"]
            char_end = item["char_end"]
            if not isinstance(char_start, int) or not isinstance(char_end, int):
                counts.invalid_offset_items += 1
                _record_error(counts, row_index, "invalid_offset", "char_start and char_end must be integers", item_index)
                continue
            if char_start < 0 or char_end < char_start or char_end > len(example.abstract):
                counts.invalid_offset_items += 1
                _record_error(counts, row_index, "invalid_offset", "character offsets are out of bounds", item_index)
                continue
            if example.abstract[char_start:char_end] != text:
                counts.non_extractive_items += 1
                _record_error(counts, row_index, "non_extractive", "offset substring does not match text", item_index)
                continue

            token_span = _char_offsets_to_token_span(example.token_offsets, char_start, char_end)
            if token_span is None:
                counts.invalid_offset_items += 1
                counts.token_boundary_invalid_items += 1
                _record_error(
                    counts,
                    row_index,
                    "token_boundary_invalid",
                    "character offsets do not align to official token boundaries",
                    item_index,
                )
                continue

            start_token, end_token = token_span
            _append_valid_span(
                valid_spans=valid_spans,
                seen_keys_by_doc=seen_keys_by_doc,
                counts=counts,
                doc_id=doc_id,
                label=label,
                text=text,
                start_token=start_token,
                end_token=end_token,
                char_start=char_start,
                char_end=char_end,
                validation_mode="provided_offsets",
            )

    _add_overlap_counts(doc_counts, valid_spans, examples_by_doc)
    quality = _build_quality(examples, raw_rows, doc_counts, unknown_counts)
    return valid_spans, quality


def _index_examples(examples: list[DocumentExample]) -> dict[str, DocumentExample]:
    examples_by_doc: dict[str, DocumentExample] = {}
    for example in examples:
        if example.doc_id in examples_by_doc:
            raise ValueError(f"Duplicate example doc_id: {example.doc_id!r}")
        if len(example.token_offsets) != len(example.tokens):
            raise ValueError(f"Example {example.doc_id!r} is missing complete token_offsets")
        examples_by_doc[example.doc_id] = example
    return examples_by_doc


def _parse_response(response: str, counts: _DocCounts, row_index: int) -> Any | None:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        counts.invalid_json_responses += 1
        _record_error(counts, row_index, "invalid_json", "response is not valid JSON")
        return None


def _schema_error(item: dict[str, Any]) -> str | None:
    label = item.get("label")
    text = item.get("text")
    if not isinstance(label, str):
        return "item requires string label"
    if label not in PICO_LABELS:
        return f"unsupported label: {label!r}"
    if not isinstance(text, str):
        return "item requires string text"
    if ("char_start" in item) != ("char_end" in item):
        return "char_start and char_end must both be present or both be absent"
    return None


def _append_valid_span(
    valid_spans: list[Span],
    seen_keys_by_doc: dict[str, set[tuple[str, int, int]]],
    counts: _DocCounts,
    doc_id: str,
    label: str,
    text: str,
    start_token: int,
    end_token: int,
    char_start: int,
    char_end: int,
    validation_mode: str,
) -> None:
    key = (label, char_start, char_end)
    counts.valid_spans += 1
    if key in seen_keys_by_doc[doc_id]:
        counts.duplicate_spans += 1
        return
    seen_keys_by_doc[doc_id].add(key)
    counts.written_spans += 1
    valid_spans.append(
        Span(
            doc_id=doc_id,
            label=label,
            text=text,
            start_token=start_token,
            end_token=end_token,
            char_start=char_start,
            char_end=char_end,
            metadata={"validator_version": LLM_VALIDATOR_VERSION, "validation_mode": validation_mode},
        )
    )


def _unique_text_match(abstract: str, text: str) -> tuple[int, int] | None:
    matches = _find_text_matches(abstract, text)
    if len(matches) == 1:
        start = matches[0]
        return start, start + len(text)
    return None


def _text_match_count(abstract: str, text: str) -> int:
    return len(_find_text_matches(abstract, text))


def _find_text_matches(abstract: str, text: str) -> list[int]:
    if text == "":
        return []
    starts: list[int] = []
    start = 0
    while True:
        index = abstract.find(text, start)
        if index == -1:
            return starts
        starts.append(index)
        start = index + 1


def _char_offsets_to_token_span(
    token_offsets: list[tuple[int, int]],
    char_start: int,
    char_end: int,
) -> tuple[int, int] | None:
    start_by_char = {start: index for index, (start, _end) in enumerate(token_offsets)}
    end_by_char = {end: index + 1 for index, (_start, end) in enumerate(token_offsets)}
    start_token = start_by_char.get(char_start)
    end_token = end_by_char.get(char_end)
    if start_token is None or end_token is None or end_token < start_token:
        return None
    return start_token, end_token


def _add_overlap_counts(
    doc_counts: dict[str, _DocCounts],
    valid_spans: list[Span],
    examples_by_doc: dict[str, DocumentExample],
) -> None:
    spans_by_doc: dict[str, list[Span]] = defaultdict(list)
    for span in valid_spans:
        spans_by_doc[span.doc_id].append(span)

    for doc_id, spans in spans_by_doc.items():
        example = examples_by_doc[doc_id]
        conflict_tokens = 0
        for token_index in range(len(example.tokens)):
            labels = {
                span.label
                for span in spans
                if span.start_token <= token_index < span.end_token
            }
            if len(labels) > 1:
                conflict_tokens += 1
        if conflict_tokens:
            doc_counts[doc_id].overlap_conflict_documents = 1
            doc_counts[doc_id].overlap_conflict_tokens = conflict_tokens


def _build_quality(
    examples: list[DocumentExample],
    raw_rows: list[dict[str, Any]],
    doc_counts: dict[str, _DocCounts],
    unknown_counts: dict[str, _DocCounts],
) -> dict[str, Any]:
    all_counts = list(doc_counts.values()) + list(unknown_counts.values())
    totals = _sum_doc_counts(all_counts)
    per_doc = {
        doc_id: {**_counts_to_public_dict(counts), **_counts_to_rate_dict(counts)}
        for doc_id, counts in sorted(doc_counts.items())
        if counts.raw_rows or counts.response_items or counts.written_spans
    }
    for doc_id, counts in sorted(unknown_counts.items()):
        per_doc[doc_id] = {**_counts_to_public_dict(counts), **_counts_to_rate_dict(counts)}

    return {
        "validator_version": LLM_VALIDATOR_VERSION,
        "counts": {
            **_counts_to_public_dict(totals),
            "examples": len(examples),
            "raw_rows": len(raw_rows),
        },
        **_counts_to_rate_dict(
            totals,
            raw_row_denominator=len(raw_rows),
            overlap_doc_denominator=len([counts for counts in doc_counts.values() if counts.written_spans > 0]),
        ),
        "per_doc": per_doc,
        "metadata": {
            "raw_response_contract": {
                "row_schema": {
                    "doc_id": "string",
                    "response": "string containing a JSON array",
                    "metadata": "optional object",
                },
                "item_schema": {
                    "label": list(PICO_LABELS),
                    "text": "string",
                    "char_start": "optional integer official character start",
                    "char_end": "optional integer official character end, exclusive",
                },
            },
            "rates": {
                "invalid_json_rate": "invalid JSON responses / raw rows",
                "schema_invalid_rate": "schema-invalid items / parsed response items",
                "non_extractive_span_rate": "offset text mismatches or text-only zero matches / parsed response items",
                "invalid_offset_rate": "invalid or non-boundary offsets / parsed response items",
                "ambiguous_match_rate": "text-only ambiguous matches / parsed response items",
                "duplicate_span_rate": "duplicate valid spans / valid spans before dedupe",
                "overlap_conflict_document_rate": "docs with multi-label token coverage / docs with written spans",
                "overlap_conflict_token_rate": "multi-label covered tokens / example tokens",
            },
        },
    }


def _sum_doc_counts(counts: list[_DocCounts]) -> _DocCounts:
    total = _DocCounts()
    for item in counts:
        total.raw_rows += item.raw_rows
        total.invalid_json_responses += item.invalid_json_responses
        total.non_array_responses += item.non_array_responses
        total.response_items += item.response_items
        total.schema_invalid_items += item.schema_invalid_items
        total.unknown_doc_items += item.unknown_doc_items
        total.missing_offset_items += item.missing_offset_items
        total.unambiguous_text_only_items += item.unambiguous_text_only_items
        total.ambiguous_match_items += item.ambiguous_match_items
        total.invalid_offset_items += item.invalid_offset_items
        total.non_extractive_items += item.non_extractive_items
        total.token_boundary_invalid_items += item.token_boundary_invalid_items
        total.duplicate_spans += item.duplicate_spans
        total.valid_spans += item.valid_spans
        total.written_spans += item.written_spans
        total.overlap_conflict_tokens += item.overlap_conflict_tokens
        total.overlap_conflict_documents += item.overlap_conflict_documents
        total.token_count += item.token_count
    return total


def _counts_to_public_dict(counts: _DocCounts) -> dict[str, Any]:
    data = {
        "raw_rows": counts.raw_rows,
        "invalid_json_responses": counts.invalid_json_responses,
        "non_array_responses": counts.non_array_responses,
        "response_items": counts.response_items,
        "schema_invalid_items": counts.schema_invalid_items,
        "unknown_doc_items": counts.unknown_doc_items,
        "missing_offset_items": counts.missing_offset_items,
        "unambiguous_text_only_items": counts.unambiguous_text_only_items,
        "ambiguous_match_items": counts.ambiguous_match_items,
        "invalid_offset_items": counts.invalid_offset_items,
        "non_extractive_items": counts.non_extractive_items,
        "token_boundary_invalid_items": counts.token_boundary_invalid_items,
        "duplicate_spans": counts.duplicate_spans,
        "valid_spans": counts.valid_spans,
        "written_spans": counts.written_spans,
        "overlap_conflict_documents": counts.overlap_conflict_documents,
        "overlap_conflict_tokens": counts.overlap_conflict_tokens,
        "token_count": counts.token_count,
    }
    if counts.errors:
        data["errors"] = counts.errors
    return data


def _counts_to_rate_dict(
    counts: _DocCounts,
    raw_row_denominator: int | None = None,
    overlap_doc_denominator: int | None = None,
) -> dict[str, float]:
    if raw_row_denominator is None:
        raw_row_denominator = counts.raw_rows
    if overlap_doc_denominator is None:
        overlap_doc_denominator = 1 if counts.written_spans > 0 else 0
    return {
        "invalid_json_rate": _safe_divide(counts.invalid_json_responses, raw_row_denominator),
        "schema_invalid_rate": _safe_divide(counts.schema_invalid_items, counts.response_items),
        "non_extractive_span_rate": _safe_divide(counts.non_extractive_items, counts.response_items),
        "invalid_offset_rate": _safe_divide(counts.invalid_offset_items, counts.response_items),
        "ambiguous_match_rate": _safe_divide(counts.ambiguous_match_items, counts.response_items),
        "duplicate_span_rate": _safe_divide(counts.duplicate_spans, counts.valid_spans),
        "overlap_conflict_document_rate": _safe_divide(
            counts.overlap_conflict_documents,
            overlap_doc_denominator,
        ),
        "overlap_conflict_token_rate": _safe_divide(counts.overlap_conflict_tokens, counts.token_count),
    }


def _record_error(
    counts: _DocCounts,
    row_index: int,
    error_type: str,
    message: str,
    item_index: int | None = None,
) -> None:
    if len(counts.errors) >= 20:
        return
    error = {
        "row_index": row_index,
        "type": error_type,
        "message": message,
    }
    if item_index is not None:
        error["item_index"] = item_index
    counts.errors.append(error)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
