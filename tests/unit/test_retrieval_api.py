from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ebm_backend.online_pipeline.application.run_pipeline import PipelineOrchestrator, SimplifiedPipelineMockGateway
from ebm_backend.online_pipeline.interfaces.api.main import create_app


def test_retrieval_route_static_mode_returns_module2_only(tmp_path, monkeypatch):
    index_path = _index_path(tmp_path)
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "static",
            "top_k": 3,
            "index_path": str(index_path),
            "use_mock_llm": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["expansion"]["expanded_question"]
    assert payload["pi"]["population"]
    assert payload["query"]["boolean_query"]
    assert payload["search"]["studies"]
    stats = payload["stats"]
    assert stats["online_backfill_used"] is False
    assert stats["pubmed_requested"] == 0
    assert stats["rct_gate_excluded"] == 0
    assert stats["download_success"] == 0
    assert stats["clean_success"] == 0
    assert stats["ingested_success"] == 0
    timings = stats["timings_ms"]
    for key in [
        "question_expansion_ms",
        "question_pi_extraction_ms",
        "query_generation_ms",
        "local_search_ms",
        "total_ms",
    ]:
        assert key in timings
        assert isinstance(timings[key], int)
        assert timings[key] >= 0
    assert payload["cleaned_article_choices"] == []
    assert "randomized" in payload["query"]["boolean_query"].lower()


def test_retrieval_route_dynamic_mode_includes_v2_stats(tmp_path, monkeypatch):
    index_path = _index_path(tmp_path)
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "dynamic",
            "top_k": 3,
            "index_path": str(index_path),
            "use_mock_llm": False,
            "enable_v2_backfill": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    stats = payload["stats"]
    for key in [
        "retrieved_total",
        "returned_top_k",
        "online_backfill_used",
        "pubmed_requested",
        "rct_gate_excluded",
        "download_success",
        "clean_success",
        "ingested_success",
        "timings_ms",
    ]:
        assert key in stats
    timings = stats["timings_ms"]
    for key in [
        "question_expansion_ms",
        "question_pi_extraction_ms",
        "query_generation_ms",
        "local_search_ms",
        "total_ms",
    ]:
        assert key in timings
        assert isinstance(timings[key], int)
        assert timings[key] >= 0
    assert isinstance(payload["cleaned_article_choices"], list)
    assert payload["stats"]["returned_top_k"] == len(payload["search"]["studies"])
    assert (payload["search"].get("fallback_search") or {}).get("reason") == "dynamic_online_first"
    assert "randomized" in payload["query"]["boolean_query"].lower()
    assert all("retrieval_cache_v2/articles_cleaned/" in path for path in payload["cleaned_article_choices"])


def test_retrieval_route_dynamic_no_pmcid_records_stats(tmp_path, monkeypatch):
    index_path = tmp_path / "local_rct_index.jsonl"
    index_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    class _DummyResponse:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")

        def read(self) -> bytes:
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeOpener:
        def __init__(self, routes: dict[str, str]):
            self.routes = routes

        def __call__(self, url: str, timeout: int):
            for key, body in self.routes.items():
                if key in url:
                    return _DummyResponse(body)
            raise RuntimeError(f"unmocked url: {url}")

    routes = {
        "esearch.fcgi": json.dumps({"esearchresult": {"idlist": ["999002"]}}),
        "efetch.fcgi": """<?xml version='1.0' encoding='UTF-8'?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>999002</PMID>
      <Article>
        <ArticleTitle>Randomized trial without PMCID</ArticleTitle>
        <Abstract>
          <AbstractText>Randomized trial signal exists but no PMCID.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
""",
    }

    from ebm_backend.online_pipeline.application.question_study import RetrievalCacheV2, RetrievalV2Config

    monkeypatch.setattr(
        RetrievalCacheV2,
        "from_paths",
        classmethod(
            lambda cls, **kwargs: cls(
                config=RetrievalV2Config(
                    cache_root=Path(kwargs.get("cache_root")),
                    index_path=Path(kwargs.get("index_path")),
                    min_local_hits=kwargs.get("min_local_hits", 5),
                    pubmed_fetch_count=kwargs.get("pubmed_fetch_count", 30),
                    timeout=kwargs.get("timeout", 30),
                    retries=kwargs.get("retries", 1),
                    requests_per_second=kwargs.get("requests_per_second", 3.0),
                ),
                opener=_FakeOpener(routes),
            ),
        ),
    )

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "dynamic",
            "top_k": 3,
            "index_path": str(index_path),
            "use_mock_llm": False,
            "enable_v2_backfill": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    stats = payload["stats"]
    assert stats["pubmed_requested"] >= 0
    assert stats["ingested_success"] == 0


def test_retrieval_route_can_disable_rct_filter(tmp_path, monkeypatch):
    index_path = _index_path(tmp_path)
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "static",
            "top_k": 3,
            "index_path": str(index_path),
            "use_mock_llm": False,
            "rct_only": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "randomized" not in payload["query"]["boolean_query"].lower()


def test_retrieval_route_dynamic_cleaned_choices_only_include_v2_cleaned_files(tmp_path, monkeypatch):
    index_path = _index_path(tmp_path)
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    v2_clean = tmp_path / "data/retrieval_cache_v2/articles_cleaned/100.json"
    v2_clean.parent.mkdir(parents=True, exist_ok=True)
    v2_clean.write_text(
        json.dumps({"study_id": "pmid:100", "metadata": {}, "derived": {}, "xml_content": {"sections": [], "tables": []}}),
        encoding="utf-8",
    )
    static_like = tmp_path / "data/data_for_test/data_demo_1000/2023/01/primary_rct/json/PMC1.json"
    static_like.parent.mkdir(parents=True, exist_ok=True)
    static_like.write_text(json.dumps({"study_id": "pmid:1"}), encoding="utf-8")

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "dynamic",
            "top_k": 3,
            "index_path": str(index_path),
            "use_mock_llm": False,
            "enable_v2_backfill": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    # Inject controlled path mix to validate route-level filter behavior.
    payload["search"]["studies"] = [
        {"article_path": str(static_like)},
        {"article_path": str(v2_clean)},
    ]
    from ebm_backend.online_pipeline.interfaces.api.routes_retrieval import _cleaned_article_choices

    choices = _cleaned_article_choices(payload["search"], mode="dynamic")
    assert choices == [str(v2_clean)]


def test_retrieval_route_dynamic_ignores_index_path_and_uses_v2_default(monkeypatch):
    monkeypatch.setattr(PipelineOrchestrator, "_real_gateway", staticmethod(lambda: SimplifiedPipelineMockGateway()))
    client = TestClient(create_app())

    response = client.post(
        "/retrieval/run",
        json={
            "question": "Does duloxetine reduce catheter-related bladder discomfort?",
            "mode": "dynamic",
            "top_k": 3,
            "index_path": "data/data_for_test/data_demo_1000/index/local_rct_index.jsonl",
            "use_mock_llm": False,
            "enable_v2_backfill": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    # Dynamic mode must be cache-first and not leak static corpus cleaned paths.
    assert all("data_demo_1000" not in path for path in payload["cleaned_article_choices"])


def _index_path(tmp_path: Path) -> Path:
    path = tmp_path / "local_rct_index.jsonl"
    doc = {
        "study_id": "pmid:37877838",
        "pmid": "37877838",
        "pmcid": "PMC1",
        "title": "Duloxetine catheter-related bladder discomfort trial",
        "abstract": "Adults with catheter related bladder discomfort received duloxetine or placebo.",
        "population": "catheter-related bladder discomfort",
        "intervention": "duloxetine",
        "source": "PMC",
        "article_path": None,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
