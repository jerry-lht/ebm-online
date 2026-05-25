"""Clean the RoB dataset into canonical single-judgement tasks.

The raw matched review/article JSON can contain extra Cochrane domains,
outcome-specific duplicates, unsupported judgements such as "Not applicable",
or malformed top-level records. This script keeps a conservative benchmark for
the current task:

    input: sr_pico + xml_content + risk-of-bias domain
    output: risk-of-bias judgement

It writes cleaned copies and reports; it never edits the source dataset.
"""

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from schemas import Judgement, RoBDomain


CORE_DOMAIN_ORDER = [
    "random sequence generation",
    "allocation concealment",
    "blinding of participants and personnel",
    "blinding of outcome assessment",
    "incomplete outcome data",
]

CANONICAL_DOMAIN_LABELS = {
    "random sequence generation": RoBDomain.RANDOM_SEQUENCE_GENERATION.value,
    "allocation concealment": RoBDomain.ALLOCATION_CONCEALMENT.value,
    "blinding of participants and personnel": RoBDomain.BLINDING_PARTICIPANTS_PERSONNEL.value,
    "blinding of outcome assessment": RoBDomain.BLINDING_OUTCOME_ASSESSORS.value,
    "incomplete outcome data": RoBDomain.INCOMPLETE_OUTCOME_DATA.value,
}

VALID_JUDGEMENTS = {item.value for item in Judgement}

EXTERNAL_OR_REVIEW_RE = re.compile(
    r"\b("
    r"mail|e-mail|email|author|contact|correspondence|personal communication|"
    r"protocol|registry|registration|clinicaltrials|review author|reviewers"
    r")\b",
    re.I,
)

NON_ARTICLE_SOURCE_RE = re.compile(
    r"\b(study author|trial author|author reply|contacted|emailed|protocol|registry)\b",
    re.I,
)


def normalize_domain(domain: str) -> str:
    normalized = re.sub(r"\s*\([^)]*\)", "", str(domain)).strip().lower()
    normalized = normalized.replace("outcome assessors", "outcome assessment")
    return normalized


def canonical_domain(domain: str) -> str:
    normalized = normalize_domain(domain)
    if "random sequence generation" in normalized:
        return "random sequence generation"
    if "allocation concealment" in normalized:
        return "allocation concealment"
    if "blinding of participants and personnel" in normalized:
        return "blinding of participants and personnel"
    if "blinding of outcome assessment" in normalized:
        return "blinding of outcome assessment"
    if "incomplete outcome data" in normalized:
        return "incomplete outcome data"
    return normalized


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def article_text(data: dict[str, Any]) -> str:
    sections = data.get("xml_content", {}).get("sections", [])
    if not isinstance(sections, list):
        return ""
    return "\n\n".join(
        str(section.get("text", ""))
        for section in sections
        if isinstance(section, dict) and section.get("text")
    )


def source_text_for_item(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("domain", "judgement", "support_text", "source")
    )


def support_has_external_or_review_context(items: list[dict[str, Any]]) -> bool:
    text = " ".join(source_text_for_item(item) for item in items)
    return bool(EXTERNAL_OR_REVIEW_RE.search(text) or NON_ARTICLE_SOURCE_RE.search(text))


def merge_support_text(items: list[dict[str, Any]]) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for item in items:
        support = re.sub(r"\s+", " ", str(item.get("support_text") or "")).strip()
        if support and support not in seen:
            seen.add(support)
            merged.append(support)
    return "\n\n".join(merged)


def validate_and_clean(data: Any) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
    """Return cleaned data, reject reasons, and per-file diagnostics."""
    diagnostics: dict[str, Any] = {
        "non_core_domains_removed": [],
        "merged_duplicate_domains": {},
        "external_or_review_context_domains": [],
    }

    if not isinstance(data, dict):
        return None, ["top_level_not_object"], diagnostics

    if not isinstance(data.get("xml_content"), dict):
        return None, ["missing_xml_content"], diagnostics

    if not article_text(data).strip():
        return None, ["empty_article_text"], diagnostics

    risk_of_bias = data.get("risk_of_bias")
    if not isinstance(risk_of_bias, list) or not risk_of_bias:
        return None, ["missing_risk_of_bias"], diagnostics

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_items = []
    non_core_domains = []

    for item in risk_of_bias:
        if not isinstance(item, dict):
            invalid_items.append(item)
            continue
        domain = canonical_domain(item.get("domain", ""))
        if domain in CORE_DOMAIN_ORDER:
            grouped[domain].append(item)
        else:
            non_core_domains.append(str(item.get("domain", "")))

    diagnostics["non_core_domains_removed"] = sorted(set(non_core_domains))

    reject_reasons: list[str] = []
    if invalid_items:
        reject_reasons.append("malformed_risk_of_bias_item")

    cleaned_risk_of_bias = []
    for domain in CORE_DOMAIN_ORDER:
        items = grouped.get(domain, [])
        if not items:
            reject_reasons.append(f"missing_core_domain:{domain}")
            continue

        judgements = [str(item.get("judgement", "")).strip() for item in items]
        invalid_judgements = sorted({value for value in judgements if value not in VALID_JUDGEMENTS})
        if invalid_judgements:
            reject_reasons.append(
                f"unsupported_judgement:{domain}:{'|'.join(invalid_judgements)}"
            )
            continue

        unique_judgements = sorted(set(judgements))
        if len(unique_judgements) != 1:
            reject_reasons.append(
                f"conflicting_judgements:{domain}:{'|'.join(unique_judgements)}"
            )
            continue

        if len(items) > 1:
            diagnostics["merged_duplicate_domains"][domain] = len(items)

        if support_has_external_or_review_context(items):
            diagnostics["external_or_review_context_domains"].append(domain)

        cleaned_risk_of_bias.append(
            {
                "domain": CANONICAL_DOMAIN_LABELS[domain],
                "judgement": unique_judgements[0],
                "support_text": merge_support_text(items),
                "source": "cleaned_ground_truth",
                "source_domains": sorted({str(item.get("domain", "")) for item in items}),
            }
        )

    if reject_reasons:
        return None, reject_reasons, diagnostics

    cleaned = dict(data)
    cleaned["risk_of_bias"] = cleaned_risk_of_bias
    cleaned["dataset_cleaning"] = {
        "canonical_core_domains_only": True,
        "valid_judgements": sorted(VALID_JUDGEMENTS),
        "removed_non_core_domains": diagnostics["non_core_domains_removed"],
        "merged_duplicate_domains": diagnostics["merged_duplicate_domains"],
    }
    return cleaned, [], diagnostics


def summarize_reasons(reasons: list[str]) -> list[str]:
    summarized = []
    for reason in reasons:
        summarized.append(reason.split(":", 1)[0])
    return summarized


def clean_dataset(
    input_dir: Path,
    core_output_dir: Path,
    article_output_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    reset_dir(core_output_dir)
    reset_dir(article_output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    file_reports = []
    reject_counts = Counter()
    reject_detail_counts = Counter()
    removed_non_core_counts = Counter()
    merged_duplicate_counts = Counter()
    external_context_counts = Counter()
    core_judgement_counts: dict[str, Counter[str]] = {
        domain: Counter() for domain in CORE_DOMAIN_ORDER
    }
    article_judgement_counts: dict[str, Counter[str]] = {
        domain: Counter() for domain in CORE_DOMAIN_ORDER
    }

    total = 0
    accepted_core = 0
    accepted_article_only = 0

    for path in sorted(input_dir.glob("*.json")):
        total += 1
        try:
            data = load_json(path)
        except json.JSONDecodeError as exc:
            reasons = [f"invalid_json:{exc.msg}"]
            cleaned = None
            diagnostics = {
                "non_core_domains_removed": [],
                "merged_duplicate_domains": {},
                "external_or_review_context_domains": [],
            }
        except OSError as exc:
            reasons = [f"read_error:{exc}"]
            cleaned = None
            diagnostics = {
                "non_core_domains_removed": [],
                "merged_duplicate_domains": {},
                "external_or_review_context_domains": [],
            }
        else:
            cleaned, reasons, diagnostics = validate_and_clean(data)

        pmid = None
        study_id = None
        if isinstance(data, dict):
            pmid = data.get("pmid") or path.stem
            study_id = data.get("study_id")
        else:
            pmid = path.stem

        for domain in diagnostics["non_core_domains_removed"]:
            removed_non_core_counts[domain] += 1
        for domain, count in diagnostics["merged_duplicate_domains"].items():
            merged_duplicate_counts[domain] += count
        for domain in diagnostics["external_or_review_context_domains"]:
            external_context_counts[domain] += 1

        report_row = {
            "file": path.name,
            "pmid": pmid,
            "study_id": study_id,
            "status": "rejected" if reasons else "accepted",
            "reasons": reasons,
            "reason_groups": summarize_reasons(reasons),
            "diagnostics": diagnostics,
        }

        if cleaned is not None:
            accepted_core += 1
            for item in cleaned["risk_of_bias"]:
                domain = canonical_domain(item["domain"])
                core_judgement_counts[domain][item["judgement"]] += 1
            write_json(core_output_dir / path.name, cleaned)

            has_external_context = bool(diagnostics["external_or_review_context_domains"])
            report_row["article_only_status"] = (
                "excluded_external_or_review_context"
                if has_external_context
                else "accepted"
            )
            if not has_external_context:
                accepted_article_only += 1
                for item in cleaned["risk_of_bias"]:
                    domain = canonical_domain(item["domain"])
                    article_judgement_counts[domain][item["judgement"]] += 1
                write_json(article_output_dir / path.name, cleaned)
        else:
            for reason in reasons:
                reject_detail_counts[reason] += 1
            for reason in summarize_reasons(reasons):
                reject_counts[reason] += 1
            report_row["article_only_status"] = "rejected"

        file_reports.append(report_row)

    summary = {
        "input_dir": str(input_dir),
        "core_output_dir": str(core_output_dir),
        "article_output_dir": str(article_output_dir),
        "report_dir": str(report_dir),
        "total_json_files": total,
        "accepted_core_files": accepted_core,
        "accepted_article_only_files": accepted_article_only,
        "rejected_files": total - accepted_core,
        "reject_reason_counts": dict(reject_counts.most_common()),
        "reject_detail_counts": dict(reject_detail_counts.most_common()),
        "removed_non_core_domain_counts": dict(removed_non_core_counts.most_common()),
        "merged_duplicate_domain_counts": dict(merged_duplicate_counts.most_common()),
        "external_or_review_context_domain_counts": dict(external_context_counts.most_common()),
        "core_domain_judgement_counts": {
            domain: dict(counts.most_common()) for domain, counts in core_judgement_counts.items()
        },
        "article_only_domain_judgement_counts": {
            domain: dict(counts.most_common())
            for domain, counts in article_judgement_counts.items()
        },
    }

    write_json(report_dir / "cleaning_summary.json", summary)
    write_json(report_dir / "cleaning_file_report.json", file_reports)
    (report_dir / "cleaning_report.md").write_text(
        render_markdown_report(summary, file_reports),
        encoding="utf-8",
    )
    return summary


def render_top_counts(title: str, counts: dict[str, int], limit: int = 12) -> list[str]:
    lines = [f"## {title}", ""]
    if not counts:
        lines.extend(["None.", ""])
        return lines
    for name, count in list(counts.items())[:limit]:
        lines.append(f"- {name}: {count}")
    lines.append("")
    return lines


def render_markdown_report(summary: dict[str, Any], file_reports: list[dict[str, Any]]) -> str:
    lines = [
        "# Dataset cleaning report",
        "",
        f"- Input files: {summary['total_json_files']}",
        f"- Accepted core benchmark files: {summary['accepted_core_files']}",
        f"- Accepted article-only files: {summary['accepted_article_only_files']}",
        f"- Rejected files: {summary['rejected_files']}",
        "",
        "Core benchmark rule: keep only files with all five canonical RoB domains, "
        "one valid judgement per canonical domain, and article XML text present.",
        "",
        "Article-only rule: additionally exclude otherwise-clean files where core "
        "support text points to author correspondence, protocol, registry, or other "
        "review/external context.",
        "",
    ]
    lines += render_top_counts("Reject reason counts", summary["reject_reason_counts"])
    lines += render_top_counts("Reject detail counts", summary["reject_detail_counts"], limit=24)
    lines += render_top_counts(
        "Removed non-core domain counts",
        summary["removed_non_core_domain_counts"],
    )
    lines += render_top_counts(
        "Merged duplicate core domain item counts",
        summary["merged_duplicate_domain_counts"],
    )
    lines += render_top_counts(
        "External/review context core-domain counts",
        summary["external_or_review_context_domain_counts"],
    )
    lines += render_domain_judgement_counts(
        "Core benchmark judgement distribution",
        summary["core_domain_judgement_counts"],
    )
    lines += render_domain_judgement_counts(
        "Article-only judgement distribution",
        summary["article_only_domain_judgement_counts"],
    )

    rejected_examples = [row for row in file_reports if row["status"] == "rejected"][:20]
    lines.extend(["## Rejected examples", ""])
    if not rejected_examples:
        lines.extend(["None.", ""])
    else:
        for row in rejected_examples:
            reason = "; ".join(row["reasons"])
            lines.append(f"- {row['file']} PMID={row['pmid']}: {reason}")
        lines.append("")
    return "\n".join(lines)


def render_domain_judgement_counts(title: str, counts_by_domain: dict[str, dict[str, int]]) -> list[str]:
    lines = [f"## {title}", ""]
    for domain in CORE_DOMAIN_ORDER:
        counts = counts_by_domain.get(domain, {})
        low = counts.get("Low risk", 0)
        high = counts.get("High risk", 0)
        unclear = counts.get("Unclear risk", 0)
        lines.append(f"- {domain}: Low={low}, High={high}, Unclear={unclear}")
    lines.append("")
    return lines


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description="Clean matched RoB JSON dataset.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("rob_cleaned_dataset"),
        help="Source dataset directory.",
    )
    parser.add_argument(
        "--core-output-dir",
        type=Path,
        default=Path("rob_core_dataset"),
        help="Output directory for schema-clean canonical five-domain data.",
    )
    parser.add_argument(
        "--article-output-dir",
        type=Path,
        default=Path("rob_article_only_dataset"),
        help="Output directory excluding labels needing external/review context.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("eval_runs") / f"dataset_cleaning_{timestamp}",
        help="Directory for cleaning reports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = clean_dataset(
        args.input_dir,
        args.core_output_dir,
        args.article_output_dir,
        args.report_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
