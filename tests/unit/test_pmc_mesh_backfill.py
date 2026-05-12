from __future__ import annotations

import json
from pathlib import Path

from ebm_backend.index_construction.application.pmc_mesh_backfill import (
    MeshBackfillCheckpoint,
    MeshBackfillRecord,
    ArticleTarget,
    backfill_article_file,
    backfill_mesh_terms,
    group_targets_by_pmid,
    parse_pubmed_mesh_xml,
    scan_pmc_manifest,
)


class _FakeFetcher:
    def __init__(self, mapping: dict[str, list[str]]):
        self.mapping = mapping
        self.calls: list[list[str]] = []

    def fetch_batch(self, pmids):
        pmid_list = list(pmids)
        self.calls.append(pmid_list)
        return {pmid: self.mapping.get(pmid, []) for pmid in pmid_list}


class _FailOnceFetcher:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.failed = False

    def fetch_batch(self, pmids):
        pmid_list = list(pmids)
        self.calls.append(pmid_list)
        if not self.failed:
            self.failed = True
            raise RuntimeError("temporary failure")
        return {pmid: ["Humans"] for pmid in pmid_list}


def _write_article(path: Path, metadata: dict[str, object] | None = None) -> None:
    payload = {
        "metadata": metadata or {},
        "sections": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_parse_pubmed_mesh_xml_reads_descriptor_names():
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>123</PMID>
          <MeshHeadingList>
            <MeshHeading><DescriptorName>Hypertension</DescriptorName></MeshHeading>
            <MeshHeading><DescriptorName>Hypertension</DescriptorName></MeshHeading>
            <MeshHeading><DescriptorName>Metformin</DescriptorName></MeshHeading>
          </MeshHeadingList>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    parsed = parse_pubmed_mesh_xml(xml)
    assert parsed["123"] == ["Hypertension", "Metformin"]


def test_scan_manifest_defaults_to_primary_only(tmp_path: Path):
    root = tmp_path / "data"
    (root / "manifest").mkdir(parents=True)
    (root / "2024" / "02" / "primary_rct" / "json").mkdir(parents=True)
    (root / "2024" / "02" / "rct_related" / "json").mkdir(parents=True)
    (root / "manifest" / "files.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "rel_path": "2024/02/primary_rct/json/a.json",
                        "classification": "primary_rct",
                        "pmid": "1",
                    }
                ),
                json.dumps(
                    {
                        "rel_path": "2024/02/rct_related/json/b.json",
                        "classification": "rct_related",
                        "pmid": None,
                    }
                ),
                json.dumps(
                    {
                        "rel_path": "2024/02/other/json/c.json",
                        "classification": "other",
                        "pmid": "3",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    targets = scan_pmc_manifest(root)
    assert len(targets) == 1
    grouped, no_pmid = group_targets_by_pmid(targets)
    assert list(grouped) == ["1"]
    assert len(no_pmid) == 0

    all_targets = scan_pmc_manifest(root, classifications=("primary_rct", "rct_related"))
    assert len(all_targets) == 2


def test_backfill_mesh_terms_writes_metadata_and_checkpoint(tmp_path: Path):
    root = tmp_path / "data"
    manifest = root / "manifest"
    manifest.mkdir(parents=True)
    (root / "2024" / "02" / "primary_rct" / "json").mkdir(parents=True)
    (root / "2024" / "02" / "rct_related" / "json").mkdir(parents=True)
    article_a = root / "2024" / "02" / "primary_rct" / "json" / "a.json"
    article_b = root / "2024" / "02" / "rct_related" / "json" / "b.json"
    article_c = root / "2024" / "02" / "rct_related" / "json" / "c.json"
    _write_article(article_a, {"pmid": "123"})
    _write_article(article_b, {"pmid": "123"})
    _write_article(article_c, {})
    manifest.joinpath("files.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"rel_path": str(article_a.relative_to(root)), "classification": "primary_rct", "pmid": "123"}),
                json.dumps({"rel_path": str(article_b.relative_to(root)), "classification": "rct_related", "pmid": "123"}),
                json.dumps({"rel_path": str(article_c.relative_to(root)), "classification": "rct_related", "pmid": None}),
            ]
        ),
        encoding="utf-8",
    )
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    fetcher = _FakeFetcher({"123": ["Hypertension", "Metformin"]})
    stats = backfill_mesh_terms(
        data_root=root,
        checkpoint_path=checkpoint_path,
        classifications=("primary_rct", "rct_related"),
        fetcher=fetcher,
        batch_size=1,
    )
    assert stats["files_seen"] == 3
    assert stats["files_updated"] == 3
    assert article_a.exists()
    assert json.loads(article_a.read_text(encoding="utf-8"))["metadata"]["mesh_term"] == ["Hypertension", "Metformin"]
    assert json.loads(article_c.read_text(encoding="utf-8"))["metadata"]["mesh_term"] == []

    fetcher.calls.clear()
    stats_second = backfill_mesh_terms(
        data_root=root,
        checkpoint_path=checkpoint_path,
        classifications=("primary_rct", "rct_related"),
        fetcher=fetcher,
        batch_size=1,
    )
    assert stats_second["files_skipped"] >= 1
    assert fetcher.calls == []


def test_backfill_article_file_does_not_overwrite_existing_terms(tmp_path: Path):
    article = tmp_path / "article.json"
    _write_article(article, {"mesh_term": ["Existing"]})
    updated = backfill_article_file(article, ["New"])
    assert updated is False
    assert json.loads(article.read_text(encoding="utf-8"))["metadata"]["mesh_term"] == ["Existing"]


def test_backfill_mesh_terms_recovers_after_batch_failure(tmp_path: Path):
    root = tmp_path / "data"
    (root / "manifest").mkdir(parents=True)
    (root / "2024" / "02" / "primary_rct" / "json").mkdir(parents=True)
    article_a = root / "2024" / "02" / "primary_rct" / "json" / "a.json"
    article_b = root / "2024" / "02" / "primary_rct" / "json" / "b.json"
    _write_article(article_a, {"pmid": "1"})
    _write_article(article_b, {"pmid": "2"})
    root.joinpath("manifest", "files.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"rel_path": str(article_a.relative_to(root)), "classification": "primary_rct", "pmid": "1"}),
                json.dumps({"rel_path": str(article_b.relative_to(root)), "classification": "primary_rct", "pmid": "2"}),
            ]
        ),
        encoding="utf-8",
    )
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    fetcher = _FailOnceFetcher()
    stats = backfill_mesh_terms(
        data_root=root,
        checkpoint_path=checkpoint_path,
        fetcher=fetcher,
        batch_size=2,
    )
    assert stats["batch_failures"] == 1
    assert stats["pmids_failed"] == 0
    assert json.loads(article_a.read_text(encoding="utf-8"))["metadata"].get("mesh_term") == ["Humans"]
    assert json.loads(article_b.read_text(encoding="utf-8"))["metadata"].get("mesh_term") == ["Humans"]
