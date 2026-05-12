"""PubMed MeSH backfill for PMC-RCT article JSON files."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

from ebm_backend.index_construction.application.pipeline import clean_text


PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_BATCH_SIZE = 200
DEFAULT_TIMEOUT = 30


class _Opener(Protocol):
    def __call__(self, url: str, timeout: int): ...


@dataclass(frozen=True)
class ArticleTarget:
    pmid: str | None
    article_path: Path
    classification: str
    rel_path: str


@dataclass(frozen=True)
class MeshBackfillRecord:
    pmid: str
    mesh_terms: list[str]
    status: str
    error: str | None = None
    retry_count: int = 0


class MeshBackfillCheckpoint:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pmid_results: dict[str, MeshBackfillRecord] = {}
        self.file_statuses: dict[str, str] = {}
        self._load()

    def close(self) -> None:
        return None

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "pmid_result":
                    pmid = str(event.get("pmid") or "").strip()
                    if not pmid:
                        continue
                    self.pmid_results[pmid] = MeshBackfillRecord(
                        pmid=pmid,
                        mesh_terms=list(event.get("mesh_terms") or []),
                        status=str(event.get("status") or "pending"),
                        error=event.get("error"),
                        retry_count=int(event.get("retry_count") or 0),
                    )
                elif event_type == "file_status":
                    article_path = str(event.get("article_path") or "").strip()
                    status = str(event.get("status") or "").strip()
                    if article_path and status:
                        self.file_statuses[article_path] = status

    def _append(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def load_pmid_result(self, pmid: str) -> MeshBackfillRecord | None:
        return self.pmid_results.get(pmid)

    def upsert_pmid_result(self, record: MeshBackfillRecord) -> None:
        self.pmid_results[record.pmid] = record
        self._append(
            {
                "type": "pmid_result",
                "pmid": record.pmid,
                "status": record.status,
                "mesh_terms": record.mesh_terms,
                "error": record.error,
                "retry_count": record.retry_count,
            }
        )

    def mark_retry(self, pmid: str, error: str) -> None:
        previous = self.pmid_results.get(pmid)
        retry_count = (previous.retry_count + 1) if previous is not None else 1
        self.pmid_results[pmid] = MeshBackfillRecord(
            pmid=pmid,
            mesh_terms=list(previous.mesh_terms) if previous else [],
            status="failed",
            error=error,
            retry_count=retry_count,
        )
        self._append(
            {
                "type": "pmid_retry",
                "pmid": pmid,
                "status": "failed",
                "error": error,
                "retry_count": retry_count,
            }
        )

    def record_file(self, target: ArticleTarget) -> None:
        self.file_statuses[str(target.article_path)] = "pending"
        self._append(
            {
                "type": "file_record",
                "article_path": str(target.article_path),
                "pmid": target.pmid,
                "classification": target.classification,
                "rel_path": target.rel_path,
                "status": "pending",
            }
        )

    def mark_file(self, article_path: Path, status: str) -> None:
        self.file_statuses[str(article_path)] = status
        self._append(
            {
                "type": "file_status",
                "article_path": str(article_path),
                "status": status,
            }
        )

    def mark_file_error(self, article_path: Path, error: str) -> None:
        self.file_statuses[str(article_path)] = "failed"
        self._append(
            {
                "type": "file_error",
                "article_path": str(article_path),
                "status": "failed",
                "error": error,
            }
        )

    def file_status(self, article_path: Path) -> str | None:
        return self.file_statuses.get(str(article_path))


class PubMedMeshFetcher:
    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        requests_per_second: float = 3.0,
        retries: int = 2,
        opener: _Opener | None = None,
    ):
        self.timeout = timeout
        self.requests_per_second = requests_per_second
        self.retries = max(0, retries)
        self.opener = opener or urllib.request.urlopen
        self._min_interval = 1.0 / requests_per_second if requests_per_second and requests_per_second > 0 else 0.0
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def fetch_batch(self, pmids: Iterable[str]) -> dict[str, list[str]]:
        pmid_list = [str(pmid).strip() for pmid in pmids if str(pmid).strip()]
        if not pmid_list:
            return {}
        query = urllib.parse.urlencode(
            {
                "db": "pubmed",
                "id": ",".join(pmid_list),
                "retmode": "xml",
            }
        )
        url = f"{PUBMED_EFETCH_URL}?{query}"
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                self._throttle()
                with self.opener(url, timeout=self.timeout) as response:
                    payload = response.read().decode("utf-8")
                return parse_pubmed_mesh_xml(payload)
            except (urllib.error.URLError, TimeoutError, ValueError, ET.ParseError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(min(2**attempt, 8))
        raise RuntimeError(f"failed to fetch PubMed batch for {len(pmid_list)} PMIDs: {last_error}") from last_error


class ProgressPrinter:
    def __init__(self, total: int | None = None):
        self.total = total
        self.last_line = ""

    def update(self, **values: Any) -> None:
        parts = []
        if self.total is not None:
            parts.append(f"files={values.get('files_seen', 0)}/{self.total}")
        for key in (
            "updated",
            "skipped",
            "failed",
            "pmids",
            "pmid_failed",
            "batches_failed",
        ):
            if key in values:
                parts.append(f"{key}={values[key]}")
        line = " | ".join(parts)
        if line != self.last_line:
            print(f"\r{line}", end="", flush=True)
            self.last_line = line

    def done(self) -> None:
        if self.last_line:
            print()


def scan_pmc_manifest(
    data_root: str | Path = Path("data/pmc-rct"),
    classifications: tuple[str, ...] = ("primary_rct",),
    checkpoint: MeshBackfillCheckpoint | None = None,
) -> list[ArticleTarget]:
    return list(iter_manifest_targets(data_root=data_root, classifications=classifications, checkpoint=checkpoint))


def iter_manifest_targets(
    data_root: str | Path = Path("data/pmc-rct"),
    classifications: tuple[str, ...] = ("primary_rct",),
    checkpoint: MeshBackfillCheckpoint | None = None,
):
    root = Path(data_root)
    manifest_path = root / "manifest" / "files.jsonl"
    with manifest_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                manifest = json.loads(line)
            except json.JSONDecodeError:
                continue
            classification = str(manifest.get("classification") or "")
            if classification not in classifications:
                continue
            rel_path = str(manifest["rel_path"])
            article_path = root / rel_path
            pmid = normalize_pmid(manifest.get("pmid"))
            target = ArticleTarget(
                pmid=pmid,
                article_path=article_path,
                classification=classification,
                rel_path=rel_path,
            )
            if checkpoint is not None:
                checkpoint.record_file(target)
            yield target


def group_targets_by_pmid(targets: Iterable[ArticleTarget]) -> tuple[dict[str, list[ArticleTarget]], list[ArticleTarget]]:
    grouped: dict[str, list[ArticleTarget]] = {}
    no_pmid: list[ArticleTarget] = []
    for target in targets:
        if target.pmid:
            grouped.setdefault(target.pmid, []).append(target)
        else:
            no_pmid.append(target)
    return grouped, no_pmid


def normalize_pmid(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_pubmed_mesh_xml(payload: str) -> dict[str, list[str]]:
    root = ET.fromstring(payload)
    records: dict[str, list[str]] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//MedlineCitation/PMID")
        if not pmid:
            continue
        mesh_terms: list[str] = []
        for heading in article.findall(".//MeshHeadingList/MeshHeading"):
            descriptor = heading.find("DescriptorName")
            if descriptor is None:
                continue
            term = clean_text(descriptor.text or "")
            if term:
                mesh_terms.append(term)
        records[pmid] = dedupe_terms(mesh_terms)
    return records


def dedupe_terms(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        term = clean_text(value)
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(term)
    return ordered


def read_article(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_article(path: Path, article: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def ensure_mesh_term_field(article: dict[str, Any], mesh_terms: list[str]) -> tuple[dict[str, Any], bool]:
    metadata = article.setdefault("metadata", {})
    existing = metadata.get("mesh_term")
    if isinstance(existing, list) and existing:
        return article, False
    if existing == mesh_terms:
        return article, False
    metadata["mesh_term"] = mesh_terms
    return article, True


def backfill_article_file(path: Path, mesh_terms: list[str], *, overwrite: bool = False) -> bool:
    article = read_article(path)
    metadata = article.setdefault("metadata", {})
    existing = metadata.get("mesh_term")
    if isinstance(existing, list) and existing and not overwrite:
        return False
    if existing == mesh_terms and not overwrite:
        return False
    metadata["mesh_term"] = mesh_terms
    write_article(path, article)
    return True


def backfill_no_pmid_file(path: Path, *, overwrite: bool = False) -> bool:
    article = read_article(path)
    metadata = article.setdefault("metadata", {})
    existing = metadata.get("mesh_term")
    if existing == [] and not overwrite:
        return False
    metadata["mesh_term"] = []
    write_article(path, article)
    return True


def _process_target(
    target: ArticleTarget,
    mesh_terms: list[str],
    *,
    overwrite: bool,
    checkpoint: MeshBackfillCheckpoint,
    stats: dict[str, int],
) -> None:
    try:
        if target.pmid is None:
            updated = backfill_no_pmid_file(target.article_path, overwrite=overwrite)
        else:
            updated = backfill_article_file(target.article_path, mesh_terms, overwrite=overwrite)
        if updated:
            stats["files_updated"] += 1
        else:
            stats["files_skipped"] += 1
        checkpoint.mark_file(target.article_path, "completed")
    except Exception as exc:
        stats["files_failed"] += 1
        checkpoint.mark_file_error(target.article_path, str(exc))


def _fetch_pmids_with_fallback(
    fetcher: PubMedMeshFetcher,
    pmids: list[str],
    *,
    stats: dict[str, int],
    checkpoint: MeshBackfillCheckpoint,
) -> tuple[dict[str, list[str]], set[str]]:
    if not pmids:
        return {}, set()
    try:
        return fetcher.fetch_batch(pmids), set()
    except Exception as exc:
        stats["batch_failures"] += 1
        batch_error = str(exc)
        for pmid in pmids:
            checkpoint.mark_retry(pmid, batch_error)
    results: dict[str, list[str]] = {}
    failed: set[str] = set()
    for pmid in pmids:
        try:
            results.update(fetcher.fetch_batch([pmid]))
        except Exception as exc:
            stats["pmids_failed"] += 1
            checkpoint.mark_retry(pmid, str(exc))
            failed.add(pmid)
    return results, failed


def backfill_mesh_terms(
    *,
    data_root: str | Path = Path("data/pmc-rct"),
    checkpoint_path: str | Path | None = None,
    classifications: tuple[str, ...] = ("primary_rct",),
    batch_size: int = DEFAULT_BATCH_SIZE,
    overwrite: bool = False,
    requests_per_second: float = 3.0,
    retries: int = 2,
    fetcher: PubMedMeshFetcher | None = None,
    checkpoint: MeshBackfillCheckpoint | None = None,
) -> dict[str, int]:
    root = Path(data_root)
    owns_checkpoint = checkpoint is None
    checkpoint = checkpoint or MeshBackfillCheckpoint(
        checkpoint_path or root / ".mesh_backfill" / "checkpoint.jsonl"
    )
    fetcher = fetcher or PubMedMeshFetcher(
        requests_per_second=requests_per_second,
        retries=retries,
    )
    stats = {
        "files_seen": 0,
        "files_updated": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "pmids_seen": 0,
        "pmids_failed": 0,
        "batch_failures": 0,
        "no_pmid_files": 0,
    }
    progress = ProgressPrinter()
    try:
        pending_targets: dict[str, list[ArticleTarget]] = {}
        resolved_mesh_terms: dict[str, list[str]] = {}
        for target in iter_manifest_targets(root, classifications=classifications, checkpoint=checkpoint):
            stats["files_seen"] += 1
            progress.update(
                files_seen=stats["files_seen"],
                updated=stats["files_updated"],
                skipped=stats["files_skipped"],
                failed=stats["files_failed"],
                pmids=stats["pmids_seen"],
                pmid_failed=stats["pmids_failed"],
                batches_failed=stats["batch_failures"],
            )
            if target.pmid is None:
                stats["no_pmid_files"] += 1
                _process_target(target, [], overwrite=overwrite, checkpoint=checkpoint, stats=stats)
                continue

            cached = resolved_mesh_terms.get(target.pmid) or (
                checkpoint.load_pmid_result(target.pmid).mesh_terms
                if checkpoint.load_pmid_result(target.pmid)
                and checkpoint.load_pmid_result(target.pmid).status == "completed"
                else None
            )
            if cached is not None:
                resolved_mesh_terms[target.pmid] = cached
                _process_target(target, cached, overwrite=overwrite, checkpoint=checkpoint, stats=stats)
                continue

            pending_targets.setdefault(target.pmid, []).append(target)
            if len(pending_targets) >= batch_size:
                batch_pmids = list(pending_targets)
                stats["pmids_seen"] += len(batch_pmids)
                batch_result, failed_pmids = _fetch_pmids_with_fallback(
                    fetcher,
                    batch_pmids,
                    stats=stats,
                    checkpoint=checkpoint,
                )
                for pmid in batch_pmids:
                    if pmid in failed_pmids:
                        continue
                    mesh_terms = batch_result.get(pmid, [])
                    resolved_mesh_terms[pmid] = mesh_terms
                    checkpoint.upsert_pmid_result(
                        MeshBackfillRecord(pmid=pmid, mesh_terms=mesh_terms, status="completed")
                    )
                    for target_for_pmid in pending_targets.get(pmid, []):
                        _process_target(
                            target_for_pmid,
                            mesh_terms,
                            overwrite=overwrite,
                            checkpoint=checkpoint,
                            stats=stats,
                        )
                pending_targets.clear()

        if pending_targets:
            batch_pmids = list(pending_targets)
            stats["pmids_seen"] += len(batch_pmids)
            batch_result, failed_pmids = _fetch_pmids_with_fallback(
                fetcher,
                batch_pmids,
                stats=stats,
                checkpoint=checkpoint,
            )
            for pmid in batch_pmids:
                if pmid in failed_pmids:
                    continue
                mesh_terms = batch_result.get(pmid, [])
                resolved_mesh_terms[pmid] = mesh_terms
                checkpoint.upsert_pmid_result(
                    MeshBackfillRecord(pmid=pmid, mesh_terms=mesh_terms, status="completed")
                )
                for target_for_pmid in pending_targets.get(pmid, []):
                    _process_target(
                        target_for_pmid,
                        mesh_terms,
                        overwrite=overwrite,
                        checkpoint=checkpoint,
                        stats=stats,
                    )
        return stats
    finally:
        progress.done()
        if owns_checkpoint:
            checkpoint.close()


def backfill_single_article(
    article_path: str | Path,
    mesh_terms: list[str],
    *,
    overwrite: bool = False,
) -> bool:
    return backfill_article_file(Path(article_path), dedupe_terms(mesh_terms), overwrite=overwrite)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Backfill PMC-RCT article-level MeSH terms")
    parser.add_argument("--data-root", default="data/pmc-rct")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--requests-per-second", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--classifications",
        nargs="+",
        default=["primary_rct"],
    )
    args = parser.parse_args(argv)
    stats = backfill_mesh_terms(
        data_root=args.data_root,
        checkpoint_path=args.checkpoint,
        classifications=tuple(args.classifications),
        batch_size=args.batch_size,
        requests_per_second=args.requests_per_second,
        retries=args.retries,
        overwrite=args.overwrite,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
