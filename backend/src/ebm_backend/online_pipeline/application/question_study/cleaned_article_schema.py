"""Validation for cleaned article payload schema (xml_content-only)."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_LEVEL_KEYS = ("study_id", "metadata", "derived", "xml_content")


def validate_cleaned_article_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("cleaned article payload must be an object")

    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
    if missing:
        raise ValueError(f"cleaned article payload missing required keys: {', '.join(missing)}")

    xml_content = payload.get("xml_content")
    if not isinstance(xml_content, dict):
        raise ValueError("cleaned article payload xml_content must be an object")

    sections = xml_content.get("sections")
    tables = xml_content.get("tables")
    if not isinstance(sections, list):
        raise ValueError("cleaned article payload xml_content.sections must be a list")
    if not isinstance(tables, list):
        raise ValueError("cleaned article payload xml_content.tables must be a list")

    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ValueError(f"cleaned article payload xml_content.sections[{idx}] must be an object")
        if "blocks" in section:
            raise ValueError(
                "legacy cleaned schema is not supported: sections[].blocks found; expected xml_content.sections[].text"
            )
        if not isinstance(section.get("section"), str):
            raise ValueError(f"cleaned article payload xml_content.sections[{idx}].section must be a string")
        if not isinstance(section.get("text"), str):
            raise ValueError(f"cleaned article payload xml_content.sections[{idx}].text must be a string")

    for idx, table in enumerate(tables):
        if not isinstance(table, dict):
            raise ValueError(f"cleaned article payload xml_content.tables[{idx}] must be an object")
        section_path = table.get("section_path")
        raw_xml = table.get("raw_xml")
        if not isinstance(section_path, list) or not all(isinstance(item, str) for item in section_path):
            raise ValueError(
                f"cleaned article payload xml_content.tables[{idx}].section_path must be a list of strings"
            )
        if not isinstance(raw_xml, str):
            raise ValueError(f"cleaned article payload xml_content.tables[{idx}].raw_xml must be a string")

    return payload

