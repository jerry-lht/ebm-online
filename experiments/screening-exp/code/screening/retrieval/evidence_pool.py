"""Evidence pool construction for criterion-wise screening."""

from __future__ import annotations

import re

from screening.schemas import EvidenceItem, InputSetting, ScreeningExample

MAX_EVIDENCE_CHARS = 1200
TARGET_EVIDENCE_CHARS = 900
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


def _split_long_text(text: str) -> list[str]:
    cleaned = text.strip()
    if len(cleaned) <= MAX_EVIDENCE_CHARS:
        return [cleaned]

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", cleaned) if part.strip()]
    if len(paragraphs) == 1:
        paragraphs = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(cleaned) if part.strip()]

    chunks: list[str] = []
    current = ""
    for part in paragraphs:
        part = part.strip()
        if not part:
            continue
        if len(part) > MAX_EVIDENCE_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(part), TARGET_EVIDENCE_CHARS):
                chunk = part[start : start + TARGET_EVIDENCE_CHARS].strip()
                if chunk:
                    chunks.append(chunk)
            continue
        candidate = f"{current} {part}".strip() if current else part
        if len(candidate) <= MAX_EVIDENCE_CHARS:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = part
    if current:
        chunks.append(current.strip())
    return chunks or [cleaned]


def build_evidence_pool(example: ScreeningExample, setting: InputSetting) -> list[EvidenceItem]:
    """Build section-level evidence items for one example and setting."""
    items: list[EvidenceItem] = []

    def add_item(*, text: str | None, source: str, section_id: str, title: str | None) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return
        chunks = _split_long_text(cleaned)
        for chunk_index, chunk_text in enumerate(chunks, start=1):
            chunk_suffix = f"__chunk_{chunk_index}" if len(chunks) > 1 else ""
            chunk_title = f"{title} [chunk {chunk_index}]" if len(chunks) > 1 and title else title
            items.append(
                EvidenceItem(
                    evidence_id=f"{example.example_id}::{section_id}{chunk_suffix}",
                    text=chunk_text,
                    source=source,
                    section_id=f"{section_id}{chunk_suffix}" if len(chunks) > 1 else section_id,
                    title=chunk_title,
                    metadata={
                        "example_id": example.example_id,
                        "chunk_index": chunk_index,
                        "chunk_count": len(chunks),
                        "original_section_id": section_id,
                    },
                )
            )

    if setting == InputSetting.full_text_only:
        for index, section in enumerate(example.full_text_sections, start=1):
            add_item(
                text=section.text,
                source=section.source or "full_text_sections",
                section_id=section.section_id or f"full_text_{index}",
                title=section.title or f"Section {index}",
            )
        return items

    if setting == InputSetting.abstract_plus_full_text:
        add_item(
            text=example.title,
            source="title",
            section_id="title",
            title="title",
        )
        add_item(
            text=example.abstract,
            source="abstract",
            section_id="abstract",
            title="abstract",
        )
        for index, section in enumerate(example.full_text_sections, start=1):
            add_item(
                text=section.text,
                source=section.source or "full_text_sections",
                section_id=section.section_id or f"full_text_{index}",
                title=section.title or f"Section {index}",
            )
        return items

    raise ValueError(
        "criterion-wise evidence pool supports only full_text_only and abstract_plus_full_text"
    )
