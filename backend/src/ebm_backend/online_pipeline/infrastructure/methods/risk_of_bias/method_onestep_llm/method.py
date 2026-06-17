"""Article-only Risk of Bias method.

The five core domains reuse the old RoB onestep criteria, but this method only
consumes workflow `CleanedArticle` inputs. It does not read benchmark gold or SR
characteristics.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ebm_backend.online_pipeline.domain.article import ArticleTable, CleanedArticle
from ebm_backend.online_pipeline.domain.risk_of_bias import RiskOfBiasAssessment, RoB1DomainJudgement
from ebm_backend.online_pipeline.infrastructure.llm import LLMConfig, call_llm_json, load_llm_config


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
LLM_DOMAINS = [
    "random_sequence_generation",
    "allocation_concealment",
    "blinding_participants_personnel",
    "blinding_outcome_assessment",
    "incomplete_outcome_data",
]
BASELINE_DOMAINS = ["selective_reporting", "other_bias"]
DOMAIN_LABELS = {
    "random_sequence_generation": "Random sequence generation (selection bias)",
    "allocation_concealment": "Allocation concealment (selection bias)",
    "blinding_participants_personnel": "Blinding of participants and personnel (performance bias)",
    "blinding_outcome_assessment": "Blinding of outcome assessment (detection bias)",
    "incomplete_outcome_data": "Incomplete outcome data (attrition bias)",
    "selective_reporting": "Selective reporting (reporting bias)",
    "other_bias": "Other bias",
}


class Method:
    def __init__(self) -> None:
        self.llm_config_path: Path | None = None
        self.workers = 1

    def configure_for_benchmark(
        self,
        *,
        llm_config: str | Path = "llm.local.json",
        workers: int = 1,
        run_dir: str | Path | None = None,
        resume: bool = False,
    ) -> None:
        self.llm_config_path = Path(llm_config)
        self.workers = max(1, int(workers or 1))

    def run(self, *, included_studies: list[str], articles: list[CleanedArticle]) -> list[RiskOfBiasAssessment]:
        config = load_llm_config(self.llm_config_path or Path("llm.local.json"))
        if config is None:
            raise RuntimeError("Missing LLM config for risk_of_bias.method_onestep_llm")
        articles_by_study = {article.study_id: article for article in articles}
        results = []
        for study_id in included_studies:
            article = articles_by_study.get(study_id)
            if article is None and len(articles) == 1:
                article = articles[0]
            if article is None:
                continue
            evidence = _article_evidence(article)
            judgements = self._run_domains(config=config, evidence=evidence)
            judgements.extend(_baseline_domains(article))
            results.append(
                RiskOfBiasAssessment(
                    study_id=study_id,
                    domains=judgements,
                    overall="unclear",
                    notes="Five-domain LLM method plus baseline fallbacks for selective reporting and other bias.",
                )
            )
        return results

    def _run_domains(self, *, config: LLMConfig, evidence: str) -> list[RoB1DomainJudgement]:
        if self.workers > 1:
            with ThreadPoolExecutor(max_workers=min(self.workers, len(LLM_DOMAINS))) as executor:
                return list(executor.map(lambda domain_id: _run_llm_domain(config=config, domain_id=domain_id, evidence=evidence), LLM_DOMAINS))
        return [_run_llm_domain(config=config, domain_id=domain_id, evidence=evidence) for domain_id in LLM_DOMAINS]


def build_method() -> Method:
    return Method()


def _run_llm_domain(*, config: LLMConfig, domain_id: str, evidence: str) -> RoB1DomainJudgement:
    prompt = _system_prompt(domain_id)
    parsed = call_llm_json(
        config=config,
        system=prompt,
        prompt=f"{evidence}\n\nAssess {DOMAIN_LABELS[domain_id]}. Output JSON only.",
    )
    return RoB1DomainJudgement(
        domain=domain_id,
        judgement=_normalize_judgement(parsed.get("judgement")),
        rationale=str(parsed.get("support_text") or parsed.get("rationale") or ""),
    )


def _system_prompt(domain_id: str) -> str:
    criteria = (PROMPT_DIR / f"{domain_id}.txt").read_text(encoding="utf-8").strip()
    return f"""You are a systematic-review risk-of-bias assessor following Cochrane Handbook Chapter 8.

You are assessing ONE domain only:
Domain: {DOMAIN_LABELS[domain_id]}

{criteria}

High risk requires positive evidence in the article, not merely missing information.
Use only the supplied article sections and tables. Do not use benchmark gold labels.
When information is insufficient, choose Unclear risk.

Output a single JSON object with exactly these fields:
{{
  "domain": "{DOMAIN_LABELS[domain_id]}",
  "judgement": "Low risk | High risk | Unclear risk",
  "support_text": "Quote: ... Comment: ... OR Summary: ... Comment: ..."
}}

Rules:
- judgement must be exactly one of: Low risk, High risk, Unclear risk
- support_text must include evidence or note its absence and explain the reasoning
- Output JSON only, no text outside the JSON object"""


def _baseline_domains(article: CleanedArticle) -> list[RoB1DomainJudgement]:
    evidence_text = _all_article_text(article).lower()
    reporting_support = _first_keyword_sentence(evidence_text, ("protocol", "registered", "registration", "primary outcome", "secondary outcome"))
    other_support = _first_keyword_sentence(evidence_text, ("funding", "conflict of interest", "competing interests", "baseline", "deviation"))
    return [
        RoB1DomainJudgement(
            domain="selective_reporting",
            judgement="unclear_risk",
            rationale=reporting_support or "Baseline fallback: selective reporting is not assessed by the imported five-domain LLM method.",
        ),
        RoB1DomainJudgement(
            domain="other_bias",
            judgement="unclear_risk",
            rationale=other_support or "Baseline fallback: other bias is not assessed by the imported five-domain LLM method.",
        ),
    ]


def _article_evidence(article: CleanedArticle) -> str:
    front: list[str] = []
    methods: list[str] = []
    results: list[str] = []
    other: list[str] = []
    for section in article.xml_content.sections:
        title = section.title or "Section"
        block = f"### {title}\n{section.text}"
        normalized = title.lower()
        if normalized in {"front", "abstract"} or "abstract" in normalized:
            front.append(block)
        elif "method" in normalized or "material" in normalized or "participant" in normalized:
            methods.append(block)
        elif "result" in normalized:
            results.append(block)
        else:
            other.append(block)

    parts = [f"Study: {article.study_id}", "\n## Abstract / Front matter", *front[:3]]
    if methods:
        parts.extend(["\n## Methods", *methods])
    if results:
        parts.extend(["\n## Results", *results])
    table_text = _tables_text(article.tables)
    if table_text:
        parts.extend(["\n## Tables", table_text])
    if other:
        parts.extend(["\n## Other sections", *[item[:5000] for item in other[:8]]])
    text = "\n\n".join(part for part in parts if part)
    max_chars = 180_000
    if len(text) > max_chars:
        table_marker = "\n\n## Tables"
        table_part = ""
        if table_marker in text:
            prefix, _, suffix = text.partition(table_marker)
            table_part = table_marker + suffix
            text = prefix
        text = text[: max_chars - len(table_part) - 2000] + "\n\n[... truncated ...]" + table_part[:80_000]
    return text


def _tables_text(tables: list[ArticleTable]) -> str:
    chunks = []
    prioritized = sorted(tables, key=lambda table: 0 if _table_is_high_priority(table) else 1)
    for index, table in enumerate(prioritized[:12], start=1):
        rows_text = _rows_text(table.rows)
        chunks.append(f"### Table {index}: {table.caption or table.table_id}\n{rows_text[:8000]}")
    return "\n\n".join(chunks)


def _table_is_high_priority(table: ArticleTable) -> bool:
    text = f"{table.caption} {json.dumps(table.rows, ensure_ascii=False)[:1000]}".lower()
    return any(keyword in text for keyword in ("flow", "attrition", "withdraw", "lost", "baseline", "outcome", "adverse", "protocol"))


def _rows_text(rows: list[dict[str, str]]) -> str:
    lines = []
    for row in rows[:80]:
        if "_raw_xml" in row:
            section_path = row.get("_section_path") or ""
            lines.append(f"Section path: {section_path}\nRaw XML: {row.get('_raw_xml', '')}")
        else:
            lines.append(" | ".join(f"{key}: {value}" for key, value in row.items()))
    return "\n".join(lines)


def _all_article_text(article: CleanedArticle) -> str:
    sections = "\n".join(section.text for section in article.xml_content.sections)
    tables = "\n".join(_rows_text(table.rows) for table in article.tables)
    return f"{sections}\n{tables}"


def _first_keyword_sentence(text: str, keywords: tuple[str, ...]) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "")):
        if any(keyword in sentence for keyword in keywords):
            return sentence[:1000]
    return ""


def _normalize_judgement(value: Any) -> str:
    text = str(value or "").lower().strip()
    if "low" in text:
        return "low_risk"
    if "high" in text:
        return "high_risk"
    return "unclear_risk"
