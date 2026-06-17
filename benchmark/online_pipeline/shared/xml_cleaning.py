"""PMC/JATS XML cleaning for benchmark article fixtures.

Adapted from `sr-cleaned/exports/xml_cleaning_reference/code/clean_pmc_xml.py`.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SKIP_XML_TAGS = {
    "fig",
    "ref-list",
    "back",
    "ack",
    "app-group",
    "supplementary-material",
}

BACK_MATTER_SECTION_TITLE_MAP = {
    "acknowledgement": "Acknowledgements",
    "acknowledgements": "Acknowledgements",
    "acknowledgment": "Acknowledgements",
    "acknowledgments": "Acknowledgements",
    "funding": "Funding",
    "funding statement": "Funding",
    "financial support": "Funding",
    "competing interests": "Conflict of Interest",
    "conflicts of interest": "Conflict of Interest",
    "conflict of interest": "Conflict of Interest",
    "data availability": "Data Availability",
    "data availability statement": "Data Availability",
    "availability of data and materials": "Data Availability",
    "ethics statements": "Ethics",
    "ethics statement": "Ethics",
    "ethics approval and consent to participate": "Ethics",
    "institutional review board statement": "Ethics",
    "informed consent statement": "Ethics",
    "author contributions": "Author Contributions",
    "authors contributions": "Author Contributions",
    "trial registration": "Trial Registration",
    "declarations": "Declarations",
}

BACK_MATTER_SEC_TYPE_MAP = {
    "coi statement": "Conflict of Interest",
    "conflict": "Conflict of Interest",
    "data availability": "Data Availability",
    "ethics statement": "Ethics",
    "funding information": "Funding",
    "trial registration": "Trial Registration",
}


def extract_xml_content(xml_path: Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    article = root.find("article")
    if article is None:
        article = root
    paragraphs: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    body = article.find("body")
    if body is not None:
        _walk_xml_node(body, [], paragraphs, tables)

    for back in article.findall("back"):
        _walk_back_matter(back, paragraphs, tables)

    for floats_group in article.findall("floats-group"):
        _walk_float_tables(floats_group, ["floats-group"], tables)

    sections = _build_markdown_sections(paragraphs)
    return {
        "article_meta": {
            "pmcid": _article_id(article, "pmcid"),
            "pmid": _article_id(article, "pmid"),
            "doi": _article_id(article, "doi"),
            "title": _article_title(article),
        },
        "sections": sections,
        "tables": tables,
        "paragraph_count": len(paragraphs),
        "section_count": len(sections),
        "table_count": len(tables),
    }


def _clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_label(value: str) -> str:
    text = (value or "").lower().strip()
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _xml_tag_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _direct_child_text(node: ET.Element, child_name: str) -> str:
    for child in node:
        if _xml_tag_name(child.tag) == child_name:
            return _clean_text("".join(child.itertext()))
    return ""


def _xml_to_string(node: ET.Element) -> str:
    return ET.tostring(node, encoding="unicode")


def _article_id(article: ET.Element, pub_id_type: str) -> str:
    for node in article.findall(f".//article-id[@pub-id-type='{pub_id_type}']"):
        value = _clean_text(node.text or "")
        if value:
            return value
    return ""


def _article_title(article: ET.Element) -> str:
    title_group = article.find(".//title-group/article-title")
    if title_group is None:
        return ""
    return _clean_text("".join(title_group.itertext()))


def _canonical_back_section_name(node: ET.Element) -> str | None:
    tag = _xml_tag_name(node.tag)
    title_key = _normalize_label(_direct_child_text(node, "title"))
    if title_key in BACK_MATTER_SECTION_TITLE_MAP:
        return BACK_MATTER_SECTION_TITLE_MAP[title_key]
    sec_type_key = _normalize_label(node.attrib.get("sec-type", ""))
    if sec_type_key in BACK_MATTER_SEC_TYPE_MAP:
        return BACK_MATTER_SEC_TYPE_MAP[sec_type_key]
    if tag == "ack":
        return "Acknowledgements"
    return None


def _back_matter_text_fallback(node: ET.Element, title: str) -> str:
    chunks: list[str] = []
    if _clean_text(node.text or ""):
        chunks.append(_clean_text(node.text or ""))
    for child in node:
        if _xml_tag_name(child.tag) == "title":
            if _clean_text(child.tail or ""):
                chunks.append(_clean_text(child.tail or ""))
            continue
        if _clean_text(child.tail or ""):
            chunks.append(_clean_text(child.tail or ""))
    text = " ".join(chunk for chunk in chunks if chunk).strip()
    if title and text.lower().startswith(title.lower()):
        text = text[len(title) :].strip(" :.-")
    return text


def _walk_back_matter(back: ET.Element, paragraphs: list[dict[str, Any]], tables: list[dict[str, Any]]) -> None:
    for child in back:
        tag = _xml_tag_name(child.tag)
        if tag not in {"ack", "notes", "sec"}:
            continue
        section_name = _canonical_back_section_name(child)
        if not section_name:
            continue

        section_path = [section_name]
        paragraph_start = len(paragraphs)
        table_start = len(tables)
        raw_title = _direct_child_text(child, "title")

        for grandchild in child:
            if _xml_tag_name(grandchild.tag) == "title":
                continue
            _walk_xml_node(grandchild, list(section_path), paragraphs, tables)

        if len(paragraphs) == paragraph_start and len(tables) == table_start:
            fallback_text = _back_matter_text_fallback(child, raw_title)
            if fallback_text:
                paragraphs.append({"section_path": section_path, "text": fallback_text})


def _walk_xml_node(
    node: ET.Element,
    section_path: list[str],
    paragraphs: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> None:
    tag = _xml_tag_name(node.tag)
    if tag in SKIP_XML_TAGS:
        return

    if tag == "sec":
        title = _direct_child_text(node, "title")
        next_path = section_path + [title] if title else list(section_path)
        for child in node:
            if _xml_tag_name(child.tag) == "title":
                continue
            _walk_xml_node(child, next_path, paragraphs, tables)
        return

    if tag == "p":
        text = _clean_text("".join(node.itertext()))
        if text:
            paragraphs.append({"section_path": list(section_path), "text": text})
        return

    if tag == "table-wrap":
        tables.append({"section_path": list(section_path), "raw_xml": _xml_to_string(node)})
        return

    for child in node:
        _walk_xml_node(child, list(section_path), paragraphs, tables)


def _walk_float_tables(node: ET.Element, section_path: list[str], tables: list[dict[str, Any]]) -> None:
    tag = _xml_tag_name(node.tag)
    if tag == "table-wrap":
        tables.append({"section_path": list(section_path), "raw_xml": _xml_to_string(node)})
        return
    for child in node:
        _walk_float_tables(child, list(section_path), tables)


def _markdown_heading(level: int, title: str) -> str:
    return f'{"#" * level} {title}'


def _build_markdown_sections(paragraphs: list[dict[str, Any]]) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_section_name: str | None = None
    current_section_record: dict[str, str] | None = None
    current_subpath: tuple[str, ...] | None = None

    for paragraph in paragraphs:
        section_path = [part for part in paragraph.get("section_path", []) if part]
        text = str(paragraph.get("text") or "")
        if not text:
            continue

        section_name = section_path[0] if section_path else "Front"
        subpath = tuple(section_path[1:])
        if section_name != current_section_name:
            current_section_record = {"section": section_name, "text": ""}
            sections.append(current_section_record)
            current_section_name = section_name
            current_subpath = None

        if current_section_record is None:
            continue

        chunks: list[str] = []
        if subpath and subpath != current_subpath:
            for index, title in enumerate(subpath):
                chunks.append(_markdown_heading(index + 2, title))
            current_subpath = subpath
        elif not subpath:
            current_subpath = None

        chunks.append(text)
        chunk_text = "\n\n".join(chunks)
        if current_section_record["text"]:
            current_section_record["text"] = f'{current_section_record["text"]}\n\n{chunk_text}'
        else:
            current_section_record["text"] = chunk_text

    return sections
