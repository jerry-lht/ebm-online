"""Batch runner for Risk of Bias workflow evolution.

This script runs a small set of studies end-to-end and writes:
- batch_results.json: machine-readable outputs and audit trace
- report.md: compact human-readable error analysis
"""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evaluator import RoBEvaluator
from main import _canonical_domain
from schemas import RiskOfBiasAssessment, RoBDomain


CORE_DOMAINS = {
    "random sequence generation",
    "allocation concealment",
    "blinding of participants and personnel",
    "blinding of outcome assessment",
    "incomplete outcome data",
}

EXTERNAL_GT_RE = re.compile(
    r"\b(mail|e-mail|email|author|contact|correspondence|protocol|registry|registration|clinicaltrials|review author)\b",
    re.I,
)
FIGURE_TABLE_RE = re.compile(r"\b(fig(?:ure)?|table|appendix|supplement)\b", re.I)
NOT_REPORTED_RE = re.compile(
    r"not (reported|provided|described)|details not provided|insufficient|unclear",
    re.I,
)


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_standard_rob_study(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    risk_of_bias = data.get("risk_of_bias") or []
    domains = {
        _canonical_domain(item.get("domain", ""))
        for item in risk_of_bias
        if isinstance(item, dict)
    }
    return CORE_DOMAINS.issubset(domains)


def text_contains_support_evidence(data: dict, min_hits: int = 2) -> bool:
    """Heuristic guard against mismatched XML/article and RoB annotations."""
    article_text = " ".join(
        section.get("text", "")
        for section in data.get("xml_content", {}).get("sections", [])
        if isinstance(section, dict)
    ).lower()
    if not article_text:
        return False

    hits = 0
    for item in data.get("risk_of_bias") or []:
        if not isinstance(item, dict):
            continue
        if _canonical_domain(item.get("domain", "")) not in CORE_DOMAINS:
            continue
        support = (item.get("support_text") or "").lower()
        phrases = extract_support_phrases(support)
        if any(phrase in article_text for phrase in phrases):
            hits += 1
    return hits >= min_hits


def extract_support_phrases(text: str) -> list[str]:
    """Extract medium-specific phrases from support text for match filtering."""
    text = re.sub(r"\s+", " ", text).strip().lower()
    if not text:
        return []

    candidates = re.findall(r'"([^"]{18,120})"', text)
    tokens = re.findall(r"[a-z0-9][a-z0-9\-']+", text)

    stop = {
        "risk",
        "bias",
        "unclear",
        "low",
        "high",
        "randomised",
        "randomized",
        "allocation",
        "concealment",
        "blinding",
        "outcome",
        "assessment",
        "participants",
        "personnel",
        "reported",
        "study",
        "authors",
        "patients",
        "groups",
        "intervention",
        "control",
    }
    content_tokens = [token for token in tokens if token not in stop and len(token) > 3]

    for n in (6, 5, 4):
        for i in range(max(len(content_tokens) - n + 1, 0)):
            phrase = " ".join(content_tokens[i : i + n])
            if len(phrase) >= 20:
                candidates.append(phrase)

    # Keep only phrases specific enough to reduce false positives.
    phrases = []
    for phrase in candidates:
        phrase = phrase.strip(" .;:,()[]{}")
        if len(phrase) >= 20 and phrase not in phrases:
            phrases.append(phrase)
    return phrases[:12]


def select_studies(
    dataset_dir: Path,
    limit: int,
    pmids: list[str] | None,
    require_support_filter: bool = True,
) -> list[Path]:
    if pmids:
        paths = []
        for pmid in pmids:
            path = dataset_dir / f"{pmid}.json"
            if not path.exists():
                raise FileNotFoundError(f"Study JSON not found for PMID {pmid}: {path}")
            paths.append(path)
        return paths

    selected = []
    for path in sorted(dataset_dir.glob("*.json")):
        try:
            data = load_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        if is_standard_rob_study(data) and (
            not require_support_filter or text_contains_support_evidence(data)
        ):
            selected.append(path)
        if len(selected) >= limit:
            break
    return selected


def format_gt_lookup(ground_truth: list[dict]) -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = {}
    for item in ground_truth:
        lookup.setdefault(_canonical_domain(item["domain"]), []).append(item)
    return lookup


def judgement_match(prediction: str, candidates: list[dict]) -> tuple[bool | None, str]:
    if not candidates:
        return None, "NOT FOUND"
    gt_values = sorted({item.get("judgement", "") for item in candidates})
    if len(gt_values) == 1:
        return prediction == gt_values[0], gt_values[0]
    return prediction in gt_values, " / ".join(gt_values)


def classify_gt_observability(
    candidates: list[dict],
    article_text: str,
) -> dict[str, Any]:
    """Classify whether GT support appears observable from the article XML."""
    support = " | ".join(
        str(item.get("support_text") or "") for item in candidates if isinstance(item, dict)
    )
    article_lower = article_text.lower()
    phrases = extract_support_phrases(support)
    phrase_hits = [phrase for phrase in phrases if phrase in article_lower]

    if not candidates:
        status = "not_found"
        observable = False
    elif EXTERNAL_GT_RE.search(support):
        status = "external_or_review_context"
        observable = False
    elif phrase_hits:
        status = "article_text_match"
        observable = True
    elif NOT_REPORTED_RE.search(support):
        status = "article_absence_or_unclear"
        observable = True
    elif FIGURE_TABLE_RE.search(support):
        status = "figure_table_or_supplement_reference"
        observable = None
    elif phrases:
        status = "no_support_phrase_match"
        observable = False
    else:
        status = "unknown"
        observable = None

    return {
        "gt_observability": status,
        "gt_observable_in_article": observable,
        "gt_support_phrase_hits": phrase_hits[:5],
    }


def classify_error(
    domain: str,
    prediction: str,
    gt: str,
    reasoning: str,
    support: str,
    gt_observability: str = "",
) -> str:
    text = f"{reasoning}\n{support}".lower()
    if gt == "NOT FOUND":
        return "label_mapping_or_missing_gt"
    if gt_observability == "external_or_review_context":
        return "external_or_review_context_needed"
    if gt_observability == "no_support_phrase_match":
        return "gt_support_not_found_in_article_text"
    if gt_observability == "figure_table_or_supplement_reference":
        return "figure_table_or_supplement_needed"
    if prediction == "Unclear risk" and gt in {"Low risk", "High risk"}:
        return "under-called_due_to_missing_or_underused_evidence"
    if prediction in {"Low risk", "High risk"} and gt == "Unclear risk":
        return "over-inferred_from_sparse_reporting"
    if "blinding" in domain.lower() and prediction != gt:
        return "blinding_outcome_type_or_role_confusion"
    if "allocation" in domain.lower() and prediction != gt:
        return "allocation_concealment_detail_threshold"
    if "incomplete outcome data" in domain.lower() and prediction != gt:
        return "attrition_balance_or_missing_data_handling"
    if "not reported" in text or "insufficient" in text:
        return "evidence_retrieval_or_reporting_gap"
    return "criteria_application_mismatch"


def truncate(text: str | None, limit: int = 900) -> str:
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rsplit(" ", 1)[0] + "..."


def is_timeout_error(exc: Exception) -> bool:
    """Return True for timeout-like exceptions from OpenAI/http layers."""
    text = f"{type(exc).__name__}: {exc}".lower()
    return isinstance(exc, TimeoutError) or "timeout" in text or "timed out" in text


def is_transient_provider_error(exc: Exception) -> bool:
    """Return True for retryable provider/gateway failures."""
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(
        marker in text
        for marker in (
            "internalservererror",
            "bad gateway",
            "502",
            "503",
            "504",
            "rate limit",
            "temporarily unavailable",
            "connection error",
            "connection reset",
        )
    )


def build_review_context(data: dict, mode: str) -> str:
    """Build optional review-level context supplied to evidence extraction."""
    if mode == "none":
        return ""
    if mode == "characteristics":
        return json.dumps(
            data.get("characteristics", {}),
            ensure_ascii=False,
            indent=2,
        )
    raise ValueError(f"Unknown review context mode: {mode}")


def run_one_study(
    evaluator: RoBEvaluator,
    study_path: Path,
    mode: str,
    review_context_mode: str = "none",
) -> dict:
    data = load_json(study_path)
    xml_content = data.get("xml_content", {})
    sr_pico = data.get("sr_pico", "")
    study_id = data.get("study_id")
    pmid = data.get("pmid") or study_path.stem
    ground_truth = data.get("risk_of_bias", [])

    article_text = evaluator._format_article(xml_content)
    gt_lookup = format_gt_lookup(ground_truth)
    review_context = build_review_context(data, review_context_mode)

    trace: dict[str, Any] = {
        "study_id": study_id,
        "pmid": pmid,
        "path": str(study_path),
        "mode": mode,
        "article_chars": len(article_text),
        "model": evaluator.model,
        "request_timeout": evaluator.request_timeout,
        "review_context_mode": review_context_mode,
        "review_context_chars": len(review_context),
        "domains": [],
    }

    started = time.perf_counter()

    if mode == "joint":
        joint_text = evaluator._build_methodology_context(
            article_text,
            max_chars=evaluator.joint_max_chars,
        )
        trace["joint_context_chars"] = len(joint_text)
        trace["joint_context_preview"] = truncate(joint_text)
        assessment = evaluator.evaluate(
            xml_content=xml_content,
            sr_pico=sr_pico,
            study_id=study_id,
            pmid=pmid,
            mode=mode,
            review_context=review_context,
        )
        methodology = None
    elif mode == "evidence":
        evidence_text = evaluator._build_methodology_context(
            article_text,
            max_chars=evaluator.extraction_max_chars,
        )
        trace["extraction_context_chars"] = len(evidence_text)
        trace["extraction_context_preview"] = truncate(evidence_text)

        extraction_started = time.perf_counter()
        evidence_table = evaluator._extract_evidence_table(
            sr_pico,
            evidence_text,
            review_context=review_context,
        )
        trace["extraction_seconds"] = round(time.perf_counter() - extraction_started, 2)
        trace["evidence_table"] = evidence_table.model_dump(mode="json")

        results = []
        for evidence in evidence_table.results:
            domain_started = time.perf_counter()
            result = evaluator._judge_domain_from_evidence(
                evidence.domain,
                evidence.model_dump_json(indent=2),
            )
            domain_seconds = round(time.perf_counter() - domain_started, 2)
            results.append(result)
            trace["domains"].append(
                {
                    "domain": evidence.domain.value,
                    "domain_context_chars": 0,
                    "domain_context_preview": "",
                    "evidence": evidence.model_dump(mode="json"),
                    "prediction": result.judgement.value,
                    "support_text": result.support_text,
                    "support_context": [
                        item.model_dump() for item in result.support_context
                    ],
                    "reasoning": result.reasoning,
                    "seconds": domain_seconds,
                }
            )

        assessment = RiskOfBiasAssessment(
            study_id=study_id,
            pmid=pmid,
            results=results,
        )
    elif mode in {"direct", "targeted", "audited"}:
        attrition_clues = evaluator._extract_attrition_numeric_clues(article_text)
        trace["attrition_clues_chars"] = len(attrition_clues)
        if attrition_clues:
            trace["attrition_clues_preview"] = truncate(attrition_clues, 1200)
        results = []
        for domain in RoBDomain:
            domain_context = evaluator._build_domain_context(
                domain,
                article_text,
                max_chars=evaluator.domain_context_max_chars,
            )
            supplementary_context = evaluator._build_supplementary_context(
                domain,
                attrition_clues=attrition_clues,
            )
            calibration_evidence = evaluator._combine_calibration_evidence(
                domain_context,
                supplementary_context,
            )

            domain_started = time.perf_counter()
            if mode == "audited":
                result = evaluator._judge_domain_audited(
                    domain,
                    sr_pico,
                    domain_context,
                    supplementary_context=supplementary_context,
                    calibration_evidence=calibration_evidence,
                )
            elif mode == "targeted":
                result = evaluator._judge_domain_targeted(
                    domain,
                    sr_pico,
                    domain_context,
                    supplementary_context=supplementary_context,
                )
                if evaluator.enable_calibration:
                    result = evaluator._calibrate_direct_domain_result(
                        domain,
                        result,
                        calibration_evidence,
                    )
            else:
                result = evaluator._judge_domain_direct(
                    domain,
                    sr_pico,
                    domain_context,
                    supplementary_context=supplementary_context,
                )
                if evaluator.enable_calibration:
                    result = evaluator._calibrate_direct_domain_result(
                        domain,
                        result,
                        calibration_evidence,
                    )
            domain_seconds = round(time.perf_counter() - domain_started, 2)
            results.append(result)
            trace["domains"].append(
                {
                    "domain": domain.value,
                    "domain_context_chars": len(domain_context),
                    "supplementary_context_chars": len(supplementary_context),
                    "domain_context_preview": truncate(domain_context),
                    "prediction": result.judgement.value,
                    "support_text": result.support_text,
                    "support_context": [
                        item.model_dump() for item in result.support_context
                    ],
                    "evidence_map": result.evidence_map,
                    "reasoning": result.reasoning,
                    "seconds": domain_seconds,
                }
            )

        assessment = RiskOfBiasAssessment(
            study_id=study_id,
            pmid=pmid,
            results=results,
        )
    else:
        extraction_text = evaluator._build_methodology_context(
            article_text,
            max_chars=evaluator.extraction_max_chars,
        )
        trace["extraction_context_chars"] = len(extraction_text)
        trace["extraction_context_preview"] = truncate(extraction_text)

        extraction_started = time.perf_counter()
        methodology = evaluator._extract_methodology(sr_pico, extraction_text)
        trace["extraction_seconds"] = round(time.perf_counter() - extraction_started, 2)
        trace["methodology"] = methodology.model_dump()

        results = []
        methodology_json = methodology.model_dump_json(indent=2)
        for domain in RoBDomain:
            domain_context = ""
            if mode == "hybrid":
                domain_context = evaluator._build_domain_context(
                    domain,
                    article_text,
                    max_chars=evaluator.domain_context_max_chars,
                )

            domain_started = time.perf_counter()
            result = evaluator._judge_domain(
                domain,
                methodology_json,
                sr_pico,
                domain_context=domain_context,
            )
            if evaluator.enable_calibration and mode == "hybrid":
                result = evaluator._calibrate_domain_result(
                    domain,
                    result,
                    methodology_json,
                    domain_context,
                )
            domain_seconds = round(time.perf_counter() - domain_started, 2)
            results.append(result)
            trace["domains"].append(
                {
                    "domain": domain.value,
                    "domain_context_chars": len(domain_context),
                    "domain_context_preview": truncate(domain_context),
                    "prediction": result.judgement.value,
                    "support_text": result.support_text,
                    "support_context": [
                        item.model_dump() for item in result.support_context
                    ],
                    "reasoning": result.reasoning,
                    "seconds": domain_seconds,
                }
            )

        assessment = RiskOfBiasAssessment(
            study_id=study_id,
            pmid=pmid,
            results=results,
        )

    trace["total_seconds"] = round(time.perf_counter() - started, 2)

    domain_rows = []
    for result in assessment.results:
        canonical = _canonical_domain(result.domain.value)
        candidates = gt_lookup.get(canonical, [])
        match, gt_label = judgement_match(result.judgement.value, candidates)
        gt_observability = classify_gt_observability(candidates, article_text)
        row = {
            "domain": result.domain.value,
            "canonical_domain": canonical,
            "prediction": result.judgement.value,
            "ground_truth": gt_label,
            "match": match,
            **gt_observability,
            "support_text": result.support_text,
            "support_context": [item.model_dump() for item in result.support_context],
            "evidence_map": result.evidence_map,
            "reasoning": result.reasoning,
            "error_type": None if match else classify_error(
                result.domain.value,
                result.judgement.value,
                gt_label,
                result.reasoning or "",
                result.support_text,
                gt_observability["gt_observability"],
            ),
            "ground_truth_support": [item.get("support_text") for item in candidates],
        }
        domain_rows.append(row)

    if mode == "joint":
        trace["domains"] = domain_rows
    else:
        by_domain = {item["domain"]: item for item in trace["domains"]}
        for row in domain_rows:
            by_domain[row["domain"]].update(row)

    correct = sum(1 for row in domain_rows if row["match"] is True)
    total = len(domain_rows)

    return {
        "study_id": study_id,
        "pmid": pmid,
        "path": str(study_path),
        "mode": mode,
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0,
        "assessment": assessment.to_cochrane_format(),
        "ground_truth": ground_truth,
        "trace": trace,
        "domain_rows": domain_rows,
    }


def write_report(results: list[dict], output_path: Path) -> None:
    total_correct = sum(item["correct"] for item in results)
    total = sum(item["total"] for item in results)
    accuracy = total_correct / total if total else 0
    rows = [row for item in results for row in item["domain_rows"]]
    observable_rows = [
        row for row in rows if row.get("gt_observable_in_article") is True
    ]
    observable_correct = sum(1 for row in observable_rows if row["match"] is True)
    observable_total = len(observable_rows)
    observable_accuracy = (
        observable_correct / observable_total if observable_total else 0
    )
    external_total = sum(
        1 for row in rows if row.get("gt_observability") == "external_or_review_context"
    )
    external_correct = sum(
        1
        for row in rows
        if row.get("gt_observability") == "external_or_review_context"
        and row["match"] is True
    )
    nonobservable_rows = [
        row for row in rows if row.get("gt_observable_in_article") is False
    ]
    nonobservable_correct = sum(
        1 for row in nonobservable_rows if row["match"] is True
    )
    nonobservable_total = len(nonobservable_rows)
    scorable_rows = [
        row
        for row in rows
        if row.get("gt_observable_in_article") is True
        or row.get("gt_observability") == "article_absence_or_unclear"
    ]
    scorable_correct = sum(1 for row in scorable_rows if row["match"] is True)
    scorable_total = len(scorable_rows)
    scorable_accuracy = scorable_correct / scorable_total if scorable_total else 0
    unknown_total = sum(
        1 for row in rows if row.get("gt_observable_in_article") is None
    )
    retry_total = sum(1 for item in results if item.get("retry"))

    lines = [
        "# Batch Risk of Bias Eval Report",
        "",
        "This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.",
        "",
        f"- Studies: {len(results)}",
        f"- Domains: {total}",
        f"- Accuracy: {total_correct}/{total} ({accuracy:.1%})",
        f"- Article-only scorable accuracy: {scorable_correct}/{scorable_total} ({scorable_accuracy:.1%})",
        f"- Article-observable accuracy: {observable_correct}/{observable_total} ({observable_accuracy:.1%})",
        f"- Non-observable/article-missing GT accuracy: {nonobservable_correct}/{nonobservable_total} ({(nonobservable_correct / nonobservable_total if nonobservable_total else 0):.1%})",
        f"- External/review-context GT domains: {external_correct}/{external_total} matched",
        f"- Unknown or non-text GT domains: {unknown_total}",
        f"- Timeout retries recovered: {retry_total}",
        "",
        "Interpretation note: `Article-only scorable` is the fairest metric for the current direct input contract (`sr_pico + xml_content + domain`). External/review-context rows often require author emails, protocols, registries, tables/figures, or review notes that are not present in the XML excerpts.",
        "",
        "## Summary",
        "",
        "| PMID | Study | Correct | Accuracy | Seconds | Retry |",
        "|---|---|---:|---:|---:|---|",
    ]

    for item in results:
        trace = item["trace"]
        lines.append(
            f"| {item['pmid']} | {item.get('study_id') or ''} | "
            f"{item['correct']}/{item['total']} | {item['accuracy']:.1%} | "
            f"{trace.get('total_seconds', 0):.2f} | "
            f"{'yes' if item.get('retry') else ''} |"
        )

    lines.extend(["", "## Error Types", ""])
    error_counts: dict[str, int] = {}
    for item in results:
        for row in item["domain_rows"]:
            if row["match"] is not True:
                error_counts[row["error_type"] or "unknown"] = (
                    error_counts.get(row["error_type"] or "unknown", 0) + 1
                )
    if error_counts:
        for error_type, count in sorted(error_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {error_type}: {count}")
    else:
        lines.append("- No mismatches.")

    for item in results:
        trace = item["trace"]
        lines.extend(
            [
                "",
                f"## {item['pmid']} - {item.get('study_id') or ''}",
                "",
                f"- Mode: {item['mode']}",
                f"- Review context: {trace.get('review_context_mode', 'none')} ({trace.get('review_context_chars', 0)} chars)",
                f"- Article chars: {trace.get('article_chars')}",
                f"- Extraction context chars: {trace.get('extraction_context_chars', 'n/a')}",
                f"- Total seconds: {trace.get('total_seconds')}",
                f"- Retry: {'yes' if item.get('retry') else 'no'}",
                "",
                "### Methodology Extraction",
                "",
            ]
        )
        methodology = trace.get("methodology") or {}
        if methodology:
            for key, value in methodology.items():
                lines.append(f"- `{key}`: {truncate(str(value), 500)}")
        elif trace.get("evidence_table"):
            evidence_table = trace["evidence_table"]
            lines.append(f"- `study_design`: {truncate(str(evidence_table.get('study_design')), 500)}")
            lines.append(f"- `notes`: {truncate(str(evidence_table.get('notes')), 500)}")
        else:
            lines.append("- No separate extraction step for this mode.")

        lines.extend(
            [
                "",
                "### Domain Judgements",
                "",
                "| Domain | Pred | GT | Match | GT Observability | Error Type |",
                "|---|---|---|---|---|---|",
            ]
        )
        for row in item["domain_rows"]:
            match = "yes" if row["match"] is True else "no" if row["match"] is False else "n/a"
            lines.append(
                f"| {row['domain']} | {row['prediction']} | {row['ground_truth']} | "
                f"{match} | {row.get('gt_observability', '')} | {row['error_type'] or ''} |"
            )

        lines.extend(["", "### Audit Details", ""])
        domain_trace = {d["domain"]: d for d in trace.get("domains", [])}
        for row in item["domain_rows"]:
            detail = domain_trace.get(row["domain"], row)
            lines.extend(
                [
                    f"#### {row['domain']}",
                    "",
                    f"- Prediction: {row['prediction']}",
                    f"- Ground truth: {row['ground_truth']}",
                    f"- Match: {row['match']}",
                    f"- GT observability: {row.get('gt_observability')} (article observable: {row.get('gt_observable_in_article')})",
                    f"- GT support phrase hits: {truncate(' | '.join(row.get('gt_support_phrase_hits') or []), 700)}",
                    f"- Model rationale: {truncate(row.get('reasoning'), 700)}",
                    f"- Model support: {truncate(row.get('support_text'), 900)}",
                    f"- Model support context: {truncate(json.dumps(row.get('support_context', []), ensure_ascii=False), 900)}",
                    f"- GT support: {truncate(' | '.join(str(x) for x in row.get('ground_truth_support') or []), 900)}",
                    f"- Evidence row: {truncate(json.dumps(detail.get('evidence', {}), ensure_ascii=False), 900)}",
                    f"- Source context preview: {truncate(detail.get('domain_context_preview'), 700)}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Workflow Evolution Notes",
            "",
            "- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.",
            "- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.",
            "- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.",
            "- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_run_outputs(
    results: list[dict],
    results_path: Path,
    report_path: Path,
) -> None:
    """Persist machine-readable results and a report checkpoint."""
    results_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    completed = [item for item in results if "domain_rows" in item]
    write_report(completed, report_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch RoB eval with audit traces.")
    parser.add_argument("--dataset-dir", default="rob_cleaned_dataset")
    parser.add_argument("--output-dir", default="eval_runs")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--pmids", default="", help="Comma-separated PMIDs to run.")
    parser.add_argument(
        "--mode",
        choices=["hybrid", "strict", "joint", "evidence", "direct", "targeted", "audited"],
        default="direct",
    )
    parser.add_argument(
        "--review-context",
        choices=["none", "characteristics"],
        default="none",
        help="Optional review-level context supplied to evidence mode.",
    )
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--extraction-max-chars", type=int, default=None)
    parser.add_argument("--domain-context-max-chars", type=int, default=None)
    parser.add_argument("--joint-max-chars", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument(
        "--calibration",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Enable or disable optional post-judgement calibration. "
            "Default follows ENABLE_CALIBRATION env, which defaults to off."
        ),
    )
    parser.add_argument("--model", default=None, help="Override BASE_MODEL for this run.")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="OpenAI SDK max retries per request. Default: MAX_RETRIES env or 0.",
    )
    parser.add_argument(
        "--retry-on-timeout",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Retry a timed-out study once with smaller source contexts. Default: enabled.",
    )
    parser.add_argument(
        "--retry-timeout",
        type=float,
        default=None,
        help="Request timeout for the smaller-context retry. Default: same as --timeout.",
    )
    parser.add_argument(
        "--retry-extraction-max-chars",
        type=int,
        default=6000,
        help="Stage 1 source characters for timeout retry. Default: 6000.",
    )
    parser.add_argument(
        "--retry-domain-context-max-chars",
        type=int,
        default=4000,
        help="Hybrid domain source characters for timeout retry. Default: 4000.",
    )
    parser.add_argument(
        "--retry-joint-max-chars",
        type=int,
        default=12000,
        help="Joint-mode source characters for timeout retry. Default: 12000.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of studies to evaluate concurrently. Default: 1.",
    )
    parser.add_argument(
        "--no-support-filter",
        action="store_true",
        help=(
            "Select from all standard RoB studies instead of requiring ground-truth "
            "support phrases to appear in the article XML."
        ),
    )
    return parser.parse_args()


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env", override=True)
    args = parse_args()

    dataset_dir = Path(args.dataset_dir)
    if not dataset_dir.is_absolute():
        dataset_dir = repo_root / dataset_dir

    pmids = [item.strip() for item in args.pmids.split(",") if item.strip()]
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")

    studies = select_studies(
        dataset_dir,
        args.limit,
        pmids or None,
        require_support_filter=not args.no_support_filter,
    )
    if not studies:
        raise RuntimeError("No eligible studies selected.")

    run_dir = Path(args.output_dir)
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir
    run_dir = run_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "batch_results.json"
    report_path = run_dir / "report.md"

    evaluator_kwargs = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "request_timeout": args.timeout,
        "extraction_max_chars": args.extraction_max_chars,
        "domain_context_max_chars": args.domain_context_max_chars,
        "joint_max_chars": args.joint_max_chars,
        "reasoning_effort": args.reasoning_effort,
        "enable_calibration": args.calibration,
        "max_retries": args.max_retries,
    }
    evaluator = RoBEvaluator(**evaluator_kwargs)

    print(f"Selected {len(studies)} studies:")
    print(
        "Support filter: "
        f"{'off' if args.no_support_filter else 'on'}; "
        f"Concurrency: {args.concurrency}; "
        f"Timeout retry: {'on' if args.retry_on_timeout else 'off'}"
    )
    for path in studies:
        print(f"  - {path.name}")

    def run_path(index: int, path: Path) -> dict:
        try:
            result = run_one_study(
                evaluator,
                path,
                args.mode,
                review_context_mode=args.review_context,
            )
            result["selection_index"] = index
            return result
        except Exception as exc:
            if args.retry_on_timeout and (
                is_timeout_error(exc) or is_transient_provider_error(exc)
            ):
                retry_kwargs = {
                    **evaluator_kwargs,
                    "request_timeout": args.retry_timeout or args.timeout,
                    "extraction_max_chars": args.retry_extraction_max_chars,
                    "domain_context_max_chars": args.retry_domain_context_max_chars,
                    "joint_max_chars": args.retry_joint_max_chars,
                }
                try:
                    retry_evaluator = RoBEvaluator(**retry_kwargs)
                    result = run_one_study(
                        retry_evaluator,
                        path,
                        args.mode,
                        review_context_mode=args.review_context,
                    )
                    result["selection_index"] = index
                    result["retry"] = {
                        "reason": repr(exc),
                        "extraction_max_chars": args.retry_extraction_max_chars,
                        "domain_context_max_chars": args.retry_domain_context_max_chars,
                        "joint_max_chars": args.retry_joint_max_chars,
                    }
                    return result
                except Exception as retry_exc:
                    return {
                        "selection_index": index,
                        "path": str(path),
                        "pmid": path.stem,
                        "mode": args.mode,
                        "error": repr(retry_exc),
                        "first_error": repr(exc),
                        "retry_attempted": True,
                    }
            return {
                "selection_index": index,
                "path": str(path),
                "pmid": path.stem,
                "mode": args.mode,
                "error": repr(exc),
                "retry_attempted": False,
            }

    results_by_index: dict[int, dict] = {}

    if args.concurrency == 1:
        for index, path in enumerate(studies, start=1):
            print(f"\n[{index}/{len(studies)}] Running {path.name}...", flush=True)
            result = run_path(index, path)
            results_by_index[index] = result
            if "domain_rows" in result:
                print(
                    f"[OK] {result['pmid']} {result['correct']}/{result['total']} "
                    f"({result['accuracy']:.1%}) in {result['trace']['total_seconds']}s",
                    flush=True,
                )
            else:
                print(f"[ERROR] {path.name}: {result['error']}", flush=True)
            write_run_outputs(
                [results_by_index[i] for i in sorted(results_by_index)],
                results_path,
                report_path,
            )
    else:
        print(
            f"\nRunning {len(studies)} studies with {args.concurrency} workers...",
            flush=True,
        )
        executor = ThreadPoolExecutor(max_workers=args.concurrency)
        try:
            future_map = {
                executor.submit(run_path, index, path): (index, path)
                for index, path in enumerate(studies, start=1)
            }
            for completed_count, future in enumerate(as_completed(future_map), start=1):
                index, path = future_map[future]
                result = future.result()
                results_by_index[index] = result
                if "domain_rows" in result:
                    print(
                        f"[OK] [{completed_count}/{len(studies)}] "
                        f"{result['pmid']} {result['correct']}/{result['total']} "
                        f"({result['accuracy']:.1%}) in "
                        f"{result['trace']['total_seconds']}s",
                        flush=True,
                    )
                else:
                    print(
                        f"[ERROR] [{completed_count}/{len(studies)}] "
                        f"{path.name}: {result['error']}",
                        flush=True,
                    )
                write_run_outputs(
                    [results_by_index[i] for i in sorted(results_by_index)],
                    results_path,
                    report_path,
                )
        except KeyboardInterrupt:
            for future in future_map:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            write_run_outputs(
                [results_by_index[i] for i in sorted(results_by_index)],
                results_path,
                report_path,
            )
            raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    results = [results_by_index[i] for i in sorted(results_by_index)]

    completed = [item for item in results if "domain_rows" in item]
    write_run_outputs(results, results_path, report_path)

    total_correct = sum(item["correct"] for item in completed)
    total = sum(item["total"] for item in completed)
    accuracy = total_correct / total if total else 0

    print("\nBatch complete")
    print(f"Completed studies: {len(completed)}/{len(results)}")
    print(f"Accuracy: {total_correct}/{total} ({accuracy:.1%})")
    print(f"Results JSON: {results_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
