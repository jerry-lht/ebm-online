"""Numerical data extraction from study full text."""

from __future__ import annotations

import asyncio
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.evidence_analysis.models import AnalysisSpec, EvidenceContext, ExtractedDataRow, ExtractionResult
from ebm_backend.online_pipeline.application.question_study.cleaned_article_schema import validate_cleaned_article_payload
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


class EvidenceContextBuilder:
    """Build compact evidence context from derived article JSON or candidate fallback."""

    def build(self, candidate: Any) -> EvidenceContext:
        article_path = _candidate_value(candidate, "article_path")
        if article_path and Path(article_path).exists():
            try:
                return self._from_article_json(candidate, Path(article_path))
            except (OSError, json.JSONDecodeError, TypeError):
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
        validate_cleaned_article_payload(payload)
        metadata = payload.get("metadata") or {}
        xml_content = payload.get("xml_content") or {}
        sections = xml_content.get("sections") or []
        abstract_parts: list[str] = []
        methods_parts: list[str] = []
        results_parts: list[str] = []
        tables: list[dict[str, str]] = []

        for section in sections:
            title = str(section.get("section") or "")
            key = _normalize_label(title)
            text = str(section.get("text") or "").strip()
            if not text:
                continue
            if "abstract" in key:
                abstract_parts.append(text)
            elif "method" in key or "material" in key:
                methods_parts.append(text)
            elif "result" in key:
                results_parts.append(text)

        for row in xml_content.get("tables") or []:
            raw_xml = str(row.get("raw_xml") or "").strip()
            if not raw_xml:
                continue
            tables.append(
                {
                    "raw_xml": raw_xml,
                    "section_path": "/".join(str(item) for item in (row.get("section_path") or []) if str(item).strip()),
                    "text": _table_raw_xml_text(raw_xml),
                }
            )

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
    _DEFAULT_CONCURRENCY = 8

    async def extract_with_llm(
        self,
        gateway: LLMGateway,
        *,
        analyses: list[AnalysisSpec],
        evidence_contexts: dict[str, EvidenceContext],
        concurrency: int | None = None,
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> ExtractionResult:
        prompt_template = load_prompt(self._PROMPT_NAME)
        response_schema = load_schema(self._PROMPT_NAME)
        semaphore = asyncio.Semaphore(_resolve_concurrency(concurrency, "MODULE3_EXTRACTION_CONCURRENCY", self._DEFAULT_CONCURRENCY))
        contexts = list(evidence_contexts.values())
        ordered_rows: list[ExtractedDataRow | None] = [None] * (len(contexts) * len(analyses))
        warnings: list[str] = []

        async def _extract_one(index: int, context: EvidenceContext, analysis: AnalysisSpec) -> None:
            async with semaphore:
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
                    ordered_rows[index] = self._row_from_payload(context.study_id, analysis, result.content)
                except Exception as exc:
                    warning = f"Extraction failed for {context.study_id}/{analysis.analysis_id}: {exc}"
                    warnings.append(warning)
                    ordered_rows[index] = ExtractedDataRow(
                        study_id=context.study_id,
                        analysis_id=analysis.analysis_id,
                        outcome_type=analysis.outcome_type,
                        effect_measure=analysis.effect_measure,
                        extraction_status="missing",
                        missing_reason=warning,
                    )

        tasks = []
        for context_index, context in enumerate(contexts):
            for analysis_index, analysis in enumerate(analyses):
                index = context_index * len(analyses) + analysis_index
                tasks.append(_extract_one(index, context, analysis))
        await asyncio.gather(*tasks)
        rows = [row for row in ordered_rows if row is not None]
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


def _table_raw_xml_text(raw_xml: str) -> str:
    try:
        node = ET.fromstring(raw_xml)
    except ET.ParseError:
        return _trim(raw_xml)
    text = " ".join(part.strip() for part in node.itertext() if str(part).strip())
    return _trim(re.sub(r"\s+", " ", text))


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


def _normalize_label(value: str) -> str:
    text = (value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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


def _resolve_concurrency(value: int | None, env_name: str, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    raw = os.getenv(env_name, str(default)).strip()
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else default
    except ValueError:
        return default
