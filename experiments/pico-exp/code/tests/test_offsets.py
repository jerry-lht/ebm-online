from __future__ import annotations

import pytest

from pico.offsets import OffsetAlignmentError, align_token_offsets


def test_align_token_offsets_with_spaces() -> None:
    assert align_token_offsets("alpha beta", ["alpha", "beta"]) == [(0, 5), (6, 10)]


def test_align_token_offsets_with_newlines_and_tabs() -> None:
    assert align_token_offsets("alpha\n\tbeta  gamma\n", ["alpha", "beta", "gamma"]) == [
        (0, 5),
        (7, 11),
        (13, 18),
    ]


def test_align_token_offsets_exactly_matches_symbols() -> None:
    text = "(alpha) 50% beta-gamma."
    tokens = ["(alpha)", "50%", "beta-gamma."]
    assert align_token_offsets(text, tokens) == [(0, 7), (8, 11), (12, 23)]


def test_align_token_offsets_rejects_non_whitespace_gap() -> None:
    with pytest.raises(OffsetAlignmentError) as error:
        align_token_offsets("alpha x beta", ["alpha", "beta"])

    assert error.value.token_index == 1
    assert error.value.token == "beta"
    assert error.value.cursor == 5
    assert error.value.message == "Non-whitespace text before token"


def test_align_token_offsets_rejects_missing_token() -> None:
    with pytest.raises(OffsetAlignmentError) as error:
        align_token_offsets("alpha beta", ["alpha", "gamma"])

    assert error.value.token_index == 1
    assert error.value.token == "gamma"
    assert error.value.cursor == 5
    assert error.value.message == "Token not found after cursor"


def test_align_token_offsets_rejects_non_whitespace_trailing_text() -> None:
    with pytest.raises(OffsetAlignmentError) as error:
        align_token_offsets("alpha beta extra", ["alpha", "beta"])

    assert error.value.token_index == 2
    assert error.value.token == ""
    assert error.value.cursor == 10
    assert error.value.message == "Non-whitespace text after final token"


def test_align_token_offsets_slices_match_tokens() -> None:
    text = "alpha\t(beta) 50% beta-gamma"
    tokens = ["alpha", "(beta)", "50%", "beta-gamma"]
    offsets = align_token_offsets(text, tokens)

    assert [text[start:end] for start, end in offsets] == tokens
