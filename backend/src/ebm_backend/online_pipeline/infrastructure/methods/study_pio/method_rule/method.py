"""Lightweight rule-based Study PIO extraction method.

This method is intended for benchmark plumbing and baseline comparisons. It
uses only the question PICO and cleaned article text; it does not read benchmark
gold labels.
"""

from __future__ import annotations

import re

from ebm_backend.online_pipeline.domain.article import CleanedArticle
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.study_characteristics import (
    StudyComparatorCharacteristics,
    StudyInterventionCharacteristics,
    StudyOutcomeCharacteristics,
    StudyPIOCharacteristics,
    StudyPopulationCharacteristics,
)


class Method:
    def run(
        self,
        *,
        question_pico: QuestionPICO,
        included_studies: list[str],
        articles: list[CleanedArticle],
    ) -> list[StudyPIOCharacteristics]:
        articles_by_study = {article.study_id: article for article in articles}
        results = []
        for study_id in included_studies:
            article = articles_by_study.get(study_id)
            if article is None:
                continue
            methods_text = _section_text(article, ("methods", "materials and methods", "participants"))
            results_text = _section_text(article, ("results",))
            fallback_text = _section_text(article, ("abstract", "introduction", "background")) or _all_text(article)
            population_text = _first_relevant_sentence(methods_text, ("participants", "patients", "adults", "children", "women", "men"))
            if not population_text:
                population_text = _first_sentences(methods_text or fallback_text, max_sentences=2)
            intervention_text = _first_relevant_sentence(methods_text, ("intervention", "random", "allocated", "treatment", "control", "placebo"))
            if not intervention_text:
                intervention_text = _pico_text(question_pico.I) or _first_sentences(methods_text or fallback_text, max_sentences=1)
            comparator_text = _pico_text(question_pico.C)
            outcome_text = _first_relevant_sentence(results_text or methods_text, ("outcome", "primary", "secondary", "measured", "assessed"))
            if not outcome_text:
                outcome_text = _pico_text(question_pico.O) or _first_sentences(results_text or fallback_text, max_sentences=1)
            results.append(
                StudyPIOCharacteristics(
                    study_id=study_id,
                    population=StudyPopulationCharacteristics(description=population_text),
                    interventions=[
                        StudyInterventionCharacteristics(
                            label=_short_label(intervention_text) or "intervention",
                            description=intervention_text,
                        )
                    ],
                    comparators=[
                        StudyComparatorCharacteristics(
                            label=_short_label(comparator_text) or "comparator",
                            description=comparator_text,
                        )
                    ]
                    if comparator_text
                    else [],
                    outcomes=[
                        StudyOutcomeCharacteristics(
                            outcome_label=_short_label(outcome_text) or "outcome",
                            measurement=outcome_text,
                        )
                    ],
                    notes="Rule baseline extracted from cleaned article sections.",
                )
            )
        return results


def build_method() -> Method:
    return Method()


def _section_text(article: CleanedArticle, names: tuple[str, ...]) -> str:
    normalized_names = tuple(_normalize_name(name) for name in names)
    chunks = []
    for section in article.xml_content.sections:
        title = _normalize_name(section.title)
        if any(name in title or title in name for name in normalized_names):
            chunks.append(section.text)
    return "\n\n".join(chunks).strip()


def _all_text(article: CleanedArticle) -> str:
    return "\n\n".join(section.text for section in article.xml_content.sections).strip()


def _first_relevant_sentence(text: str, keywords: tuple[str, ...]) -> str:
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence
    return ""


def _first_sentences(text: str, *, max_sentences: int) -> str:
    return " ".join(_sentences(text)[:max_sentences]).strip()


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _pico_text(items: list[str]) -> str:
    return "; ".join(str(item).strip() for item in items if str(item).strip())


def _short_label(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:80].rstrip(" ,.;:")


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
