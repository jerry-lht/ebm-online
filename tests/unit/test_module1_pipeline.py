from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ebm_backend.index_construction.interfaces.cli import main as module1_cli_main
from ebm_backend.index_construction.application import (
    ExtractionStore,
    LocalRCTIndex,
    Module1BatchRunner,
    Module1DemoRunner,
    Module1SimplifiedRunner,
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
    run_module1_simplified_sync,
    validate_module1_local_queries,
)


class _FakeLLMResult:
    def __init__(self, content: dict[str, object]):
        self.content = content


class _FakeLLMGateway:
    async def call(self, **kwargs):
        return _FakeLLMResult(
            {
                "study_id": kwargs["study_id"],
                "population_spans": [
                    {
                        "text": "Eighty participants with occlusal carious teeth",
                        "source": "abstract",
                    }
                ],
                "intervention_spans": [
                    {
                        "text": "zinc-carbonate hydroxyapatite",
                        "source": "abstract",
                    }
                ],
                "extraction_source": "abstract",
            }
        )


class _InvalidLLMGateway:
    async def call(self, **kwargs):
        return _FakeLLMResult(
            {
                "study_id": kwargs["study_id"],
                "population_spans": [],
                "intervention_spans": [],
                "extraction_source": "abstract",
            }
        )


class _FakeBatchGateway:
    def __init__(self, *, create_status="completed"):
        self.requests = None
        self.poll_calls = 0
        self.create_calls = 0
        self.create_status = create_status

    async def create_batch_job(self, *, requests, completion_window="24h"):
        self.create_calls += 1
        self.requests = requests
        return {
            "batch_id": "batch-1",
            "input_file_id": "file-in-1",
            "status": self.create_status,
            "raw": {"status": self.create_status},
        }

    async def poll_batch(self, batch_id):
        self.poll_calls += 1
        return {
            "id": batch_id,
            "status": "completed",
            "output_file_id": "file-out-1",
        }

    async def fetch_batch_output(self, output_file_id):
        study_id = self.requests[0].study_id
        return [
            {
                "custom_id": f"{study_id}:pi_extraction",
                "response": {
                    "body": {
                        "choices": [
                            {
                                "message": {
                                    "content": {
                                        "study_id": study_id,
                                        "population_spans": [
                                            {"text": "Eighty participants with occlusal carious teeth", "source": "abstract"}
                                        ],
                                        "intervention_spans": [
                                            {"text": "zinc-carbonate hydroxyapatite", "source": "abstract"}
                                        ],
                                        "extraction_source": "abstract",
                                    }
                                }
                            }
                        ]
                    }
                },
            }
        ]


def test_primary_rct_loader_reads_sample():
    reader = PMCReader()
    studies = reader.iter_primary_rct(limit=3)
    assert len(studies) == 3
    assert all(study.study_id for study in studies)
    assert all(study.title for study in studies)
    assert all(study.abstract for study in studies)


def test_pi_normalizer_produces_indexable_text():
    reader = PMCReader()
    study = reader.iter_primary_rct(limit=1)[0]
    extraction = PIExtractor().extract_local(study)
    normalized = PINormalizer().normalize(extraction)
    assert normalized.population.indexable_text
    assert normalized.intervention.indexable_text
    assert normalized.population.cleaned_text


def test_pi_normalizer_dedupes_spans_and_maps_mesh_fallback():
    extraction = PIExtractionResult(
        study_id="demo",
        population_spans=[
            SpanResult(text="Eighty participants with occlusal carious teeth", source="abstract"),
            SpanResult(text="Eighty participants with occlusal carious teeth", source="abstract"),
        ],
        intervention_spans=[
            SpanResult(text="zinc-carbonate hydroxyapatite", source="abstract"),
            SpanResult(text="zinc-carbonate hydroxyapatite", source="abstract"),
            SpanResult(text="Class I restoration using self-etch or selective-etch as well as with or without zinc-carbonate hydroxyapatite", source="abstract"),
        ],
        extraction_source="abstract",
    )
    normalized = PINormalizer().normalize(extraction)
    assert normalized.population.original_spans == ["Eighty participants with occlusal carious teeth"]
    assert normalized.intervention.original_spans.count("zinc-carbonate hydroxyapatite") == 1
    assert "Dental Caries" in [term.preferred_term for term in normalized.population.mesh_terms]
    assert "Hydroxyapatites" in [term.preferred_term for term in normalized.intervention.mesh_terms]
    assert "Dental Caries" in normalized.population.indexable_text
    assert "Hydroxyapatites" in normalized.intervention.indexable_text


def test_pi_extractor_validate_accepts_unicode_normalized_span():
    study = StudyRecord(
        study_id="demo",
        manifest_rel_path="demo.json",
        article_path="demo.json",
        pmid="1",
        pmcid="PMC1",
        title="SoftClamp™ trial",
        abstract=(
            "Forty-two children aged between 8 and 12 years were divided into groups. "
            "This study evaluated SoftClamp™ compared to the conventional metal clamp."
        ),
        source="PMC",
        publication_year=2023,
    )
    result = PIExtractionResult(
        study_id=study.study_id,
        population_spans=[
            SpanResult(
                text="Forty-two children aged between 8 and 12 years",
                source="abstract",
            )
        ],
        intervention_spans=[
            SpanResult(
                text="SoftClampTM compared to the conventional metal clamp",
                source="abstract",
            )
        ],
        extraction_source="abstract",
    )
    assert PIExtractor().validate(study, result) == []


def test_index_document_contains_core_fields():
    reader = PMCReader()
    study = reader.iter_primary_rct(limit=1)[0]
    extraction = PIExtractor().extract_local(study)
    normalized = PINormalizer().normalize(extraction)
    doc = RCTIndexBuilder(None).build_documents(normalized, study)
    assert doc.study_id == study.study_id
    assert doc.title == study.title
    assert doc.population
    assert doc.intervention
    assert doc.article_path == study.article_path
    # Article-level MeSH (metadata.mesh_term) vs PI-normalized MeSH (mesh_population / mesh_intervention).
    all_mesh = [*doc.mesh_terms, *doc.mesh_population, *doc.mesh_intervention]
    assert "Dental Caries" in all_mesh


def test_demo_runner_single_smoke(tmp_path):
    runner = Module1DemoRunner(
        database_url=None,
        data_root="data/data_for_test/data_demo",
        export_dir=tmp_path,
        llm_gateway=_FakeLLMGateway(),
    )
    try:
        result = asyncio.run(runner.run_single_by_index(0))
        assert result.study_id
        assert result.export_path.endswith(".json")
        payload = json.loads(Path(result.export_path).read_text(encoding="utf-8"))
        assert list(payload)[:4] == ["pi", "extraction", "normalized", "document"]
        assert payload["pi"]["population"]["indexable_text"]
    finally:
        runner.close()


def test_module1_batch_runner_builds_requests_from_prompt_and_schema(tmp_path):
    db_path = tmp_path / "requests.db"
    runner = Module1BatchRunner(
        database_url=f"sqlite:///{db_path}",
        data_root="data/data_for_test/data_demo",
        llm_gateway=_FakeBatchGateway(),
    )
    try:
        studies = runner.reader.iter_primary_rct(limit=2)
        requests = runner._make_batch_requests(studies)
        assert len(requests) == 2
        assert requests[0].task_type == "pi_extraction"
        assert requests[0].study_id == studies[0].study_id
        assert "Extract literal Population and Intervention spans" in requests[0].prompt_template
        assert requests[0].response_schema["required"] == [
            "study_id",
            "population_spans",
            "intervention_spans",
            "extraction_source",
        ]
    finally:
        runner.close()


def test_module1_batch_runner_parses_custom_id_with_colon_study_id(tmp_path):
    db_path = tmp_path / "parse.db"
    runner = Module1BatchRunner(
        database_url=f"sqlite:///{db_path}",
        data_root="data/data_for_test/data_demo",
        llm_gateway=_FakeBatchGateway(),
    )
    try:
        study_id, content, error = runner._parse_batch_result(
            {
                "custom_id": "pmid:12345:pi_extraction",
                "response": {
                    "body": {
                        "output_text": json.dumps(
                            {
                                "study_id": "pmid:12345",
                                "population_spans": [{"text": "patients", "source": "abstract"}],
                                "intervention_spans": [{"text": "metformin", "source": "abstract"}],
                                "extraction_source": "abstract",
                            }
                        )
                    }
                },
            }
        )
        assert study_id == "pmid:12345"
        assert content["study_id"] == "pmid:12345"
        assert error is None
    finally:
        runner.close()


def test_module1_batch_runner_smoke(tmp_path):
    db_path = tmp_path / "batch.db"
    gateway = _FakeBatchGateway()
    runner = Module1BatchRunner(
        database_url=f"sqlite:///{db_path}",
        data_root="data/data_for_test/data_demo",
        llm_gateway=gateway,
    )
    try:
        result = asyncio.run(runner.run(limit=1, poll=True))
        assert result.summary.batch_id == "batch-1"
        assert result.summary.completed == 1
        assert gateway.requests[0].task_type == "pi_extraction"
        assert gateway.requests[0].study_id
        store = ExtractionStore(database_url=f"sqlite:///{db_path}")
        row = store.get_study(gateway.requests[0].study_id)
        assert row["extraction_status"] == "completed"
        batch_row = store.get_batch_record("batch-1")
        assert batch_row["request_completed"] == 1
        assert batch_row["request_failed"] == 0
        store.close()
    finally:
        runner.close()


def test_module1_batch_runner_skips_completed_study(tmp_path):
    db_path = tmp_path / "skip.db"
    gateway = _FakeBatchGateway()
    runner = Module1BatchRunner(
        database_url=f"sqlite:///{db_path}",
        data_root="data/data_for_test/data_demo",
        llm_gateway=gateway,
    )
    try:
        first = asyncio.run(runner.run(limit=1, poll=True))
        second = asyncio.run(runner.run(limit=1, poll=True))
        assert first.summary.completed == 1
        assert second.summary.status == "skipped"
        assert gateway.create_calls == 1
    finally:
        runner.close()


def test_copy_demo_primary_subset_writes_files(tmp_path):
    dest = tmp_path / "demo_mesh"
    copy_demo_primary_subset("data/data_for_test/data_demo", dest, limit=2)
    manifest = dest / "manifest" / "files.jsonl"
    assert manifest.exists()
    lines = [ln for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    for line in lines:
        rel = json.loads(line)["rel_path"]
        assert (dest / rel).is_file()


def test_copy_theme_demo_subset_writes_theme_clustered_manifest(tmp_path):
    dest = tmp_path / "demo1000"
    result = copy_theme_demo_subset(
        "data/pmc-rct",
        dest,
        total=12,
        theme_quotas={
            "surgery_anesthesia_pain": 4,
            "diabetes_metabolic": 3,
            "dental_oral_caries": 2,
        },
    )
    manifest = dest / "manifest" / "files.jsonl"
    summary = dest / "manifest" / "selection_summary.json"
    assert result.selected_total == 12
    assert result.theme_counts["surgery_anesthesia_pain"] == 4
    assert result.theme_counts["diabetes_metabolic"] == 3
    assert result.theme_counts["dental_oral_caries"] == 2
    assert result.filler_count == 3
    assert manifest.is_file()
    assert summary.is_file()
    lines = [json.loads(ln) for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 12
    assert len({row["rel_path"] for row in lines}) == 12
    for row in lines:
        assert (dest / row["rel_path"]).is_file()


def test_module1_cli_select_demo(tmp_path, capsys):
    dest = tmp_path / "cli_demo1000"
    exit_code = module1_cli_main(
        [
            "select-demo",
            "--source-data-root",
            "data/pmc-rct",
            "--dest-data-root",
            str(dest),
            "--total",
            "10",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["selected_total"] == 10
    assert (dest / "manifest" / "files.jsonl").is_file()


def test_local_rct_index_search_finds_study(tmp_path):
    reader = PMCReader()
    study = reader.iter_primary_rct(limit=1)[0]
    extraction = PIExtractor().extract_local(study)
    normalized = PINormalizer().normalize(extraction)
    doc = RCTIndexBuilder(None).build_documents(normalized, study)
    index_path = tmp_path / "local.jsonl"
    idx = LocalRCTIndex(index_path)
    idx.build([doc])
    hits = idx.search("remineralizing", top_k=5)
    assert hits
    assert hits[0].study_id == study.study_id


def test_validate_module1_local_queries_smoke(tmp_path):
    reader = PMCReader()
    study = reader.iter_primary_rct(limit=1)[0]
    extraction = PIExtractor().extract_local(study)
    normalized = PINormalizer().normalize(extraction)
    doc = RCTIndexBuilder(None).build_documents(normalized, study)
    idx = LocalRCTIndex(tmp_path / "q.jsonl")
    idx.build([doc])
    rows = validate_module1_local_queries(
        idx,
        queries=(
            ("zinc-carbonate hydroxyapatite dental caries", study.study_id),
            ("postrestorative sensitivity", None),
            ("zinc-carbonate hydroxyapatite dental caries", "pmid:not-present"),
        ),
        top_k=10,
    )
    assert len(rows) == 3
    assert rows[0].passed
    assert rows[0].expected_in_top_hits is True
    assert rows[1].passed
    assert not rows[2].passed
    assert rows[2].expected_in_top_hits is False


def test_module1_simplified_runner_smoke(tmp_path):
    db_path = tmp_path / "simp.db"
    dest = tmp_path / "data/data_for_test/data/data_for_test/data_demo_with_mesh"
    gateway = _FakeLLMGateway()
    runner = Module1SimplifiedRunner(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        database_url=f"sqlite:///{db_path}",
        llm_gateway=gateway,
        copy_source=True,
        limit=1,
        skip_existing_derived=False,
        run_query_validation=True,
        validation_queries=(
            ("zinc-carbonate hydroxyapatite dental caries", "pmid:36908720"),
            ("postrestorative sensitivity", "pmid:36908720"),
        ),
    )
    try:
        result = asyncio.run(runner.run())
        assert result.studies_total == 1
        assert result.extracted == 1
        assert result.failed == 0
        assert Path(result.index_path).is_file()
        assert result.queries_passed == 2
        assert result.queries_total == 2
    finally:
        runner.close()


def test_run_module1_simplified_sync_wrapper(tmp_path):
    db_path = tmp_path / "wrap.db"
    dest = tmp_path / "mesh2"
    result = run_module1_simplified_sync(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        database_url=f"sqlite:///{db_path}",
        llm_gateway=_FakeLLMGateway(),
        copy_source=True,
        limit=1,
        skip_existing_derived=False,
        run_query_validation=False,
    )
    assert result.studies_total == 1
    assert result.queries_total == 0


def test_module1_simplified_runner_local_pi_mode_without_gateway(tmp_path):
    dest = tmp_path / "local_mesh"
    result = run_module1_simplified_sync(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        use_database=False,
        copy_source=True,
        limit=2,
        pi_mode="local",
        workers=2,
        skip_existing_derived=False,
        run_query_validation=False,
    )
    assert result.failed == 0
    assert result.indexed == 2
    payload = json.loads((dest / "derived" / "pmid_36908720.json").read_text(encoding="utf-8"))
    assert "mesh_terms" in payload["document"]
    assert "Dental Caries" in payload["document"]["mesh_population"]


def test_module1_simplified_runner_falls_back_when_llm_output_invalid(tmp_path):
    dest = tmp_path / "fallback_mesh"
    result = run_module1_simplified_sync(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        use_database=False,
        llm_gateway=_InvalidLLMGateway(),
        copy_source=True,
        limit=1,
        pi_mode="llm",
        workers=1,
        skip_existing_derived=False,
        run_query_validation=False,
    )
    assert result.failed == 0
    payload = json.loads((dest / "derived" / "pmid_36908720.json").read_text(encoding="utf-8"))
    assert payload["extraction"]["extraction_source"] == "local_fallback"
    assert payload["extraction"]["population_spans"]


def test_module1_simplified_runner_rejects_unknown_pi_mode(tmp_path):
    with pytest.raises(ValueError, match="pi_mode"):
        Module1SimplifiedRunner(
            source_data_root="data/data_for_test/data_demo",
            dest_data_root=tmp_path / "bad",
            database_url=f"sqlite:///{tmp_path / 'bad.db'}",
            pi_mode="api",
        )


def test_module1_cli_simplified_local_mode(tmp_path):
    dest = tmp_path / "cli_mesh"
    exit_code = module1_cli_main(
        [
            "simplified",
            "--source-data-root",
            "data/data_for_test/data_demo",
            "--dest-data-root",
            str(dest),
            "--limit",
            "1",
            "--pi-mode",
            "local",
            "--workers",
            "2",
            "--no-query-validation",
            "--force",
        ]
    )
    assert exit_code == 0
    assert (dest / "index" / "local_rct_index.jsonl").is_file()


def test_module1_cli_simplified_no_copy_source_reads_source_manifest(tmp_path):
    dest = tmp_path / "cli_no_copy_mesh"
    exit_code = module1_cli_main(
        [
            "simplified",
            "--source-data-root",
            "data/data_for_test/data_demo",
            "--dest-data-root",
            str(dest),
            "--limit",
            "1",
            "--pi-mode",
            "local",
            "--workers",
            "2",
            "--no-copy-source",
            "--no-query-validation",
            "--force",
        ]
    )
    assert exit_code == 0
    assert not (dest / "manifest" / "files.jsonl").exists()
    assert (dest / "derived" / "pmid_36908720.json").is_file()
    assert (dest / "index" / "local_rct_index.jsonl").is_file()


def test_build_module1_local_index_from_existing_derived(tmp_path):
    dest = tmp_path / "derived_index"
    result = run_module1_simplified_sync(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        use_database=False,
        copy_source=True,
        limit=1,
        pi_mode="local",
        skip_existing_derived=False,
        run_query_validation=False,
    )
    assert result.failed == 0
    rebuilt = build_module1_local_index_from_derived(
        data_root=dest,
        run_query_validation=False,
    )
    assert rebuilt.indexed == 1
    assert Path(rebuilt.index_path).is_file()


def test_module1_cli_search_local_outputs_hits(tmp_path, capsys):
    dest = tmp_path / "search_index"
    result = run_module1_simplified_sync(
        source_data_root="data/data_for_test/data_demo",
        dest_data_root=dest,
        use_database=False,
        copy_source=True,
        limit=1,
        pi_mode="local",
        skip_existing_derived=False,
        run_query_validation=False,
    )
    assert result.failed == 0
    exit_code = module1_cli_main(
        [
            "search-local",
            "--index-path",
            result.index_path,
            "--query",
            "zinc-carbonate hydroxyapatite dental caries",
            "--top-k",
            "1",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["hits"][0]["study_id"] == "pmid:36908720"


def test_module1_batch_runner_recovers_existing_active_batch(tmp_path):
    db_path = tmp_path / "recover.db"
    gateway = _FakeBatchGateway(create_status="queued")
    runner = Module1BatchRunner(
        database_url=f"sqlite:///{db_path}",
        data_root="data/data_for_test/data_demo",
        llm_gateway=gateway,
    )
    try:
        queued = asyncio.run(runner.run(limit=1, poll=False))
        assert queued.summary.status == "queued"
        assert gateway.create_calls == 1

        recovered = asyncio.run(runner.run(limit=1, poll=True))
        assert recovered.summary.completed == 1
        assert gateway.create_calls == 1
        assert gateway.poll_calls >= 1
    finally:
        runner.close()
