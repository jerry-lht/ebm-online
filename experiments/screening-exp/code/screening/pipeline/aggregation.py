"""Local conservative aggregation for criterion-wise screening."""

from __future__ import annotations

from screening.schemas import (
    AggregationResult,
    CriterionJudgmentValue,
    Decision,
    ScreeningPrediction,
)


def aggregate_csmed_criterion_judgments(
    prediction: ScreeningPrediction,
    criterion_specs: list[object],
) -> AggregationResult:
    """Aggregate criterion-level judgments into a binary screening decision."""
    criterion_ids = list(prediction.criterion_judgments)

    for criterion_id, judgment in prediction.criterion_judgments.items():
        if criterion_id.startswith("exc_") and judgment.judgment == CriterionJudgmentValue.yes:
            return AggregationResult(
                final_decision=Decision.exclude,
                aggregation_status="exclude_hard",
                failed_criterion=criterion_id,
                main_reason=f"Excluded because {criterion_id} was judged yes.",
                metadata={"trigger_group": "exclusion"},
            )

    for criterion_id, judgment in prediction.criterion_judgments.items():
        if criterion_id.startswith("inc_") and judgment.judgment == CriterionJudgmentValue.no:
            return AggregationResult(
                final_decision=Decision.exclude,
                aggregation_status="exclude_hard",
                failed_criterion=criterion_id,
                main_reason=f"Excluded because {criterion_id} was judged no.",
                metadata={"trigger_group": "inclusion"},
            )

    unclear_ids: list[str] = []
    for criterion_id, judgment in prediction.criterion_judgments.items():
        if judgment.judgment == CriterionJudgmentValue.unclear:
            unclear_ids.append(criterion_id)
    if unclear_ids:
        return AggregationResult(
            final_decision=Decision.include,
            aggregation_status="needs_review",
            failed_criterion=None,
            main_reason="Conservative include because criterion judgments remain unclear: "
            + ", ".join(unclear_ids),
            metadata={"unclear_criteria": unclear_ids},
        )

    return AggregationResult(
        final_decision=Decision.include,
        aggregation_status="include_clear",
        failed_criterion=None,
        main_reason="Included because no exclusion criterion triggered and no required inclusion criterion failed.",
        metadata={"criterion_count": len(criterion_ids)},
    )


def apply_aggregation_to_prediction(
    prediction: ScreeningPrediction,
    aggregation_result: AggregationResult,
) -> ScreeningPrediction:
    """Apply the local aggregation result to a criterion-wise prediction."""
    updated = prediction.model_copy(deep=True)
    updated.decision = aggregation_result.final_decision
    updated.failed_criterion = aggregation_result.failed_criterion
    updated.main_reason = aggregation_result.main_reason
    updated.evidence_spans = aggregation_result.evidence_spans
    updated.metadata.update(
        {
            "aggregation_status": aggregation_result.aggregation_status,
            **aggregation_result.metadata,
        }
    )
    return updated
