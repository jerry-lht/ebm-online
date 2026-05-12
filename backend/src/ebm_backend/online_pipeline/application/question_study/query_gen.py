"""Boolean query generation from PICO terms."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study.llm_io import load_prompt, load_schema


MESH_FALLBACK = {
    "type 2 diabetes mellitus": ("Diabetes Mellitus, Type 2", ["Type 2 Diabetes", "Adult-Onset Diabetes"]),
    "dental caries": ("Dental Caries", ["Carious Teeth", "Tooth Decay"]),
    "hydroxyapatite": ("Hydroxyapatites", ["Hydroxyapatite"]),
    "zinc-carbonate hydroxyapatite": ("Hydroxyapatites", ["Hydroxyapatite", "Zinc-Carbonate Hydroxyapatite"]),
    "metformin": ("Metformin", ["Dimethylbiguanidine"]),
}


@dataclass(frozen=True)
class TermMapping:
    original: str
    mesh_preferred: list[str] = field(default_factory=list)
    entry_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QueryGenOutput:
    boolean_query: str
    population_block: str
    intervention_block: str
    mapping_detail: dict[str, list[TermMapping]]
    search_filters: dict[str, str | bool]


class QueryGenerator:
    """Generate deterministic Boolean queries for Module 2 MVP."""

    _LLM_PROMPT_NAME = "query_generation"

    def generate(self, *, population: list[str], intervention: list[str]) -> QueryGenOutput:
        pop_mappings = [self._map_term(term) for term in population if term.strip()]
        int_mappings = [self._map_term(term) for term in intervention if term.strip()]
        pop_terms = self._collect_terms(pop_mappings)
        int_terms = self._collect_terms(int_mappings)

        population_block = self._build_or_block(pop_terms)
        intervention_block = self._build_or_block(int_terms)
        if population_block and intervention_block:
            boolean_query = f"({population_block}) AND ({intervention_block})"
        else:
            boolean_query = population_block or intervention_block

        return QueryGenOutput(
            boolean_query=boolean_query,
            population_block=population_block,
            intervention_block=intervention_block,
            mapping_detail={
                "population": pop_mappings,
                "intervention": int_mappings,
            },
            search_filters={
                "open_access": True,
                "article_type": "primary_rct",
            },
        )

    async def generate_with_llm(
        self,
        gateway: LLMGateway,
        *,
        population: list[str],
        intervention: list[str],
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QueryGenOutput:
        """Ask LLM for extra search terms, then run offline MeSH fallback + Boolean assembly."""
        prompt_template = load_prompt(self._LLM_PROMPT_NAME)
        response_schema: dict[str, Any] = load_schema(self._LLM_PROMPT_NAME)
        pop_clean = [t.strip() for t in population if t.strip()]
        int_clean = [t.strip() for t in intervention if t.strip()]
        result = await gateway.call(
            task_type=self._LLM_PROMPT_NAME,
            inputs={"population": pop_clean, "intervention": int_clean},
            prompt_template=prompt_template,
            prompt_vars={
                "population_json": json.dumps(pop_clean, ensure_ascii=False),
                "intervention_json": json.dumps(int_clean, ensure_ascii=False),
            },
            response_schema=response_schema,
            temperature=0.0,
            cacheable=False,
            run_id=run_id,
            module="module2",
            task_name="query_generation",
            study_id="question",
            prompt_version=prompt_version,
        )
        extra_p = list(result.content.get("population_extra_terms") or [])
        extra_i = list(result.content.get("intervention_extra_terms") or [])
        pop_mappings = self._llm_mappings(result.content.get("population_mappings"), pop_clean)
        int_mappings = self._llm_mappings(result.content.get("intervention_mappings"), int_clean)
        if extra_p:
            pop_mappings.extend(TermMapping(original=term) for term in self._new_terms(pop_mappings, extra_p))
        if extra_i:
            int_mappings.extend(TermMapping(original=term) for term in self._new_terms(int_mappings, extra_i))
        return self._build_output(pop_mappings, int_mappings)

    def generate_with_llm_sync(
        self,
        gateway: LLMGateway,
        *,
        population: list[str],
        intervention: list[str],
        run_id: str | None = None,
        prompt_version: str = "v1",
    ) -> QueryGenOutput:
        return asyncio.run(
            self.generate_with_llm(
                gateway,
                population=population,
                intervention=intervention,
                run_id=run_id,
                prompt_version=prompt_version,
            )
        )

    def _merge_extra_terms(self, base: list[str], extra: list[str]) -> list[str]:
        seen = {self._normalize_key(t) for t in base if t.strip()}
        out = [t.strip() for t in base if t.strip()]
        for raw in extra:
            term = (raw or "").strip()
            if not term:
                continue
            key = self._normalize_key(term)
            if key in seen:
                continue
            seen.add(key)
            out.append(term)
        return out

    def _llm_mappings(self, raw_mappings: Any, fallback_terms: list[str]) -> list[TermMapping]:
        mappings: list[TermMapping] = []
        if isinstance(raw_mappings, list):
            for raw in raw_mappings:
                if not isinstance(raw, dict):
                    continue
                original = str(raw.get("original") or "").strip()
                if not original:
                    continue
                mappings.append(
                    TermMapping(
                        original=original,
                        mesh_preferred=[str(term).strip() for term in raw.get("mesh_preferred") or [] if str(term).strip()],
                        entry_terms=[str(term).strip() for term in raw.get("entry_terms") or [] if str(term).strip()],
                    )
                )
        seen = {self._normalize_key(mapping.original) for mapping in mappings}
        for term in fallback_terms:
            key = self._normalize_key(term)
            if key and key not in seen:
                mappings.append(self._map_term(term))
                seen.add(key)
        return mappings

    def _new_terms(self, mappings: list[TermMapping], terms: list[str]) -> list[str]:
        seen: set[str] = set()
        for mapping in mappings:
            for term in [mapping.original, *mapping.mesh_preferred, *mapping.entry_terms]:
                key = self._normalize_key(term)
                if key:
                    seen.add(key)
        out: list[str] = []
        for term in terms:
            key = self._normalize_key(str(term))
            if key and key not in seen:
                out.append(str(term).strip())
                seen.add(key)
        return out

    def _build_output(self, pop_mappings: list[TermMapping], int_mappings: list[TermMapping]) -> QueryGenOutput:
        pop_terms = self._collect_terms(pop_mappings)
        int_terms = self._collect_terms(int_mappings)

        population_block = self._build_or_block(pop_terms)
        intervention_block = self._build_or_block(int_terms)
        if population_block and intervention_block:
            boolean_query = f"({population_block}) AND ({intervention_block})"
        else:
            boolean_query = population_block or intervention_block

        return QueryGenOutput(
            boolean_query=boolean_query,
            population_block=population_block,
            intervention_block=intervention_block,
            mapping_detail={
                "population": pop_mappings,
                "intervention": int_mappings,
            },
            search_filters={
                "open_access": True,
                "article_type": "primary_rct",
            },
        )

    @staticmethod
    def _normalize_key(term: str) -> str:
        return " ".join(term.lower().strip().split())

    def _map_term(self, term: str) -> TermMapping:
        key = self._normalize_key(term)
        if key in MESH_FALLBACK:
            preferred, entries = MESH_FALLBACK[key]
            return TermMapping(
                original=term.strip(),
                mesh_preferred=[preferred],
                entry_terms=list(entries),
            )
        return TermMapping(original=term.strip())

    def _collect_terms(self, mappings: list[TermMapping]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for mapping in mappings:
            for term in [mapping.original, *mapping.mesh_preferred, *mapping.entry_terms]:
                normalized = self._normalize_key(term)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                merged.append(term.strip())
        return merged

    @staticmethod
    def _quote(term: str) -> str:
        escaped = term.replace('"', '\\"')
        return f'"{escaped}"'

    def _build_or_block(self, terms: list[str]) -> str:
        return " OR ".join(self._quote(term) for term in terms if term)
