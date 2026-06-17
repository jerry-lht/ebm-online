"""Deterministic study-result extraction method."""

from __future__ import annotations

import re
from typing import Any

from ebm_backend.online_pipeline.infrastructure.methods.meta_analysis.base import StudyResultsMethod


class Method(StudyResultsMethod):
    def run(self, *, instance: dict[str, Any], articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return predict_study_result_rows(instance=instance, articles=articles)


def predict_study_result_rows(*, instance: dict[str, Any], articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    setting = instance.get("analysis_setting") or {}
    data_type = setting.get("data_type")
    comparison = setting.get("comparison") or {}
    outcome = setting.get("outcome") or {}
    subgroup = setting.get("subgroup") or {}
    article_by_study = {str(article.get("study_id") or ""): article for article in articles}
    rows: list[dict[str, Any]] = []
    for study_id in instance.get("included_studies") or []:
        article = article_by_study.get(str(study_id))
        if not article:
            continue
        result_data = _extract_result_data(article=article, data_type=data_type)
        if result_data is None:
            continue
        rows.append(
            {
                "row_id": f"rule-row::{instance['instance_id']}::{_slug(str(study_id))}",
                "setting_id": setting.get("setting_id"),
                "study_id": str(study_id),
                "study_year": _study_year(article),
                "footnote": None,
                "extraction_status": "extracted",
                "data_type": data_type,
                "comparison": {
                    "experimental_arm": comparison.get("experimental"),
                    "control_arm": comparison.get("comparator"),
                },
                "outcome": {
                    "label": outcome.get("label"),
                    "timepoint": (setting.get("timepoint") or {}).get("label"),
                },
                "subgroup": subgroup,
                "result_data": result_data,
                "source": {
                    "method": "method_test",
                    "article_id": article.get("article_id"),
                    "table_id": result_data.pop("_table_id"),
                },
            }
        )
    return rows


def predict_study_result_rows_llm(*, instance: dict[str, Any], llm_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    setting = instance.get("analysis_setting") or {}
    comparison = setting.get("comparison") or {}
    outcome = setting.get("outcome") or {}
    subgroup = setting.get("subgroup") or {}
    data_type = setting.get("data_type")
    rows = []
    for item in llm_rows:
        if not isinstance(item, dict):
            continue
        result_data = item.get("result_data") if isinstance(item.get("result_data"), dict) else {}
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        if data_type == "Dichotomous":
            coerced = {
                "experimental_events": _optional_int(result_data.get("experimental_events")),
                "experimental_total": _optional_int(result_data.get("experimental_total")),
                "control_events": _optional_int(result_data.get("control_events")),
                "control_total": _optional_int(result_data.get("control_total")),
            }
        else:
            coerced = {
                "experimental_mean": _optional_float(result_data.get("experimental_mean")),
                "experimental_sd": _optional_float(result_data.get("experimental_sd")),
                "experimental_total": _optional_int(result_data.get("experimental_total")),
                "control_mean": _optional_float(result_data.get("control_mean")),
                "control_sd": _optional_float(result_data.get("control_sd")),
                "control_total": _optional_int(result_data.get("control_total")),
            }
        if any(value is None for value in coerced.values()):
            continue
        study_id = str(item.get("study_id") or "")
        if not study_id:
            continue
        rows.append(
            {
                "row_id": f"llm-row::{instance['instance_id']}::{_slug(study_id)}",
                "setting_id": setting.get("setting_id"),
                "study_id": study_id,
                "study_year": _nullable_text(item.get("study_year")),
                "footnote": None,
                "extraction_status": "extracted",
                "data_type": data_type,
                "comparison": {
                    "experimental_arm": comparison.get("experimental"),
                    "control_arm": comparison.get("comparator"),
                },
                "outcome": {
                    "label": outcome.get("label"),
                    "timepoint": (setting.get("timepoint") or {}).get("label"),
                },
                "subgroup": subgroup,
                "result_data": coerced,
                "source": {
                    "method": "method_test",
                    "article_id": _nullable_text(source.get("article_id")),
                    "table_id": _nullable_text(source.get("table_id")),
                    "reason": _nullable_text(source.get("reason")),
                },
            }
        )
    return rows


def _extract_result_data(*, article: dict[str, Any], data_type: str | None) -> dict[str, Any] | None:
    for table in article.get("tables") or []:
        table_id = table.get("table_id")
        numbers = _table_numbers(table)
        if data_type == "Dichotomous" and len(numbers) >= 4:
            return {
                "experimental_events": int(numbers[0]),
                "experimental_total": int(numbers[1]),
                "control_events": int(numbers[2]),
                "control_total": int(numbers[3]),
                "_table_id": table_id,
            }
        if data_type == "Continuous" and len(numbers) >= 6:
            return {
                "experimental_mean": float(numbers[0]),
                "experimental_sd": float(numbers[1]),
                "experimental_total": int(numbers[2]),
                "control_mean": float(numbers[3]),
                "control_sd": float(numbers[4]),
                "control_total": int(numbers[5]),
                "_table_id": table_id,
            }
    return None


def _table_numbers(table: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for row in table.get("rows") or []:
        for cell in row:
            if not isinstance(cell, str):
                continue
            for match in re.findall(r"-?\d+(?:\.\d+)?", cell):
                try:
                    values.append(float(match))
                except ValueError:
                    continue
    return values


def _study_year(article: dict[str, Any]) -> str | None:
    metadata = article.get("metadata") or {}
    for key in ("year", "published_year", "publication_year"):
        value = metadata.get(key)
        if value:
            return str(value)
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return cleaned or "study"


def build_method() -> Method:
    return Method()
