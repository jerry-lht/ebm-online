"""Offline Module 1 pipeline for PMC-RCT index construction."""

from __future__ import annotations

import html
import json
import re
import shutil
import sqlite3
import asyncio
import unicodedata
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from openai import AsyncOpenAI
except ModuleNotFoundError:  # pragma: no cover - optional during unit tests
    AsyncOpenAI = Any  # type: ignore[assignment]

from ebm_backend.shared.config.settings import settings
from ebm_backend.shared.llm.gateway import LLMGateway, LLMRequest
from ebm_backend.index_construction.application.mesh import MeshLookupClient
from ebm_backend.shared.persistence.db import get_connection, get_dict_cursor, init_db


STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "with",
    "in",
    "on",
    "at",
    "by",
    "from",
    "vs",
    "versus",
}

ABBREVIATIONS = {
    "t2dm": "type 2 diabetes mellitus",
    "dm": "diabetes mellitus",
    "copd": "chronic obstructive pulmonary disease",
    "cad": "coronary artery disease",
    "htn": "hypertension",
}

MESH_FALLBACK = {
    "type 2 diabetes mellitus": {
        "descriptor_id": "D003924",
        "preferred_term": "Diabetes Mellitus, Type 2",
        "entry_terms": ["Type 2 Diabetes", "Adult-Onset Diabetes"],
    },
    "hypertension": {
        "descriptor_id": "D006973",
        "preferred_term": "Hypertension",
        "entry_terms": ["High Blood Pressure"],
    },
    "dental caries": {
        "descriptor_id": "D003731",
        "preferred_term": "Dental Caries",
        "entry_terms": ["Carious Teeth", "Tooth Decay"],
    },
    "carious teeth": {
        "descriptor_id": "D003731",
        "preferred_term": "Dental Caries",
        "entry_terms": ["Carious Teeth", "Tooth Decay"],
    },
    "hydroxyapatite": {
        "descriptor_id": "D006845",
        "preferred_term": "Hydroxyapatites",
        "entry_terms": ["Hydroxyapatite"],
    },
    "zinc-carbonate hydroxyapatite": {
        "descriptor_id": "D006845",
        "preferred_term": "Hydroxyapatites",
        "entry_terms": ["Hydroxyapatite", "Zinc-Carbonate Hydroxyapatite"],
    },
    "composite restoration": {
        "descriptor_id": "D003802",
        "preferred_term": "Composite Resins",
        "entry_terms": ["Composite Restoration", "Dental Composite"],
    },
    "composite resins": {
        "descriptor_id": "D003802",
        "preferred_term": "Composite Resins",
        "entry_terms": ["Composite Restoration", "Dental Composite"],
    },
    "metformin": {
        "descriptor_id": "D008687",
        "preferred_term": "Metformin",
        "entry_terms": ["Dimethylbiguanidine"],
    },
    "adults": {
        "descriptor_id": "D000328",
        "preferred_term": "Adult",
        "entry_terms": ["Adults"],
    },
}


@dataclass(frozen=True)
class StudyRecord:
    study_id: str
    manifest_rel_path: str
    article_path: str
    pmid: str | None
    pmcid: str | None
    title: str
    abstract: str
    source: str
    publication_year: int | None
    article_type: str = "primary_rct"
    open_access: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SpanResult:
    text: str
    source: str
    start_char: int | None = None
    end_char: int | None = None


@dataclass(frozen=True)
class PIExtractionResult:
    study_id: str
    population_spans: list[SpanResult]
    intervention_spans: list[SpanResult]
    extraction_source: str


@dataclass(frozen=True)
class MedicalConcept:
    text: str
    type: str
    mesh_descriptor: str | None = None


@dataclass(frozen=True)
class MeSHTerm:
    descriptor_id: str
    preferred_term: str
    entry_terms: list[str]
    match_source: str


@dataclass(frozen=True)
class NormalizedField:
    original_spans: list[str]
    cleaned_text: str
    concepts: list[MedicalConcept]
    mesh_terms: list[MeSHTerm]
    synonyms: list[str]
    indexable_text: str


@dataclass(frozen=True)
class NormalizedPI:
    study_id: str
    population: NormalizedField
    intervention: NormalizedField


@dataclass(frozen=True)
class IndexDocument:
    study_id: str
    pmid: str | None
    pmcid: str | None
    title: str
    abstract: str
    population: str
    intervention: str
    population_original: str
    intervention_original: str
    mesh_terms: list[str]
    mesh_population: list[str]
    mesh_intervention: list[str]
    article_type: str
    open_access: bool
    source: str
    publication_year: int | None
    article_path: str
    indexed_at: str


@dataclass(frozen=True)
class LocalSearchHit:
    study_id: str
    score: float
    title: str
    matched_fields: list[str]
    document: dict[str, Any]


@dataclass(frozen=True)
class Module1QueryValidationRow:
    """One fixed-query check against LocalRCTIndex."""

    query: str
    passed: bool
    hit_count: int
    top_hits: tuple[dict[str, Any], ...]
    expected_study_id: str | None = None
    expected_in_top_hits: bool | None = None


@dataclass(frozen=True)
class Module1SimplifiedResult:
    data_root: str
    export_dir: str
    index_path: str
    studies_total: int
    extracted: int
    normalized: int
    indexed: int
    failed: int
    failures: list[dict[str, str]]
    query_validation: tuple[Module1QueryValidationRow, ...] = ()
    queries_passed: int = 0
    queries_total: int = 0


# Fixed retrieval smoke queries for Phase 2 (see docs/plans/implementation-plan.md).
# Optional expected_study_id checks recall for the 100-demo subset titles.
MODULE1_FIXED_QUERIES: tuple[tuple[str, str | None], ...] = (
    ("zinc-carbonate hydroxyapatite dental caries", "pmid:36908720"),
    ("tranexamic acid orthopedic surgery", "pmid:36919025"),
    ("Epley maneuver positional nystagmus", "pmid:36923489"),
    ("ADHDCoach parents children ADHD", "pmid:36923370"),
    ("garlic extract coronavirus hospitalized", "pmid:36998289"),
)

MODULE1_DEMO_1000_THEME_QUOTAS: dict[str, int] = {
    "surgery_anesthesia_pain": 250,
    "exercise_rehab": 150,
    "mental_neuro": 150,
    "diabetes_metabolic": 120,
    "covid_respiratory": 120,
    "dental_oral_caries": 120,
    "pregnancy_women": 90,
}

MODULE1_DEMO_1000_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "surgery_anesthesia_pain": (
        "surgery",
        "surgical",
        "anesthesia",
        "anaesthesia",
        "postoperative",
        "orthopedic",
        "catheter",
        "pain",
        "analgesia",
        "nerve block",
    ),
    "exercise_rehab": (
        "exercise",
        "rehabilitation",
        "training",
        "physical activity",
        "fitness",
        "motor",
    ),
    "mental_neuro": (
        "depression",
        "adhd",
        "stroke",
        "narcolepsy",
        "cognitive",
        "anxiety",
        "neuro",
    ),
    "diabetes_metabolic": (
        "diabetes",
        "glucose",
        "glycemic",
        "glycaemic",
        "metformin",
        "insulin",
        "metabolic",
    ),
    "covid_respiratory": (
        "covid",
        "coronavirus",
        "respiratory",
        "pneumonia",
        "asthma",
        "copd",
    ),
    "dental_oral_caries": (
        "dental",
        "caries",
        "tooth",
        "teeth",
        "oral",
        "periodontal",
        "orthodontic",
    ),
    "pregnancy_women": (
        "pregnancy",
        "pregnant",
        "postpartum",
        "women",
        "maternal",
        "prenatal",
    ),
}


@dataclass(frozen=True)
class DemoSelectionResult:
    source_data_root: str
    dest_data_root: str
    manifest_path: str
    summary_path: str
    selected_total: int
    requested_total: int
    theme_counts: dict[str, int]
    filler_count: int


@dataclass(frozen=True)
class Module1BatchSummary:
    batch_id: str | None
    status: str
    request_total: int
    submitted: int
    completed: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class Module1BatchRecord:
    batch_id: str
    step_name: str
    status: str
    model: str
    input_file_id: str | None = None
    output_file_id: str | None = None
    error_file_id: str | None = None
    request_total: int = 0
    request_completed: int = 0
    request_failed: int = 0
    manifest_path: str | None = None
    completion_window: str = "24h"
    metadata_json: dict[str, Any] = field(default_factory=dict)


def slugify_study_id(pmid: str | None, pmcid: str | None, article_path: str) -> str:
    if pmid:
        return f"pmid:{pmid}"
    if pmcid:
        return f"pmcid:{pmcid}"
    return f"path:{Path(article_path).stem}"


class PMCReader:
    def __init__(self, data_root: str | Path | None = None):
        self.data_root = Path(data_root or Path("data/data_for_test/data_demo"))
        self.manifest_path = self.data_root / "manifest" / "files.jsonl"

    def iter_primary_rct(self, limit: int = 100) -> list[StudyRecord]:
        studies: list[StudyRecord] = []
        with self.manifest_path.open(encoding="utf-8") as fh:
            for line in fh:
                if len(studies) >= limit:
                    break
                if not line.strip():
                    continue
                manifest = json.loads(line)
                if manifest.get("classification") != "primary_rct":
                    continue
                rel_path = manifest["rel_path"]
                article_path = self.data_root / rel_path
                article = json.loads(article_path.read_text(encoding="utf-8"))
                metadata = article.get("metadata", {})
                sections = article.get("sections", [])
                title = metadata.get("title") or manifest.get("title") or ""
                abstract = extract_abstract_text(sections)
                if not abstract:
                    abstract = extract_section_text(sections, "abstract")
                pmid = str(metadata.get("pmid") or manifest.get("pmid") or "") or None
                pmcid = str(metadata.get("pmc_id") or manifest.get("pmc_id") or "") or None
                publication_year = manifest.get("year")
                source = metadata.get("source_type") or manifest.get("source_type") or "PMC"
                study_id = slugify_study_id(pmid, pmcid, rel_path)
                studies.append(
                    StudyRecord(
                        study_id=study_id,
                        manifest_rel_path=rel_path,
                        article_path=str(article_path),
                        pmid=pmid,
                        pmcid=pmcid,
                        title=title,
                        abstract=abstract,
                        source=source,
                        publication_year=publication_year,
                        metadata=metadata,
                        sections=sections,
                    )
                )
        return studies


class ExtractionStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or settings.database_url
        init_db(self.database_url)
        self.conn = get_connection(self.database_url)

    def close(self) -> None:
        self.conn.close()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()):
        if not isinstance(self.conn, sqlite3.Connection):
            sql = sql.replace("?", "%s")
        cur = get_dict_cursor(self.conn)
        cur.execute(sql, params)
        return cur

    def upsert_study(self, study: StudyRecord) -> None:
        self._execute(
            """
            INSERT INTO module1_studies (
                study_id, manifest_rel_path, article_path, pmid, pmcid, title, abstract,
                source, publication_year, article_type, open_access, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(study_id) DO UPDATE SET
                manifest_rel_path=excluded.manifest_rel_path,
                article_path=excluded.article_path,
                pmid=excluded.pmid,
                pmcid=excluded.pmcid,
                title=excluded.title,
                abstract=excluded.abstract,
                source=excluded.source,
                publication_year=excluded.publication_year,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                study.study_id,
                study.manifest_rel_path,
                study.article_path,
                study.pmid,
                study.pmcid,
                study.title,
                study.abstract,
                study.source,
                study.publication_year,
                study.article_type,
                study.open_access,
            ),
        )
        self.conn.commit()

    def save_extraction(
        self,
        study_id: str,
        batch_id: str | None,
        result: dict[str, Any] | None,
        error: str | None = None,
    ) -> None:
        self._execute(
            """
            UPDATE module1_studies
            SET extraction_status = ?,
                extraction_batch_id = ?,
                extraction_result_json = ?,
                extraction_error = ?,
                retry_count = CASE WHEN ? IS NULL THEN retry_count ELSE retry_count + 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE study_id = ?
            """,
            (
                "completed" if result and not error else "failed",
                batch_id,
                json.dumps(to_jsonable(result), ensure_ascii=False) if result else None,
                error,
                error,
                study_id,
            ),
        )
        self.conn.commit()

    def save_normalization(self, study_id: str, result: dict[str, Any] | None, error: str | None = None) -> None:
        self._execute(
            """
            UPDATE module1_studies
            SET normalization_status = ?,
                normalization_result_json = ?,
                normalization_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE study_id = ?
            """,
            (
                "completed" if result and not error else "failed",
                json.dumps(to_jsonable(result), ensure_ascii=False) if result else None,
                error,
                study_id,
            ),
        )
        self.conn.commit()

    def save_index_status(self, study_id: str, indexed: bool) -> None:
        self._execute(
            """
            UPDATE module1_studies
            SET indexed_status = ?,
                indexed_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE study_id = ?
            """,
            (
                "completed" if indexed else "failed",
                datetime.now(timezone.utc).isoformat() if indexed else None,
                study_id,
            ),
        )
        self.conn.commit()

    def get_study(self, study_id: str) -> sqlite3.Row | None:
        cur = self._execute("SELECT * FROM module1_studies WHERE study_id = ?", (study_id,))
        return cur.fetchone()

    def get_active_batch(self, step_name: str) -> sqlite3.Row | None:
        cur = self._execute(
            """
            SELECT * FROM module1_batches
            WHERE step_name = ?
              AND status IN ('queued', 'processing', 'validating', 'finalizing')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (step_name,),
        )
        return cur.fetchone()

    def save_batch_record(self, batch: Module1BatchRecord) -> None:
        self._execute(
            """
            INSERT INTO module1_batches (
                batch_id, step_name, status, model, input_file_id, output_file_id, error_file_id,
                request_total, request_completed, request_failed, manifest_path, completion_window,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(batch_id) DO UPDATE SET
                step_name=excluded.step_name,
                status=excluded.status,
                model=excluded.model,
                input_file_id=excluded.input_file_id,
                output_file_id=excluded.output_file_id,
                error_file_id=excluded.error_file_id,
                request_total=excluded.request_total,
                request_completed=excluded.request_completed,
                request_failed=excluded.request_failed,
                manifest_path=excluded.manifest_path,
                completion_window=excluded.completion_window,
                metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                batch.batch_id,
                batch.step_name,
                batch.status,
                batch.model,
                batch.input_file_id,
                batch.output_file_id,
                batch.error_file_id,
                batch.request_total,
                batch.request_completed,
                batch.request_failed,
                batch.manifest_path,
                batch.completion_window,
                json.dumps(to_jsonable(batch.metadata_json), ensure_ascii=False) if batch.metadata_json else None,
            ),
        )
        self.conn.commit()

    def update_batch_status(
        self,
        batch_id: str,
        *,
        status: str | None = None,
        input_file_id: str | None = None,
        output_file_id: str | None = None,
        error_file_id: str | None = None,
        request_total: int | None = None,
        request_completed: int | None = None,
        request_failed: int | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        columns = []
        params: list[Any] = []
        if status is not None:
            columns.append("status = ?")
            params.append(status)
        if input_file_id is not None:
            columns.append("input_file_id = ?")
            params.append(input_file_id)
        if output_file_id is not None:
            columns.append("output_file_id = ?")
            params.append(output_file_id)
        if error_file_id is not None:
            columns.append("error_file_id = ?")
            params.append(error_file_id)
        if request_total is not None:
            columns.append("request_total = ?")
            params.append(request_total)
        if request_completed is not None:
            columns.append("request_completed = ?")
            params.append(request_completed)
        if request_failed is not None:
            columns.append("request_failed = ?")
            params.append(request_failed)
        if metadata_json is not None:
            columns.append("metadata_json = ?")
            params.append(json.dumps(to_jsonable(metadata_json), ensure_ascii=False))
        if not columns:
            return
        columns.append("updated_at = CURRENT_TIMESTAMP")
        params.append(batch_id)
        self._execute(
            f"UPDATE module1_batches SET {', '.join(columns)} WHERE batch_id = ?",
            tuple(params),
        )
        self.conn.commit()

    def get_batch_record(self, batch_id: str) -> sqlite3.Row | None:
        cur = self._execute("SELECT * FROM module1_batches WHERE batch_id = ?", (batch_id,))
        return cur.fetchone()

    def get_studies_for_batch(self, batch_id: str) -> list[sqlite3.Row]:
        cur = self._execute(
            """
            SELECT * FROM module1_studies
            WHERE extraction_batch_id = ?
            ORDER BY created_at ASC
            """,
            (batch_id,),
        )
        return cur.fetchall()

    def upsert_batch_from_payload(self, payload: dict[str, Any]) -> None:
        batch = Module1BatchRecord(
            batch_id=payload["batch_id"],
            step_name=payload.get("step_name", "pi_extraction"),
            status=payload.get("status", "queued"),
            model=payload.get("model", settings.llm_model),
            input_file_id=payload.get("input_file_id"),
            output_file_id=payload.get("output_file_id"),
            error_file_id=payload.get("error_file_id"),
            request_total=payload.get("request_total", 0),
            request_completed=payload.get("request_completed", 0),
            request_failed=payload.get("request_failed", 0),
            manifest_path=payload.get("manifest_path"),
            completion_window=payload.get("completion_window", "24h"),
            metadata_json=payload.get("metadata_json") or payload.get("raw") or {},
        )
        self.save_batch_record(batch)

    def get_pending_studies(self, limit: int = 100) -> list[sqlite3.Row]:
        cur = self._execute(
            """
            SELECT * FROM module1_studies
            WHERE extraction_status != 'completed'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_ready_for_normalization(self, limit: int = 100) -> list[sqlite3.Row]:
        cur = self._execute(
            """
            SELECT * FROM module1_studies
            WHERE extraction_status = 'completed'
              AND normalization_status != 'completed'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_ready_for_indexing(self, limit: int = 1000) -> list[sqlite3.Row]:
        cur = self._execute(
            """
            SELECT * FROM module1_studies
            WHERE extraction_status = 'completed'
              AND normalization_status = 'completed'
              AND indexed_status != 'completed'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def mark_extraction_from_batch(
        self,
        *,
        study_id: str,
        batch_id: str | None,
        result: dict[str, Any] | None,
        error: str | None,
        extraction_status: str,
    ) -> None:
        self._execute(
            """
            UPDATE module1_studies
            SET extraction_status = ?,
                extraction_batch_id = ?,
                extraction_result_json = ?,
                extraction_error = ?,
                retry_count = CASE WHEN ? IS NULL THEN retry_count ELSE retry_count + 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE study_id = ?
            """,
            (
                extraction_status,
                batch_id,
                json.dumps(to_jsonable(result), ensure_ascii=False) if result else None,
                error,
                error,
                study_id,
            ),
        )
        self.conn.commit()

    def mark_batch_submitted(self, study_id: str, batch_id: str) -> None:
        self._execute(
            """
            UPDATE module1_studies
            SET extraction_status = ?,
                extraction_batch_id = ?,
                extraction_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE study_id = ?
            """,
            ("submitted", batch_id, study_id),
        )
        self.conn.commit()

    def close_and_commit(self) -> None:
        self.conn.commit()
        self.conn.close()

    def save_demo_export(self, study_id: str, payload: dict[str, Any], export_dir: str | Path = "data/data_for_test/data/data_for_test/data_demo/derived") -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        out = export_path / f"{study_id.replace(':', '_')}.json"
        out.write_text(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return out


class PIExtractor:
    def build_prompt(self, study: StudyRecord) -> str:
        return (
            "You are a medical information extraction expert.\n"
            "Extract only literal text spans from the study title and abstract.\n"
            f"Title: {study.title}\n"
            f"Abstract: {study.abstract}\n"
            "Return JSON with population_spans and intervention_spans."
        )

    def response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "study_id": {"type": "string"},
                "population_spans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source": {"type": "string", "enum": ["title", "abstract"]},
                            "start_char": {"type": ["integer", "null"]},
                            "end_char": {"type": ["integer", "null"]},
                        },
                        "required": ["text", "source", "start_char", "end_char"],
                        "additionalProperties": False,
                    },
                },
                "intervention_spans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source": {"type": "string", "enum": ["title", "abstract"]},
                            "start_char": {"type": ["integer", "null"]},
                            "end_char": {"type": ["integer", "null"]},
                        },
                        "required": ["text", "source", "start_char", "end_char"],
                        "additionalProperties": False,
                    },
                },
                "extraction_source": {
                    "type": "string",
                    "enum": ["title", "abstract", "both"],
                },
            },
            "required": ["study_id", "population_spans", "intervention_spans", "extraction_source"],
            "additionalProperties": False,
        }

    def extract_local(self, study: StudyRecord) -> PIExtractionResult:
        population_spans = guess_spans(study.abstract or study.title, target="population")
        intervention_spans = guess_spans(study.abstract or study.title, target="intervention")
        extraction_source = "abstract" if study.abstract else "title"
        return PIExtractionResult(
            study_id=study.study_id,
            population_spans=population_spans,
            intervention_spans=intervention_spans,
            extraction_source=extraction_source,
        )

    def validate(self, study: StudyRecord, result: PIExtractionResult) -> list[str]:
        errors: list[str] = []
        if not result.population_spans:
            errors.append("population_spans empty")
        if not result.intervention_spans:
            errors.append("intervention_spans empty")
        source_text = f"{study.title} {study.abstract}"
        normalized_source_text = clean_text(source_text)
        for span in result.population_spans + result.intervention_spans:
            if span.text and span.text not in source_text and clean_text(span.text) not in normalized_source_text:
                errors.append(f"span mismatch: {span.text}")
        return errors


@dataclass(frozen=True)
class Module1DemoResult:
    study_id: str
    extraction: PIExtractionResult
    normalized: NormalizedPI
    document: IndexDocument
    export_path: str


class Module1DemoRunner:
    def __init__(
        self,
        database_url: str | None = None,
        data_root: str | Path | None = None,
        export_dir: str | Path = "data/data_for_test/data/data_for_test/data_demo/derived",
        llm_gateway: LLMGateway | None = None,
        mesh_client: MeshLookupClient | None = None,
        verbose: bool = False,
        request_timeout: float = 120.0,
    ):
        self.database_url = database_url
        self.data_root = data_root or Path("data/data_for_test/data_demo")
        self.export_dir = Path(export_dir)
        self.verbose = verbose
        self.request_timeout = request_timeout
        self.store = None
        if self.database_url is not None:
            init_db(self.database_url)
            self.store = ExtractionStore(database_url=self.database_url)
        self.reader = PMCReader(data_root=self.data_root)
        self.extractor = PIExtractor()
        self.normalizer = PINormalizer(mesh_client=mesh_client)
        self.llm = llm_gateway
        self.client = None if llm_gateway else AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.llm_model

    def close(self) -> None:
        if self.store is not None:
            self.store.close()

    async def run_single(self, study: StudyRecord) -> Module1DemoResult:
        self._log(f"[module1-demo] study={study.study_id}")
        self._log("[module1-demo] saving study state")
        if self.store is not None:
            self.store.upsert_study(study)
        self._log("[module1-demo] calling LLM for PI extraction")
        content = await self._extract_with_llm(study)
        self._log("[module1-demo] validating extracted spans")
        extraction = PIExtractionResult(
            study_id=study.study_id,
            population_spans=[SpanResult(**span) for span in content.get("population_spans", [])],
            intervention_spans=[SpanResult(**span) for span in content.get("intervention_spans", [])],
            extraction_source=content.get("extraction_source", "abstract"),
        )
        errors = self.extractor.validate(study, extraction)
        if errors:
            if self.store is not None:
                self.store.save_extraction(study.study_id, None, None, "; ".join(errors))
            raise ValueError("; ".join(errors))
        if self.store is not None:
            self.store.save_extraction(study.study_id, None, content)
        self._log("[module1-demo] normalizing PI and mapping MeSH terms")
        normalized = self.normalizer.normalize(extraction)
        if self.store is not None:
            self.store.save_normalization(study.study_id, normalized.__dict__)
        self._log("[module1-demo] building index document")
        document = RCTIndexBuilder(None).build_documents(normalized, study)
        payload = {
            "pi": build_pi_summary(extraction, normalized, document),
            "extraction": extraction.__dict__,
            "normalized": normalized.__dict__,
            "document": document.__dict__,
            "study": study.__dict__,
        }
        export_path = self._save_local_export(
            study.study_id,
            payload,
            export_dir=self.export_dir,
        )
        if self.store is not None:
            self.store.save_index_status(study.study_id, True)
        self._log(f"[module1-demo] exported {export_path}")
        return Module1DemoResult(
            study_id=study.study_id,
            extraction=extraction,
            normalized=normalized,
            document=document,
            export_path=str(export_path),
        )

    @staticmethod
    def _save_local_export(study_id: str, payload: dict[str, Any], export_dir: str | Path) -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        out = export_path / _safe_derived_filename(study_id)
        out.write_text(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)

    async def _extract_with_llm(self, study: StudyRecord) -> dict[str, Any]:
        prompt = self.extractor.build_prompt(study)
        response_schema = self.extractor.response_schema()
        if self.llm is not None:
            result = await self.llm.call(
                task_type="pi_extraction",
                inputs={
                    "study_id": study.study_id,
                    "pmid": study.pmid,
                    "pmcid": study.pmcid,
                    "title": study.title,
                    "abstract": study.abstract,
                },
                prompt_template=prompt,
                prompt_vars={"title": study.title, "abstract": study.abstract},
                response_schema=response_schema,
                temperature=0.0,
                cacheable=False,
                module="module1",
                task_name="pi_extraction",
                study_id=study.study_id,
                prompt_version="v1",
            )
            return result.content
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You extract medical PI spans and return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "pi_extraction",
                    "schema": response_schema,
                },
            },
            timeout=self.request_timeout,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    async def run_single_by_index(self, index: int = 0) -> Module1DemoResult:
        studies = self.reader.iter_primary_rct(limit=max(index + 1, 1))
        if index >= len(studies):
            raise IndexError("study index out of range")
        return await self.run_single(studies[index])


@dataclass(frozen=True)
class Module1BatchResult:
    summary: Module1BatchSummary
    batch_record: dict[str, Any] | None


class Module1BatchRunner:
    def __init__(
        self,
        database_url: str | None = None,
        data_root: str | Path | None = None,
        llm_gateway: LLMGateway | None = None,
        verbose: bool = False,
        request_timeout: float = 120.0,
        completion_window: str = "24h",
    ):
        self.database_url = database_url or settings.database_url
        self.data_root = Path(data_root or "data/data_for_test/data_demo")
        self.verbose = verbose
        self.request_timeout = request_timeout
        self.completion_window = completion_window
        init_db(self.database_url)
        self.store = ExtractionStore(database_url=self.database_url)
        self.reader = PMCReader(data_root=self.data_root)
        self.extractor = PIExtractor()
        self.llm = llm_gateway or LLMGateway(conn=self.store.conn, model=settings.llm_model)
        self.client = None if llm_gateway else AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.llm_model
        llm_dir = Path(__file__).resolve().parents[2] / "shared" / "llm"
        self.prompt_template = (llm_dir / "prompts" / "pi_extraction.txt").read_text(encoding="utf-8")
        self.response_schema = json.loads((llm_dir / "schemas" / "pi_extraction.json").read_text(encoding="utf-8"))

    def close(self) -> None:
        self.store.close()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)

    def _load_studies(self, limit: int, force: bool) -> tuple[list[StudyRecord], int]:
        studies: list[StudyRecord] = []
        skipped = 0
        for study in self.reader.iter_primary_rct(limit=limit):
            self.store.upsert_study(study)
            row = self.store.get_study(study.study_id)
            if row is not None and row["extraction_status"] == "completed" and not force:
                skipped += 1
                continue
            studies.append(study)
        return studies, skipped

    def _make_batch_requests(self, studies: list[StudyRecord]) -> list[LLMRequest]:
        requests: list[LLMRequest] = []
        for study in studies:
            requests.append(
                LLMRequest(
                    task_type="pi_extraction",
                    inputs={
                        "study_id": study.study_id,
                        "pmid": study.pmid,
                        "pmcid": study.pmcid,
                        "title": study.title,
                        "abstract": study.abstract,
                    },
                    prompt_template=self.prompt_template,
                    prompt_vars={"title": study.title, "abstract": study.abstract},
                    response_schema=self.response_schema,
                    temperature=0.0,
                    cacheable=False,
                    run_id=None,
                    module="module1",
                    task_name="pi_extraction",
                    study_id=study.study_id,
                    prompt_version="v1",
                )
            )
        return requests

    @staticmethod
    def _row_to_study(row: sqlite3.Row) -> StudyRecord:
        return StudyRecord(
            study_id=row["study_id"],
            manifest_rel_path=row["manifest_rel_path"],
            article_path=row["article_path"],
            pmid=row["pmid"],
            pmcid=row["pmcid"],
            title=row["title"] or "",
            abstract=row["abstract"] or "",
            source=row["source"] or "PMC",
            publication_year=row["publication_year"],
            article_type=row["article_type"] or "primary_rct",
            open_access=bool(row["open_access"]),
        )

    def _parse_batch_result(self, record: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None, str | None]:
        custom_id = record.get("custom_id")
        if not custom_id:
            return None, None, "missing custom_id"
        study_id = custom_id.rsplit(":", 1)[0]
        if record.get("error"):
            return study_id, None, json.dumps(record.get("error"), ensure_ascii=False)
        response = record.get("response") or {}
        body = response.get("body") if isinstance(response, dict) else None
        if isinstance(body, dict) and "output_text" in body:
            try:
                content = body["output_text"]
                if isinstance(content, str):
                    content = json.loads(content)
            except Exception as exc:  # pragma: no cover - defensive
                return study_id, None, str(exc)
            return study_id, content if isinstance(content, dict) else None, None
        if isinstance(response, dict):
            try:
                content = response["body"]["choices"][0]["message"]["content"]
                if isinstance(content, str):
                    return study_id, json.loads(content), None
                if isinstance(content, dict):
                    return study_id, content, None
                return study_id, None, "unsupported content type"
            except Exception as exc:  # pragma: no cover - defensive
                return study_id, None, str(exc)
        return study_id, None, "unrecognized batch response"

    async def _recover_batch(self, batch_row: sqlite3.Row) -> Module1BatchResult:
        studies = [self._row_to_study(row) for row in self.store.get_studies_for_batch(batch_row["batch_id"])]
        if not studies:
            summary = Module1BatchSummary(
                batch_id=batch_row["batch_id"],
                status=batch_row["status"],
                request_total=batch_row["request_total"],
                submitted=0,
                completed=0,
                failed=0,
                skipped=0,
            )
            return Module1BatchResult(summary=summary, batch_record=dict(batch_row))
        return await self._finalize_batch(
            batch_id=batch_row["batch_id"],
            studies=studies,
            initial_status=batch_row["status"],
            initial_output_file_id=batch_row["output_file_id"],
            initial_error_file_id=batch_row["error_file_id"],
            request_total=batch_row["request_total"] or len(studies),
        )

    async def _finalize_batch(
        self,
        *,
        batch_id: str,
        studies: list[StudyRecord],
        initial_status: str,
        initial_output_file_id: str | None,
        initial_error_file_id: str | None,
        request_total: int,
    ) -> Module1BatchResult:
        status = initial_status
        output_file_id = initial_output_file_id
        error_file_id = initial_error_file_id
        batch_payload: dict[str, Any] = {
            "status": status,
            "output_file_id": output_file_id,
            "error_file_id": error_file_id,
        }
        if status in {"completed", "failed", "cancelled", "expired"} and (output_file_id is None and error_file_id is None):
            batch_payload = await self.llm.poll_batch(batch_id)
            status = batch_payload.get("status", status)
            output_file_id = batch_payload.get("output_file_id") or output_file_id
            error_file_id = batch_payload.get("error_file_id") or error_file_id
        while status not in {"completed", "failed", "cancelled", "expired"}:
            await asyncio.sleep(1)
            batch_payload = await self.llm.poll_batch(batch_id)
            status = batch_payload.get("status", status)
            output_file_id = batch_payload.get("output_file_id") or output_file_id
            error_file_id = batch_payload.get("error_file_id") or error_file_id
        self.store.update_batch_status(
            batch_id,
            status=status,
            output_file_id=output_file_id,
            error_file_id=error_file_id,
            metadata_json=batch_payload,
        )
        completed = 0
        failed = 0
        if output_file_id:
            output_records = await self.llm.fetch_batch_output(output_file_id)
            study_map = {study.study_id: study for study in studies}
            for record in output_records:
                study_id, content, error = self._parse_batch_result(record)
                if not study_id or study_id not in study_map:
                    failed += 1
                    continue
                study = study_map[study_id]
                if error or not content:
                    self.store.mark_extraction_from_batch(
                        study_id=study_id,
                        batch_id=batch_id,
                        result=None,
                        error=error or "empty batch result",
                        extraction_status="failed",
                    )
                    failed += 1
                    continue
                extraction = PIExtractionResult(
                    study_id=study_id,
                    population_spans=[SpanResult(**span) for span in content.get("population_spans", [])],
                    intervention_spans=[SpanResult(**span) for span in content.get("intervention_spans", [])],
                    extraction_source=content.get("extraction_source", "abstract"),
                )
                errors = self.extractor.validate(study, extraction)
                if errors:
                    self.store.mark_extraction_from_batch(
                        study_id=study_id,
                        batch_id=batch_id,
                        result=content,
                        error="; ".join(errors),
                        extraction_status="failed",
                    )
                    failed += 1
                    continue
                self.store.mark_extraction_from_batch(
                    study_id=study_id,
                    batch_id=batch_id,
                    result=content,
                    error=None,
                    extraction_status="completed",
                )
                completed += 1
        self.store.update_batch_status(
            batch_id,
            request_total=request_total,
            request_completed=completed,
            request_failed=failed,
        )
        summary = Module1BatchSummary(
            batch_id=batch_id,
            status=status,
            request_total=request_total,
            submitted=request_total,
            completed=completed,
            failed=failed,
            skipped=0,
        )
        return Module1BatchResult(summary=summary, batch_record=dict(self.store.get_batch_record(batch_id) or {}))

    async def run(
        self,
        *,
        limit: int = 100,
        force: bool = False,
        poll: bool = True,
    ) -> Module1BatchResult:
        if self.llm is None:
            raise RuntimeError("Module1BatchRunner requires an llm_gateway for batch submission")
        active_batch = self.store.get_active_batch("pi_extraction")
        if active_batch is not None:
            self._log(f"[module1-batch] recovering active batch {active_batch['batch_id']}")
            return await self._recover_batch(active_batch)
        studies, skipped = self._load_studies(limit=limit, force=force)
        if not studies:
            return Module1BatchResult(
                summary=Module1BatchSummary(
                    batch_id=None,
                    status="skipped",
                    request_total=0,
                    submitted=0,
                    completed=0,
                    failed=0,
                    skipped=0,
                ),
                batch_record=None,
            )
        requests = self._make_batch_requests(studies)
        batch_payload = await self.llm.create_batch_job(requests=requests, completion_window=self.completion_window)
        batch_id = batch_payload["batch_id"]
        self.store.upsert_batch_from_payload(
            {
                "batch_id": batch_id,
                "step_name": "pi_extraction",
                "status": batch_payload.get("status", "queued"),
                "model": self.model,
                "input_file_id": batch_payload.get("input_file_id"),
                "request_total": len(requests),
                "manifest_path": str(self.reader.manifest_path),
                "completion_window": self.completion_window,
                "metadata_json": batch_payload.get("raw", {}),
            }
        )
        for study in studies:
            self.store.mark_batch_submitted(study.study_id, batch_id)
        if not poll:
            return Module1BatchResult(
                summary=Module1BatchSummary(
                    batch_id=batch_id,
                    status=batch_payload.get("status", "queued"),
                    request_total=len(requests),
                    submitted=len(requests),
                    completed=0,
                    failed=0,
                    skipped=0,
                ),
                batch_record=dict(self.store.get_batch_record(batch_id) or {}),
            )
        result = await self._finalize_batch(
            batch_id=batch_id,
            studies=studies,
            initial_status=batch_payload.get("status", "queued"),
            initial_output_file_id=batch_payload.get("output_file_id"),
            initial_error_file_id=batch_payload.get("error_file_id"),
            request_total=len(requests),
        )
        summary = Module1BatchSummary(
            batch_id=result.summary.batch_id,
            status=result.summary.status,
            request_total=result.summary.request_total,
            submitted=result.summary.submitted,
            completed=result.summary.completed,
            failed=result.summary.failed,
            skipped=skipped,
        )
        return Module1BatchResult(summary=summary, batch_record=result.batch_record)


class PINormalizer:
    def __init__(self, mesh_client: MeshLookupClient | None = None):
        self.mesh_client = mesh_client or OfflineMeshLookupClient()

    def normalize(self, extraction: PIExtractionResult) -> NormalizedPI:
        population = self._normalize_field(extraction.population_spans, kind="population")
        intervention = self._normalize_field(extraction.intervention_spans, kind="intervention")
        return NormalizedPI(
            study_id=extraction.study_id,
            population=population,
            intervention=intervention,
        )

    def _normalize_field(self, spans: list[SpanResult], kind: str) -> NormalizedField:
        originals = dedupe_list(clean_text(span.text) for span in spans if span.text)
        cleaned_text = merge_spans(originals)
        concepts = self._extract_concepts(cleaned_text, kind=kind)
        mesh_terms: list[MeSHTerm] = []
        synonyms: list[str] = []
        for concept in concepts:
            mesh = self._mesh_lookup(concept.text)
            if mesh:
                term = MeSHTerm(
                    descriptor_id=mesh["descriptor_id"],
                    preferred_term=mesh["preferred_term"],
                    entry_terms=list(dict.fromkeys(mesh["entry_terms"]))[:10],
                    match_source=concept.text,
                )
                mesh_terms.append(term)
                synonyms.extend(term.entry_terms)
                synonyms.append(term.preferred_term)
            synonyms.extend(self._expand_abbreviations(concept.text))
        mesh_terms = dedupe_mesh_terms(mesh_terms)
        indexable_text = dedupe_join(
            [cleaned_text]
            + [term.preferred_term for term in mesh_terms]
            + [entry for term in mesh_terms for entry in term.entry_terms]
            + synonyms
        )
        return NormalizedField(
            original_spans=originals,
            cleaned_text=cleaned_text,
            concepts=concepts or [MedicalConcept(text=cleaned_text, type=kind)],
            mesh_terms=mesh_terms,
            synonyms=dedupe_list(synonyms),
            indexable_text=indexable_text,
        )

    def _extract_concepts(self, text: str, kind: str) -> list[MedicalConcept]:
        if not text:
            return []
        raw_parts = split_concepts(text, kind)
        concepts: list[MedicalConcept] = []
        for part in raw_parts:
            normalized = clean_text(part)
            if not normalized:
                continue
            concept_type = "drug" if kind == "intervention" else "condition"
            concepts.append(MedicalConcept(text=normalized, type=concept_type))
        return dedupe_concepts(concepts)

    def _mesh_lookup(self, concept: str) -> dict[str, Any] | None:
        for candidate in mesh_lookup_candidates(concept):
            online = self.mesh_client.lookup(candidate)
            if online:
                return {
                    "descriptor_id": online.descriptor_id,
                    "preferred_term": online.preferred_term,
                    "entry_terms": online.entry_terms,
                }
            if candidate in MESH_FALLBACK:
                return MESH_FALLBACK[candidate]
            for key, value in MESH_FALLBACK.items():
                if key in candidate or candidate in key:
                    return value
        return None

    def _expand_abbreviations(self, text: str) -> list[str]:
        normalized = normalize_phrase(text)
        if normalized in ABBREVIATIONS:
            return [ABBREVIATIONS[normalized]]
        return [ABBREVIATIONS[abbr] for abbr in ABBREVIATIONS if abbr in normalized]


class RCTIndexBuilder:
    def __init__(self, es_client: Any):
        self.es = es_client
        self.index_name = "ebm_rct_index"

    def ensure_index(self) -> None:
        if self.es.indices.exists(index=self.index_name):
            return
        self.es.indices.create(index=self.index_name, body=self.mapping())

    @staticmethod
    def mapping() -> dict[str, Any]:
        return {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "english_medical": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "english_stop",
                                "english_stemmer",
                                "english_possessive_stemmer",
                            ],
                        }
                    },
                    "filter": {
                        "english_stop": {"type": "stop", "stopwords": "_english_"},
                        "english_stemmer": {"type": "stemmer", "language": "english"},
                        "english_possessive_stemmer": {
                            "type": "stemmer",
                            "language": "possessive_english",
                        },
                    },
                }
            },
            "mappings": {
                "properties": {
                    "study_id": {"type": "keyword"},
                    "pmid": {"type": "keyword"},
                    "pmcid": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "english_medical"},
                    "abstract": {"type": "text", "analyzer": "english_medical"},
                    "population": {"type": "text", "analyzer": "english_medical"},
                    "intervention": {"type": "text", "analyzer": "english_medical"},
                    "population_original": {"type": "text", "analyzer": "english_medical"},
                    "intervention_original": {"type": "text", "analyzer": "english_medical"},
                    "mesh_terms": {"type": "keyword"},
                    "mesh_population": {"type": "keyword"},
                    "mesh_intervention": {"type": "keyword"},
                    "article_type": {"type": "keyword"},
                    "open_access": {"type": "boolean"},
                    "source": {"type": "keyword"},
                    "publication_year": {"type": "integer"},
                    "article_path": {"type": "keyword"},
                    "indexed_at": {"type": "date"},
                }
            },
        }

    def build_documents(self, normalized: NormalizedPI, study: StudyRecord) -> IndexDocument:
        article_mesh_terms = extract_article_mesh_terms(study.metadata)
        return IndexDocument(
            study_id=study.study_id,
            pmid=study.pmid,
            pmcid=study.pmcid,
            title=study.title,
            abstract=study.abstract,
            population=normalized.population.indexable_text,
            intervention=normalized.intervention.indexable_text,
            population_original=normalized.population.cleaned_text,
            intervention_original=normalized.intervention.cleaned_text,
            mesh_terms=article_mesh_terms,
            mesh_population=dedupe_list(term.preferred_term for term in normalized.population.mesh_terms),
            mesh_intervention=dedupe_list(term.preferred_term for term in normalized.intervention.mesh_terms),
            article_type=study.article_type,
            open_access=study.open_access,
            source=study.source,
            publication_year=study.publication_year,
            article_path=study.article_path,
            indexed_at=datetime.now(timezone.utc).isoformat(),
        )

    def bulk_index(self, documents: Iterable[IndexDocument]) -> list[dict[str, Any]]:
        actions = []
        for doc in documents:
            actions.append({"index": {"_index": self.index_name, "_id": doc.study_id}})
            actions.append(doc.__dict__)
        if not actions:
            return []
        return self.es.bulk(operations=actions)


class LocalRCTIndex:
    """Small JSONL-backed retrieval index for the simplified Module 1 path."""

    FIELD_WEIGHTS = {
        "title": 4.0,
        "population": 3.0,
        "intervention": 3.0,
        "mesh_population": 2.5,
        "mesh_intervention": 2.5,
        "mesh_terms": 1.5,
        "population_original": 2.0,
        "intervention_original": 2.0,
        "abstract": 1.0,
    }

    def __init__(self, index_path: str | Path = "data/data_for_test/data_demo_with_mesh/index/local_rct_index.jsonl"):
        self.index_path = Path(index_path)
        self.documents: list[dict[str, Any]] = []
        if self.index_path.exists():
            self.load()

    def build(self, documents: Iterable[IndexDocument]) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.documents = [to_jsonable(document) for document in documents]
        with self.index_path.open("w", encoding="utf-8") as fh:
            for document in self.documents:
                fh.write(json.dumps(document, ensure_ascii=False) + "\n")
        return self.index_path

    def load(self) -> list[dict[str, Any]]:
        self.documents = []
        with self.index_path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    self.documents.append(json.loads(line))
        return self.documents

    def search(self, query: str, *, top_k: int = 10) -> list[LocalSearchHit]:
        query_tokens = tokenize_for_search(query)
        if not query_tokens:
            return []
        hits: list[LocalSearchHit] = []
        for document in self.documents:
            score = 0.0
            matched_fields: list[str] = []
            for field, weight in self.FIELD_WEIGHTS.items():
                field_text = stringify_search_field(document.get(field))
                field_tokens = tokenize_for_search(field_text)
                if not field_tokens:
                    continue
                overlap = query_tokens & field_tokens
                if not overlap:
                    continue
                score += weight * len(overlap)
                if normalize_phrase(query) and normalize_phrase(query) in normalize_phrase(field_text):
                    score += weight
                matched_fields.append(field)
            if score > 0:
                hits.append(
                    LocalSearchHit(
                        study_id=str(document.get("study_id") or ""),
                        score=score,
                        title=str(document.get("title") or ""),
                        matched_fields=matched_fields,
                        document=document,
                    )
                )
        hits.sort(key=lambda hit: (-hit.score, hit.study_id))
        return hits[:top_k]


def tokenize_for_search(text: str) -> set[str]:
    normalized = normalize_phrase(text)
    tokens = re.findall(r"[a-z0-9][a-z0-9-]{1,}", normalized)
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if token.endswith("s") and len(token) > 3:
            expanded.append(token[:-1])
    return {token for token in expanded if token not in STOPWORDS}


def stringify_search_field(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(stringify_search_field(item) for item in value)
    if isinstance(value, dict):
        return " ".join(stringify_search_field(item) for item in value.values())
    return str(value)


def extract_section_text(sections: list[dict[str, Any]], target_key: str) -> str:
    for section in sections:
        if normalize_phrase(section.get("section_key", "")) == target_key:
            return section_text(section)
        if normalize_phrase(section.get("section_title_normalized", "")) == target_key:
            return section_text(section)
    return ""


def extract_abstract_text(sections: list[dict[str, Any]]) -> str:
    return extract_section_text(sections, "abstract")


def section_text(section: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in section.get("blocks", []):
        text = block.get("text_md") or block.get("text") or ""
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[[0-9,\s-]+\]", " ", text)
    text = re.sub(r"\((?:ref|citation)[^)]+\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .;:,")
    return text


def normalize_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text).lower()).strip()


def merge_spans(spans: list[str]) -> str:
    if not spans:
        return ""
    merged = " ".join(span for span in spans if span)
    merged = re.sub(r"\s+", " ", merged).strip(" .;:,")
    return merged


def dedupe_list(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = clean_text(value)
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        ordered.append(normalized)
    return ordered


def dedupe_concepts(concepts: Iterable[MedicalConcept]) -> list[MedicalConcept]:
    seen: set[str] = set()
    ordered: list[MedicalConcept] = []
    for concept in concepts:
        key = normalize_phrase(concept.text)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(concept)
    return ordered


def dedupe_mesh_terms(terms: Iterable[MeSHTerm]) -> list[MeSHTerm]:
    seen: set[str] = set()
    ordered: list[MeSHTerm] = []
    for term in terms:
        key = term.descriptor_id or normalize_phrase(term.preferred_term)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(term)
    return ordered


def dedupe_join(values: Iterable[str]) -> str:
    return " ".join(dedupe_list(values)).strip()


def build_pi_summary(
    extraction: PIExtractionResult,
    normalized: NormalizedPI,
    document: IndexDocument,
) -> dict[str, Any]:
    return {
        "study_id": extraction.study_id,
        "population": {
            "spans": normalized.population.original_spans,
            "cleaned_text": normalized.population.cleaned_text,
            "concepts": [concept.text for concept in normalized.population.concepts],
            "mesh_terms": [term.preferred_term for term in normalized.population.mesh_terms],
            "synonyms": normalized.population.synonyms,
            "indexable_text": normalized.population.indexable_text,
        },
        "intervention": {
            "spans": normalized.intervention.original_spans,
            "cleaned_text": normalized.intervention.cleaned_text,
            "concepts": [concept.text for concept in normalized.intervention.concepts],
            "mesh_terms": [term.preferred_term for term in normalized.intervention.mesh_terms],
            "synonyms": normalized.intervention.synonyms,
            "indexable_text": normalized.intervention.indexable_text,
        },
        "mesh_terms": document.mesh_terms,
    }


def extract_article_mesh_terms(metadata: dict[str, Any]) -> list[str]:
    values = metadata.get("mesh_term")
    if values is None:
        values = metadata.get("mesh_terms")
    if isinstance(values, str):
        return dedupe_list([values])
    if isinstance(values, list):
        return dedupe_list(str(value) for value in values if value is not None)
    return []


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    return value


def split_concepts(text: str, kind: str) -> list[str]:
    text = clean_text(text)
    separators = [r"\bversus\b", r"\bvs\b", r"\band\b", r"\bor\b", r","]
    if kind == "population":
        separators.extend([r"\bwith\b", r"\bin\b", r"\bamong\b"])
    pattern = "|".join(separators)
    parts = [part.strip() for part in re.split(pattern, text, flags=re.IGNORECASE)]
    return [part for part in parts if part and part.lower() not in STOPWORDS]


def mesh_lookup_candidates(text: str) -> list[str]:
    normalized = normalize_phrase(text)
    if not normalized:
        return []
    candidates = [normalized]
    patterns = [
        r"\bwith\s+(.+)",
        r"\busing\s+(.+)",
        r"\bof\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            candidates.extend(split_candidate_tail(match.group(1)))
    candidates.extend(extract_known_mesh_phrases(normalized))
    return dedupe_list(candidates)


def split_candidate_tail(text: str) -> list[str]:
    tail = re.split(r"\bas well as\b|\bwith or without\b|\bwithout\b|\busing\b|\band\b|\bor\b|,", text)
    return [clean_candidate(part) for part in tail if clean_candidate(part)]


def clean_candidate(text: str) -> str:
    text = re.sub(r"\b(all|eighty|\d+)\s+participants?\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(class\s+[ivx]+)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(self-etch|selective-etch|placement)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return normalize_phrase(text)


def extract_known_mesh_phrases(text: str) -> list[str]:
    phrases = []
    for phrase in MESH_FALLBACK:
        if phrase in text:
            phrases.append(phrase)
    return phrases


def guess_spans(text: str, target: str) -> list[SpanResult]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    spans: list[SpanResult] = []
    keywords = {
        "population": ["participants", "patients", "adults", "children", "women", "men", "subjects"],
        "intervention": ["received", "treated", "assigned", "metformin", "placebo", "therapy", "treatment"],
    }.get(target, [])
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            spans.append(SpanResult(text=sentence.strip(), source="abstract"))
    if not spans:
        fallback = sentences[0].strip() if sentences else cleaned
        spans.append(SpanResult(text=fallback, source="abstract"))
    return spans[:3]


def copy_demo_primary_subset(
    source_root: str | Path,
    dest_root: str | Path,
    *,
    limit: int = 100,
) -> Path:
    """Copy the first ``limit`` manifest ``primary_rct`` JSON files into ``dest_root`` and write manifest."""
    src = Path(source_root)
    dst = Path(dest_root)
    manifest_src = src / "manifest" / "files.jsonl"
    lines_out: list[str] = []
    count = 0
    with manifest_src.open(encoding="utf-8") as fh:
        for line in fh:
            if count >= limit:
                break
            if not line.strip():
                continue
            manifest = json.loads(line)
            if manifest.get("classification") != "primary_rct":
                continue
            rel_path = manifest["rel_path"]
            src_file = src / rel_path
            dest_file = dst / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            lines_out.append(line.rstrip("\n"))
            count += 1
    dest_manifest = dst / "manifest" / "files.jsonl"
    dest_manifest.parent.mkdir(parents=True, exist_ok=True)
    dest_manifest.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    return dest_manifest


def copy_theme_demo_subset(
    source_root: str | Path,
    dest_root: str | Path,
    *,
    total: int = 1000,
    theme_quotas: dict[str, int] | None = None,
    theme_keywords: dict[str, tuple[str, ...]] | None = None,
) -> DemoSelectionResult:
    """Copy a stable theme-clustered primary RCT subset for larger Module 1 demos."""
    src = Path(source_root)
    dst = Path(dest_root)
    manifest_src = src / "manifest" / "files.jsonl"
    quotas = dict(theme_quotas) if theme_quotas is not None else scale_theme_quotas(total)
    keywords = dict(theme_keywords or MODULE1_DEMO_1000_THEME_KEYWORDS)
    if total < 1:
        raise ValueError("total must be >= 1")
    if sum(quotas.values()) > total:
        raise ValueError("theme quotas must not exceed total")

    records: list[dict[str, Any]] = []
    with manifest_src.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            manifest = json.loads(line)
            if manifest.get("classification") != "primary_rct":
                continue
            records.append(manifest)

    selected: list[dict[str, Any]] = []
    selected_rel_paths: set[str] = set()
    theme_counts: dict[str, int] = {theme: 0 for theme in quotas}
    for theme, quota in quotas.items():
        theme_terms = keywords.get(theme, ())
        for manifest in records:
            if theme_counts[theme] >= quota:
                break
            rel_path = str(manifest.get("rel_path") or "")
            if not rel_path or rel_path in selected_rel_paths:
                continue
            title = str(manifest.get("title") or "").lower()
            if any(term in title for term in theme_terms):
                selected.append(manifest)
                selected_rel_paths.add(rel_path)
                theme_counts[theme] += 1

    filler_count = 0
    for manifest in records:
        if len(selected) >= total:
            break
        rel_path = str(manifest.get("rel_path") or "")
        if not rel_path or rel_path in selected_rel_paths:
            continue
        selected.append(manifest)
        selected_rel_paths.add(rel_path)
        filler_count += 1

    if len(selected) < total:
        raise ValueError(f"Only found {len(selected)} primary_rct records, requested {total}")

    lines_out: list[str] = []
    for manifest in selected[:total]:
        rel_path = manifest["rel_path"]
        src_file = src / rel_path
        dest_file = dst / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        lines_out.append(json.dumps(manifest, ensure_ascii=False))

    dest_manifest = dst / "manifest" / "files.jsonl"
    dest_manifest.parent.mkdir(parents=True, exist_ok=True)
    dest_manifest.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
    summary_path = dst / "manifest" / "selection_summary.json"
    summary = {
        "source_data_root": str(src),
        "dest_data_root": str(dst),
        "requested_total": total,
        "selected_total": len(lines_out),
        "strategy": "theme_clustered_manifest_order",
        "theme_quotas": quotas,
        "theme_counts": theme_counts,
        "filler_count": filler_count,
        "theme_keywords": {theme: list(values) for theme, values in keywords.items()},
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return DemoSelectionResult(
        source_data_root=str(src),
        dest_data_root=str(dst),
        manifest_path=str(dest_manifest),
        summary_path=str(summary_path),
        selected_total=len(lines_out),
        requested_total=total,
        theme_counts=theme_counts,
        filler_count=filler_count,
    )


def scale_theme_quotas(total: int, base_quotas: dict[str, int] | None = None) -> dict[str, int]:
    """Scale default theme quotas to the requested total while preserving theme proportions."""
    quotas = dict(base_quotas or MODULE1_DEMO_1000_THEME_QUOTAS)
    base_total = sum(quotas.values())
    if total < 1:
        raise ValueError("total must be >= 1")
    if total >= base_total:
        return quotas
    scaled: dict[str, int] = {}
    fractions: list[tuple[float, str]] = []
    assigned = 0
    for theme, quota in quotas.items():
        raw = quota * total / base_total
        whole = int(raw)
        scaled[theme] = whole
        assigned += whole
        fractions.append((raw - whole, theme))
    for _, theme in sorted(fractions, reverse=True)[: total - assigned]:
        scaled[theme] += 1
    return {theme: quota for theme, quota in scaled.items() if quota > 0}


def _safe_derived_filename(study_id: str) -> str:
    return f"{study_id.replace(':', '_')}.json"


def index_document_from_derived_payload(payload: dict[str, Any]) -> IndexDocument:
    doc = payload["document"]
    return IndexDocument(**doc)


def build_module1_local_index_from_derived(
    *,
    data_root: str | Path = "data/data_for_test/data/data_for_test/data_demo_with_mesh",
    export_dir: str | Path | None = None,
    index_path: str | Path | None = None,
    run_query_validation: bool = True,
    validation_queries: tuple[tuple[str, str | None], ...] | None = None,
    top_k_search: int = 10,
) -> Module1SimplifiedResult:
    """Build the local retrieval index from already exported PI-first derived JSON files."""
    root = Path(data_root)
    derived_root = Path(export_dir) if export_dir else root / "derived"
    target_index_path = Path(index_path) if index_path else root / "index" / "local_rct_index.jsonl"
    documents: list[IndexDocument] = []
    failures: list[dict[str, str]] = []
    for path in sorted(derived_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            documents.append(index_document_from_derived_payload(payload))
        except Exception as exc:
            failures.append({"study_id": path.stem, "error": str(exc)})
    local = LocalRCTIndex(target_index_path)
    local.build(documents)
    query_rows: tuple[Module1QueryValidationRow, ...] = ()
    q_passed = q_total = 0
    if run_query_validation:
        query_rows = validate_module1_local_queries(
            local,
            queries=validation_queries,
            top_k=top_k_search,
        )
        q_total = len(query_rows)
        q_passed = sum(1 for row in query_rows if row.passed)
    return Module1SimplifiedResult(
        data_root=str(root),
        export_dir=str(derived_root),
        index_path=str(target_index_path),
        studies_total=len(documents) + len(failures),
        extracted=len(documents),
        normalized=len(documents),
        indexed=len(documents),
        failed=len(failures),
        failures=failures,
        query_validation=query_rows,
        queries_passed=q_passed,
        queries_total=q_total,
    )


def validate_module1_local_queries(
    index: LocalRCTIndex,
    *,
    queries: tuple[tuple[str, str | None], ...] | None = None,
    top_k: int = 10,
) -> tuple[Module1QueryValidationRow, ...]:
    """Run fixed queries; ``passed`` means at least one hit. Optional expected study must appear in top_k."""
    spec = queries or MODULE1_FIXED_QUERIES
    rows: list[Module1QueryValidationRow] = []
    for query, expected_study_id in spec:
        hits = index.search(query, top_k=top_k)
        hit_count = len(hits)
        top = tuple(
            {
                "study_id": h.study_id,
                "score": h.score,
                "matched_fields": h.matched_fields,
                "title": h.title,
            }
            for h in hits
        )
        expected_in_top: bool | None = None
        if expected_study_id:
            expected_in_top = any(h.study_id == expected_study_id for h in hits)
        passed = hit_count > 0 if expected_in_top is None else expected_in_top
        rows.append(
            Module1QueryValidationRow(
                query=query,
                passed=passed,
                hit_count=hit_count,
                top_hits=top,
                expected_study_id=expected_study_id,
                expected_in_top_hits=expected_in_top,
            )
        )
    return tuple(rows)


class OfflineMeshLookupClient:
    """Disable network MeSH lookup while preserving local fallback mapping."""

    def lookup(self, label: str) -> None:
        return None


class Module1SimplifiedRunner:
    """Phase 2 simplified path: copy demo subset, per-study PI + normalization, local JSONL index, query smoke."""

    def __init__(
        self,
        *,
        source_data_root: str | Path = Path("data/data_for_test/data_demo"),
        dest_data_root: str | Path = Path("data/data_for_test/data/data_for_test/data_demo_with_mesh"),
        database_url: str | None = None,
        export_dir: str | Path | None = None,
        index_path: str | Path | None = None,
        llm_gateway: LLMGateway | None = None,
        mesh_client: MeshLookupClient | None = None,
        verbose: bool = False,
        request_timeout: float = 120.0,
        skip_existing_derived: bool = True,
        copy_source: bool = True,
        limit: int = 100,
        run_query_validation: bool = True,
        top_k_search: int = 10,
        validation_queries: tuple[tuple[str, str | None], ...] | None = None,
        pi_mode: str = "llm",
        use_database: bool = True,
        mesh_mode: str = "offline",
        workers: int = 1,
        fallback_local_on_error: bool = True,
    ):
        if pi_mode not in {"llm", "local"}:
            raise ValueError("pi_mode must be 'llm' or 'local'")
        if mesh_mode not in {"online", "offline"}:
            raise ValueError("mesh_mode must be 'online' or 'offline'")
        if workers < 1:
            raise ValueError("workers must be >= 1")
        if use_database and workers != 1:
            raise ValueError("database mode only supports workers=1")
        self.source_data_root = Path(source_data_root)
        self.dest_data_root = Path(dest_data_root)
        self.database_url = database_url or settings.database_url
        self.export_dir = Path(export_dir) if export_dir else self.dest_data_root / "derived"
        self.index_path = Path(index_path) if index_path else self.dest_data_root / "index" / "local_rct_index.jsonl"
        self.verbose = verbose
        self.request_timeout = request_timeout
        self.skip_existing_derived = skip_existing_derived
        self.copy_source = copy_source
        self.limit = limit
        self.run_query_validation = run_query_validation
        self.top_k_search = top_k_search
        self.validation_queries = validation_queries
        self.pi_mode = pi_mode
        self.use_database = use_database
        self.mesh_mode = mesh_mode
        self.workers = workers
        self.fallback_local_on_error = fallback_local_on_error
        self.store = None
        if self.use_database:
            init_db(self.database_url)
            self.store = ExtractionStore(database_url=self.database_url)
        self.reader_data_root = self.dest_data_root if self.copy_source else self.source_data_root
        self.reader = PMCReader(data_root=self.reader_data_root)
        self.extractor = PIExtractor()
        if mesh_client is None and self.mesh_mode == "offline":
            mesh_client = OfflineMeshLookupClient()
        self.normalizer = PINormalizer(mesh_client=mesh_client)
        self.llm = llm_gateway
        self.client = None if llm_gateway else AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.llm_model
        llm_dir = Path(__file__).resolve().parents[2] / "shared" / "llm"
        self.prompt_template = (llm_dir / "prompts" / "pi_extraction.txt").read_text(encoding="utf-8")
        self.response_schema = json.loads(
            (llm_dir / "schemas" / "pi_extraction.json").read_text(encoding="utf-8")
        )

    def close(self) -> None:
        if self.store is not None:
            self.store.close()

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)

    def _user_pi_prompt(self, study: StudyRecord) -> str:
        return (
            self.prompt_template.strip()
            + f"\n\nTitle: {study.title}\nAbstract: {study.abstract}\n"
        )

    async def _extract_with_llm(self, study: StudyRecord) -> dict[str, Any]:
        prompt = self._user_pi_prompt(study)
        response_schema = self.response_schema
        if self.llm is not None:
            result = await self.llm.call(
                task_type="pi_extraction",
                inputs={
                    "study_id": study.study_id,
                    "pmid": study.pmid,
                    "pmcid": study.pmcid,
                    "title": study.title,
                    "abstract": study.abstract,
                },
                prompt_template=prompt,
                prompt_vars={},
                response_schema=response_schema,
                temperature=0.0,
                cacheable=False,
                module="module1",
                task_name="pi_extraction",
                study_id=study.study_id,
                prompt_version="v1",
            )
            content = dict(result.content)
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract medical PI spans and return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "pi_extraction",
                        "schema": response_schema,
                    },
                },
                timeout=self.request_timeout,
            )
            raw = response.choices[0].message.content or "{}"
            content = dict(json.loads(raw))
        content.setdefault("study_id", study.study_id)
        return content

    def _extract_local_payload(self, study: StudyRecord) -> dict[str, Any]:
        extraction = self.extractor.extract_local(study)
        return {
            "study_id": extraction.study_id,
            "population_spans": [span.__dict__ for span in extraction.population_spans],
            "intervention_spans": [span.__dict__ for span in extraction.intervention_spans],
            "extraction_source": extraction.extraction_source,
        }

    @staticmethod
    def _spans_from_payload(raw_spans: list[dict[str, Any]]) -> list[SpanResult]:
        out: list[SpanResult] = []
        for span in raw_spans:
            out.append(
                SpanResult(
                    text=str(span["text"]),
                    source=str(span["source"]),
                    start_char=span.get("start_char"),
                    end_char=span.get("end_char"),
                )
            )
        return out

    async def _process_one_study(self, study: StudyRecord) -> IndexDocument:
        self._log(f"[module1-simplified] study={study.study_id}")
        if self.store is not None:
            self.store.upsert_study(study)
        content = self._extract_local_payload(study) if self.pi_mode == "local" else await self._extract_with_llm(study)
        extraction = PIExtractionResult(
            study_id=study.study_id,
            population_spans=self._spans_from_payload(content.get("population_spans", [])),
            intervention_spans=self._spans_from_payload(content.get("intervention_spans", [])),
            extraction_source=content.get("extraction_source", "abstract"),
        )
        errors = self.extractor.validate(study, extraction)
        if errors and self.pi_mode == "llm" and self.fallback_local_on_error:
            self._log(f"[module1-simplified] local fallback {study.study_id}: {'; '.join(errors)}")
            content = self._extract_local_payload(study)
            content["llm_validation_error"] = "; ".join(errors)
            content["extraction_source"] = "local_fallback"
            extraction = PIExtractionResult(
                study_id=study.study_id,
                population_spans=self._spans_from_payload(content.get("population_spans", [])),
                intervention_spans=self._spans_from_payload(content.get("intervention_spans", [])),
                extraction_source=content.get("extraction_source", "local_fallback"),
            )
            errors = self.extractor.validate(study, extraction)
        if errors:
            if self.store is not None:
                self.store.save_extraction(study.study_id, None, None, "; ".join(errors))
            raise ValueError("; ".join(errors))
        if self.store is not None:
            self.store.save_extraction(study.study_id, None, content)
        normalized = self.normalizer.normalize(extraction)
        if self.store is not None:
            self.store.save_normalization(study.study_id, normalized.__dict__)
        document = RCTIndexBuilder(None).build_documents(normalized, study)
        export_path = self._save_local_export(
            study.study_id,
            {
                "pi": build_pi_summary(extraction, normalized, document),
                "extraction": extraction.__dict__,
                "normalized": normalized.__dict__,
                "document": document.__dict__,
                "study": study.__dict__,
            },
            export_dir=self.export_dir,
        )
        if self.store is not None:
            self.store.save_index_status(study.study_id, True)
        self._log(f"[module1-simplified] exported {export_path}")
        return document

    @staticmethod
    def _save_local_export(study_id: str, payload: dict[str, Any], export_dir: str | Path) -> Path:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        out = export_path / _safe_derived_filename(study_id)
        out.write_text(json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def _load_skipped_document(self, study: StudyRecord) -> IndexDocument:
        path = self.export_dir / _safe_derived_filename(study.study_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return index_document_from_derived_payload(payload)

    async def _process_one_for_run(
        self,
        index: int,
        study: StudyRecord,
        semaphore: asyncio.Semaphore,
    ) -> tuple[int, IndexDocument | None, dict[str, str] | None, bool]:
        derived_path = self.export_dir / _safe_derived_filename(study.study_id)
        try:
            if self.skip_existing_derived and derived_path.exists():
                self._log(f"[module1-simplified] skip existing {derived_path.name}")
                return index, self._load_skipped_document(study), None, True
            async with semaphore:
                doc = await self._process_one_study(study)
            return index, doc, None, True
        except Exception as exc:
            self._log(f"[module1-simplified] FAILED {study.study_id}: {exc}")
            return index, None, {"study_id": study.study_id, "error": str(exc)}, False

    async def run(self) -> Module1SimplifiedResult:
        if self.copy_source:
            self._log(f"[module1-simplified] copying subset to {self.dest_data_root}")
            copy_demo_primary_subset(self.source_data_root, self.dest_data_root, limit=self.limit)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        studies = self.reader.iter_primary_rct(limit=self.limit)
        semaphore = asyncio.Semaphore(self.workers)
        total = len(studies)
        tasks = [
            asyncio.create_task(self._process_one_for_run(index, study, semaphore))
            for index, study in enumerate(studies)
        ]
        rows = []
        completed = 0
        succeeded = 0
        failed = 0
        for task in asyncio.as_completed(tasks):
            row = await task
            rows.append(row)
            completed += 1
            if row[3]:
                succeeded += 1
            else:
                failed += 1
            self._log_progress(completed=completed, total=total, succeeded=succeeded, failed=failed, row=row)
        rows.sort(key=lambda row: row[0])
        documents = [doc for _, doc, _, ok in rows if ok and doc is not None]
        failures = [failure for _, _, failure, ok in rows if not ok and failure is not None]
        extracted = normalized = indexed = len(documents)
        local = LocalRCTIndex(self.index_path)
        local.build(documents)
        self._log(f"[module1-simplified] index written {self.index_path}")
        query_rows: tuple[Module1QueryValidationRow, ...] = ()
        q_passed = q_total = 0
        if self.run_query_validation:
            query_rows = validate_module1_local_queries(
                local,
                queries=self.validation_queries,
                top_k=self.top_k_search,
            )
            q_total = len(query_rows)
            q_passed = sum(1 for row in query_rows if row.passed)
            self._log(f"[module1-simplified] query checks passed {q_passed}/{q_total}")
        return Module1SimplifiedResult(
            data_root=str(self.dest_data_root),
            export_dir=str(self.export_dir),
            index_path=str(self.index_path),
            studies_total=len(studies),
            extracted=extracted,
            normalized=normalized,
            indexed=indexed,
            failed=len(failures),
            failures=failures,
            query_validation=query_rows,
            queries_passed=q_passed,
            queries_total=q_total,
        )

    def _log_progress(
        self,
        *,
        completed: int,
        total: int,
        succeeded: int,
        failed: int,
        row: tuple[int, IndexDocument | None, dict[str, str] | None, bool],
    ) -> None:
        if not self.verbose:
            return
        _, doc, failure, ok = row
        study_id = doc.study_id if doc is not None else (failure or {}).get("study_id", "unknown")
        pct = (completed / total * 100) if total else 100.0
        status = "ok" if ok else "failed"
        print(
            "[module1-simplified] progress "
            f"{completed}/{total} ({pct:.1f}%) "
            f"ok={succeeded} failed={failed} last={study_id} {status}",
            flush=True,
        )


def load_module1_sample(limit: int = 100, data_root: str | Path | None = None) -> list[StudyRecord]:
    return PMCReader(data_root=data_root).iter_primary_rct(limit=limit)


def run_module1_pipeline(
    *,
    limit: int = 100,
    database_url: str | None = None,
    data_root: str | Path | None = None,
) -> list[IndexDocument]:
    store = ExtractionStore(database_url=database_url)
    reader = PMCReader(data_root=data_root)
    extractor = PIExtractor()
    normalizer = PINormalizer()
    studies = reader.iter_primary_rct(limit=limit)
    indexed: list[IndexDocument] = []
    try:
        for study in studies:
            store.upsert_study(study)
            extraction = extractor.extract_local(study)
            errors = extractor.validate(study, extraction)
            if errors:
                store.save_extraction(study.study_id, None, None, "; ".join(errors))
                continue
            store.save_extraction(study.study_id, None, extraction.__dict__)
            normalized = normalizer.normalize(extraction)
            store.save_normalization(study.study_id, normalized.__dict__)
            doc = RCTIndexBuilder(None).build_documents(normalized, study)
            indexed.append(doc)
            store.save_index_status(study.study_id, True)
        return indexed
    finally:
        store.close_and_commit()


def run_module1_demo_sync(**kwargs: Any) -> Module1DemoResult:
    import asyncio

    runner = Module1DemoRunner(**kwargs)
    try:
        return asyncio.run(runner.run_single_by_index(0))
    finally:
        runner.close()


def run_module1_batch_sync(**kwargs: Any) -> Module1BatchResult:
    import asyncio

    run_keys = {"limit", "force", "poll"}
    runner_kwargs = {key: value for key, value in kwargs.items() if key not in run_keys}
    run_kwargs = {key: value for key, value in kwargs.items() if key in run_keys}
    runner = Module1BatchRunner(**runner_kwargs)
    try:
        return asyncio.run(runner.run(**run_kwargs))
    finally:
        runner.close()


def run_module1_simplified_sync(**kwargs: Any) -> Module1SimplifiedResult:
    import asyncio

    runner = Module1SimplifiedRunner(**kwargs)
    try:
        return asyncio.run(runner.run())
    finally:
        runner.close()
