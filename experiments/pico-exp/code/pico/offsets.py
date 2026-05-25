"""Strict token-to-character offset alignment helpers."""

from __future__ import annotations


class OffsetAlignmentError(ValueError):
    """Raised when official tokens cannot be exactly aligned to text."""

    def __init__(self, message: str, token_index: int, token: str, cursor: int) -> None:
        super().__init__(message)
        self.message = message
        self.token_index = token_index
        self.token = token
        self.cursor = cursor


def align_token_offsets(text: str, tokens: list[str]) -> list[tuple[int, int]]:
    """Align official tokens to exact character offsets in text.

    Tokens are matched in order. Between the previous token end and the next
    token start, only whitespace may be skipped. No normalization is applied.
    """
    offsets: list[tuple[int, int]] = []
    cursor = 0

    for token_index, token in enumerate(tokens):
        if token == "":
            raise OffsetAlignmentError("Empty token cannot be aligned", token_index, token, cursor)

        start = text.find(token, cursor)
        if start == -1:
            raise OffsetAlignmentError("Token not found after cursor", token_index, token, cursor)

        skipped = text[cursor:start]
        if any(not character.isspace() for character in skipped):
            raise OffsetAlignmentError("Non-whitespace text before token", token_index, token, cursor)

        end = start + len(token)
        if text[start:end] != token:
            raise OffsetAlignmentError("Aligned slice does not match token", token_index, token, cursor)
        if start < cursor or end < start:
            raise OffsetAlignmentError("Token offsets are not monotonic", token_index, token, cursor)

        offsets.append((start, end))
        cursor = end

    trailing = text[cursor:]
    if any(not character.isspace() for character in trailing):
        raise OffsetAlignmentError("Non-whitespace text after final token", len(tokens), "", cursor)

    if len(offsets) != len(tokens):
        token_index = len(offsets)
        token = tokens[token_index] if token_index < len(tokens) else ""
        raise OffsetAlignmentError("Offset count does not match token count", token_index, token, cursor)

    return offsets
