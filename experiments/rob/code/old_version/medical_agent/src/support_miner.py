"""Mine ground-truth support_text for workflow/prompt evolution.

This script is for development only. It reads batch outputs and compares model
predictions with ground-truth support text to identify reusable rules, likely
missing inputs, and candidate few-shot cases. It must not be used inside the
actual evaluator prompt for held-out assessment.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


EXTERNAL_RE = re.compile(
    r"\b(mail|email|author|contact|correspondence|protocol|registry|registration|clinicaltrials|review author)\b",
    re.I,
)
NOT_REPORTED_RE = re.compile(
    r"not (reported|provided|described)|details not provided|insufficient|unclear",
    re.I,
)
LOW_RANDOM_RE = re.compile(
    r"computer|random number|permuted block|randomi[sz]ation list|generated|coin|dice|lot",
    re.I,
)
LOW_ALLOC_RE = re.compile(
    r"central|opaque|sealed|envelope|pharmacy|conceal|senior editor|independent|not aware|notified only|at distance",
    re.I,
)
BLIND_RE = re.compile(
    r"double[- ]blind|single[- ]masked|masked|blinded|placebo|identical|attention control|not group assignment",
    re.I,
)
ATTRITION_RE = re.compile(
    r"dropout|withdrew|withdraw|lost|loss|discontinued|excluded|per-protocol|intention-to-treat|itt|locf|last observation|missing|analysed|analyzed",
    re.I,
)


def load_results(paths: Iterable[Path]) -> list[dict]:
    rows = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for study in data:
            if "domain_rows" not in study:
                continue
            for row in study["domain_rows"]:
                rows.append(
                    {
                        "run": str(path),
                        "pmid": study.get("pmid"),
                        "study_id": study.get("study_id"),
                        **row,
                    }
                )
    return rows


def classify_support(row: dict) -> list[str]:
    support = " | ".join(str(x) for x in row.get("ground_truth_support") or [])
    domain = row.get("canonical_domain", "")
    labels = []

    if EXTERNAL_RE.search(support):
        labels.append("gt_uses_external_or_review_context")
    if NOT_REPORTED_RE.search(support):
        labels.append("gt_support_says_not_reported_or_unclear")
    if domain == "random sequence generation" and LOW_RANDOM_RE.search(support):
        labels.append("random_sequence_low_signal")
    if domain == "allocation concealment" and LOW_ALLOC_RE.search(support):
        labels.append("allocation_concealment_low_signal")
    if "blinding" in domain and BLIND_RE.search(support):
        labels.append("blinding_signal")
    if domain == "incomplete outcome data" and ATTRITION_RE.search(support):
        labels.append("attrition_signal")
    if not labels:
        labels.append("support_needs_manual_review")
    return labels


def make_recommendations(rows: list[dict]) -> list[str]:
    missed = [row for row in rows if row.get("match") is not True]
    labels = Counter(label for row in missed for label in classify_support(row))
    recs = []

    if labels["gt_uses_external_or_review_context"]:
        recs.append(
            "Add an evaluation split flag for review-level/external evidence. "
            "When GT support mentions mail, author contact, registry, or protocol, "
            "article-only evaluation should mark the item as not fully observable."
        )
    if labels["allocation_concealment_low_signal"]:
        recs.append(
            "Revise allocation concealment rubric: central/independent control, "
            "senior editor only aware, or randomization list kept at distance can be Low risk "
            "even without opaque sealed envelopes."
        )
    if labels["attrition_signal"]:
        recs.append(
            "Strengthen incomplete outcome data evidence extraction: require randomized/analyzed/missing "
            "counts by arm, timing, reasons, ITT vs per-protocol, LOCF/imputation, and whether attrition "
            "is substantial or outcome-related."
        )
    if labels["blinding_signal"]:
        recs.append(
            "For blinding, distinguish participant masking, personnel masking, outcome assessor masking, "
            "and whether outcomes are self-reported/objective. Attention-control or single-masked designs "
            "can be Low risk when the relevant outcome is unlikely to be biased."
        )
    if labels["gt_support_says_not_reported_or_unclear"]:
        recs.append(
            "When GT support itself says details are not provided, prefer Unclear even if the model sees "
            "generic randomized/double-blind language."
        )
    return recs


def print_report(rows: list[dict]) -> None:
    total = len(rows)
    wrong = [row for row in rows if row.get("match") is not True]
    print(f"Rows: {total}")
    print(f"Mismatches: {len(wrong)}")
    print()

    print("Mismatches by domain:")
    by_domain = Counter(row.get("canonical_domain") for row in wrong)
    for domain, count in by_domain.most_common():
        print(f"- {domain}: {count}")
    print()

    print("GT support labels in mismatches:")
    label_counts = Counter(label for row in wrong for label in classify_support(row))
    for label, count in label_counts.most_common():
        print(f"- {label}: {count}")
    print()

    print("Recommendations:")
    for rec in make_recommendations(rows):
        print(f"- {rec}")
    print()

    print("Candidate few-shot/error cases:")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in wrong:
        grouped[row.get("canonical_domain", "unknown")].append(row)
    for domain, items in grouped.items():
        print(f"\n## {domain}")
        for row in items[:3]:
            gt_support = " | ".join(str(x) for x in row.get("ground_truth_support") or [])
            print(f"- PMID {row.get('pmid')} ({row.get('study_id')}):")
            print(f"  pred={row.get('prediction')} gt={row.get('ground_truth')}")
            print(f"  error_type={row.get('error_type')}")
            print(f"  gt_support={truncate(gt_support, 500)}")


def truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mine GT support_text for prompt evolution.")
    parser.add_argument(
        "results",
        nargs="+",
        type=Path,
        help="One or more eval_runs/.../batch_results.json files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_results(args.results)
    print_report(rows)


if __name__ == "__main__":
    main()
