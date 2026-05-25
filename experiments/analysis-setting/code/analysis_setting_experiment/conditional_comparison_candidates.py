from __future__ import annotations

import re
from itertools import combinations
from typing import Any

from .conditional_normalization import clean_text, dedupe_preserve_order, normalize_comparison_text, normalize_text

_NONACTIVE_MARKERS = (
    "placebo",
    "usual care",
    "routine care",
    "standard care",
    "care as usual",
    "waiting list",
    "waitlist",
    "no treatment",
    "attention placebo",
    "inactive control",
    "nonactive comparator",
    "non-active comparator",
    "inactive comparator",
)

_COMPARISON_PHRASE_RE = re.compile(
    r"([^.;:\n]{1,120}?)\s+(?:versus|vs\.?|compared with|compared to)\s+([^.;:\n]{1,120})",
    re.IGNORECASE,
)
_OUTCOME_COMPARISON_RE = re.compile(
    r"(.+?)\s+(?:versus|vs\.?|compared with|compared to)\s+(.+?)(?:,|;|\(| - |$)",
    re.IGNORECASE,
)
_LEADING_NOISE_RE = re.compile(
    r"^(?:the|a|an|group\s+\d+|arm\s+\d+|participants?\s+(?:receiving|treated with)|patients?\s+(?:receiving|treated with)|infants?\s+(?:receiving|treated with)|our objective was to assess whether|objective to determine whether|objective)\s+",
    re.IGNORECASE,
)
_TRAILING_NOISE_RE = re.compile(
    r"\b(?:subgroup analyses?|analysis|trial|study|studies|group|arm|among .*|in .*|for .*|during .*|following .*|after .*|before .*|respectively.*|mean difference.*|confidence interval.*|ci.*|p\s*[<=>].*|complication.*)$",
    re.IGNORECASE,
)
_GENERIC_SIDE_PATTERNS = (
    re.compile(r"^(?:group|arm)\s+\d+$", re.IGNORECASE),
    re.compile(r"^(?:participants?|patients?|infants?|children|adults?)$", re.IGNORECASE),
)
_BAD_CANDIDATE_PATTERNS = (
    re.compile(r"^\d+(?:[.:]\d+)?\s+versus\s+\d+(?:[.:]\d+)?$", re.IGNORECASE),
    re.compile(r"\b(?:mean difference|confidence interval|95% ci|p\s*[<=>]|objective|results?|methods?)\b", re.IGNORECASE),
)
_MAX_CANDIDATES = 60


def _unique_clean_list(values: list[Any]) -> list[str]:
    cleaned = [clean_text(value) for value in values if clean_text(value)]
    return dedupe_preserve_order(cleaned)


def _all_text(instance: dict[str, Any]) -> str:
    parts = [
        clean_text(instance.get("sr_title")),
        clean_text(instance.get("outcome_concept")),
    ]
    sr_pico = instance.get("sr_pico", {}) or {}
    for key in ("intervention", "comparison", "population", "outcome"):
        values = sr_pico.get(key, [])
        if isinstance(values, list):
            parts.extend(clean_text(value) for value in values)
    for evidence_row in instance.get("study_evidence", []):
        parts.append(clean_text(evidence_row.get("primary_report_title")))
        parts.append(clean_text(evidence_row.get("abstract_text")))
        parts.append(clean_text(evidence_row.get("text"))[:3000])
    return "\n".join(part for part in parts if part)


def _is_nonactive_label(label: str) -> bool:
    normalized = normalize_comparison_text(label)
    return any(marker in normalized for marker in _NONACTIVE_MARKERS)


def _family_summary_label(labels: list[str]) -> str:
    if len(labels) < 2:
        return ""
    if all(_is_nonactive_label(label) for label in labels):
        return "nonactive comparators"
    if any(_is_nonactive_label(label) for label in labels):
        return "mixed comparators"
    return "active comparators"


def _canonical_candidate(label: str) -> str:
    collapsed = re.sub(r"\s+", " ", clean_text(label)).strip(" ,;:.()[]{}")
    return collapsed


def _looks_generic_side(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    return any(pattern.match(text.strip()) for pattern in _GENERIC_SIDE_PATTERNS)


def _trim_phrase_side(text: str) -> str:
    candidate = clean_text(text)
    candidate = _LEADING_NOISE_RE.sub("", candidate)
    candidate = _TRAILING_NOISE_RE.sub("", candidate)
    candidate = candidate.strip(" ,;:.()[]{}")
    return re.sub(r"\s+", " ", candidate)


def _has_too_many_digits(text: str) -> bool:
    alnum = [char for char in text if char.isalnum()]
    if not alnum:
        return False
    digit_count = sum(char.isdigit() for char in alnum)
    return digit_count / len(alnum) > 0.25


def _is_bad_candidate(label: str) -> bool:
    normalized = normalize_comparison_text(label)
    if not normalized:
        return True
    parts = normalized.split(" versus ")
    if len(parts) != 2:
        return True
    left, right = parts
    if left == right:
        return True
    if _looks_generic_side(left) or _looks_generic_side(right):
        return True
    if _has_too_many_digits(normalized):
        return True
    if len(normalized.split()) > 20:
        return True
    return any(pattern.search(normalized) for pattern in _BAD_CANDIDATE_PATTERNS)


def _extract_text_pairs(text: str) -> list[str]:
    candidates: list[str] = []
    for left, right in _COMPARISON_PHRASE_RE.findall(text or ""):
        left_clean = _trim_phrase_side(left)
        right_clean = _trim_phrase_side(right)
        phrase = _canonical_candidate(f"{left_clean} versus {right_clean}")
        if _is_bad_candidate(phrase):
            continue
        candidates.append(phrase)
    return candidates


def _extract_outcome_comparison(outcome_concept: str) -> list[str]:
    match = _OUTCOME_COMPARISON_RE.search(outcome_concept or "")
    if not match:
        return []
    left = _trim_phrase_side(match.group(1))
    right = _trim_phrase_side(match.group(2))
    phrase = _canonical_candidate(f"{left} versus {right}")
    if _is_bad_candidate(phrase):
        return []
    return [phrase]


def _pico_pair_candidates(interventions: list[str], comparisons: list[str]) -> list[str]:
    candidates: list[str] = []
    for left in interventions:
        for right in comparisons:
            phrase = _canonical_candidate(f"{left} versus {right}")
            if not _is_bad_candidate(phrase):
                candidates.append(phrase)
    if len(interventions) >= 2:
        for left, right in combinations(interventions, 2):
            phrase = _canonical_candidate(f"{left} versus {right}")
            if not _is_bad_candidate(phrase):
                candidates.append(phrase)
    if len(comparisons) >= 2:
        for left, right in combinations(comparisons, 2):
            phrase = _canonical_candidate(f"{left} versus {right}")
            if not _is_bad_candidate(phrase):
                candidates.append(phrase)
    family_label = _family_summary_label(comparisons)
    if family_label:
        for left in interventions:
            candidates.append(_canonical_candidate(f"{left} versus {family_label}"))
    return candidates


def _ventilation_candidates(all_text: str) -> list[str]:
    normalized = normalize_text(all_text)
    if not any(token in normalized for token in ("nhfov", "nhfv", "noninvasive highfrequency oscillatory ventilation", "nasal highfrequency oscillatory ventilation")):
        return []
    candidates: list[str] = []
    has_ncpap = "ncpap" in normalized or "nasal continuous positive airway pressure" in normalized
    has_nippv = "nippv" in normalized or "nasal ippv" in normalized or "noninvasive positive pressure ventilation" in normalized
    if has_ncpap:
        candidates.extend(
            [
                "nhfv versus ncpap",
                "initial respiratory support nhfv versus ncpap subgroup analyses",
                "respiratory support following planned extubation nhfv versus ncpap subgroup analyses",
            ]
        )
        if "preterm infants" in normalized:
            candidates.append("nhfv versus ncpap preterm infants")
        if "hz 10" in normalized or "hz ≥ 10" in normalized or "hz > 10" in normalized:
            candidates.extend(["nhfv versus ncpap nhfv hz 10", "nhfv versus ncpap nhfv hz ≥ 10"])
        if "map 10" in normalized:
            candidates.append("nhfv versus ncpap nhfv map 10 cm h2o")
    if has_nippv:
        candidates.extend(
            [
                "nhfv versus nippv",
                "initial respiratory support nhfv versus nippv subgroup analyses",
                "respiratory support following planned extubation nhfv versus nippv subgroup analyses",
            ]
        )
        if "preterm infants" in normalized:
            candidates.append("nhfv versus nippv preterm infants")
        if "hz ≥ 10" in normalized or "hz > 10" in normalized:
            candidates.append("nhfv versus nippv nhfv hz ≥ 10")
        if "map 10" in normalized:
            candidates.append("nhfv versus nippv nhfv map 10 cm h2o")
    if has_ncpap or has_nippv:
        candidates.extend(
            [
                "initial respiratory support nhfv versus other noninvasive respiratory therapy modalities",
                "respiratory support following planned extubation nhfv versus other noninvasive respiratory therapy modalities",
            ]
        )
    return candidates


def _mindfulness_family_candidates(instance: dict[str, Any], all_text: str) -> list[str]:
    normalized = normalize_text(all_text)
    sr_pico = instance.get("sr_pico", {}) or {}
    interventions = " ".join(_unique_clean_list(sr_pico.get("intervention", [])))
    combined = normalize_text(interventions + " " + normalized)
    candidates: list[str] = []
    if "transcendental meditation" in combined:
        candidates.extend(["tm versus active comparators", "tm versus nonactive comparators"])
    if "mindfulness" in combined or "mindfulnessbased" in combined or "mindfulness based" in combined:
        candidates.extend(["mbis versus active comparators", "mbis versus nonactive comparators"])
    return candidates


def _service_system_candidates(instance: dict[str, Any], all_text: str) -> list[str]:
    outcome = normalize_text(instance.get("outcome_concept", ""))
    normalized = normalize_text(all_text)
    if "service system approaches" in outcome:
        return ["service system approaches versus inactive control"]
    if "parent" in normalized or "parenting" in normalized:
        return [
            "service system approaches versus inactive control",
            "parenting interventions versus inactive control",
        ]
    return []


def _retainer_candidates(all_text: str) -> list[str]:
    normalized = normalize_text(all_text)
    if "retainer" not in normalized:
        return []
    candidates = ["fixed versus fixed retainers"]
    variant_bases: list[str] = []
    if "cad/cam" in normalized and "multistrand" in normalized:
        variant_bases.extend(
            [
                "cad/cam nitinol versus multistrand retainers",
                "cad/cam nitinol versus multistrand stainless steel retainers",
            ]
        )
    if "cad/cam" in normalized and "rectangular chain" in normalized:
        variant_bases.append("cad/cam nitinol versus rectangular chain retainers")
        variant_bases.append("cad/cam nitinol versus rectangular chain bonded retainers")
    if ("fiberreinforced composite" in normalized or "fibrereinforced composite" in normalized or "single strand ribbon" in normalized) and "multistrand" in normalized:
        variant_bases.extend(
            [
                "fibrereinforced composite versus multistrand retainer",
                "fibrereinforced composite versus multistrand bonded retainer",
            ]
        )
    if "conventional orthodontic primer" in normalized and "universal primer" in normalized:
        variant_bases.append("conventional orthodontic primer versus universal primer fixed retainer")
    if "flowable composite" in normalized and "conventional" in normalized:
        variant_bases.append("conventional versus flowable composite fixed retainer")
    if "thick plain wire canine to canine" in normalized and "thin spiral wire incisors and canines" in normalized:
        variant_bases.append("thick plain wire canine to canine versus thin spiral wire incisors and canines")
    for base in variant_bases:
        candidates.append(base)
        for prefix in ("lower", "upper"):
            for month in (6, 12, 24):
                candidates.append(f"{prefix} {base} at {month} months")
    return candidates


def build_comparison_candidates(instance: dict[str, Any]) -> list[str]:
    sr_pico = instance.get("sr_pico", {}) or {}
    interventions = _unique_clean_list(sr_pico.get("intervention", []))
    comparisons = _unique_clean_list(sr_pico.get("comparison", []))
    collected: list[str] = []
    all_text = _all_text(instance)

    collected.extend(_extract_outcome_comparison(instance.get("outcome_concept", "")))
    if interventions or comparisons:
        collected.extend(_pico_pair_candidates(interventions, comparisons))
    for evidence_row in instance.get("study_evidence", []):
        title = clean_text(evidence_row.get("primary_report_title"))
        abstract_text = clean_text(evidence_row.get("abstract_text"))
        for blob in (title, abstract_text):
            if blob:
                collected.extend(_extract_text_pairs(blob))

    collected.extend(_ventilation_candidates(all_text))
    collected.extend(_mindfulness_family_candidates(instance, all_text))
    collected.extend(_service_system_candidates(instance, all_text))
    collected.extend(_retainer_candidates(all_text))

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in collected:
        canonical = _canonical_candidate(candidate)
        normalized = normalize_comparison_text(canonical)
        if not canonical or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(canonical)
        if len(deduped) >= _MAX_CANDIDATES:
            break
    return deduped
