"""Module 2 retrieval cache v2: local-first search with PubMed/PMC backfill."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ebm_backend.index_construction.application import LocalRCTIndex
from ebm_backend.index_construction.application.pipeline import normalize_phrase
from ebm_backend.online_pipeline.application.question_study.cleaned_article_schema import validate_cleaned_article_payload
from ebm_backend.online_pipeline.application.question_study.query_gen import QueryGenOutput, TermMapping

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

DEFAULT_V2_CACHE_ROOT = "data/retrieval_cache_v2"
DEFAULT_V2_INDEX_PATH = f"{DEFAULT_V2_CACHE_ROOT}/index/local_rct_index_v2.jsonl"
DEFAULT_V2_MIN_HITS = 5
DEFAULT_V2_PUBMED_FETCH_COUNT = 30
DEFAULT_V2_REQUEST_TIMEOUT = 30

_NON_RCT_PUB_TYPES = {
    "review",
    "systematic review",
    "meta-analysis",
    "practice guideline",
    "guideline",
    "case reports",
    "comment",
    "editorial",
    "letter",
}

_RCT_TEXT_PATTERNS = (
    r"\brandomized\b",
    r"\brandomised\b",
    r"\brandomly assigned\b",
    r"\bdouble blind\b",
    r"\bsingle blind\b",
    r"\bplacebo\b",
    r"\bcontrolled trial\b",
)

_SKIP_XML_TAGS = {
    "fig",
    "ref-list",
    "app-group",
    "supplementary-material",
}

_BACK_MATTER_SECTION_TITLE_MAP = {
    "acknowledgement": "Acknowledgements",
    "acknowledgements": "Acknowledgements",
    "acknowledgment": "Acknowledgements",
    "acknowledgments": "Acknowledgements",
    "funding": "Funding",
    "funding statement": "Funding",
    "financial support": "Funding",
    "competing interests": "Conflict of Interest",
    "conflicts of interest": "Conflict of Interest",
    "conflict of interest": "Conflict of Interest",
    "data availability": "Data Availability",
    "data availability statement": "Data Availability",
    "availability of data and materials": "Data Availability",
    "ethics statements": "Ethics",
    "ethics statement": "Ethics",
    "ethics approval and consent to participate": "Ethics",
    "institutional review board statement": "Ethics",
    "informed consent statement": "Ethics",
    "author contributions": "Author Contributions",
    "authors contributions": "Author Contributions",
    "trial registration": "Trial Registration",
    "declarations": "Declarations",
}

_BACK_MATTER_SEC_TYPE_MAP = {
    "coi statement": "Conflict of Interest",
    "conflict": "Conflict of Interest",
    "data availability": "Data Availability",
    "ethics statement": "Ethics",
    "funding information": "Funding",
    "trial registration": "Trial Registration",
}


class _Opener(Protocol):
    def __call__(self, url: str, timeout: int): ...


@dataclass(frozen=True)
class RetrievalV2Config:
    cache_root: Path
    index_path: Path
    min_local_hits: int = DEFAULT_V2_MIN_HITS
    pubmed_fetch_count: int = DEFAULT_V2_PUBMED_FETCH_COUNT
    timeout: int = DEFAULT_V2_REQUEST_TIMEOUT
    retries: int = 1
    requests_per_second: float = 3.0


class RetrievalCacheV2:
    """Manage v2 cached retrieval index and incremental ingestion."""

    def __init__(
        self,
        *,
        config: RetrievalV2Config,
        opener: _Opener | None = None,
    ):
        self.config = config
        self.opener = opener or urllib.request.urlopen

        self.index_path = config.index_path
        self.cache_root = config.cache_root
        self.raw_dir = self.cache_root / "articles_raw"
        self.cleaned_dir = self.cache_root / "articles_cleaned"
        self.manifest_path = self.cache_root / "manifest" / "ingest_log.jsonl"

        self._ensure_layout()
        self._sanitize_existing_jsonl()
        self.index = LocalRCTIndex(self.index_path)

        self._min_interval = 1.0 / config.requests_per_second if config.requests_per_second > 0 else 0.0
        self._last_request_at = 0.0

    @classmethod
    def from_paths(
        cls,
        *,
        cache_root: str | Path = DEFAULT_V2_CACHE_ROOT,
        index_path: str | Path = DEFAULT_V2_INDEX_PATH,
        min_local_hits: int = DEFAULT_V2_MIN_HITS,
        pubmed_fetch_count: int = DEFAULT_V2_PUBMED_FETCH_COUNT,
        timeout: int = DEFAULT_V2_REQUEST_TIMEOUT,
        retries: int = 1,
        requests_per_second: float = 3.0,
        opener: _Opener | None = None,
    ) -> "RetrievalCacheV2":
        config = RetrievalV2Config(
            cache_root=Path(cache_root),
            index_path=Path(index_path),
            min_local_hits=min_local_hits,
            pubmed_fetch_count=pubmed_fetch_count,
            timeout=timeout,
            retries=retries,
            requests_per_second=requests_per_second,
        )
        return cls(config=config, opener=opener)

    def maybe_backfill(
        self,
        *,
        output: QueryGenOutput,
        fallback_terms: list[str],
        top_k: int,
        current_local_hits: int | None = None,
    ) -> dict[str, Any]:
        local_hits = int(current_local_hits or 0)
        if local_hits >= self.config.min_local_hits:
            return {
                "used": False,
                "reason": "local_hits_sufficient",
                "local_hits": local_hits,
                "min_local_hits": self.config.min_local_hits,
                "requested": 0,
                "ingested": 0,
                "rct_gate_excluded": 0,
                "download_success": 0,
                "clean_success": 0,
            }

        before = len(self.index.documents)
        ingest_stats = self._ingest_from_pubmed(output=output, fallback_terms=fallback_terms)
        after = len(self.index.documents)

        return {
            "used": ingest_stats.get("requested", 0) > 0,
            "reason": "local_hits_below_threshold",
            "local_hits": local_hits,
            "min_local_hits": self.config.min_local_hits,
            "requested": ingest_stats.get("requested", 0),
            "ingested": after - before,
            "rct_gate_excluded": ingest_stats.get("rct_gate_excluded", 0),
            "download_success": ingest_stats.get("download_success", 0),
            "clean_success": ingest_stats.get("clean_success", 0),
            "query": ingest_stats.get("query", ""),
        }

    def online_first_retrieve(
        self,
        *,
        output: QueryGenOutput,
        fallback_terms: list[str],
        top_k: int,
    ) -> dict[str, Any]:
        query = self._build_pubmed_query(output=output, fallback_terms=fallback_terms)
        pmids = self._pubmed_esearch(query, retmax=max(top_k, self.config.pubmed_fetch_count))
        if not pmids:
            return {"query": query, "studies": [], "v2_backfill": {"used": False, "requested": 0, "ingested": 0, "download_success": 0, "clean_success": 0, "rct_gate_excluded": 0, "reused_cleaned": 0}}

        records = self._pubmed_efetch(pmids)
        by_pmid = {str(item.get("pmid") or ""): item for item in records}
        by_cached_pmid = {str(doc.get("pmid") or ""): doc for doc in self.index.documents}

        requested = len(pmids)
        ingested = 0
        download_success = 0
        clean_success = 0
        rct_gate_excluded = 0
        reused_cleaned = 0

        for pmid in pmids:
            record = by_pmid.get(str(pmid))
            if not record:
                continue

            cached = by_cached_pmid.get(str(pmid))
            if cached and Path(str(cached.get("article_path") or "")).exists():
                reused_cleaned += 1
                continue

            event = {
                "source": "pubmed",
                "pmid": pmid,
                "requested_at": _utc_now_iso(),
                "query": query,
                "status": "fetched",
            }
            try:
                self._write_raw_payload(pmid=pmid, payload=record)
                gate = self._rct_gate(record)
                if gate["status"] != "passed":
                    rct_gate_excluded += 1
                    event.update({"status": "rct_gate_failed", "rct_gate_status": gate["status"], "reason": gate.get("reason")})
                    self._append_manifest(event)
                    continue

                pmcid = str(record.get("pmcid") or "").strip() or None
                if not pmcid:
                    event.update({"status": "no_pmcid", "rct_gate_status": "passed"})
                    self._append_manifest(event)
                    continue

                xml_payload = self._fetch_pmc_jats_xml(pmcid)
                download_success += 1
                cleaned = self._clean_article_xml(pmid=pmid, pmcid=pmcid, xml_payload=xml_payload, record=record)
                cleaned_path = self._write_cleaned_payload(pmid=pmid, payload=cleaned)
                clean_success += 1

                index_doc = self._to_v2_index_doc(record=record, cleaned_path=cleaned_path)
                self._append_index_doc(index_doc)
                by_cached_pmid[str(pmid)] = index_doc
                ingested += 1
                event.update({"status": "indexed", "rct_gate_status": "passed", "full_text_available": True, "xml_status": "completed", "clean_status": "completed", "raw_path": str(self._raw_path_for_pmid(pmid)), "cleaned_path": str(cleaned_path)})
                self._append_manifest(event)
            except Exception as exc:
                event.update({"status": "failed", "error": str(exc)})
                self._append_manifest(event)

        studies: list[dict[str, Any]] = []
        for rank, pmid in enumerate(pmids):
            doc = by_cached_pmid.get(str(pmid))
            if not doc:
                continue
            article_path = str(doc.get("article_path") or "").strip()
            if not article_path or not Path(article_path).exists():
                continue
            doc_copy = dict(doc)
            doc_copy["_online_rank"] = rank
            studies.append(doc_copy)
            if len(studies) >= top_k:
                break

        return {
            "query": query,
            "studies": studies,
            "v2_backfill": {
                "used": requested > 0,
                "requested": requested,
                "ingested": ingested,
                "download_success": download_success,
                "clean_success": clean_success,
                "rct_gate_excluded": rct_gate_excluded,
                "reused_cleaned": reused_cleaned,
            },
        }

    def _ingest_from_pubmed(self, *, output: QueryGenOutput, fallback_terms: list[str]) -> dict[str, Any]:
        query = self._build_pubmed_query(output=output, fallback_terms=fallback_terms)
        pmids = self._pubmed_esearch(query, retmax=self.config.pubmed_fetch_count)
        if not pmids:
            return {
                "requested": 0,
                "added": 0,
                "failed": 0,
                "rct_gate_excluded": 0,
                "download_success": 0,
                "clean_success": 0,
                "query": query,
            }

        records = self._pubmed_efetch(pmids)
        by_pmid = {str(item.get("pmid") or ""): item for item in records}

        existing = {str(doc.get("pmid") or "") for doc in self.index.documents}

        added_docs = 0
        failed = 0
        rct_gate_excluded = 0
        download_success = 0
        clean_success = 0

        for pmid in pmids:
            record = by_pmid.get(str(pmid))
            if not record:
                continue
            if not pmid or pmid in existing:
                continue

            event = {
                "source": "pubmed",
                "pmid": pmid,
                "requested_at": _utc_now_iso(),
                "query": query,
                "status": "fetched",
            }

            try:
                self._write_raw_payload(pmid=pmid, payload=record)

                gate = self._rct_gate(record)
                if gate["status"] != "passed":
                    rct_gate_excluded += 1
                    event.update(
                        {
                            "status": "rct_gate_failed",
                            "rct_gate_status": gate["status"],
                            "reason": gate.get("reason"),
                        }
                    )
                    self._append_manifest(event)
                    continue

                pmcid = str(record.get("pmcid") or "").strip() or None
                if not pmcid:
                    event.update(
                        {
                            "status": "no_pmcid",
                            "rct_gate_status": "passed",
                        }
                    )
                    self._append_manifest(event)
                    continue

                xml_payload = self._fetch_pmc_jats_xml(pmcid)
                download_success += 1

                cleaned = self._clean_article_xml(pmid=pmid, pmcid=pmcid, xml_payload=xml_payload, record=record)
                cleaned_path = self._write_cleaned_payload(pmid=pmid, payload=cleaned)
                clean_success += 1

                index_doc = self._to_v2_index_doc(record=record, cleaned_path=cleaned_path)
                self._append_index_doc(index_doc)
                existing.add(pmid)
                added_docs += 1

                event.update(
                    {
                        "status": "indexed",
                        "rct_gate_status": "passed",
                        "full_text_available": True,
                        "xml_status": "completed",
                        "clean_status": "completed",
                        "raw_path": str(self._raw_path_for_pmid(pmid)),
                        "cleaned_path": str(cleaned_path),
                    }
                )
                self._append_manifest(event)
            except Exception as exc:
                failed += 1
                event.update(
                    {
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                self._append_manifest(event)

        return {
            "requested": len(pmids),
            "added": added_docs,
            "failed": failed,
            "rct_gate_excluded": rct_gate_excluded,
            "download_success": download_success,
            "clean_success": clean_success,
            "query": query,
        }

    def re_clean_existing_articles(self, *, pmids: list[str] | None = None) -> dict[str, Any]:
        targets = sorted({str(item).strip() for item in (pmids or []) if str(item).strip()})
        if not targets:
            targets = sorted(path.stem for path in self.cleaned_dir.glob("*.json"))

        requested = len(targets)
        cleaned = 0
        failed = 0

        for pmid in targets:
            cleaned_path = self.cleaned_dir / f"{pmid}.json"
            if not cleaned_path.exists():
                failed += 1
                continue
            try:
                old_payload = json.loads(cleaned_path.read_text(encoding="utf-8"))
                metadata = old_payload.get("metadata") or {}
                derived = old_payload.get("derived") or {}
                raw_path = self._raw_path_for_pmid(pmid)
                raw_record = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
                pmcid = str(metadata.get("pmc_id") or raw_record.get("pmcid") or "").strip()
                if not pmcid:
                    raise ValueError("missing pmcid in cleaned and raw payload")
                record = {
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "title": str(metadata.get("title") or raw_record.get("title") or ""),
                    "abstract": str(derived.get("abstract") or raw_record.get("abstract") or "") or None,
                    "publication_year": metadata.get("publication_year") or raw_record.get("publication_year"),
                    "mesh_terms": metadata.get("mesh_terms") or raw_record.get("mesh_terms") or [],
                }
                xml_payload = self._fetch_pmc_jats_xml(pmcid)
                new_payload = self._clean_article_xml(pmid=pmid, pmcid=pmcid, xml_payload=xml_payload, record=record)
                cleaned_path.write_text(json.dumps(new_payload, ensure_ascii=False, indent=2), encoding="utf-8")
                cleaned += 1
            except Exception:
                failed += 1

        return {
            "requested": requested,
            "cleaned": cleaned,
            "failed": failed,
        }

    def _build_pubmed_query(self, *, output: QueryGenOutput, fallback_terms: list[str]) -> str:
        terms: list[str] = []
        terms.extend(self._extract_mapping_terms(output.mapping_detail.get("population") or []))
        terms.extend(self._extract_mapping_terms(output.mapping_detail.get("intervention") or []))

        for term in fallback_terms:
            cleaned = " ".join(str(term or "").strip().split())
            if cleaned:
                terms.append(cleaned)

        deduped: list[str] = []
        seen: set[str] = set()
        for term in terms:
            key = normalize_phrase(term)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(term)

        if not deduped:
            return "randomized controlled trial[Title/Abstract]"

        term_block = " OR ".join(f'"{_escape_quotes(term)}"[Title/Abstract]' for term in deduped[:20])
        return f"({term_block}) AND (randomized[Title/Abstract] OR placebo[Title/Abstract] OR trial[Title/Abstract])"

    def _pubmed_esearch(self, term: str, *, retmax: int) -> list[str]:
        query = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "retmode": "json",
                "retmax": str(max(1, retmax)),
                "sort": "relevance",
                "term": term,
            }
        )
        payload = self._fetch_text(f"{PUBMED_ESEARCH_URL}?{query}")
        data = json.loads(payload)
        id_list = (data.get("esearchresult") or {}).get("idlist") or []
        return [str(value).strip() for value in id_list if str(value).strip()]

    def _pubmed_efetch(self, pmids: list[str]) -> list[dict[str, Any]]:
        if not pmids:
            return []
        query = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
            }
        )
        payload = self._fetch_text(f"{PUBMED_EFETCH_URL}?{query}")
        return self._parse_pubmed_xml(payload)

    def _fetch_pmc_jats_xml(self, pmcid: str) -> str:
        normalized = pmcid.strip()
        if not normalized:
            raise ValueError("empty PMCID")
        if not normalized.upper().startswith("PMC"):
            normalized = f"PMC{normalized}"
        query = urllib.parse.urlencode(
            {
                "db": "pmc",
                "id": normalized,
                "retmode": "xml",
            }
        )
        return self._fetch_text(f"{PMC_EFETCH_URL}?{query}")

    def _fetch_text(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self.config.retries + 1):
            try:
                self._throttle()
                with self.opener(url, timeout=self.config.timeout) as response:
                    return response.read().decode("utf-8")
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                last_error = exc
                if attempt >= self.config.retries:
                    break
                time.sleep(min(2**attempt, 8))
        raise RuntimeError(f"network request failed: {url}: {last_error}") from last_error

    def _parse_pubmed_xml(self, payload: str) -> list[dict[str, Any]]:
        root = ET.fromstring(payload)
        records: list[dict[str, Any]] = []
        for article in root.findall(".//PubmedArticle"):
            pmid = _safe_text(article.findtext(".//MedlineCitation/PMID") or "")
            if not pmid:
                continue

            title = _safe_text(article.findtext(".//Article/ArticleTitle") or "")
            abstract = " ".join(
                _safe_text(node.text or "")
                for node in article.findall(".//Article/Abstract/AbstractText")
                if _safe_text(node.text or "")
            ).strip() or None

            pmcid = None
            for aid in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                if (aid.attrib.get("IdType") or "").lower() == "pmc":
                    value = _safe_text(aid.text or "")
                    if value:
                        pmcid = value if value.upper().startswith("PMC") else f"PMC{value}"
                        break

            pub_types = [
                _safe_text(node.text or "")
                for node in article.findall(".//PublicationTypeList/PublicationType")
                if _safe_text(node.text or "")
            ]
            mesh_terms = [
                _safe_text(node.text or "")
                for node in article.findall(".//MeshHeadingList/MeshHeading/DescriptorName")
                if _safe_text(node.text or "")
            ]

            records.append(
                {
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "title": title,
                    "abstract": abstract,
                    "publication_year": _extract_publication_year(article),
                    "publication_types": pub_types,
                    "mesh_terms": _dedupe_terms(mesh_terms),
                    "source": "PubMed",
                }
            )
        return records

    def _rct_gate(self, record: dict[str, Any]) -> dict[str, str]:
        pub_types = [normalize_phrase(term) for term in record.get("publication_types") or []]
        if any(term in _NON_RCT_PUB_TYPES for term in pub_types):
            return {"status": "failed_non_rct_pubtype", "reason": "non_rct_publication_type"}
        if any("randomized controlled trial" in term or "clinical trial" in term for term in pub_types):
            return {"status": "passed", "reason": "publication_type_indicates_rct"}

        text = normalize_phrase(" ".join([record.get("title") or "", record.get("abstract") or ""]))
        if any(re.search(pattern, text) for pattern in _RCT_TEXT_PATTERNS):
            return {"status": "passed", "reason": "title_abstract_pattern"}
        return {"status": "failed_no_rct_signal", "reason": "missing_rct_signal"}

    def _clean_article_xml(self, *, pmid: str, pmcid: str, xml_payload: str, record: dict[str, Any]) -> dict[str, Any]:
        xml_content = _extract_xml_content(xml_payload)
        sections = xml_content.get("sections") or []
        abstract_text = _extract_abstract_from_xml_content(xml_content)
        population, intervention = _infer_population_intervention(
            title=record.get("title") or "",
            abstract=record.get("abstract") or abstract_text,
        )
        return {
            "study_id": f"pmid:{pmid}",
            "metadata": {
                "pmid": pmid,
                "pmc_id": pmcid,
                "title": record.get("title") or "",
                "source_type": "PubMed/PMC",
                "publication_year": record.get("publication_year"),
                "mesh_terms": record.get("mesh_terms") or [],
            },
            "xml_content": xml_content,
            "derived": {
                "population": population,
                "intervention": intervention,
                "abstract": record.get("abstract") or abstract_text,
            },
        }

    def _to_v2_index_doc(self, *, record: dict[str, Any], cleaned_path: Path) -> dict[str, Any]:
        cleaned = json.loads(cleaned_path.read_text(encoding="utf-8"))
        derived = cleaned.get("derived") or {}

        pmid = str(record.get("pmid") or "").strip()
        pmcid = record.get("pmcid")
        population = str(derived.get("population") or "")
        intervention = str(derived.get("intervention") or "")
        mesh_terms = [str(item) for item in record.get("mesh_terms") or [] if str(item).strip()]

        return {
            "study_id": f"pmid:{pmid}",
            "pmid": pmid or None,
            "pmcid": pmcid,
            "title": str(record.get("title") or ""),
            "abstract": str(record.get("abstract") or derived.get("abstract") or "") or None,
            "publication_year": record.get("publication_year"),
            "source": "PubMed",
            "rct_gate_status": "passed",
            "full_text_available": True,
            "xml_status": "completed",
            "clean_status": "completed",
            "population": population,
            "intervention": intervention,
            "mesh_population": _dedupe_terms(_pick_mesh_terms(mesh_terms, hint=population)),
            "mesh_intervention": _dedupe_terms(_pick_mesh_terms(mesh_terms, hint=intervention)),
            "mesh_terms": _dedupe_terms(mesh_terms),
            "population_original": population,
            "intervention_original": intervention,
            "article_type": "primary_rct",
            "open_access": True,
            "article_path": str(cleaned_path),
            "raw_path": str(self._raw_path_for_pmid(pmid)),
            "cleaned_path": str(cleaned_path),
            "indexed_at": _utc_now_iso(),
        }

    def _append_index_doc(self, doc: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        self.index.documents.append(doc)

    def _write_raw_payload(self, *, pmid: str, payload: dict[str, Any]) -> Path:
        path = self._raw_path_for_pmid(pmid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _write_cleaned_payload(self, *, pmid: str, payload: dict[str, Any]) -> Path:
        validate_cleaned_article_payload(payload)
        path = self.cleaned_dir / f"{pmid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _raw_path_for_pmid(self, pmid: str) -> Path:
        return self.raw_dir / f"{pmid}.json"

    def _append_manifest(self, event: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _ensure_layout(self) -> None:
        (self.cache_root / "index").mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def _sanitize_existing_jsonl(self) -> None:
        for path in (self.index_path, self.manifest_path):
            if not path.exists():
                continue
            changed = False
            cleaned_lines: list[str] = []
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                if line.endswith("\\n"):
                    line = line[:-2]
                    changed = True
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    changed = True
                    continue
                cleaned_lines.append(json.dumps(payload, ensure_ascii=False))
            if changed:
                path.write_text("".join(f"{line}\n" for line in cleaned_lines), encoding="utf-8")

    @staticmethod
    def _extract_mapping_terms(mappings: list[TermMapping]) -> list[str]:
        terms: list[str] = []
        for mapping in mappings:
            terms.append(mapping.original)
            terms.extend(mapping.mesh_preferred)
            terms.extend(mapping.entry_terms)
        return [term for term in terms if str(term).strip()]


def _extract_publication_year(article: ET.Element) -> int | None:
    candidates = [
        article.findtext(".//Article/Journal/JournalIssue/PubDate/Year"),
        article.findtext(".//Article/ArticleDate/Year"),
        article.findtext(".//PubmedData/History/PubMedPubDate/Year"),
    ]
    for value in candidates:
        text = _safe_text(value or "")
        if text.isdigit():
            year = int(text)
            if 1800 <= year <= 3000:
                return year
    return None


def _infer_population_intervention(*, title: str, abstract: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", f"{title}. {abstract}".strip())

    population = ""
    intervention = ""

    pop_match = re.search(r"\bin\s+([^.,;]{8,120})", text, flags=re.IGNORECASE)
    if pop_match:
        population = pop_match.group(1).strip(" .;,")

    int_patterns = [
        r"\b(received|given|treated with)\s+([^.,;]{3,120})",
        r"\b(intervention|therapy|treatment):?\s*([^.,;]{3,120})",
    ]
    for pattern in int_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            intervention = match.group(2).strip(" .;,")
            break

    if not population:
        population = text[:120].strip(" .;,")
    if not intervention:
        intervention = _heuristic_drug_phrase(text)

    return population, intervention


def _heuristic_drug_phrase(text: str) -> str:
    match = re.search(
        r"\b([A-Za-z][A-Za-z0-9-]{2,}(?:\s+[A-Za-z0-9-]{2,}){0,4})\s+(?:versus|vs|compared with|against)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(" .;,")
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)
    return " ".join(tokens[:4]) if tokens else ""


def _pick_mesh_terms(mesh_terms: list[str], *, hint: str) -> list[str]:
    if not mesh_terms:
        return []
    hint_tokens = set(re.findall(r"[a-z0-9]+", normalize_phrase(hint)))
    if not hint_tokens:
        return mesh_terms[:5]
    picked: list[str] = []
    for term in mesh_terms:
        term_tokens = set(re.findall(r"[a-z0-9]+", normalize_phrase(term)))
        if hint_tokens & term_tokens:
            picked.append(term)
    return picked or mesh_terms[:5]


def _dedupe_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = _safe_text(value)
        key = normalize_phrase(text)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _safe_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_text(value: str) -> str:
    return _safe_text(html.unescape(value or ""))


def _normalize_label(value: str) -> str:
    text = (value or "").lower().strip()
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _xml_tag_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _direct_child_text(node: ET.Element, child_name: str) -> str:
    for child in node:
        if _xml_tag_name(child.tag) == child_name:
            return _clean_text("".join(child.itertext()))
    return ""


def _xml_to_string(node: ET.Element) -> str:
    return ET.tostring(node, encoding="unicode")


def _extract_xml_content(payload: str) -> dict[str, Any]:
    root = ET.fromstring(payload)
    article = root.find("article")
    if article is None:
        article = root

    paragraphs: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    body = article.find("body")
    if body is not None:
        _walk_xml_node(body, [], paragraphs, tables)

    for back in article.findall("back"):
        _walk_back_matter(back, paragraphs, tables)

    for floats_group in article.findall("floats-group"):
        _walk_float_tables(floats_group, ["floats-group"], tables)

    sections = _build_markdown_sections(paragraphs)
    return {
        "sections": sections,
        "tables": tables,
    }


def _extract_abstract_from_xml_content(xml_content: dict[str, Any]) -> str:
    parts: list[str] = []
    for section in xml_content.get("sections") or []:
        name = _normalize_label(str(section.get("section") or ""))
        if "abstract" in name:
            text = _safe_text(str(section.get("text") or ""))
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _canonical_back_section_name(node: ET.Element) -> str | None:
    tag = _xml_tag_name(node.tag)
    title_key = _normalize_label(_direct_child_text(node, "title"))
    if title_key in _BACK_MATTER_SECTION_TITLE_MAP:
        return _BACK_MATTER_SECTION_TITLE_MAP[title_key]
    sec_type_key = _normalize_label(node.attrib.get("sec-type", ""))
    if sec_type_key in _BACK_MATTER_SEC_TYPE_MAP:
        return _BACK_MATTER_SEC_TYPE_MAP[sec_type_key]
    if tag == "ack":
        return "Acknowledgements"
    return None


def _back_matter_text_fallback(node: ET.Element, title: str) -> str:
    chunks: list[str] = []
    if _clean_text(node.text or ""):
        chunks.append(_clean_text(node.text or ""))
    for child in node:
        if _xml_tag_name(child.tag) == "title":
            if _clean_text(child.tail or ""):
                chunks.append(_clean_text(child.tail or ""))
            continue
        if _clean_text(child.tail or ""):
            chunks.append(_clean_text(child.tail or ""))
    text = " ".join(chunk for chunk in chunks if chunk).strip()
    if title and text.lower().startswith(title.lower()):
        text = text[len(title):].strip(" :.-")
    return text


def _walk_back_matter(
    back: ET.Element,
    paragraphs: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> None:
    for child in back:
        tag = _xml_tag_name(child.tag)
        if tag not in {"ack", "notes", "sec"}:
            continue
        section_name = _canonical_back_section_name(child)
        if not section_name:
            continue
        section_path = [section_name]
        paragraph_start = len(paragraphs)
        table_start = len(tables)
        raw_title = _direct_child_text(child, "title")
        for grandchild in child:
            if _xml_tag_name(grandchild.tag) == "title":
                continue
            _walk_xml_node(grandchild, list(section_path), paragraphs, tables)
        if len(paragraphs) == paragraph_start and len(tables) == table_start:
            fallback_text = _back_matter_text_fallback(child, raw_title)
            if fallback_text:
                paragraphs.append({"section_path": section_path, "text": fallback_text})


def _walk_xml_node(
    node: ET.Element,
    section_path: list[str],
    paragraphs: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> None:
    tag = _xml_tag_name(node.tag)
    if tag in _SKIP_XML_TAGS:
        return

    if tag == "sec":
        title = _direct_child_text(node, "title")
        next_path = section_path + [title] if title else list(section_path)
        for child in node:
            if _xml_tag_name(child.tag) == "title":
                continue
            _walk_xml_node(child, next_path, paragraphs, tables)
        return

    if tag == "p":
        text = _clean_text("".join(node.itertext()))
        if text:
            paragraphs.append({"section_path": list(section_path), "text": text})
        return

    if tag == "table-wrap":
        tables.append({"section_path": list(section_path), "raw_xml": _xml_to_string(node)})
        return

    for child in node:
        _walk_xml_node(child, list(section_path), paragraphs, tables)


def _walk_float_tables(node: ET.Element, section_path: list[str], tables: list[dict[str, Any]]) -> None:
    tag = _xml_tag_name(node.tag)
    if tag == "table-wrap":
        tables.append({"section_path": list(section_path), "raw_xml": _xml_to_string(node)})
        return
    for child in node:
        _walk_float_tables(child, list(section_path), tables)


def _markdown_heading(level: int, title: str) -> str:
    return f'{"#" * level} {title}'


def _build_markdown_sections(paragraphs: list[dict[str, Any]]) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_section_name: str | None = None
    current_section_record: dict[str, str] | None = None
    current_subpath: tuple[str, ...] | None = None

    for paragraph in paragraphs:
        section_path = [part for part in (paragraph.get("section_path") or []) if part]
        text = str(paragraph.get("text") or "")
        if not text:
            continue

        section_name = section_path[0] if section_path else "Front"
        subpath = tuple(section_path[1:])
        if section_name != current_section_name:
            current_section_record = {"section": section_name, "text": ""}
            sections.append(current_section_record)
            current_section_name = section_name
            current_subpath = None

        if current_section_record is None:
            continue

        chunks: list[str] = []
        if subpath and subpath != current_subpath:
            for idx, title in enumerate(subpath):
                chunks.append(_markdown_heading(idx + 2, title))
            current_subpath = subpath
        elif not subpath:
            current_subpath = None

        chunks.append(text)
        chunk_text = "\n\n".join(chunks)
        if current_section_record["text"]:
            current_section_record["text"] = f'{current_section_record["text"]}\n\n{chunk_text}'
        else:
            current_section_record["text"] = chunk_text

    return sections


def _escape_quotes(term: str) -> str:
    return str(term).replace('"', "\\\"")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
