"""
5 RoB extraction slots - one independent API call per slot per study.

Slots:
    1. random_sequence_generation
    2. allocation_concealment
    3. blinding_participants
    4. blinding_outcome
    5. incomplete_outcome
"""

from dataclasses import dataclass, field


@dataclass
class DomainSpec:
    slot_id: str
    domain_label: str
    criteria: str
    extraction_schema: str = ""  # JSON schema (as text) for stage-1 evidence extraction


# --- Random sequence: permissive criteria with context-clue recognition ---
# Validated on 93 studies: 68.82% -> 75.27% (+6.45%) vs strict criteria.
_RANDOM_SEQUENCE_CRITERIA = """\
Evaluate whether the study used a truly random allocation sequence.

Be reasonably PERMISSIVE for Low risk: if the paper describes randomization
with sufficient detail to suggest a proper random method was used, Low risk
is appropriate even without exhaustive methodological detail.

Low risk - any one of these supports Low:
- Explicit random method: random number table, computer random number generator,
  coin toss, shuffled cards/envelopes, dice, drawing lots, minimization
- "Randomized" or "randomly allocated" PLUS context clues that suggest proper
  randomization (e.g., "computer-generated", "random number generator",
  "permuted blocks", "stratified randomization", "central randomization",
  "pharmacy randomization", or similar phrases indicating a systematic random process)
- Random permuted blocks WITH the random generation method described
- Description of randomization procedure that clearly indicates random allocation
  (e.g., "participants were randomly assigned using a computerized system")

High risk - requires clear evidence of non-random or predictable allocation:
- Explicitly non-random rules: birth date parity, admission date or day of week,
  hospital record number, alternation, clinician judgement, patient preference,
  test results, intervention availability
- Paper explicitly states a non-random method was used

Unclear risk - reserve for genuinely ambiguous cases:
- Only states "randomized" or "randomly allocated" with NO additional context
  (no mention of computer, blocks, stratification, central allocation, etc.)
- Insufficient information to judge AND no context clues

Important: "randomized" alone with NO context -> Unclear. But "randomized" PLUS
context clues (computer-generated, blocks, stratification, central allocation) -> Low risk.

Common mistakes to avoid:
- "Computer-generated randomization" -> Low risk (not Unclear)
- "Block randomization" or "stratified randomization" -> Low risk (these imply proper random sequence)
- "Randomization was performed by statistician" -> Low risk (suggests proper method)"""

# --- Allocation concealment: v3 criteria (66.7% in v3 vs 59.1% in baseline) ---
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
- "Block randomization" → describes the sequence structure, not concealment → Unclear"""

# --- Blinding participants: baseline criteria (58.8% in baseline vs 55.0% in v3) ---
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

# --- Blinding outcome ---
_BLINDING_OUTCOME_CRITERIA = """\
Evaluate whether the outcome assessor was blinded to allocation, AND
whether the outcome measurement could be influenced by lack of blinding.

First identify WHO assessed the outcomes in this study: patient self-report,
clinician judgement, independent assessor, blinded coder, lab/imaging system,
or chart abstractor.

IMPORTANT: The key question is whether KNOWLEDGE OF ALLOCATION could bias
the MEASUREMENT of the outcome. Consider the nature of the outcome:
- Objective outcomes (lab values, mortality, imaging) -> hard to bias even unblinded
- Subjective outcomes (pain, QoL, satisfaction, clinician scales) -> easily biased

WORST-OUTCOME RULE (CRITICAL): RoB is judged at the level of the most-vulnerable
outcome, NOT averaged across the outcome set. If the study reports a MIX of
objective and subjective/patient-reported outcomes, and the subjective outcomes
are unblinded (or the patient is unblinded and the patient is the assessor),
the overall judgement is HIGH RISK -- even if the objective outcomes by
themselves would be Low. Do not "average out" detection bias by pointing to
the objective outcomes that are fine.

Examples that are HIGH RISK (not Low):
- Study reports both mortality (objective) AND a self-report quality-of-life
  questionnaire, and participants are not blinded -> High risk (the QoL is biased
  even though mortality is fine)
- Outcome assessors are not blinded AND any clinician-rated scale, symptom score,
  or patient-reported measure is among the outcomes -> High risk
- Patient self-report outcomes when participants are not blinded -> High risk
  (the patient IS the assessor)

Low risk:
- Outcome assessor explicitly blinded; unlikely to be broken
- OR assessor unblinded BUT ALL outcomes are objective and measurement cannot
  be influenced (e.g. all-cause mortality from records, lab assays,
  automated measurements, radiological imaging with standardized criteria).
  This requires that there are NO subjective outcomes in the mix.

High risk -- any of:
- Assessor unblinded or likely unblinded AND at least one outcome is subjective
  or judgement-dependent (clinician-rated scales, patient-reported questionnaires
  when the patient is unblinded, diagnosis requiring clinical judgement)
- Patient self-report outcomes AND participants are not blinded
- Mix of objective + subjective outcomes with no blinding of assessor for
  the subjective ones

Unclear risk -- only when:
- Does not state whether outcome assessors were blinded AND outcomes are
  entirely objective so blinding may not matter
- Only says "double blind" without clarifying whether this includes outcome
  assessment, AND outcome types cannot be inferred
- No information about outcome assessment blinding at all AND outcome types unclear

Common mistakes to avoid:
- Do NOT average across outcome types. One unblinded subjective outcome makes the
  whole domain High risk -- mortality / lab values being objective does not save it.
- Patient self-report outcomes: the PATIENT is the assessor. If participants
  are not blinded and outcomes are self-reported -> High risk (not Low, not Unclear).
- "Objective" does not mean "unbiasable". Blood pressure measured by an
  unblinded clinician who decides when to stop measuring -> potentially biased.
- Lab values measured by automated analyzer -> Low risk for THAT outcome only;
  if other subjective outcomes exist, judge the domain on the subjective ones."""

# --- Incomplete outcome ---
_INCOMPLETE_OUTCOME_CRITERIA = """\
Evaluate whether attrition, withdrawals, exclusions or missing data could
bias the result for the OUTCOMES OF INTEREST.

To judge this domain you need actual reported numbers about post-randomization
attrition on the analysed outcome (per-arm randomized vs analysed, reasons
for loss, time horizon). When those numbers are not in the paper, you almost
certainly should be at Unclear, not High.

Step 1 -- identify what counts as attrition for THIS judgement.
- Only post-randomization loss on the analysed outcome counts. Exclude:
  * Losses BEFORE randomization or before the intervention started
    (e.g. authors who missed a deadline before allocation, screening fails)
    -- these do not bias the randomised comparison.
  * Participants in a study sub-design that was never intended to contribute
    to the outcome (e.g. a short-follow-up arm by design).
  * "Anticipated" or "planned for" attrition stated only in the protocol or
    sample-size justification -- you need actual observed numbers.
- Use the analysed outcome's denominator at the analysed time point, NOT some
  other intermediate questionnaire return rate that the paper happens to
  mention.

Step 2 -- judge using these guidelines (apply with judgement, not mechanically).

Low risk -- typical signals (need positive evidence):
- Essentially complete follow-up on the outcome (loss <= ~10%) with no
  meaningful arm imbalance.
- Loss <= ~20%, balanced across arms (within ~5 pp), reasons not outcome-related.
- Appropriate missing-data handling (multiple imputation with MAR justification,
  mixed models for repeated measures) AND attrition is moderate.
- ITT analysis combined with low or balanced attrition.
- Pre-randomization losses ONLY -- the post-randomization data are intact.

High risk -- requires the paper to REPORT numbers that establish bias on the
analysed outcome. Any of:
- Reported total loss >= ~30% on the analysed outcome at the analysed time
  point AND no convincing missing-data analysis showing robustness.
- Reported differential loss >= ~10 percentage points between arms.
- Reported loss > ~20% AND differential >= ~5 pp.
- Attrition imbalance with reasons plausibly related to the outcome
  (more dropouts for "lack of efficacy" or AEs in one arm).
- Exclusions for "lack of efficacy" or AE imbalanced across arms.
- Per-protocol / as-treated analysis materially deviating from random
  assignment with substantial crossover or post-hoc exclusion (e.g. the
  paper drops participants for "not meeting inclusion criteria after
  randomization").
- Inappropriate simple imputation (e.g. unjustified LOCF) when outcome
  trajectories likely differ across arms.

Unclear risk -- when the paper does not let you compute the above. This is
common and is the correct call in many real papers. Examples:
- No CONSORT flow diagram and no per-arm analysed numbers in the text or
  tables. You cannot tell whether loss was 5% or 40%.
- Only "ITT" is stated, with no numbers and no flow.
- Attrition is mentioned but reasons / per-arm split / size cannot be
  inferred.
- The article's flow figure is referenced but not in the supplied text and
  no equivalent numbers appear in the article.

Important calibration notes:
- Missing CONSORT / per-arm numbers / reasons => Unclear, not High. Do not
  upgrade to High because attrition data is absent. Inferring attrition bias
  from the absence of data is the most common over-call in this domain.
- "Lost to follow-up before randomization" or "lost before the intervention"
  is not attrition for this domain.
- A protocol expectation like "33% loss expected" without observed data is
  not enough to judge High; treat it as Unclear unless observed numbers
  confirm the loss happened.
- A drop in questionnaire response on a SECONDARY measure does not flip the
  primary outcome to High if the primary outcome's denominator is intact.
- A paper saying "completers did not differ from non-completers" or "reasons
  were similar across groups" does NOT downgrade High when the raw numbers
  reported in the paper actually cross the High thresholds. But if the raw
  numbers themselves are not reported, that reassurance also does not let
  you assert High."""


# ---------------------------------------------------------------------------
# Stage-1 extraction schemas (used only when run with --two_stage)
# Each schema tells the model what to PULL OUT of the article before judging.
# Required quotes force grounded extraction; "..." is allowed if truly absent.
# ---------------------------------------------------------------------------

_RANDOM_SEQUENCE_SCHEMA = """\
{
  "method_quote":   "verbatim sentence(s) describing how the allocation sequence was generated, or \\"\\" if absent",
  "method_summary": "1-line paraphrase of the method described, or 'not described'",
  "context_clues":  ["list of phrases like 'computer-generated', 'block randomisation', 'central randomisation', 'stratified', 'permuted blocks' that appear in the article"],
  "non_random_signals": ["list of phrases suggesting non-random rules: alternation, birth date, admission date, record number, clinician choice, etc., or empty list"],
  "suggested_judgement": "Low risk | High risk | Unclear risk  -- High only if non_random_signals is non-empty; Low if method_quote describes a proper random method OR randomised + at least one context clue; Unclear if 'randomised' alone with no context"
}"""

_ALLOCATION_CONCEALMENT_SCHEMA = """\
{
  "concealment_quote":  "verbatim sentence(s) describing how upcoming assignment was concealed from the recruiter, or \\"\\" if absent",
  "mechanism":          "one of: central allocation | SNOSE (sequentially numbered + opaque + sealed envelopes) | identical drug containers | other-explicit | not described",
  "envelope_features":  {"sequentially_numbered": "yes|no|unknown", "opaque": "yes|no|unknown", "sealed": "yes|no|unknown"},
  "predictability_signals": ["phrases like 'open list', 'alternation', 'birth date', 'record number' if present, else empty list"],
  "suggested_judgement": "Low risk | High risk | Unclear risk  -- High if predictability_signals is non-empty OR envelopes lack any of seq-numbered/opaque/sealed; Low only if mechanism is an explicit concealment method; Unclear if mechanism is 'not described' (this is the common case -- do not infer High from absence)",
  "note": "brief comment if the article only describes sequence generation but says nothing about concealment"
}"""

_BLINDING_PARTICIPANTS_SCHEMA = """\
{
  "blinding_quote":          "verbatim sentence(s) describing whether participants and personnel were blinded, or \\"\\" if absent",
  "participants_blinded":    "yes | no | partial | unclear",
  "personnel_blinded":       "yes | no | partial | unclear",
  "blinding_method":         "e.g. identical placebo, sham device, double-blind capsule, none",
  "outcome_categories":      ["short labels of the main outcomes: e.g. 'mortality', 'pain (VAS)', 'QoL questionnaire', 'lab HbA1c'"],
  "subjective_outcomes":     ["subset of outcome_categories that are subjective / self-report / clinician-rated"],
  "objective_outcomes":      ["subset that are objective: mortality, automated labs, imaging-with-criteria, etc."],
  "suggested_judgement": "Low risk | High risk | Unclear risk  -- High if (participants_blinded=no OR personnel_blinded=no) AND subjective_outcomes is non-empty; Low if successfully blinded OR all outcomes are objective; Unclear if blinding status is unclear and outcomes mix subjective/unknown"
}"""

_BLINDING_OUTCOME_SCHEMA = """\
{
  "assessor_blinding_quote": "verbatim sentence(s) about outcome assessor blinding, or \\"\\" if absent",
  "assessor_role":           "who measured the outcomes: patient self-report | unblinded clinician | blinded assessor | independent rater | automated/lab | chart abstractor | mixed | unclear",
  "participants_blinded":    "yes | no | unclear  (relevant when outcomes are patient self-report)",
  "outcomes": [
    {
      "label": "short label",
      "type":  "objective | subjective | patient-reported",
      "assessor_blinded": "yes | no | unclear"
    }
  ],
  "worst_outcome_flag": "true | false  -- any outcome is subjective/patient-reported AND its assessor is unblinded",
  "any_subjective_unknown": "true | false  -- any subjective/patient-reported outcome whose assessor blinding is unclear",
  "suggested_judgement": "Low risk | High risk | Unclear risk  -- based on the rules: any outcome subjective + unblinded => High; all objective with adequate measurement => Low; subjective + assessor blinding unknown => Unclear"
}"""

_INCOMPLETE_OUTCOME_SCHEMA = """\
{
  "consort_present":         "true | false  -- did the article supply a CONSORT-style flow or per-arm analysed numbers?",
  "per_arm_flow": [
    {"arm": "name of arm", "randomised": "n or null", "analysed": "n or null", "lost": "n or null", "reasons": "free text or null"}
  ],
  "total_loss_pct":          "computed total loss % at the analysed time point, or null if uncomputable",
  "differential_loss_pp":    "absolute difference in loss % between arms, in percentage points, or null",
  "outcome_related_reasons": "true | false | unclear  -- do the dropout reasons look related to the outcome (lack of efficacy, AEs)?",
  "missing_data_method":     "e.g. ITT, mITT, per-protocol, as-treated, multiple imputation, mixed-effects MMRM, LOCF, complete-case, none-reported",
  "pre_randomisation_loss":  "true | false  -- are the only mentioned losses pre-randomisation?",
  "threshold_flags": {
    "loss_ge_30":       "true | false  -- total_loss_pct >= 30 on the analysed outcome",
    "diff_ge_10":       "true | false  -- differential_loss_pp >= 10",
    "loss_gt_20_diff_ge_5": "true | false  -- total_loss_pct > 20 AND differential_loss_pp >= 5",
    "outcome_related":  "true | false  -- reasons clearly tied to outcome (efficacy/AE imbalance)",
    "pp_deviation":     "true | false  -- per-protocol/as-treated analysis materially deviates from random assignment"
  },
  "suggested_judgement": "Low risk | High risk | Unclear risk  -- ONLY based on extracted numbers and threshold_flags above",
  "notes": "brief comment if numbers come from a sub-design / secondary measure rather than the analysed primary outcome"
}"""


SPECS: list[DomainSpec] = [
    DomainSpec(
        slot_id="random_sequence_generation",
        domain_label="Random sequence generation (selection bias)",
        criteria=_RANDOM_SEQUENCE_CRITERIA,
        extraction_schema=_RANDOM_SEQUENCE_SCHEMA,
    ),
    DomainSpec(
        slot_id="allocation_concealment",
        domain_label="Allocation concealment (selection bias)",
        criteria=_ALLOCATION_CONCEALMENT_CRITERIA,
        extraction_schema=_ALLOCATION_CONCEALMENT_SCHEMA,
    ),
    DomainSpec(
        slot_id="blinding_participants",
        domain_label="Blinding of participants and personnel (performance bias)",
        criteria=_BLINDING_PARTICIPANTS_CRITERIA,
        extraction_schema=_BLINDING_PARTICIPANTS_SCHEMA,
    ),
    DomainSpec(
        slot_id="blinding_outcome",
        domain_label="Blinding of outcome assessment (detection bias)",
        criteria=_BLINDING_OUTCOME_CRITERIA,
        extraction_schema=_BLINDING_OUTCOME_SCHEMA,
    ),
    DomainSpec(
        slot_id="incomplete_outcome",
        domain_label="Incomplete outcome data (attrition bias)",
        criteria=_INCOMPLETE_OUTCOME_CRITERIA,
        extraction_schema=_INCOMPLETE_OUTCOME_SCHEMA,
    ),
]


def build_system_prompt(spec: DomainSpec) -> str:
    return f"""You are a systematic-review risk-of-bias assessor following Cochrane Handbook Chapter 8.

You are assessing ONE domain only:
Domain: {spec.domain_label}

{spec.criteria}

META-PRINCIPLE — High risk requires POSITIVE evidence, not absence of evidence:

To call a domain High risk, you must point to something the article SAYS or
SHOWS that constitutes a flaw. Missing information by itself is NOT evidence
of High risk -- it is evidence of Unclear risk. Concretely:

  Random sequence generation (selection bias)
    High requires: the paper describes a non-random or predictable rule
    (birth date parity, admission date / day of week, hospital record number,
    alternation, clinician judgement, patient preference, test results,
    intervention availability). Silence about the method => Unclear, not High.

  Allocation concealment (selection bias)
    High requires: the paper describes a procedure where the recruiter could
    foresee the upcoming assignment (open random list visible to recruiters,
    envelopes that are NOT sequentially numbered + opaque + sealed, alternation,
    allocation by birth date / admission date / record number). Silence about
    concealment => Unclear, not High.

  Blinding of participants and personnel (performance bias)
    High requires: paper says blinding was absent or incomplete AND the
    outcome can plausibly be influenced by knowledge of allocation
    (subjective outcomes such as pain, QoL, symptom scales, self-report).
    Silence about blinding AND silence about outcome subjectivity => Unclear.
    Objective outcomes (e.g. all-cause mortality from records, automated lab
    assays) without blinding can still be Low.

  Blinding of outcome assessment (detection bias)
    High requires: paper indicates the assessor was unblinded (or the patient
    is unblinded and the patient is the assessor for self-report measures)
    AND at least one outcome is subjective / judgement-dependent. Silence
    about assessor blinding => Unclear, not High. Apply the worst-outcome
    rule: one unblinded subjective outcome makes the domain High even if
    objective outcomes are also reported.

  Incomplete outcome data (attrition bias)
    High requires that the paper REPORTS numbers establishing the bias:
    e.g. observed loss >= ~30% on the analysed outcome, observed differential
    loss >= ~10 percentage points, dropout reasons clearly tied to the
    intervention, or PP/as-treated analyses materially deviating from random
    assignment. If CONSORT flow / per-arm analysed numbers / reasons are
    missing and cannot be inferred from the article, this is Unclear, not
    High. Do not infer "High" from the absence of attrition data.

  Selective reporting (reporting bias) — not assessed here, listed for context:
    High requires direct comparison of pre-specified outcomes (protocol /
    registry / Methods) against what is actually reported, with concrete
    discrepancies. Without that comparison, treat as Unclear.

GLOBAL JUDGEMENT GUIDANCE:

1. Use the domain-specific criteria above as your primary guide. Different
   domains have different evidence thresholds — Random sequence and
   Allocation concealment expect explicit descriptions to call Low; Blinding
   and Incomplete outcome require positive evidence of a flaw to call High.

2. Unclear risk is the appropriate judgement when the paper does not say
   enough to confirm Low or High. It is not a fallback, but it is also not
   wrong — when the article is silent on the question, Unclear is correct.

3. Use only what the paper explicitly states or what can be reasonably read
   from the reported methods. Do not invent details. Do not infer High risk
   from missing detail.

4. The support_text quote should directly bear on this domain. If you cannot
   find a direct quote, write "Summary: ..." and explain what you concluded
   from the available evidence (including absence of evidence).

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


# ---------------------------------------------------------------------------
# Two-stage prompt builders (used when --two_stage is passed to run_experiment)
# Stage 1: extract structured evidence into the per-domain schema.
# Stage 2: judge given BOTH the extracted evidence AND the original article.
# ---------------------------------------------------------------------------

def build_extraction_prompt(spec: DomainSpec) -> str:
    return f"""You are an evidence extractor for systematic-review risk-of-bias.

You are working on ONE domain only:
Domain: {spec.domain_label}

Your job is NOT to judge risk yet. Your job is to PULL FACTS out of the
article that the judge will need.

Rules:
- Quote verbatim from the article whenever possible. If a field cannot be
  found in the article, set it to "" (empty string), null, or "not described"
  as appropriate -- NEVER invent or paraphrase content the article does not
  contain.
- For numeric fields, only report numbers that appear in the article. If
  per-arm flow numbers are not given, report null.
- Be exhaustive: scan the Abstract, Methods, Results, tables (CONSORT flow
  in particular for incomplete outcome), and any captions. The signal is
  often in tables.
- Do not interpret. Do not write "this looks like high risk". Just extract.

Output a single JSON object matching exactly this schema (keys and types):

{spec.extraction_schema}

Output JSON only, no text outside the JSON object."""


def build_judgement_prompt_with_evidence(spec: DomainSpec, evidence_json: str) -> str:
    """Stage-2 prompt: original criteria + meta-principle + extracted evidence."""
    base = build_system_prompt(spec)
    addendum = f"""

----------------------------------------------------------------------
EXTRACTED EVIDENCE (from a stage-1 pass over the same article):
----------------------------------------------------------------------
{evidence_json}
----------------------------------------------------------------------

How to use the extracted evidence:

1. Treat the EXTRACTED FIELDS as your primary inputs. They were pulled
   verbatim from the article. The article text is provided again below
   only to disambiguate or to look up wording for support_text.

2. If a numerically-defined threshold in the criteria is satisfied by the
   extracted numbers, you must apply that threshold. Do NOT explain the
   numbers away by re-reading the article's narrative. Common traps:
     - Stage-1 reports total_loss_pct = 22% and differential_loss_pp = 5+,
       but the article text says "dropouts were balanced" -> the numbers
       win, judgement is High.
     - Stage-1 reports per_arm_flow with one arm losing 30%+ at the
       analysed time point -> High, even if the abstract claims "good
       follow-up".
     - Stage-1 reports unblinded assessor + at least one subjective /
       patient-reported outcome -> High, regardless of what the article
       says about objective secondary outcomes.

3. If the extracted evidence shows the article is silent on the question
   (empty quotes, null numbers, "not described"), that supports Unclear
   -- do NOT infer High from absence. Do NOT infer Low either, unless the
   silence itself is informative (e.g. for Random sequence, "randomised"
   without any context clue is Unclear, not High).

4. Quote support_text from the extracted fields when possible. Only fall
   back to the article when the extraction did not capture the relevant
   wording.

5. If the extracted evidence and the article disagree, prefer the
   extraction. The extraction step was instructed to copy verbatim, so a
   discrepancy usually means you are misreading the article, not that
   stage-1 made things up.
"""
    return base + addendum

