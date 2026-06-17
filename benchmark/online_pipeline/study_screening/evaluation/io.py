"""Study screening benchmark I/O and domain mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ebm_backend.online_pipeline.domain.article import (
    ArticleMetadata,
    ArticleSection,
    ArticleSource,
    ArticleXmlContent,
    CleanedArticle,
)
from ebm_backend.online_pipeline.domain.screening import ScreeningCriteria

from benchmark.online_pipeline.shared.jsonl import read_jsonl


def load_dataset(dataset_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    resolved = Path(dataset_dir)
    instances = read_jsonl(resolved / "instances.jsonl")
    gold_rows = read_jsonl(resolved / "gold.jsonl")
    return instances, {str(row["instance_id"]): row for row in gold_rows}


def screening_criteria_from_instance(instance: dict[str, Any]) -> ScreeningCriteria:
    payload = instance.get("screening_criteria") or instance.get("criteria") or {}
    return ScreeningCriteria(
        inclusion_criteria=list(payload.get("inclusion_criteria") or payload.get("inclusion") or []),
        exclusion_criteria=list(payload.get("exclusion_criteria") or payload.get("exclusion") or []),
        rationale=str(payload.get("rationale") or ""),
    )


def articles_from_instance(
    instance: dict[str, Any],
    *,
    section_policy: str = "abstract_plus_fulltext",
    max_abstract_chars: int | None = None,
    max_full_text_chars: int | None = 12000,
) -> list[CleanedArticle]:
    return [
        _article_from_payload(
            payload,
            section_policy=section_policy,
            max_abstract_chars=max_abstract_chars,
            max_full_text_chars=max_full_text_chars,
        )
        for payload in list(instance.get("articles") or [])
    ]


def _article_from_payload(
    payload: dict[str, Any],
    *,
    section_policy: str,
    max_abstract_chars: int | None,
    max_full_text_chars: int | None,
) -> CleanedArticle:
    metadata_payload = payload.get("metadata") or {}
    xml_payload = payload.get("xml_content") or {}
    source_payload = payload.get("source") or {}
    return CleanedArticle(
        study_id=str(payload["study_id"]),
        metadata=ArticleMetadata(
            title=str(metadata_payload.get("title") or payload.get("title") or ""),
            pmid=_optional_str(metadata_payload.get("pmid")),
            pmc_id=_optional_str(metadata_payload.get("pmc_id")),
            source_type=_optional_str(metadata_payload.get("source_type")),
            publication_year=_optional_str(metadata_payload.get("publication_year")),
            mesh_terms=list(metadata_payload.get("mesh_terms") or []),
            doi=_optional_str(metadata_payload.get("doi")),
        ),
        xml_content=ArticleXmlContent(
            sections=[
                ArticleSection(
                    section_id=str(section.get("section_id") or section.get("section") or section.get("title") or f"s{index}"),
                    title=str(section.get("title") or section.get("section") or ""),
                    text=_section_text(section, max_abstract_chars=max_abstract_chars, max_full_text_chars=max_full_text_chars),
                )
                for index, section in enumerate(
                    _filtered_sections(list(xml_payload.get("sections") or []), section_policy=section_policy),
                    start=1,
                )
            ]
        ),
        source=ArticleSource(
            database=str(source_payload.get("database") or "benchmark"),
            retrieval_rank=source_payload.get("retrieval_rank"),
            retrieval_score=source_payload.get("retrieval_score"),
            raw_source_url=_optional_str(source_payload.get("raw_source_url")),
            raw_record_id=_optional_str(source_payload.get("raw_record_id") or payload.get("study_id")),
        ),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _filtered_sections(sections: list[dict[str, Any]], *, section_policy: str) -> list[dict[str, Any]]:
    if section_policy == "abstract_plus_fulltext":
        return sections
    if section_policy == "abstract_only":
        return [section for section in sections if _section_kind(section) == "abstract"]
    raise ValueError(f"Unsupported section policy: {section_policy}")


def _section_text(section: dict[str, Any], *, max_abstract_chars: int | None, max_full_text_chars: int | None) -> str:
    text = str(section.get("text") or "")
    limit = max_abstract_chars if _section_kind(section) == "abstract" else max_full_text_chars
    return text if limit is None else text[:limit]


def _section_kind(section: dict[str, Any]) -> str:
    title = str(section.get("title") or section.get("section") or "").strip().lower()
    return "abstract" if title == "abstract" else "full_text"
