"""Tests for GRADE risk-of-bias LLM post-processing."""

from ebm_backend.online_pipeline.infrastructure.methods.grade.risk_of_bias import method_llm


def _payload(*footnotes: str) -> dict:
    return {
        "sof_context": {
            "footnote_texts": list(footnotes),
            "comment_text": "",
            "source_summary_of_findings_span_text": "",
        }
    }


def _judge(severity: str, levels=1, downgraded: str = "yes") -> dict:
    return {
        "domain": "risk_of_bias",
        "downgraded": downgraded,
        "severity": severity,
        "levels": levels,
        "level_evaluable": severity != "unclear",
        "rationale": "model rationale",
        "source_spans": [],
    }


def test_guardrail_blocks_study_level_bias_without_downgrade():
    result = method_llm._apply_sof_guardrails(
        _judge("serious"),
        _payload("High risk of bias for performance bias and unclear or high for allocation concealment"),
    )

    assert result["downgraded"] == "no"
    assert result["severity"] == "none"
    assert result["levels"] == 0


def test_guardrail_keeps_explicit_one_level_rob_downgrade():
    result = method_llm._apply_sof_guardrails(
        _judge("serious"),
        _payload("Downgraded one level for risk of bias; unclear information on blinding"),
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "serious"
    assert result["levels"] == 1


def test_guardrail_marks_ambiguous_level_as_downgraded_unclear():
    result = method_llm._apply_sof_guardrails(
        _judge("serious"),
        _payload("Downgraded due to high/unclear risk of bias"),
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "unclear"
    assert result["levels"] == "unclear"
    assert result["level_evaluable"] is False


def test_guardrail_preserves_three_level_rob_downgrade():
    result = method_llm._apply_sof_guardrails(
        _judge("very_serious", levels=2),
        _payload("Downgraded three levels for very serious risk of bias, serious imprecision, poor reporting of methods in the primary studies."),
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "very_serious"
    assert result["levels"] == 3


def test_guardrail_uses_matched_downgrade_clause_for_level():
    result = method_llm._apply_sof_guardrails(
        _judge("very_serious", levels=3),
        _payload(
            "Downgraded two levels for very serious risk of bias associated with poor reporting of methods in the primary studies.",
            "Clinical pregnancies 264 (3 studies) Low",
        ),
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "very_serious"
    assert result["levels"] == 2


def test_guardrail_does_not_treat_not_accounted_as_not_downgraded():
    result = method_llm._apply_sof_guardrails(
        _judge("none", levels=0, downgraded="no"),
        _payload(
            "Downgraded once for unclear risk of selection bias and other bias, where the effect of the clustering was not accounted for in the analysis; downgraded twice for imprecision due to a small number of events."
        ),
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "unclear"
    assert result["levels"] == "unclear"


def test_normalize_unclear_severity_matches_benchmark_semantics():
    result = method_llm._normalize_judgement(
        {
            "downgraded": "yes",
            "severity": "unclear",
            "levels": "unclear",
            "level_evaluable": False,
            "rationale": "ambiguous",
        }
    )

    assert result["downgraded"] == "yes"
    assert result["severity"] == "unclear"
    assert result["levels"] == "unclear"
    assert result["level_evaluable"] is False
