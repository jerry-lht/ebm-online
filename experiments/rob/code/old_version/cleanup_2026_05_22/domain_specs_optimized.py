"""
5 RoB extraction slots — optimized version (v2, after small-test feedback).

Key changes from v5 baseline:
1. Random sequence: added permissive guidance + context-clue recognition
   (small test: +5.26%, 2 fixed / 1 broken)
2. Allocation concealment: REVERTED — small test showed strict "Default Unclear"
   actually outperforms inference-based approach (3/3 broken cases were
   Unclear -> Low after my looser prompt). Cochrane convention is correct here.
3. Incomplete outcome & Blinding outcome: UNCHANGED (keep the gains)
4. Blinding participants: UNCHANGED (baseline was already good)

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


# --- Random sequence: OPTIMIZED with permissive guidance ---
_RANDOM_SEQUENCE_CRITERIA = """\
Evaluate whether the study used a truly random allocation sequence.

Be reasonably PERMISSIVE for Low risk: if the paper describes randomization
with sufficient detail to suggest a proper random method was used, Low risk
is appropriate even without exhaustive methodological detail.

Low risk — any one of these supports Low:
- Explicit random method: random number table, computer random number generator,
  coin toss, shuffled cards/envelopes, dice, drawing lots, minimization
- "Randomized" or "randomly allocated" PLUS context clues that suggest proper
  randomization (e.g., "computer-generated", "random number generator",
  "permuted blocks", "stratified randomization", "central randomization",
  "pharmacy randomization", or similar phrases indicating a systematic random process)
- Random permuted blocks WITH the random generation method described
- Description of randomization procedure that clearly indicates random allocation
  (e.g., "participants were randomly assigned using a computerized system")

High risk — requires clear evidence of non-random or predictable allocation:
- Explicitly non-random rules: birth date parity, admission date or day of week,
  hospital record number, alternation, clinician judgement, patient preference,
  test results, intervention availability
- Paper explicitly states a non-random method was used

Unclear risk — reserve for genuinely ambiguous cases:
- Only states "randomized" or "randomly allocated" with NO additional context
  (no mention of computer, blocks, stratification, central allocation, etc.)
- Insufficient information to judge AND no context clues

Important: "randomized" alone with NO context → Unclear. But "randomized" PLUS
context clues (computer-generated, blocks, stratification, central allocation) → Low risk.

Common mistakes to avoid:
- "Computer-generated randomization" → Low risk (not Unclear)
- "Block randomization" or "stratified randomization" → Low risk (these imply proper random sequence)
- "Randomization was performed by statistician" → Low risk (suggests proper method)"""

# --- Allocation concealment: REVERTED to original (small-test showed regression) ---
# Original v3 criteria — the strict "Default is Unclear" approach actually works
# best for this domain. My earlier "reasonable inference" path caused the model
# to over-call Low risk when GT was Unclear (3/3 broken cases were Unclear -> Low).
_ALLOCATION_CONCEALMENT_CRITERIA = """\
Evaluate whether the person enrolling participants could foresee the upcoming
group assignment BEFORE each participant was enrolled.

CRITICAL DISTINCTION: This domain is NOT about how the random sequence was
generated. "Computer-generated randomization" or "random number generator"
describes SEQUENCE GENERATION (a different domain). Allocation concealment
is about whether the RECRUITER could peek at or predict the next assignment.

Default is Unclear. Only upgrade to Low if there is EXPLICIT description of
a concealment mechanism that prevents foreknowledge.

Low risk — requires EXPLICIT mention of one of these mechanisms:
- Central allocation (telephone, web-based, pharmacy-controlled randomization)
- Sequentially numbered, opaque, sealed envelopes (SNOSE) — all 3 features required
- Sequentially numbered identical drug containers
- Other mechanism that clearly prevents the recruiter from knowing the next assignment

High risk:
- Open random allocation schedule (list visible to recruiters)
- Envelopes without ALL of: sequential numbering + opaque + sealed
- Alternation or rotation
- Allocation by birth date, admission date, hospital record number
- Any procedure where the recruiter could foresee the assignment

Unclear risk (the DEFAULT):
- Paper describes randomization method but says NOTHING about how assignments
  were concealed from recruiters — this is the most common scenario
- Mentions "envelopes" without specifying opaque + sealed + sequentially numbered
- No information about concealment at all
- Cluster trial where it is unclear whether participants were recruited before
  or after cluster randomization

Common mistakes to avoid:
- "Computer-generated randomization" → this is about sequence generation, NOT concealment → Unclear
- "Randomization was performed by [person]" → describes who did it, not whether it was concealed → Unclear
- "Block randomization" → describes the sequence structure, not concealment → Unclear
- "Double-blind with identical placebo" alone → does NOT imply allocation concealment → Unclear"""

# --- Blinding participants: UNCHANGED (baseline was good at 58.8%) ---
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

# --- Blinding outcome: UNCHANGED (improved from 48.9% to 51.1% in v3) ---
_BLINDING_OUTCOME_CRITERIA = """\
Evaluate whether the outcome assessor was blinded to allocation, AND
whether the outcome measurement could be influenced by lack of blinding.

First identify WHO assessed the outcomes in this study: patient self-report,
clinician judgement, independent assessor, blinded coder, lab/imaging system,
or chart abstractor.

IMPORTANT: The key question is whether KNOWLEDGE OF ALLOCATION could bias
the MEASUREMENT of the outcome. Consider the nature of the outcome:
- Objective outcomes (lab values, mortality, imaging) → hard to bias even unblinded
- Subjective outcomes (pain, QoL, satisfaction, clinician scales) → easily biased

Default is Unclear when assessor blinding is not reported AND outcomes are
a mix of objective and subjective.

Low risk:
- Outcome assessor explicitly blinded; unlikely to be broken
- OR assessor unblinded BUT outcomes are objective and measurement cannot
  be influenced (e.g. all-cause mortality from records, lab assays,
  automated measurements, radiological imaging with standardized criteria)

High risk — requires BOTH:
- Assessor unblinded or likely unblinded, AND
- Outcomes are subjective or judgement-dependent (e.g. clinician-rated scales,
  patient-reported questionnaires when the patient knows their group,
  diagnosis requiring clinical judgement)

Unclear risk (the DEFAULT):
- Does not state whether outcome assessors were blinded
- Only says "double blind" without clarifying whether this includes outcome assessment
- Outcomes are patient-reported (self-report questionnaires) AND blinding of
  participants is not described — since the patient IS the assessor, their
  blinding status determines detection bias, and if unknown → Unclear
- No information about outcome assessment blinding at all

Common mistakes to avoid:
- Patient self-report outcomes: the PATIENT is the assessor. If participants
  are not blinded and outcomes are self-reported → High risk (not Low).
- "Objective" does not mean "unbiasable". Blood pressure measured by an
  unblinded clinician who decides when to stop measuring → potentially biased.
- Lab values measured by automated analyzer → Low risk even if staff unblinded."""

# --- Incomplete outcome: UNCHANGED (improved from 57.4% to 62.8% in v3) ---
_INCOMPLETE_OUTCOME_CRITERIA = """\
Evaluate whether attrition, withdrawals, exclusions or missing data could
bias the result.

Be reasonably PERMISSIVE for Low risk: most well-conducted RCTs with reasonable
attrition (≤20%) and balanced reasons across groups should be judged Low,
even if the paper does not state every per-arm number explicitly. Use
overall judgement based on what the paper communicates.

Low risk — any one of these supports Low:
- No missing outcome data, or essentially complete follow-up
- Per-arm attrition is reasonable (typically ≤20%) AND appears balanced
  across groups, with reasons not obviously related to the outcome
- "Most participants completed" with no signal of imbalance or
  outcome-related dropout
- Appropriate missing-data method described (multiple imputation, mixed
  models, etc.) and the method is plausible for the data
- ITT analysis combined with low or balanced attrition

High risk — requires evidence pointing at bias, such as:
- Imbalanced attrition across groups with reasons plausibly related to
  the outcome (e.g. more dropouts in one arm due to lack of efficacy
  or adverse events)
- Large overall attrition (typically >20%) with poor handling
- Exclusions for "lack of efficacy" or AE imbalanced across groups
- As-treated analysis that materially deviates from random assignment
- Inappropriate simple imputation in a context where it biases the result
  (e.g. unjustified LOCF where outcomes worsen over time differently across arms)

Unclear risk — when the paper genuinely does not let you tell:
- No information about attrition at all
- Says only "ITT" without any numbers or reasoning, AND no other clue
- Substantial attrition mentioned but no reasons or breakdown given,
  preventing any judgement on bias direction

Note: a paper does NOT need to list all four of (randomized, analysed,
missing, reasons) per arm to qualify for Low risk. If the paper makes the
attrition picture clear enough that bias is unlikely, Low risk is appropriate.
Reserve Unclear for cases where you genuinely cannot tell whether attrition
was substantial, imbalanced, or outcome-related."""


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

GLOBAL JUDGEMENT GUIDANCE:

1. Use the domain-specific criteria above as your primary guide. The criteria
   for each domain define how strict or permissive you should be — different
   domains have different evidence thresholds.

2. Unclear risk is appropriate when the paper does not provide enough
   information to judge. It is not a fallback, but it is also not the default —
   if the paper communicates enough to make a confident judgement (even
   without exhaustive detail), commit to Low or High accordingly.

3. Use only what the paper explicitly states or what can be reasonably read
   from the reported methods. Do not invent details, but also do not refuse
   to judge when the picture is clear in aggregate.

4. The support_text quote should directly bear on this domain. If you cannot
   find a direct quote, write "Summary: ..." and explain what you concluded
   from the available evidence.

Output a single JSON object with exactly these fields:
{{
  "domain": "{spec.domain_label}",
  "judgement": "Low risk | High risk | Unclear risk",
  "support_text": "Quote: \\"...\\" Comment: ... OR Summary: ... Comment: ...",
  "source": "source_full_text | source_review_characteristics | source_protocol | source_registry | author_correspondence"
}}

Rules:
- judgement must be exactly one of: Low risk, High risk, Unclear risk
- support_text must include both the evidence (or note its absence) and the reasoning
- Output JSON only, no text outside the JSON object"""


# Backward-compat aliases for any code that imports the 2-stage helpers.
def build_extraction_prompt(spec: DomainSpec) -> str:
    return build_system_prompt(spec)


build_judgement_prompt = build_system_prompt
