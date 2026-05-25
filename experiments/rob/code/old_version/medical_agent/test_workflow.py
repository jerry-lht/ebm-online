"""Test script to validate the two-stage workflow without API calls."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from schemas import (
    RoBDomain,
    MethodologyExtraction,
    DomainResult,
    Judgement,
    RiskOfBiasAssessment,
)
from prompts import (
    build_extraction_prompt,
    build_judgement_prompt,
    DOMAIN_CRITERIA,
)


def test_schemas():
    """Test that schemas can be instantiated."""
    print("Testing schemas...")

    # Test MethodologyExtraction
    methodology = MethodologyExtraction(
        randomization_method="Computer random number generator",
        allocation_concealment_method="Central allocation via web",
        blinding_participants="Double-blind",
        blinding_personnel="Double-blind",
        blinding_outcome_assessors="Outcome assessors were blinded",
        attrition_details="5% lost to follow-up, balanced across groups",
        study_design="RCT",
        additional_notes="None",
    )
    print(f"✓ MethodologyExtraction: {methodology.randomization_method[:50]}...")

    # Test DomainResult
    result = DomainResult(
        domain=RoBDomain.RANDOM_SEQUENCE_GENERATION,
        judgement=Judgement.LOW,
        support_text='Quote: "Computer random number generator" Comment: Adequate method',
        reasoning="Random component clearly described",
    )
    print(f"✓ DomainResult: {result.domain.value} -> {result.judgement.value}")

    # Test RiskOfBiasAssessment
    assessment = RiskOfBiasAssessment(
        study_id="Test 2024",
        pmid="12345678",
        results=[result],
    )
    print(f"✓ RiskOfBiasAssessment: {len(assessment.results)} domains")
    print(f"✓ Cochrane format: {assessment.to_cochrane_format()[0]['source']}")


def test_prompts():
    """Test that prompts can be built."""
    print("\nTesting prompts...")

    # Test extraction prompt
    sr_pico = "Population: Adults with diabetes"
    article_text = "Methods: Participants were randomly allocated..."
    extraction_prompt = build_extraction_prompt(sr_pico, article_text)
    print(f"✓ Extraction prompt length: {len(extraction_prompt)} chars")
    assert "PICO Context" in extraction_prompt
    assert article_text in extraction_prompt

    # Test judgement prompt
    methodology_json = '{"randomization_method": "Computer RNG"}'
    judgement_prompt = build_judgement_prompt(
        RoBDomain.RANDOM_SEQUENCE_GENERATION,
        methodology_json,
        sr_pico,
    )
    print(f"✓ Judgement prompt length: {len(judgement_prompt)} chars")
    assert "Random sequence generation" in judgement_prompt
    assert "LOW RISK" in judgement_prompt

    # Test all domains have criteria
    for domain in RoBDomain:
        assert domain in DOMAIN_CRITERIA, f"Missing criteria for {domain}"
    print(f"✓ All {len(RoBDomain)} domains have criteria defined")


def test_data_loading():
    """Test that we can load a study from the dataset."""
    print("\nTesting data loading...")

    dataset_dir = Path(__file__).parent / "rob_cleaned_dataset"
    json_files = list(dataset_dir.glob("*.json"))

    if not json_files:
        print("✗ No JSON files found in dataset")
        return

    # Load first study
    test_file = json_files[0]
    with open(test_file, "r", encoding="utf-8") as f:
        study_data = json.load(f)

    print(f"✓ Loaded study: {study_data.get('study_id', 'Unknown')}")
    print(f"  PMID: {study_data.get('pmid', 'N/A')}")
    print(f"  Has xml_content: {'xml_content' in study_data}")
    print(f"  Has risk_of_bias: {'risk_of_bias' in study_data}")

    if "risk_of_bias" in study_data:
        print(f"  Ground truth domains: {len(study_data['risk_of_bias'])}")


def main():
    print("=" * 60)
    print("Risk of Bias Evaluator - Validation Tests")
    print("=" * 60)

    try:
        test_schemas()
        test_prompts()
        test_data_loading()

        print("\n" + "=" * 60)
        print("✓ All validation tests passed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Add OPENAI_API_KEY, OPENAI_BASE_URL, and BASE_MODEL to .env")
        print("2. Run: python src/main.py --pmid 32306943 --mode hybrid")
        print("3. Compare modes with: --mode strict or --mode joint --compare")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
