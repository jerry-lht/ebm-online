from __future__ import annotations

import json
from pathlib import Path

import pytest

from ebm_backend.online_pipeline.application.question_study.query_gen import QueryGenerator
from ebm_backend.online_pipeline.application.question_study.retrieval_cache_v2 import RetrievalCacheV2
from ebm_backend.online_pipeline.application.question_study.search import QuestionStudySearcher


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
        self.calls: list[str] = []

    def __call__(self, url: str, timeout: int):
        self.calls.append(url)
        for key, body in self.routes.items():
            if key in url:
                return _DummyResponse(body)
        raise RuntimeError(f"unmocked url: {url}")


def _write_doc(path: Path, *, study_id: str, title: str, population: str, intervention: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "study_id": study_id,
        "pmid": study_id.split(":")[-1],
        "pmcid": None,
        "title": title,
        "abstract": f"{title} abstract",
        "population": population,
        "intervention": intervention,
        "source": "unit",
        "article_path": None,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_doc(path: Path, *, study_id: str, title: str, population: str, intervention: str) -> None:
    doc = {
        "study_id": study_id,
        "pmid": study_id.split(":")[-1],
        "pmcid": None,
        "title": title,
        "abstract": f"{title} abstract",
        "population": population,
        "intervention": intervention,
        "source": "unit",
        "article_path": None,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _query_output():
    return QueryGenerator().generate(population=["dental caries"], intervention=["hydroxyapatite"])


def _pubmed_xml_with_pmcid() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>999001</PMID>
      <Article>
        <ArticleTitle>Hydroxyapatite randomized trial in dental caries</ArticleTitle>
        <Abstract>
          <AbstractText>Adults with dental caries were randomly assigned to hydroxyapatite versus placebo.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Dental Caries</DescriptorName></MeshHeading>
        <MeshHeading><DescriptorName>Hydroxyapatites</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType='pmc'>PMC1234567</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _pubmed_xml_without_pmcid() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
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
"""


def _pmc_jats_xml() -> str:
    return """<?xml version='1.0' encoding='utf-8'?>
<pmc-articleset>
  <article>
    <front>
      <article-meta>
        <title-group>
          <article-title>Hydroxyapatite randomized trial in dental caries</article-title>
        </title-group>
      </article-meta>
    </front>
    <body>
      <sec>
        <title>Abstract</title>
        <p>Adults with dental caries were randomly assigned to hydroxyapatite versus placebo.</p>
      </sec>
      <sec>
        <title>Results</title>
        <p>The hydroxyapatite group improved.</p>
      </sec>
      <sec>
        <title>Tables</title>
        <table-wrap id="t1">
          <label>Table 1</label>
          <caption><p>Main outcomes.</p></caption>
          <table>
            <tbody>
              <tr><td>Group</td><td>Outcome</td></tr>
              <tr><td>Hydroxyapatite</td><td>Improved</td></tr>
            </tbody>
          </table>
        </table-wrap>
      </sec>
    </body>
  </article>
</pmc-articleset>
"""


def test_v2_dynamic_online_first_still_uses_online_search(tmp_path: Path):
    local_index = tmp_path / "local.jsonl"
    _write_doc(
        local_index,
        study_id="pmid:1",
        title="Hydroxyapatite trial A",
        population="dental caries",
        intervention="hydroxyapatite",
    )
    _append_doc(
        local_index,
        study_id="pmid:2",
        title="Hydroxyapatite trial B",
        population="dental caries",
        intervention="hydroxyapatite",
    )

    routes = {
        "esearch.fcgi": json.dumps({"esearchresult": {"idlist": ["999001"]}}),
        "db=pubmed": _pubmed_xml_with_pmcid(),
        "db=pmc": _pmc_jats_xml(),
    }
    opener = _FakeOpener(routes)
    searcher = QuestionStudySearcher(
        index_path=local_index,
        enable_v2_backfill=True,
        v2_cache_root=tmp_path / "cache_v2",
        v2_index_path=tmp_path / "cache_v2/index/local_rct_index_v2.jsonl",
        v2_min_local_hits=2,
    )
    assert searcher.v2_cache is not None
    searcher.v2_cache.opener = opener

    result = searcher.search_from_query_output(_query_output(), top_k=5, fallback_terms=["dental caries", "hydroxyapatite"])

    assert result.returned_count >= 1
    assert result.fallback_search is not None
    assert result.fallback_search.get("reason") == "dynamic_online_first"
    assert result.fallback_search.get("v2_backfill", {}).get("used") is True
    assert any("esearch.fcgi" in call for call in opener.calls)


def test_v2_backfill_ingests_and_reuses(tmp_path: Path):
    local_index = tmp_path / "local.jsonl"
    _write_doc(
        local_index,
        study_id="pmid:1",
        title="Unrelated trial",
        population="other population",
        intervention="other intervention",
    )

    routes = {
        "esearch.fcgi": json.dumps({"esearchresult": {"idlist": ["999001"]}}),
        "db=pubmed": _pubmed_xml_with_pmcid(),
        "db=pmc": _pmc_jats_xml(),
    }
    opener = _FakeOpener(routes)

    v2_index = tmp_path / "retrieval_cache_v2/index/local_rct_index_v2.jsonl"
    cache = RetrievalCacheV2.from_paths(
        cache_root=tmp_path / "retrieval_cache_v2",
        index_path=v2_index,
        min_local_hits=2,
        pubmed_fetch_count=10,
        opener=opener,
    )

    searcher = QuestionStudySearcher(
        index_path=local_index,
        enable_v2_backfill=True,
        v2_cache_root=tmp_path / "retrieval_cache_v2",
        v2_index_path=v2_index,
        v2_min_local_hits=2,
    )
    assert searcher.v2_cache is not None
    searcher.v2_cache = cache

    result = searcher.search_from_query_output(_query_output(), top_k=5, fallback_terms=["dental caries", "hydroxyapatite"])

    assert result.returned_count >= 1
    assert any(study.pmid == "999001" for study in result.studies)
    assert result.fallback_search is not None
    backfill = result.fallback_search.get("v2_backfill") or {}
    assert backfill.get("used") is True
    assert backfill.get("ingested") >= 1

    opener.calls.clear()
    second = searcher.search_from_query_output(_query_output(), top_k=5, fallback_terms=["dental caries", "hydroxyapatite"])
    second_backfill = (second.fallback_search or {}).get("v2_backfill") or {}
    assert second.returned_count >= 1
    assert second_backfill.get("reused_cleaned", 0) >= 1
    assert second_backfill.get("clean_success", 0) == 0

    assert v2_index.exists()
    lines = [line for line in v2_index.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    doc = json.loads(lines[-1])
    assert doc["pmid"] == "999001"
    assert doc["full_text_available"] is True
    assert doc["clean_status"] == "completed"
    assert Path(doc["article_path"]).exists()
    cleaned_payload = json.loads(Path(doc["article_path"]).read_text(encoding="utf-8"))
    assert (cleaned_payload.get("xml_content") or {}).get("sections")
    tables = (cleaned_payload.get("xml_content") or {}).get("tables") or []
    assert tables and "<table-wrap" in str(tables[0].get("raw_xml") or "")


def test_v2_logs_no_pmcid_and_does_not_index(tmp_path: Path):
    local_index = tmp_path / "local.jsonl"
    _write_doc(
        local_index,
        study_id="pmid:1",
        title="Unrelated trial",
        population="other",
        intervention="other",
    )

    routes = {
        "esearch.fcgi": json.dumps({"esearchresult": {"idlist": ["999002"]}}),
        "db=pubmed": _pubmed_xml_without_pmcid(),
    }
    opener = _FakeOpener(routes)

    cache_root = tmp_path / "retrieval_cache_v2"
    v2_index = cache_root / "index/local_rct_index_v2.jsonl"
    cache = RetrievalCacheV2.from_paths(
        cache_root=cache_root,
        index_path=v2_index,
        min_local_hits=2,
        pubmed_fetch_count=10,
        opener=opener,
    )

    searcher = QuestionStudySearcher(
        index_path=local_index,
        enable_v2_backfill=True,
        v2_cache_root=cache_root,
        v2_index_path=v2_index,
        v2_min_local_hits=2,
    )
    assert searcher.v2_cache is not None
    searcher.v2_cache = cache

    result = searcher.search_from_query_output(_query_output(), top_k=5, fallback_terms=["dental caries", "hydroxyapatite"])

    assert all(study.pmid != "999002" for study in result.studies)
    if v2_index.exists():
        lines = [line for line in v2_index.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert all(json.loads(line).get("pmid") != "999002" for line in lines)

    manifest = cache_root / "manifest/ingest_log.jsonl"
    assert manifest.exists()
    events = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(evt.get("pmid") == "999002" and evt.get("status") == "no_pmcid" for evt in events)


def test_v2_write_cleaned_payload_rejects_legacy_blocks_schema(tmp_path: Path):
    cache = RetrievalCacheV2.from_paths(
        cache_root=tmp_path / "retrieval_cache_v2",
        index_path=tmp_path / "retrieval_cache_v2/index/local_rct_index_v2.jsonl",
    )
    with pytest.raises(ValueError, match="legacy cleaned schema is not supported"):
        cache._write_cleaned_payload(
            pmid="999003",
            payload={
                "study_id": "pmid:999003",
                "metadata": {},
                "derived": {},
                "xml_content": {
                    "sections": [{"section": "results", "blocks": [{"text": "legacy"}]}],
                    "tables": [],
                },
            },
        )
