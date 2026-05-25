from __future__ import annotations

from pico.conversions import (
    binary_token_labels_to_spans,
    blurb_bio_labels_to_spans,
    describe_overlap_conflicts,
    spans_to_blurb_bio_labels,
    spans_to_multi_label_token_coverage,
)


def test_binary_token_labels_to_single_span() -> None:
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [0, 1, 1, 0], "I": [0, 0, 0, 0], "O": [0, 0, 0, 0]},
        tokens=["a", "b", "c", "d"],
    )

    assert [(span.label, span.start_token, span.end_token, span.text) for span in spans] == [
        ("P", 1, 3, "b c")
    ]


def test_binary_token_labels_to_multiple_spans() -> None:
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [1, 0, 1, 1], "I": [0, 1, 0, 0], "O": [0, 0, 0, 1]},
        tokens=["a", "b", "c", "d"],
    )

    assert [(span.label, span.start_token, span.end_token) for span in spans] == [
        ("P", 0, 1),
        ("P", 2, 4),
        ("I", 1, 2),
        ("O", 3, 4),
    ]


def test_adjacent_non_overlapping_spans_stay_separate_by_label() -> None:
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [1, 0, 0], "I": [0, 1, 0], "O": [0, 0, 1]},
        tokens=["alpha", "beta", "gamma"],
    )

    assert [(span.label, span.start_token, span.end_token) for span in spans] == [
        ("P", 0, 1),
        ("I", 1, 2),
        ("O", 2, 3),
    ]


def test_empty_annotations_return_empty_spans_and_o_labels() -> None:
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [0, 0], "I": [0, 0], "O": [0, 0]},
        tokens=["alpha", "beta"],
    )

    assert spans == []
    assert spans_to_blurb_bio_labels(spans, token_count=2) == ["O", "O"]
    assert describe_overlap_conflicts(spans_to_multi_label_token_coverage(spans, 2))[
        "has_conflict"
    ] is False


def test_overlap_uses_blurb_out_int_par_overwrite_policy() -> None:
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [1, 1, 0], "I": [0, 1, 1], "O": [0, 0, 1]},
        tokens=["alpha", "beta", "gamma"],
    )
    coverage = spans_to_multi_label_token_coverage(spans, token_count=3)

    assert spans_to_blurb_bio_labels(spans, token_count=3) == ["I-PAR", "I-INT", "I-OUT"]
    assert describe_overlap_conflicts(coverage) == {
        "has_conflict": True,
        "conflict_token_count": 2,
        "label_combinations": {"I+O": 1, "P+I": 1},
        "blurb_policy": {
            "label_scheme": "O/I-PAR/I-INT/I-OUT",
            "overwrite_order": ["P", "I", "O"],
            "conflict_priority": "OUT > INT > PAR",
        },
    }


def test_span_text_and_char_offsets_from_token_offsets() -> None:
    abstract = "alpha beta gamma"
    spans = binary_token_labels_to_spans(
        doc_id="1",
        label_sets={"P": [0, 1, 1], "I": [0, 0, 0], "O": [0, 0, 0]},
        tokens=["alpha", "beta", "gamma"],
        token_offsets=[(0, 5), (6, 10), (11, 16)],
        abstract=abstract,
    )

    assert len(spans) == 1
    assert spans[0].text == "beta gamma"
    assert spans[0].char_start == 6
    assert spans[0].char_end == 16


def test_multi_label_coverage_round_trip_from_spans() -> None:
    labels = {"P": [1, 0, 1], "I": [0, 1, 0], "O": [0, 0, 1]}
    spans = binary_token_labels_to_spans("1", labels, ["a", "b", "c"])

    assert spans_to_multi_label_token_coverage(spans, token_count=3) == labels


def test_no_overlap_spans_to_bio_to_spans_preserves_boundaries_and_labels() -> None:
    labels = {"P": [1, 1, 0, 0], "I": [0, 0, 1, 0], "O": [0, 0, 0, 1]}
    tokens = ["alpha", "beta", "gamma", "delta"]
    offsets = [(0, 5), (6, 10), (11, 16), (17, 22)]
    abstract = "alpha beta gamma delta"
    spans = binary_token_labels_to_spans("1", labels, tokens, offsets, abstract)
    bio_labels = spans_to_blurb_bio_labels(spans, token_count=len(tokens))
    round_trip = blurb_bio_labels_to_spans("1", bio_labels, tokens, offsets, abstract)

    assert [(span.label, span.start_token, span.end_token) for span in round_trip] == [
        (span.label, span.start_token, span.end_token) for span in spans
    ]
