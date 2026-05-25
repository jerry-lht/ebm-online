"""CLI for Risk of Bias assessment.

Usage:
    # By PMID (looks up in rob_article_only_dataset/)
    python main.py --pmid 32306943
    python main.py --pmid 32306943 --compare

    # By direct JSON path
    python main.py --json-path ../rob_cleaned_dataset/32306943.json
    python main.py --json-path ../rob_cleaned_dataset/32306943.json --compare
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from evaluator import RoBEvaluator
from schemas import RiskOfBiasAssessment


def load_study_by_pmid(pmid: str, dataset_dir: str = "rob_article_only_dataset") -> dict:
    """Load study JSON by PMID."""
    dataset_path = Path(dataset_dir)
    if not dataset_path.is_absolute():
        dataset_path = Path(__file__).parent.parent / dataset_path
    json_file = dataset_path / f"{pmid}.json"

    if not json_file.exists():
        raise FileNotFoundError(f"Study {pmid} not found in {dataset_path}")

    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_study_by_path(json_path: str) -> dict:
    """Load study JSON by direct file path."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_assessment(assessment: RiskOfBiasAssessment):
    """Pretty print assessment results."""
    print("\n" + "=" * 80)
    print("RISK OF BIAS ASSESSMENT")
    if assessment.study_id:
        print(f"Study: {assessment.study_id}")
    if assessment.pmid:
        print(f"PMID: {assessment.pmid}")
    print("=" * 80)

    for result in assessment.results:
        print(f"\n[{result.domain.value}]")
        print(f"   Judgement: {result.judgement.value}")
        print(f"   Support: {result.support_text[:200]}...")
        if result.reasoning:
            print(f"   Reasoning: {result.reasoning}")


def _normalize_domain(domain: str) -> str:
    """Normalize domain names for comparison (strip Cochrane suffix in parentheses)."""
    import re
    # Remove suffix like "(selection bias)", "(performance bias)", etc.
    normalized = re.sub(r"\s*\([^)]*\)", "", domain).strip()
    return normalized.lower()


def _canonical_domain(domain: str) -> str:
    """Map dataset-specific domain labels onto the evaluator's domain set."""
    normalized = _normalize_domain(domain)
    normalized = normalized.replace("outcome assessors", "outcome assessment")

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


def compare_with_ground_truth(
    assessment: RiskOfBiasAssessment,
    ground_truth: list[dict],
):
    """Compare LLM assessment with ground truth annotations."""
    print("\n" + "=" * 80)
    print("COMPARISON WITH GROUND TRUTH")
    print("=" * 80)

    # Build ground truth lookup with canonical domain names. Some studies contain
    # outcome-specific labels, so keep all candidates instead of overwriting.
    gt_lookup: dict[str, list[dict]] = {}
    for item in ground_truth:
        gt_lookup.setdefault(_canonical_domain(item["domain"]), []).append(item)

    matches = 0
    total = 0

    for result in assessment.results:
        domain_name = result.domain.value
        llm_judgement = result.judgement.value
        candidates = gt_lookup.get(_canonical_domain(domain_name), [])

        if not candidates:
            gt_judgement = "NOT FOUND"
        elif len(candidates) == 1:
            gt_judgement = candidates[0]["judgement"]
        else:
            judgements = sorted({item["judgement"] for item in candidates})
            gt_judgement = " / ".join(judgements)

        match = "[OK]" if llm_judgement == gt_judgement else "[X]"
        if llm_judgement == gt_judgement:
            matches += 1
        total += 1

        print(f"\n{match} {domain_name}")
        print(f"   LLM:          {llm_judgement}")
        print(f"   Ground Truth: {gt_judgement}")
        if len(candidates) > 1:
            print(f"   Note:         {len(candidates)} outcome-specific labels found")

    accuracy = matches / total if total > 0 else 0
    print(f"\n{'=' * 80}")
    print(f"Accuracy: {matches}/{total} ({accuracy:.1%})")
    print("=" * 80)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Risk of Bias Assessment using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--pmid",
        type=str,
        help="PMID of study (looks up in --dataset-dir, default: rob_article_only_dataset/)",
    )
    input_group.add_argument(
        "--json-path",
        type=str,
        help="Direct path to study JSON file",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare with ground truth annotations",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save output JSON (default: current dir)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="rob_article_only_dataset",
        help="Dataset directory used with --pmid (default: rob_article_only_dataset)",
    )
    parser.add_argument(
        "--mode",
        choices=["hybrid", "strict", "joint", "evidence", "direct", "targeted", "audited"],
        default="direct",
        help=(
            "Evaluation mode: direct is the recommended default and judges each "
            "domain from PICO plus source excerpts; hybrid uses extraction plus source excerpts; "
            "strict uses extraction only; joint judges all domains in one call; "
            "evidence extracts a domain evidence table before judgement; "
            "targeted uses direct mode plus structured evidence maps for complex domains; "
            "audited uses direct as primary and evidence maps as conservative guardrails."
        ),
    )
    parser.add_argument(
        "--review-context",
        choices=["none", "characteristics"],
        default="none",
        help="Optional review-level context to include in evidence mode.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Request timeout in seconds (default: REQUEST_TIMEOUT env or 90).",
    )
    parser.add_argument(
        "--extraction-max-chars",
        type=int,
        default=None,
        help=(
            "Maximum source characters used for Stage 1 extraction "
            "(default: EXTRACTION_MAX_CHARS env or 18000)."
        ),
    )
    parser.add_argument(
        "--domain-context-max-chars",
        type=int,
        default=None,
        help=(
            "Maximum source characters used for each hybrid domain judgement "
            "(default: DOMAIN_CONTEXT_MAX_CHARS env or 8000)."
        ),
    )
    parser.add_argument(
        "--joint-max-chars",
        type=int,
        default=None,
        help=(
            "Maximum source characters used for joint mode "
            "(default: JOINT_MAX_CHARS env or 24000)."
        ),
    )
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        help="Optional reasoning effort passed to compatible GPT-5 chat endpoints.",
    )
    parser.add_argument(
        "--calibration",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Enable or disable optional post-judgement calibration. "
            "Default follows ENABLE_CALIBRATION env, which defaults to off."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override BASE_MODEL for this run.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="OpenAI SDK max retries per request. Default: MAX_RETRIES env or 0.",
    )
    return parser.parse_args()


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    args = parse_args()

    # Load study data
    if args.pmid:
        print(f"Loading study by PMID: {args.pmid} from {args.dataset_dir}...")
        study_data = load_study_by_pmid(args.pmid, dataset_dir=args.dataset_dir)
    else:
        print(f"Loading study from: {args.json_path}...")
        study_data = load_study_by_path(args.json_path)

    # Extract inputs
    xml_content = study_data.get("xml_content", {})
    sr_pico = study_data.get("sr_pico", "")
    study_id = study_data.get("study_id")
    pmid = study_data.get("pmid") or args.pmid
    ground_truth = study_data.get("risk_of_bias", [])
    review_context = ""
    if args.review_context == "characteristics":
        review_context = json.dumps(
            study_data.get("characteristics", {}),
            ensure_ascii=False,
            indent=2,
        )

    # Run evaluation
    print(f"\nEvaluating {study_id or pmid}...\n")
    evaluator = RoBEvaluator(
        model=args.model,
        request_timeout=args.timeout,
        extraction_max_chars=args.extraction_max_chars,
        domain_context_max_chars=args.domain_context_max_chars,
        joint_max_chars=args.joint_max_chars,
        reasoning_effort=args.reasoning_effort,
        enable_calibration=args.calibration,
        max_retries=args.max_retries,
    )
    assessment = evaluator.evaluate(
        xml_content=xml_content,
        sr_pico=sr_pico,
        study_id=study_id,
        pmid=pmid,
        mode=args.mode,
        review_context=review_context,
    )

    # Print results
    print_assessment(assessment)

    # Compare with ground truth if requested
    if args.compare:
        if ground_truth:
            compare_with_ground_truth(assessment, ground_truth)
        else:
            print("\n[!] No ground truth found in study data for comparison.")

    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename_key = pmid or study_id or "output"
    output_file = output_dir / f"output_{filename_key}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "study_id": assessment.study_id,
                "pmid": assessment.pmid,
                "llm_assessment": assessment.to_cochrane_format(),
                "ground_truth": ground_truth if args.compare else None,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\n[OK] Results saved to {output_file}")


if __name__ == "__main__":
    main()
