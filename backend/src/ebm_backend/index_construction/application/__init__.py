"""Module 1: Index Construction."""

from importlib import import_module

from .pipeline import (
    DemoSelectionResult,
    ExtractionStore,
    IndexDocument,
    LocalRCTIndex,
    MODULE1_FIXED_QUERIES,
    Module1BatchResult,
    Module1BatchRunner,
    Module1BatchSummary,
    Module1DemoResult,
    Module1DemoRunner,
    Module1QueryValidationRow,
    Module1SimplifiedResult,
    Module1SimplifiedRunner,
    MedicalConcept,
    MeSHTerm,
    NormalizedField,
    NormalizedPI,
    PIExtractionResult,
    PIExtractor,
    PINormalizer,
    PMCReader,
    RCTIndexBuilder,
    SpanResult,
    StudyRecord,
    build_module1_local_index_from_derived,
    copy_demo_primary_subset,
    copy_theme_demo_subset,
    index_document_from_derived_payload,
    load_module1_sample,
    run_module1_batch_sync,
    run_module1_demo_sync,
    run_module1_pipeline,
    run_module1_simplified_sync,
    validate_module1_local_queries,
)

_BACKFILL_EXPORTS = {
    "ArticleTarget",
    "MeshBackfillCheckpoint",
    "MeshBackfillRecord",
    "PubMedMeshFetcher",
    "backfill_article_file",
    "backfill_mesh_terms",
    "backfill_no_pmid_file",
    "backfill_single_article",
    "dedupe_terms",
    "group_targets_by_pmid",
    "normalize_pmid",
    "parse_pubmed_mesh_xml",
    "scan_pmc_manifest",
}


def __getattr__(name: str):
    if name in _BACKFILL_EXPORTS:
        module = import_module(".pmc_mesh_backfill", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _BACKFILL_EXPORTS)
