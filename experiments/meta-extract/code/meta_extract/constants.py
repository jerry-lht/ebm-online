"""Project constants for benchmark2-v2 item evaluation."""

from __future__ import annotations

DEFAULT_DEV_FRACTION = 0.2
DEFAULT_SPLIT_SEED = "meta-extract-benchmark2-v2-split-v1"
DEFAULT_EVIDENCE_MODE = "full-text"
RUN_SUBDIRS = (
    "instances",
    "predictions",
    "scores",
    "reports",
    "manifests",
    "logs",
)

SUPPORT_TASK = "support"
PROPOSAL_TASK = "proposal"
ORACLE_EXTRACTION_TASK = "oracle_extraction"
ROUTED_EXTRACTION_TASK = "routed_extraction"
TASK_NAMES = (
    SUPPORT_TASK,
    PROPOSAL_TASK,
    ORACLE_EXTRACTION_TASK,
    ROUTED_EXTRACTION_TASK,
)

ALLOWED_SUPPORT_STATUSES = ("supported", "not_supported", "uncertain")
ALLOWED_UNCERTAIN_REASONS = (
    "insufficient_evidence",
    "timepoint_granularity_mismatch",
    "multiple_plausible_interpretations",
)

DIRECT_FIELD_ORDER = [
    "Experimental N",
    "Control N",
    "Experimental cases",
    "Control cases",
    "Experimental mean",
    "Experimental SD",
    "Control mean",
    "Control SD",
    "GIV Mean",
    "GIV SE",
    "Mean",
    "Variance",
    "CI start",
    "CI end",
    "Footnotes",
]

DIRECT_FIELDS_BY_DATA_TYPE = {
    "Dichotomous": [
        "Experimental cases",
        "Experimental N",
        "Control cases",
        "Control N",
    ],
    "Continuous": [
        "Experimental mean",
        "Experimental SD",
        "Experimental N",
        "Control mean",
        "Control SD",
        "Control N",
    ],
    "Contrast level": [
        "GIV Mean",
        "GIV SE",
        "Mean",
        "Variance",
        "CI start",
        "CI end",
        "Footnotes",
    ],
}

TASK_SPECS = {
    SUPPORT_TASK: {
        "label": "Official Item Support",
        "instance_filename": "support_instances.jsonl",
        "prediction_filename": "support_predictions.jsonl",
        "run_summary_filename": "support_run_summary.json",
        "failed_filename": "support_failed_instances.jsonl",
        "score_filename": "support_scores.jsonl",
        "summary_filename": "support_summary.json",
        "report_sections": ("main", "per_data_type", "failures"),
    },
    PROPOSAL_TASK: {
        "label": "Open-world Item Proposal",
        "instance_filename": "proposal_instances.jsonl",
        "prediction_filename": "proposal_predictions.jsonl",
        "run_summary_filename": "proposal_run_summary.json",
        "failed_filename": "proposal_failed_instances.jsonl",
        "score_filename": "proposal_scores.jsonl",
        "summary_filename": "proposal_summary.json",
        "report_sections": ("main", "per_data_type", "error_buckets", "failures"),
    },
    ORACLE_EXTRACTION_TASK: {
        "label": "Oracle Extraction",
        "instance_filename": "oracle_extraction_instances.jsonl",
        "prediction_filename": "oracle_extraction_predictions.jsonl",
        "run_summary_filename": "oracle_extraction_run_summary.json",
        "failed_filename": "oracle_extraction_failed_instances.jsonl",
        "score_filename": "oracle_extraction_scores.jsonl",
        "summary_filename": "oracle_extraction_summary.json",
        "report_sections": ("main", "per_data_type", "per_field", "per_match_status", "failures"),
    },
    ROUTED_EXTRACTION_TASK: {
        "label": "Routed Extraction",
        "instance_filename": "routed_extraction_instances.jsonl",
        "prediction_filename": "routed_extraction_predictions.jsonl",
        "run_summary_filename": "routed_extraction_run_summary.json",
        "failed_filename": "routed_extraction_failed_instances.jsonl",
        "score_filename": "routed_extraction_scores.jsonl",
        "summary_filename": "routed_extraction_summary.json",
        "report_sections": ("main", "per_data_type", "error_buckets", "failures"),
    },
}
