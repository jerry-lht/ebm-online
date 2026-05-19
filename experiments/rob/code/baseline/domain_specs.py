"""
5 RoB extraction slots — one independent API call per slot per study.
Baseline version (59.3% overall accuracy on n=100).

Slots:
    1. random_sequence_generation
    2. allocation_concealment
    3. blinding_participants
    4. blinding_outcome
    5. incomplete_outcome
"""

from dataclasses import dataclass


@dataclass
class DomainSpec:
    slot_id: str
    domain_label: str
    criteria: str


_RANDOM_SEQUENCE_CRITERIA = """\
Evaluate whether the study used a truly random allocation sequence.

Low risk:
- Random number table, computer random number generator, coin toss,
  shuffled cards/envelopes, dice, drawing lots, minimization
- Random permuted blocks WITH the random generation method described

High risk:
- Non-random or predictable rules: birth date parity, admission date or
  day of week, hospital record number, alternation, clinician judgement,
  patient preference, test results, intervention availability

Unclear risk:
- Only states "randomized" or "randomly allocated" without describing the method
- States blocked / stratified randomization but does not say how the sequence was generated
- Insufficient information to judge

Important: the word "randomized" alone is NOT enough to judge Low risk."""

_ALLOCATION_CONCEALMENT_CRITERIA = """\
Evaluate whether allocation could be foreseen by recruiters before enrolment.
This is different from blinding — concealment happens BEFORE allocation.

Low risk:
- Central allocation (telephone, web, pharmacy-controlled)
- Sequentially numbered identical drug containers
- Sequentially numbered, opaque, sealed envelopes (SNOSE)

High risk:
- Open random allocation list
- Envelopes that are not sealed, not opaque, or not sequentially numbered
- Alternation
- Allocation by birth date, admission date, hospital record number
- Any procedure that is clearly not concealed

Unclear risk:
- Mentions envelopes but does not specify sequentially numbered, opaque, sealed
- Does not describe the concealment method"""

_BLINDING_PARTICIPANTS_CRITERIA = """\
Evaluate whether participants and personnel delivering the intervention
knew the group assignment, AND whether knowing could plausibly affect
the outcomes.

Note: this domain is judged across all study outcomes overall — give the
single judgement that best represents the dominant risk for this study.

Low risk:
- Participants and key personnel were successfully blinded; unlikely to be broken
- OR not blinded / blinding incomplete BUT outcomes are unlikely to be
  influenced by knowledge of allocation (e.g. all-cause mortality)

High risk:
- Not blinded or blinding incomplete AND outcomes could be influenced
- Blinding attempted but likely broken AND outcomes could be affected

Unclear risk:
- Does not specify who was blinded
- Only says "double blind" without specifying participants/personnel
- Insufficient information"""

_BLINDING_OUTCOME_CRITERIA = """\
Evaluate whether the outcome assessor was blinded to allocation, AND
whether the outcome measurement could be influenced.

First identify who assessed the outcomes: patient self-report, clinician
judgement, independent assessor, blinded coder, lab/imaging system, or
chart abstractor.

Note: this domain is judged across all study outcomes overall — give the
single judgement that best represents the dominant risk for this study.

Low risk:
- Outcome assessor blinded; unlikely to be broken
- OR assessor unblinded BUT outcome measurement unlikely to be affected
  (e.g. all-cause mortality from medical records)

High risk:
- Assessor unblinded AND outcome is subjective or judgement-based
- Assessor likely unblinded AND measurement could be affected

Unclear risk:
- Does not state whether assessor was blinded
- Only says "double blind" without clarifying outcome assessment
- Insufficient information"""

_INCOMPLETE_OUTCOME_CRITERIA = """\
Evaluate whether attrition, withdrawals, exclusions or missing data could
bias the result.

Extract: numbers randomized per arm, numbers analysed, numbers missing,
reasons for missingness, whether missingness is balanced, whether ITT was
used, whether imputation was appropriate.

Note: this domain is judged across all study outcomes overall — give the
single judgement that best represents the dominant risk for this study.

Low risk:
- No missing outcome data
- Reasons for missingness unlikely to relate to true outcome
- Missing numbers and reasons balanced across groups
- Missing proportion small relative to event rate / effect size
- Appropriate missing-data handling

High risk:
- Reasons for missingness likely related to true outcome AND imbalanced across groups
- Missing proportion large enough to bias the effect
- Exclusions for "lack of efficacy" or adverse events imbalanced across groups
- As-treated analysis with substantial deviation from random assignment
- Inappropriate simple imputation (e.g. unjustified LOCF, treating missing as failure/success)

Unclear risk:
- Per-arm attrition not reported
- Reasons for missingness not reported
- Says "ITT" but does not describe missing-data handling"""


SPECS: list[DomainSpec] = [
    DomainSpec(
        slot_id="random_sequence_generation",
        domain_label="Random sequence generation (selection bias)",
        criteria=_RANDOM_SEQUENCE_CRITERIA,
    ),
    DomainSpec(
        slot_id="allocation_concealment",
        domain_label="Allocation concealment (selection bias)",
        criteria=_ALLOCATION_CONCEALMENT_CRITERIA,
    ),
    DomainSpec(
        slot_id="blinding_participants",
        domain_label="Blinding of participants and personnel (performance bias)",
        criteria=_BLINDING_PARTICIPANTS_CRITERIA,
    ),
    DomainSpec(
        slot_id="blinding_outcome",
        domain_label="Blinding of outcome assessment (detection bias)",
        criteria=_BLINDING_OUTCOME_CRITERIA,
    ),
    DomainSpec(
        slot_id="incomplete_outcome",
        domain_label="Incomplete outcome data (attrition bias)",
        criteria=_INCOMPLETE_OUTCOME_CRITERIA,
    ),
]


def build_system_prompt(spec: DomainSpec) -> str:
    return f"""You are a systematic-review risk-of-bias assessor following Cochrane Handbook Chapter 8.

You are assessing ONE domain only:
Domain: {spec.domain_label}

{spec.criteria}

Output a single JSON object with exactly these fields:
{{
  "domain": "{spec.domain_label}",
  "judgement": "Low risk | High risk | Unclear risk",
  "support_text": "Quote: \\"...\\" Comment: ... OR Summary: ... Comment: ...",
  "source": "source_full_text | source_review_characteristics | source_protocol | source_registry | author_correspondence"
}}

Rules:
- judgement must be exactly one of: Low risk, High risk, Unclear risk
- Unclear risk means insufficient information — not medium risk
- support_text must include both the evidence and the reasoning
- Output JSON only, no text outside the JSON object"""
