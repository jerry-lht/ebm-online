"""Numerical data extraction from study full text."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import AnalysisSpec, EvidenceContext, ExtractedDataRow, ExtractionResult
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


class EvidenceContextBuilder:
    """Build compact evidence context from derived article JSON or candidate fallback."""

    def build(self, candidate: Any) -> EvidenceContext:
        article_path = _candidate_value(candidate, "article_path")
        if article_path and Path(article_path).exists():
            try:
                return self._from_article_json(candidate, Path(article_path))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        return EvidenceContext(
            study_id=_study_id(candidate),
            title=str(_candidate_value(candidate, "title") or ""),
            abstract=str(_candidate_value(candidate, "abstract") or ""),
            source_path=str(article_path) if article_path else None,
            full_text_available=False,
        )

    def _from_article_json(self, candidate: Any, path: Path) -> EvidenceContext:
        payload = json.loads(path.read_text(encoding="utf-8"))
        metadata = payload.get("metadata") or {}
        sections = payload.get("sections") or []
        abstract_parts: list[str] = []
        methods_parts: list[str] = []
        results_parts: list[str] = []
        tables: list[dict[str, str]] = []
        for section in sections:
            key = str(section.get("section_key") or section.get("section_title_normalized") or "").lower()
            title = str(section.get("section_title_normalized") or section.get("section_title_raw") or key)
            text = _section_text(section)
            if "abstract" in key:
                abstract_parts.append(text)
            elif "method" in key or "material" in key:
                methods_parts.append(text)
            elif "result" in key:
                results_parts.append(text)
            elif "table" in key:
                tables.extend(_section_tables(section))
            elif "table" in title.lower():
                tables.extend(_section_tables(section))
        return EvidenceContext(
            study_id=_study_id(candidate) or str(metadata.get("pmid") or metadata.get("pmc_id") or ""),
            title=str(_candidate_value(candidate, "title") or metadata.get("title") or ""),
            abstract=_trim("\n\n".join(part for part in abstract_parts if part) or str(_candidate_value(candidate, "abstract") or "")),
            methods=_trim("\n\n".join(part for part in methods_parts if part)),
            results=_trim("\n\n".join(part for part in results_parts if part)),
            tables=tables[:8],
            source_path=str(path),
            full_text_available=True,
        )


class DataExtractor:
    """Extract visible numerical data for each study-analysis pair."""

    _PROMPT_NAME = "data_extraction"

    async def extract_with_llm(
        self,
        gateway: LLMGateway,
        *,
        analyses: list[AnalysisSpec],
        evidence_contexts: dict[str, EvidenceContext],
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> ExtractionResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        rows: list[ExtractedDataRow] = []
        warnings: list[str] = []
        for context in evidence_contexts.values():
            for analysis in analyses:
                try:
                    result = await gateway.call(
                        task_type=self._PROMPT_NAME,
                        inputs={"analysis": asdict(analysis), "evidence_context": asdict(context)},
                        prompt_template=prompt_template,
                        prompt_vars={
                            "analysis_json": json.dumps(asdict(analysis), ensure_ascii=False),
                            "evidence_json": json.dumps(asdict(context), ensure_ascii=False),
                        },
                        response_schema=response_schema,
                        temperature=0.0,
                        cacheable=False,
                        run_id=run_id,
                        module="module3",
                        task_name="data_extraction",
                        study_id=context.study_id,
                        prompt_version=prompt_version,
                    )
                    rows.append(self._row_from_payload(context.study_id, analysis, result.content))
                except Exception as exc:
                    warning = f"Extraction failed for {context.study_id}/{analysis.analysis_id}: {exc}"
                    warnings.append(warning)
                    rows.append(
                        ExtractedDataRow(
                            study_id=context.study_id,
                            analysis_id=analysis.analysis_id,
                            outcome_type=analysis.outcome_type,
                            effect_measure=analysis.effect_measure,
                            extraction_status="missing",
                            missing_reason=warning,
                        )
                    )
        return ExtractionResult(rows=rows, warnings=warnings)

    def _row_from_payload(self, study_id: str, analysis: AnalysisSpec, content: dict[str, Any]) -> ExtractedDataRow:
        status = str(content.get("extraction_status") or "included")
        row = ExtractedDataRow(
            study_id=str(content.get("study_id") or study_id),
            analysis_id=str(content.get("analysis_id") or analysis.analysis_id),
            outcome_type=str(content.get("outcome_type") or analysis.outcome_type),
            effect_measure=str(content.get("effect_measure") or analysis.effect_measure),
            extraction_status=status,
            missing_reason=content.get("missing_reason"),
            exp_mean=_float_or_none(content.get("exp_mean")),
            exp_sd=_float_or_none(content.get("exp_sd")),
            exp_n=_int_or_none(content.get("exp_n")),
            ctrl_mean=_float_or_none(content.get("ctrl_mean")),
            ctrl_sd=_float_or_none(content.get("ctrl_sd")),
            ctrl_n=_int_or_none(content.get("ctrl_n")),
            exp_events=_int_or_none(content.get("exp_events")),
            ctrl_events=_int_or_none(content.get("ctrl_events")),
            giv_effect=_float_or_none(content.get("giv_effect")),
            giv_se=_float_or_none(content.get("giv_se")),
            evidence_spans=[str(item) for item in content.get("evidence_spans") or [] if str(item).strip()],
            notes=str(content.get("notes") or ""),
        )
        if row.extraction_status != "included" and _has_required_raw_values(row):
            return ExtractedDataRow(
                study_id=row.study_id,
                analysis_id=row.analysis_id,
                outcome_type=row.outcome_type,
                effect_measure=row.effect_measure,
                extraction_status="included",
                missing_reason=None,
                exp_mean=row.exp_mean,
                exp_sd=row.exp_sd,
                exp_n=row.exp_n,
                ctrl_mean=row.ctrl_mean,
                ctrl_sd=row.ctrl_sd,
                ctrl_n=row.ctrl_n,
                exp_events=row.exp_events,
                ctrl_events=row.ctrl_events,
                giv_effect=row.giv_effect,
                giv_se=row.giv_se,
                evidence_spans=row.evidence_spans,
                notes=(row.notes + " " if row.notes else "") + "Status normalized because required raw values were present.",
            )
        return row


def _section_text(section: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in section.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "table":
            continue
        text = block.get("text_md") or block.get("text") or ""
        if text:
            parts.append(str(text))
    return _trim("\n".join(parts))


def _section_tables(section: dict[str, Any]) -> list[dict[str, str]]:
    tables: list[dict[str, str]] = []
    for block in section.get("blocks") or []:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        tables.append(
            {
                "table_id": str(block.get("table_id") or ""),
                "title": str(block.get("table_title") or ""),
                "caption": str(block.get("table_caption") or ""),
                "text": _trim(str(block.get("table_text_raw") or "")),
            }
        )
    return tables


def _trim(text: str, limit: int = 12000) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rsplit(" ", 1)[0]


def _candidate_value(candidate: Any, key: str) -> Any:
    if isinstance(candidate, dict):
        return candidate.get(key)
    return getattr(candidate, key, None)


def _study_id(candidate: Any) -> str:
    return str(_candidate_value(candidate, "study_id") or _candidate_value(candidate, "pmid") or "unknown")


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _has_required_raw_values(row: ExtractedDataRow) -> bool:
    measure = row.effect_measure.upper()
    if measure in {"RR", "OR"}:
        return (
            row.exp_events is not None
            and row.ctrl_events is not None
            and row.exp_n is not None
            and row.ctrl_n is not None
        )
    if measure in {"MD", "SMD"}:
        return (
            row.exp_mean is not None
            and row.exp_sd is not None
            and row.exp_n is not None
            and row.ctrl_mean is not None
            and row.ctrl_sd is not None
            and row.ctrl_n is not None
        )
    if measure in {"HR", "GIV"}:
        return row.giv_effect is not None and row.giv_se is not None
    return False
