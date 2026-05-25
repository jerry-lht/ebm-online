"""Criterion planning for CSMeD-FT criterion-wise screening."""

from __future__ import annotations

from screening.schemas import CriterionGroup, CriterionSpec, ScreeningExample

REVIEW_CLAUSES_MODE = "review_clauses"
FALLBACK_MODE = "fallback_question_only"


def build_csmed_criterion_specs(example: ScreeningExample) -> tuple[list[CriterionSpec], str]:
    """Build benchmark-aligned criterion specs from review inclusion/exclusion clauses."""
    inclusion = [item.strip() for item in example.criteria.inclusion if item and item.strip()]
    exclusion = [item.strip() for item in example.criteria.exclusion if item and item.strip()]
    clause_metadata = _parsed_clause_metadata_by_group(example)

    specs: list[CriterionSpec] = []
    for index, clause in enumerate(inclusion, start=1):
        metadata = {
            "source": "review_inclusion_clause",
            "clause_index": index,
            **_metadata_for_clause(clause_metadata["inclusion"], clause, index),
        }
        specs.append(
            CriterionSpec(
                criterion_id=f"inc_{index}",
                criterion_group=CriterionGroup.inclusion,
                criterion_text=clause,
                required=True,
                metadata=metadata,
            )
        )
    for index, clause in enumerate(exclusion, start=1):
        metadata = {
            "source": "review_exclusion_clause",
            "clause_index": index,
            **_metadata_for_clause(clause_metadata["exclusion"], clause, index),
        }
        specs.append(
            CriterionSpec(
                criterion_id=f"exc_{index}",
                criterion_group=CriterionGroup.exclusion,
                criterion_text=clause,
                required=True,
                metadata=metadata,
            )
        )

    if specs:
        return specs, REVIEW_CLAUSES_MODE

    question_text = (example.question or "").strip() or "Study relevance to the review question."
    fallback_specs = [
        CriterionSpec(
            criterion_id="inc_1",
            criterion_group=CriterionGroup.inclusion,
            criterion_text=question_text,
            required=True,
            metadata={"source": "fallback_question"},
        ),
        CriterionSpec(
            criterion_id="exc_1",
            criterion_group=CriterionGroup.exclusion,
            criterion_text="Explicit evidence that the study should be excluded from this review.",
            required=True,
            metadata={"source": "fallback_exclusion_signal"},
        ),
    ]
    return fallback_specs, FALLBACK_MODE


def _parsed_clause_metadata_by_group(example: ScreeningExample) -> dict[str, list[dict[str, str]]]:
    raw_items = example.criteria.raw.get("parsed_review_clauses")
    grouped: dict[str, list[dict[str, str]]] = {"inclusion": [], "exclusion": []}
    if not isinstance(raw_items, list):
        return grouped
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        group = str(item.get("group", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if group not in grouped or not text:
            continue
        grouped[group].append(
            {
                "text": text,
                "section": str(item.get("section") or "").strip(),
                "clause_source_mode": str(item.get("source_mode") or "").strip(),
            }
        )
    return grouped


def _metadata_for_clause(
    candidates: list[dict[str, str]],
    clause_text: str,
    clause_index: int,
) -> dict[str, str]:
    if clause_index - 1 < len(candidates):
        candidate = candidates[clause_index - 1]
        if candidate.get("text") == clause_text:
            return {
                key: value
                for key, value in candidate.items()
                if key != "text" and value
            }
    for candidate in candidates:
        if candidate.get("text") == clause_text:
            return {
                key: value
                for key, value in candidate.items()
                if key != "text" and value
            }
    return {}
