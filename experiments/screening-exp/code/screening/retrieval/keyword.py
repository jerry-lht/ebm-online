"""Deterministic keyword retrieval for criterion-wise screening."""

from __future__ import annotations

import re
from collections import Counter

from screening.pipeline.criteria import build_csmed_criterion_specs
from screening.retrieval.evidence_pool import build_evidence_pool
from screening.schemas import CriterionGroup, CriterionSpec, EvidenceItem, InputSetting, ScreeningExample

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
INCLUSION_CUES = {
    "include",
    "eligible",
    "randomized",
    "trial",
    "participants",
    "patients",
    "adults",
    "children",
    "outcome",
    "intervention",
}
EXCLUSION_CUES = {
    "exclude",
    "excluded",
    "protocol",
    "editorial",
    "commentary",
    "review",
    "animal",
    "conference",
    "case",
}


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _token_counter(text: str) -> Counter[str]:
    return Counter(token for token in _tokenize(text) if token not in STOPWORDS)


def _cue_overlap_score(text: str, cues: set[str]) -> int:
    evidence_tokens = set(_tokenize(text))
    return sum(1 for cue in cues if cue in evidence_tokens)


def _score_evidence(
    *,
    criterion: CriterionSpec,
    question: str,
    item: EvidenceItem,
) -> tuple[float, dict[str, object]]:
    criterion_tokens = _token_counter(criterion.criterion_text)
    text_tokens = _token_counter(item.text)
    title_tokens = _token_counter(item.title or "")
    question_tokens = _token_counter(question)

    overlap_tokens = sorted(set(criterion_tokens) & set(text_tokens))
    title_overlap_tokens = sorted(set(criterion_tokens) & set(title_tokens))
    question_overlap_tokens = sorted(set(question_tokens) & set(text_tokens))

    overlap_score = float(sum(min(criterion_tokens[token], text_tokens[token]) for token in overlap_tokens))
    title_overlap_score = float(
        sum(min(criterion_tokens[token], title_tokens[token]) for token in title_overlap_tokens)
    )
    weak_question_score = 0.25 * float(
        sum(min(question_tokens[token], text_tokens[token]) for token in question_overlap_tokens)
    )
    cue_words = EXCLUSION_CUES if criterion.criterion_group == CriterionGroup.exclusion else INCLUSION_CUES
    cue_score = 0.5 * float(_cue_overlap_score(item.text, cue_words))
    total_score = overlap_score + title_overlap_score + weak_question_score + cue_score

    breakdown = {
        "score": total_score,
        "overlap_score": overlap_score,
        "title_overlap_score": title_overlap_score,
        "weak_question_score": weak_question_score,
        "cue_score": cue_score,
        "overlap_tokens": overlap_tokens,
        "title_overlap_tokens": title_overlap_tokens,
        "question_overlap_tokens": question_overlap_tokens,
    }
    return total_score, breakdown


def select_evidence_for_criteria(
    example: ScreeningExample,
    criterion_specs: list[CriterionSpec],
    setting: InputSetting,
    top_k: int,
) -> dict[str, list[EvidenceItem]]:
    """Select deterministic top-k evidence chunks per criterion."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    question = (example.question or "").strip()
    evidence_pool = build_evidence_pool(example, setting)
    selections: dict[str, list[EvidenceItem]] = {}

    for criterion in criterion_specs:
        scored: list[tuple[float, EvidenceItem, dict[str, object]]] = []
        for item in evidence_pool:
            score, breakdown = _score_evidence(
                criterion=criterion,
                question=question,
                item=item,
            )
            scored.append((score, item, breakdown))

        scored.sort(
            key=lambda entry: (
                -entry[0],
                entry[1].source,
                entry[1].section_id,
                entry[1].evidence_id,
            )
        )
        selected: list[EvidenceItem] = []
        for score, item, breakdown in scored[:top_k]:
            selected.append(
                item.model_copy(
                    update={
                        "metadata": {
                            **item.metadata,
                            "retrieval_strategy": "keyword_v1",
                            "retrieval_score": score,
                            "retrieval_breakdown": breakdown,
                        }
                    }
                )
            )
        selections[criterion.criterion_id] = selected
    return selections


def select_evidence_for_example(
    example: ScreeningExample,
    *,
    setting: InputSetting,
    top_k: int,
) -> tuple[list[CriterionSpec], str, dict[str, list[EvidenceItem]]]:
    """Convenience helper that plans criteria and retrieves evidence."""
    criterion_specs, criterion_mode = build_csmed_criterion_specs(example)
    selections = select_evidence_for_criteria(example, criterion_specs, setting, top_k)
    return criterion_specs, criterion_mode, selections
