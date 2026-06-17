"""I/O helpers for Risk of Bias evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ebm_backend.online_pipeline.domain.article import (
    ArticleMetadata,
    ArticleSection,
    ArticleSource,
    ArticleTable,
    ArticleXmlContent,
    CleanedArticle,
)

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_dataset(dataset_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved = Path(dataset_dir)
    instances = read_jsonl(resolved / "instances.jsonl")
    gold_rows = read_jsonl(resolved / "gold.jsonl")
    article_index_rows = read_jsonl(resolved / "article_index.jsonl")
    dataset_root = _dataset_root_from_split(resolved)
    articles = {}
    for row in article_index_rows:
        article_id = str(row["article_id"])
        article_path = dataset_root / str(row["article_path"])
        articles[article_id] = json.loads(article_path.read_text(encoding="utf-8"))
    return instances, {str(row["instance_id"]): row for row in gold_rows}, articles


def cleaned_article_from_payload(payload: dict[str, Any]) -> CleanedArticle:
    metadata = payload.get("metadata") or {}
    source = payload.get("source") or {}
    return CleanedArticle(
        study_id=str(payload.get("study_id") or ""),
        metadata=ArticleMetadata(
            title=str(metadata.get("title") or ""),
            pmid=metadata.get("pmid"),
            pmc_id=metadata.get("pmc_id"),
            source_type=metadata.get("source_type"),
            publication_year=metadata.get("publication_year"),
            mesh_terms=[str(item) for item in (metadata.get("mesh_terms") or [])],
            doi=metadata.get("doi"),
        ),
        xml_content=ArticleXmlContent(
            sections=[
                ArticleSection(
                    section_id=str(section.get("section_id") or ""),
                    title=str(section.get("title") or section.get("section") or ""),
                    text=str(section.get("text") or ""),
                )
                for section in ((payload.get("xml_content") or {}).get("sections") or [])
                if isinstance(section, dict)
            ]
        ),
        tables=[
            ArticleTable(
                table_id=str(table.get("table_id") or ""),
                caption=str(table.get("caption") or ""),
                rows=_table_rows(table),
            )
            for table in (payload.get("tables") or [])
            if isinstance(table, dict)
        ],
        source=ArticleSource(
            database=str(source.get("database") or ""),
            retrieval_rank=source.get("retrieval_rank"),
            retrieval_score=source.get("retrieval_score"),
            raw_source_url=source.get("raw_source_url"),
            raw_record_id=source.get("raw_record_id"),
        )
        if source
        else None,
    )


def _table_rows(table: dict[str, Any]) -> list[dict[str, str]]:
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    normalized = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append({str(key): str(value) for key, value in row.items()})
    raw_xml = str(table.get("raw_xml") or "")
    section_path = table.get("section_path") if isinstance(table.get("section_path"), list) else []
    if raw_xml and not any("_raw_xml" in row for row in normalized):
        normalized.append({"_raw_xml": raw_xml, "_section_path": " > ".join(str(part) for part in section_path)})
    return normalized


def _dataset_root_from_split(dataset_dir: Path) -> Path:
    if dataset_dir.parent.name == "splits":
        return dataset_dir.parent.parent
    return dataset_dir
