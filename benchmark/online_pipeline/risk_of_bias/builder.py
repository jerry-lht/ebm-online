"""Build Risk of Bias benchmark datasets from Cochrane SR sources."""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmark.online_pipeline.shared.building import (
    DEFAULT_SEED,
    RAW_DATA_DIR,
    ROOT,
    select_records,
    sha256_file,
    sha256_json,
    source_manifest,
    stable_order,
)
from benchmark.online_pipeline.shared.jsonl import write_jsonl
from benchmark.online_pipeline.shared.report_utils import write_json


MODULE = "risk_of_bias"
SOURCE = "cochrane_rob1"
SMOKE_SIZE = 5
UPSTREAM_ROB_DATASET = Path("sr-cleaned/data/intermediate/risk_of_bias/rob_dataset")
UPSTREAM_CLEANED_ARTICLES = Path("sr-cleaned/data/final/rob_cleaned_dataset")

ROB1_DOMAINS = [
    "random_sequence_generation",
    "allocation_concealment",
    "blinding_participants_personnel",
    "blinding_outcome_assessment",
    "incomplete_outcome_data",
    "selective_reporting",
    "other_bias",
]

DOMAIN_LABELS = {
    "random_sequence_generation": "Random sequence generation (selection bias)",
    "allocation_concealment": "Allocation concealment (selection bias)",
    "blinding_participants_personnel": "Blinding of participants and personnel (performance bias)",
    "blinding_outcome_assessment": "Blinding of outcome assessment (detection bias)",
    "incomplete_outcome_data": "Incomplete outcome data (attrition bias)",
    "selective_reporting": "Selective reporting (reporting bias)",
    "other_bias": "Other bias",
}

JUDGEMENT_SEVERITY = {"low_risk": 0, "unclear_risk": 1, "high_risk": 2}


def build_dataset(
    *,
    source: str,
    dataset_name: str,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    source_url: str | None = None,
) -> dict[str, Any]:
    if source != SOURCE:
        raise ValueError(f"Unsupported risk_of_bias source: {source}")
    raw_root = Path(source_url) if source_url else RAW_DATA_DIR / MODULE
    if not _raw_snapshot_exists(raw_root):
        freeze_raw_snapshot(raw_root=raw_root)

    records, articles, manifest, analysis = load_source(raw_root=raw_root)
    selected = select_records(records, sample_size=sample_size, seed=seed, module=MODULE)
    selected_article_ids = {article_id for record in selected for article_id in record["article_ids"]}
    selected_articles = {article_id: articles[article_id] for article_id in sorted(selected_article_ids)}
    splits = build_splits(selected, seed=seed)
    dataset_dir = ROOT / MODULE / "datasets" / dataset_name
    write_dataset(
        dataset_dir=dataset_dir,
        records=selected,
        articles=selected_articles,
        splits=splits,
        source=source,
        source_manifest_data=manifest,
        seed=seed,
        sample_size=sample_size,
        source_record_count=analysis["candidate_count"],
        dataset_analysis_data=analysis,
    )
    return {
        "dataset_dir": str(dataset_dir),
        "source_manifest": manifest,
        "build_manifest": json.loads((dataset_dir / "build_manifest.json").read_text(encoding="utf-8")),
        "split_manifest": json.loads((dataset_dir / "split_manifest.json").read_text(encoding="utf-8")),
    }


def freeze_raw_snapshot(*, raw_root: Path = RAW_DATA_DIR / MODULE) -> dict[str, Any]:
    source_reviews_dir = raw_root / "source_reviews"
    study_links_dir = raw_root / "study_links"
    indexes_dir = raw_root / "indexes"
    for directory in (source_reviews_dir, study_links_dir, indexes_dir):
        directory.mkdir(parents=True, exist_ok=True)

    shared_cleaned_articles_dir = _shared_cleaned_articles_dir(raw_root)
    shared_cleaned_articles_dir.mkdir(parents=True, exist_ok=True)
    cleaned_article_sources = _load_cleaned_article_source_index(shared_cleaned_articles_dir)
    upstream_cleaned_article_sources = _load_cleaned_article_source_index(UPSTREAM_CLEANED_ARTICLES)
    inventory_rows: list[dict[str, Any]] = []
    copied_source_reviews: set[Path] = set()
    copied_study_links: set[Path] = set()

    for review_dir in _iter_review_dirs(UPSTREAM_ROB_DATASET):
        cd_number = review_dir.name
        source_review_path = review_dir / "sr" / "source_review.json"
        source_review = _read_json(source_review_path)
        target_review_path = source_reviews_dir / cd_number / "source_review.json"
        target_review_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_review_path, target_review_path)
        copied_source_reviews.add(target_review_path)

        exact_characteristics, normalized_characteristics = _characteristic_index(source_review)
        for study_link_path in sorted((review_dir / "studies").glob("*.json")):
            study_link = _read_json(study_link_path)
            if study_link.get("category") != "included":
                continue
            normalized_study_id = _normalize_study_id(str(study_link.get("study_id") or ""))
            match_method, characteristic = _match_characteristic(
                str(study_link.get("study_id") or ""),
                exact_characteristics,
                normalized_characteristics,
            )
            target_study_link = study_links_dir / cd_number / "studies" / study_link_path.name
            target_study_link.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(study_link_path, target_study_link)
            copied_study_links.add(target_study_link)

            pmid = str(study_link.get("pmid") or "").strip()
            pmcid = str(study_link.get("pmcid") or "").strip()
            doi = str(study_link.get("doi") or "").strip()
            source_article = _resolve_cleaned_article_source(
                source_index=cleaned_article_sources,
                pmid=pmid,
                pmcid=pmcid,
                cd_number=cd_number,
                study_id=str(study_link.get("study_id") or ""),
            )
            source_article_from_shared = source_article is not None
            if source_article is None:
                source_article = _resolve_cleaned_article_source(
                    source_index=upstream_cleaned_article_sources,
                    pmid=pmid,
                    pmcid=pmcid,
                    cd_number=cd_number,
                    study_id=str(study_link.get("study_id") or ""),
                )
            article_id = _article_id(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=str(study_link.get("study_id") or ""))
            has_cleaned_article = source_article is not None
            has_tables = False
            if source_article is not None:
                payload = _select_cleaned_article_payload(
                    _read_json(source_article),
                    pmid=pmid,
                    pmcid=pmcid,
                    cd_number=cd_number,
                    study_id=str(study_link.get("study_id") or ""),
                )
                has_tables = bool((payload.get("tables") or (payload.get("xml_content") or {}).get("tables") or []))
                if not source_article_from_shared:
                    target_shared_article = shared_cleaned_articles_dir / f"{_article_filename(article_id)}.json"
                    normalized_article = _normalize_static_cleaned_article(
                        payload=payload,
                        article_id=article_id,
                        study_id=str(study_link.get("study_id") or ""),
                        pmid=pmid or str(payload.get("pmid") or ""),
                        pmcid=pmcid or str(payload.get("pmcid") or ""),
                        doi=doi or str(payload.get("doi") or ""),
                        raw_record_id=pmcid or pmid or study_link_path.stem,
                    )
                    _write_json(target_shared_article, normalized_article)
                    source_article = target_shared_article
                    source_article_from_shared = True
                    for key in _cleaned_article_keys(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=str(study_link.get("study_id") or "")):
                        cleaned_article_sources.setdefault(key, target_shared_article)
                source_article_file = str(source_article.relative_to(_shared_raw_root(raw_root)))
            else:
                source_article_file = ""

            inventory_rows.append(
                {
                    "cd_number": cd_number,
                    "review_id": str(source_review.get("id") or ""),
                    "study_id": str(study_link.get("study_id") or ""),
                    "study_id_normalized": normalized_study_id,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "doi": doi,
                    "article_id": article_id,
                    "source_review_file": str(target_review_path.relative_to(raw_root)),
                    "study_link_file": str(target_study_link.relative_to(raw_root)),
                    "cleaned_article_file": source_article_file,
                    "match_method": match_method,
                    "has_cleaned_article": str(has_cleaned_article).lower(),
                    "has_tables": str(has_tables).lower(),
                    "has_rob_gold": str(bool(_risk_of_bias_items(characteristic))).lower(),
                    "has_required_benchmark_fields": str(
                        _has_required_benchmark_fields(source_review, characteristic)
                    ).lower(),
                }
            )

    _write_csv(indexes_dir / "rob_source_inventory.csv", inventory_rows)
    summary = {
        "source": SOURCE,
        "upstream_rob_dataset": str(UPSTREAM_ROB_DATASET),
        "shared_cleaned_articles": str(shared_cleaned_articles_dir),
        "source_review_count": len(copied_source_reviews),
        "study_link_count": len(copied_study_links),
        "cleaned_article_count": sum(1 for row in inventory_rows if row.get("has_cleaned_article") == "true"),
        "shared_cleaned_article_file_count": len(list(shared_cleaned_articles_dir.glob("*.json"))),
        "inventory_row_count": len(inventory_rows),
        "note": "Article content is reused from the shared raw_data/cleaned_articles snapshot; XML is not re-cleaned.",
    }
    write_json(indexes_dir / "rob_source_manifest.json", summary)
    return summary


def load_source(*, raw_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    inventory_path = raw_root / "indexes" / "rob_source_inventory.csv"
    rows = _read_csv(inventory_path)
    records: list[dict[str, Any]] = []
    articles: dict[str, dict[str, Any]] = {}
    filter_counts: Counter[str] = Counter()
    raw_domain_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()

    source_reviews: dict[str, dict[str, Any]] = {}
    characteristics_cache: dict[str, tuple[dict[str, list[dict[str, Any]]], list[tuple[str, dict[str, Any]]]]] = {}
    for row in rows:
        candidate_id = f"{row['cd_number']}::{row['study_id']}"
        if row.get("has_cleaned_article") != "true":
            filter_counts["missing_cleaned_article"] += 1
            continue
        source_review_file = str(row.get("source_review_file") or "")
        if source_review_file not in source_reviews:
            source_reviews[source_review_file] = _read_json(raw_root / source_review_file)
            characteristics_cache[source_review_file] = _characteristic_index(source_reviews[source_review_file])
        _, characteristic = _match_characteristic(
            str(row.get("study_id") or ""),
            *characteristics_cache[source_review_file],
        )
        if characteristic is None:
            filter_counts["unmatched_characteristics"] += 1
            continue
        if not _has_required_benchmark_fields(source_reviews[source_review_file], characteristic):
            filter_counts["missing_required_benchmark_fields"] += 1
            continue
        raw_rob = _risk_of_bias_items(characteristic)
        if not raw_rob:
            filter_counts["missing_rob_gold"] += 1
            continue
        normalized_rob, normalization_audit = normalize_risk_of_bias(raw_rob)
        raw_domain_counts.update(normalization_audit["raw_domain_counts"])
        label_counts.update(item["judgement"] for item in normalized_rob)
        if normalization_audit["invalid_judgement_count"]:
            filter_counts["invalid_judgement"] += 1
            continue
        if not normalized_rob:
            filter_counts["unmapped_domains"] += 1
            continue

        article_id = str(row["article_id"])
        article_path = _shared_raw_root(raw_root) / str(row["cleaned_article_file"])
        article_payload = _select_cleaned_article_payload(
            _read_json(article_path),
            pmid=str(row.get("pmid") or ""),
            pmcid=str(row.get("pmcid") or ""),
            cd_number=str(row.get("cd_number") or ""),
            study_id=str(row.get("study_id") or ""),
        )
        article = _normalize_static_cleaned_article(
            payload=article_payload,
            article_id=article_id,
            study_id=str(row.get("study_id") or ""),
            pmid=str(row.get("pmid") or ""),
            pmcid=str(row.get("pmcid") or ""),
            doi=str(row.get("doi") or ""),
            raw_record_id=str(row.get("pmcid") or row.get("pmid") or row.get("study_id") or ""),
        )
        articles.setdefault(article_id, article)
        instance_id = f"risk-of-bias::{row['cd_number']}::{_slug(str(row['study_id']))}"
        records.append(
            {
                "source_id": instance_id,
                "article_ids": [article_id],
                "instance": {
                    "instance_id": instance_id,
                    "study_id": str(row["study_id"]),
                    "review_id": str(row["review_id"]),
                    "cd_number": str(row["cd_number"]),
                    "included_studies": [str(row["study_id"])],
                    "article_ids": [article_id],
                    "source": {
                        "dataset": SOURCE,
                        "source_review_file": source_review_file,
                        "study_link_file": str(row["study_link_file"]),
                        "pmid": str(row.get("pmid") or ""),
                        "pmcid": str(row.get("pmcid") or ""),
                        "doi": str(row.get("doi") or ""),
                    },
                },
                "gold": {
                    "instance_id": instance_id,
                    "study_id": str(row["study_id"]),
                    "risk_of_bias": normalized_rob,
                    "source": {
                        "dataset": SOURCE,
                        "source_review_file": source_review_file,
                        "study_link_file": str(row["study_link_file"]),
                    },
                },
                "strata": {
                    "cd_number": str(row["cd_number"]),
                    "has_tables": str(row.get("has_tables") or "false"),
                },
            }
        )

    manifest = source_manifest(
        source=SOURCE,
        records=records,
        source_url=str(raw_root),
        raw_sha256=_raw_snapshot_sha256(raw_root),
        extra={
            "loader": "local_frozen_sr_characteristics_plus_cleaned_articles",
            "inventory": str(inventory_path),
            "source_review_dir": str(raw_root / "source_reviews"),
            "study_links_dir": str(raw_root / "study_links"),
            "cleaned_articles_dir": str(_shared_cleaned_articles_dir(raw_root)),
            "article_count": len(articles),
            "source_candidate_count": len(rows),
        },
    )
    analysis = {
        "candidate_count": len(rows),
        "record_count": len(records),
        "article_count": len(articles),
        "filter_counts": dict(sorted(filter_counts.items())),
        "raw_domain_counts": dict(sorted(raw_domain_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "table_article_count": sum(1 for article in articles.values() if article.get("tables")),
        "cd_number_counts": dict(sorted(Counter(str((record.get("strata") or {}).get("cd_number") or "") for record in records).items())),
    }
    return records, articles, manifest, analysis


def normalize_risk_of_bias(raw_items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_domain_counts: Counter[str] = Counter()
    invalid_judgement_count = 0
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_domain = _clean_text(str(item.get("bias") or item.get("domain") or ""))
        raw_domain_counts[raw_domain] += 1
        judgement = normalize_judgement(str(item.get("judgement") or ""))
        if judgement is None:
            invalid_judgement_count += 1
            continue
        support_text = _html_fragment_to_text(str(item.get("support") or item.get("support_text") or ""))
        for domain_id in map_domain(raw_domain):
            grouped[domain_id].append(
                {
                    "domain_id": domain_id,
                    "domain": DOMAIN_LABELS[domain_id],
                    "judgement": judgement,
                    "support_text": support_text,
                    "source": item.get("source") or "source_review_characteristics",
                }
            )

    normalized = []
    for domain_id in ROB1_DOMAINS:
        entries = grouped.get(domain_id) or []
        if not entries:
            continue
        normalized.append(_worst_rob_entry(entries))
    return normalized, {
        "raw_domain_counts": dict(raw_domain_counts),
        "invalid_judgement_count": invalid_judgement_count,
    }


def map_domain(value: str) -> list[str]:
    text = value.lower()
    head = text.split(":", 1)[0]
    compact = re.sub(r"\s*\([^)]*\)", "", head).strip()
    if "blinding" in text and "performance" in text and "detection" in text:
        return ["blinding_participants_personnel", "blinding_outcome_assessment"]
    if "random sequence" in text:
        return ["random_sequence_generation"]
    if "allocation conceal" in text:
        return ["allocation_concealment"]
    if "blinding" in text and ("participants and personnel" in text or "performance" in text):
        return ["blinding_participants_personnel"]
    if "blinding" in text and ("outcome assessment" in text or "detection" in text):
        return ["blinding_outcome_assessment"]
    if compact == "blinding":
        return ["blinding_participants_personnel", "blinding_outcome_assessment"]
    if "incomplete outcome" in text or "attrition" in text:
        return ["incomplete_outcome_data"]
    if "selective reporting" in text or "reporting bias" in text:
        return ["selective_reporting"]
    if "other bias" in text:
        return ["other_bias"]
    return []


def normalize_judgement(value: str) -> str | None:
    text = value.lower().strip()
    if "low" in text:
        return "low_risk"
    if "unclear" in text:
        return "unclear_risk"
    if "high" in text:
        return "high_risk"
    return None


def build_splits(records: list[dict[str, Any]], *, seed: str = DEFAULT_SEED) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str((record.get("strata") or {}).get("cd_number") or "unknown")].append(record)
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for cd_number in sorted(grouped):
        items = stable_order(grouped[cd_number], seed=f"{seed}:{MODULE}:split:{cd_number}", module=MODULE)
        dev_count = max(1, round(len(items) * 0.4)) if items else 0
        if len(items) > 1:
            dev_count = min(dev_count, len(items) - 1)
        dev.extend(items[:dev_count])
        test.extend(items[dev_count:])
    dev = sorted(dev, key=lambda record: record["source_id"])
    test = sorted(test, key=lambda record: record["source_id"])
    smoke_pool = dev or test
    smoke = stable_order(smoke_pool, seed=f"{seed}:{MODULE}:smoke", module=MODULE)[: min(SMOKE_SIZE, len(smoke_pool))]
    return {"smoke": sorted(smoke, key=lambda record: record["source_id"]), "dev": dev, "test": test}


def write_dataset(
    *,
    dataset_dir: Path,
    records: list[dict[str, Any]],
    articles: dict[str, dict[str, Any]],
    splits: dict[str, list[dict[str, Any]]],
    source: str,
    source_manifest_data: dict[str, Any],
    seed: str,
    sample_size: int | None,
    source_record_count: int,
    dataset_analysis_data: dict[str, Any],
) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    articles_dir = dataset_dir / "articles"
    if articles_dir.exists():
        shutil.rmtree(articles_dir)
    articles_dir.mkdir(parents=True, exist_ok=True)
    article_index = []
    for article_id, article in articles.items():
        article_path = articles_dir / f"{_safe_filename(article_id)}.json"
        _write_json(article_path, article)
        meta = article.get("metadata") or {}
        article_index.append(
            {
                "article_id": article_id,
                "study_id": str(article.get("study_id") or ""),
                "pmid": meta.get("pmid") or "",
                "pmcid": meta.get("pmc_id") or "",
                "doi": meta.get("doi") or "",
                "article_path": str(article_path.relative_to(dataset_dir)),
                "cleaned_article_sha256": sha256_file(article_path),
            }
        )

    _write_records(dataset_dir, records)
    write_jsonl(dataset_dir / "article_index.jsonl", article_index, sort_keys=False)
    for split_name, split_records in splits.items():
        split_dir = dataset_dir / "splits" / split_name
        _write_records(split_dir, split_records)
        split_article_ids = {article_id for record in split_records for article_id in record["article_ids"]}
        write_jsonl(
            split_dir / "article_index.jsonl",
            [row for row in article_index if row["article_id"] in split_article_ids],
            sort_keys=False,
        )

    split_manifest = {
        "builder_version": "online-pipeline-builder-v2",
        "seed": seed,
        "module": MODULE,
        "dataset_name": dataset_dir.name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "split_strategy": "seeded_stratified_by_cd_number_dev40_test60_smoke5_from_dev",
        "splits": {
            split_name: {
                "count": len(split_records),
                "instance_ids": [record["instance"]["instance_id"] for record in split_records],
            }
            for split_name, split_records in {"all": records, **splits}.items()
        },
    }
    build_manifest = {
        "builder_version": "online-pipeline-builder-v2",
        "module": MODULE,
        "dataset_name": dataset_dir.name,
        "source": source,
        "sample_size": sample_size,
        "source_record_count": source_record_count,
        "selected_count": len(records),
        "seed": seed,
        "source_manifest_sha256": sha256_json(source_manifest_data),
        "split_manifest_sha256": sha256_json(split_manifest),
    }
    write_json(dataset_dir / "source_manifest.json", source_manifest_data)
    write_json(dataset_dir / "split_manifest.json", split_manifest)
    write_json(dataset_dir / "build_manifest.json", build_manifest)
    write_json(dataset_dir / "dataset_analysis.json", dataset_analysis_data)
    _write_schema(dataset_dir / "schema.md")


def _normalize_static_cleaned_article(
    *,
    payload: dict[str, Any],
    article_id: str,
    study_id: str,
    pmid: str,
    pmcid: str,
    doi: str,
    raw_record_id: str,
) -> dict[str, Any]:
    xml_content = payload.get("xml_content") or {}
    sections = xml_content.get("sections") or []
    tables = payload.get("tables") or xml_content.get("tables") or []
    normalized_sections = [
        {
            "title": str(section.get("section") or section.get("title") or "Section"),
            "section_id": str(section.get("section_id") or f"s{index}"),
            "text": str(section.get("text") or ""),
        }
        for index, section in enumerate(sections, start=1)
        if isinstance(section, dict) and str(section.get("text") or "").strip()
    ]
    normalized_tables = [_normalize_table(table, index=index) for index, table in enumerate(tables, start=1) if isinstance(table, dict)]
    title = (
        payload.get("title")
        or (payload.get("metadata") or {}).get("title")
        or _title_from_sections(normalized_sections)
        or ""
    )
    return {
        "article_id": article_id,
        "study_id": study_id,
        "metadata": {
            "title": str(title),
            "pmid": pmid or payload.get("pmid") or (payload.get("metadata") or {}).get("pmid") or None,
            "pmc_id": pmcid or payload.get("pmcid") or (payload.get("metadata") or {}).get("pmc_id") or None,
            "source_type": "static cleaned article",
            "publication_year": payload.get("publication_year") or None,
            "mesh_terms": payload.get("mesh_terms") if isinstance(payload.get("mesh_terms"), list) else [],
            "doi": doi or payload.get("doi") or (payload.get("metadata") or {}).get("doi") or None,
        },
        "xml_content": {"sections": normalized_sections},
        "tables": normalized_tables,
        "source": {
            "database": "sr_cleaned_static_article",
            "retrieval_rank": None,
            "retrieval_score": None,
            "raw_source_url": None,
            "raw_record_id": raw_record_id,
        },
    }


def _normalize_table(table: dict[str, Any], *, index: int) -> dict[str, Any]:
    section_path = table.get("section_path") if isinstance(table.get("section_path"), list) else []
    raw_xml = str(table.get("raw_xml") or "")
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    if raw_xml and not rows:
        rows = [{"_raw_xml": raw_xml, "_section_path": " > ".join(str(part) for part in section_path)}]
    caption = str(table.get("caption") or " > ".join(str(part) for part in section_path) or f"Table {index}")
    return {
        "table_id": str(table.get("table_id") or f"t{index}"),
        "caption": caption,
        "section_path": [str(part) for part in section_path],
        "rows": rows,
        "raw_xml": raw_xml,
    }


def _characteristic_index(source_review: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[tuple[str, dict[str, Any]]]]:
    included = ((source_review.get("characteristics_of_studies") or {}).get("included") or [])
    exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized_items: list[tuple[str, dict[str, Any]]] = []
    for item in included:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_study_id(str(item.get("study_id") or ""))
        if not normalized:
            continue
        exact[normalized].append(item)
        normalized_items.append((normalized, item))
    return exact, normalized_items


def _characteristics_by_study(source_review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exact, normalized_items = _characteristic_index(source_review)
    result: dict[str, dict[str, Any]] = {}
    for normalized, items in exact.items():
        if len(items) == 1:
            result[normalized] = items[0]
    for normalized, item in normalized_items:
        result.setdefault(normalized, item)
    return result


def _match_characteristic(
    study_id: str,
    exact: dict[str, list[dict[str, Any]]],
    normalized_items: list[tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, Any] | None]:
    normalized = _normalize_study_id(study_id)
    exact_candidates = exact.get(normalized, [])
    if len(exact_candidates) == 1:
        return "exact_normalized", exact_candidates[0]
    if len(exact_candidates) > 1:
        return "unmatched", None

    suffix_candidates = [
        item for item_normalized, item in normalized_items if item_normalized.endswith(normalized)
    ]
    if len(suffix_candidates) == 1:
        return "suffix_normalized", suffix_candidates[0]
    return "unmatched", None


def _has_required_benchmark_fields(source_review: dict[str, Any], characteristic: dict[str, Any] | None) -> bool:
    if not isinstance(characteristic, dict):
        return False
    sr_pico = source_review.get("pico") if isinstance(source_review.get("pico"), dict) else {}
    for key in ("population", "intervention", "comparison", "outcome"):
        if _is_empty(sr_pico.get(key)):
            return False
    for key in ("participants", "interventions", "outcomes", "notes"):
        if _is_empty(characteristic.get(key)):
            return False
    return True


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _risk_of_bias_items(characteristic: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(characteristic, dict):
        return []
    items = characteristic.get("risk_of_bias")
    return items if isinstance(items, list) else []


def _load_cleaned_article_source_index(cleaned_articles_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not cleaned_articles_dir.exists():
        return index
    for path in sorted(cleaned_articles_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            payload = _read_json(path)
        except Exception:
            continue
        payloads = payload if isinstance(payload, list) else [payload]
        for item in payloads:
            if not isinstance(item, dict):
                continue
            pmid = str(item.get("pmid") or (item.get("metadata") or {}).get("pmid") or "").strip()
            pmcid = str(item.get("pmcid") or (item.get("metadata") or {}).get("pmc_id") or "").strip()
            cd_number = str(item.get("cd_number") or "").strip()
            study_id = str(item.get("study_id") or "").strip()
            for key in _cleaned_article_keys(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=study_id):
                index.setdefault(key, path)
    return index


def _select_cleaned_article_payload(
    value: Any,
    *,
    pmid: str,
    pmcid: str,
    cd_number: str,
    study_id: str,
) -> dict[str, Any]:
    payloads = value if isinstance(value, list) else [value]
    candidates = [payload for payload in payloads if isinstance(payload, dict)]
    if not candidates:
        return {}
    wanted_keys = set(_cleaned_article_keys(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=study_id))
    for payload in candidates:
        payload_keys = set(
            _cleaned_article_keys(
                pmid=str(payload.get("pmid") or (payload.get("metadata") or {}).get("pmid") or ""),
                pmcid=str(payload.get("pmcid") or (payload.get("metadata") or {}).get("pmc_id") or ""),
                cd_number=str(payload.get("cd_number") or ""),
                study_id=str(payload.get("study_id") or ""),
            )
        )
        if wanted_keys & payload_keys:
            return payload
    return candidates[0]


def _resolve_cleaned_article_source(
    *,
    source_index: dict[str, Path],
    pmid: str,
    pmcid: str,
    cd_number: str,
    study_id: str,
) -> Path | None:
    for key in _cleaned_article_keys(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=study_id):
        if key in source_index:
            return source_index[key]
    return None


def _cleaned_article_keys(*, pmid: str, pmcid: str, cd_number: str, study_id: str) -> list[str]:
    keys = []
    if pmid and not pmid.startswith("STUDYREF::"):
        keys.append(f"pmid:{pmid}")
    if pmcid:
        keys.append(f"pmcid:{pmcid.upper()}")
    if cd_number and study_id:
        keys.append(f"study:{cd_number}:{_normalize_study_id(study_id)}")
    return keys


def _iter_review_dirs(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Missing RoB source directory: {input_dir}")
    return sorted(path for path in input_dir.iterdir() if path.is_dir() and (path / "sr" / "source_review.json").exists())


def _write_records(directory: Path, records: list[dict[str, Any]]) -> None:
    write_jsonl(directory / "instances.jsonl", [record["instance"] for record in records], sort_keys=False)
    write_jsonl(directory / "gold.jsonl", [record["gold"] for record in records], sort_keys=False)


def _write_schema(path: Path) -> None:
    path.write_text(
        "# risk_of_bias benchmark dataset\n\n"
        "Generated by `benchmark/online_pipeline/benchmark.py build`.\n\n"
        "- `instances.jsonl`: RoB inputs with `article_ids`, no embedded article text or gold\n"
        "- `gold.jsonl`: fixed seven-domain RoB 1 gold labels from SR characteristics\n"
        "- `article_index.jsonl`: article id to de-duplicated cleaned article file\n"
        "- `articles/*.json`: cleaned article fixtures, including sections and tables\n"
        "- `source_manifest.json`: frozen raw source metadata\n"
        "- `build_manifest.json`: reproducible build metadata\n"
        "- `split_manifest.json`: split IDs and strategy\n",
        encoding="utf-8",
    )


def _raw_snapshot_exists(raw_root: Path) -> bool:
    manifest_path = raw_root / "indexes" / "rob_source_manifest.json"
    if not (
        (raw_root / "source_reviews").is_dir()
        and (raw_root / "study_links").is_dir()
        and (raw_root / "indexes" / "rob_source_inventory.csv").exists()
        and manifest_path.exists()
    ):
        return False
    try:
        manifest = _read_json(manifest_path)
    except Exception:
        return False
    inventory_path = raw_root / "indexes" / "rob_source_inventory.csv"
    try:
        with inventory_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
    except Exception:
        return False
    return (
        bool(manifest.get("shared_cleaned_articles"))
        and not (raw_root / "cleaned_articles").exists()
        and "has_required_benchmark_fields" in header
    )


def _raw_snapshot_sha256(raw_root: Path) -> str:
    values = []
    for path in sorted((raw_root / "indexes").glob("*")):
        if path.is_file():
            values.append((str(path.relative_to(raw_root)), sha256_file(path)))
    return sha256_json(values)


def _shared_raw_root(raw_root: Path) -> Path:
    return raw_root.parent if raw_root.name == MODULE else RAW_DATA_DIR


def _shared_cleaned_articles_dir(raw_root: Path) -> Path:
    return _shared_raw_root(raw_root) / "cleaned_articles"


def _worst_rob_entry(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return max(entries, key=lambda item: JUDGEMENT_SEVERITY.get(str(item.get("judgement") or ""), -1))


def _normalize_study_id(value: str) -> str:
    text = unicodedata.normalize("NFKC", (value or "").strip()).lower()
    text = text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-")
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return re.sub(r"\s+", " ", text)


def _clean_text(value: str) -> str:
    text = html.unescape(value or "")
    return re.sub(r"\s+", " ", text).strip()


def _html_fragment_to_text(value: str) -> str:
    text = value or ""
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*p\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*li\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _article_id(*, pmid: str, pmcid: str, cd_number: str, study_id: str) -> str:
    if pmcid:
        return f"pmc::{pmcid.upper()}"
    if pmid:
        return f"pmid::{pmid}"
    return f"study::{cd_number}::{_slug(study_id)}"


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "item"


def _article_filename(article_id: str) -> str:
    return article_id.replace("::", "__").replace(":", "_")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")


def _title_from_sections(sections: list[dict[str, Any]]) -> str:
    for section in sections:
        title = str(section.get("title") or "").strip()
        if title and title.lower() not in {"front", "abstract", "introduction"}:
            return title
    return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "cd_number",
        "review_id",
        "study_id",
        "study_id_normalized",
        "pmid",
        "pmcid",
        "doi",
        "article_id",
        "source_review_file",
        "study_link_file",
        "cleaned_article_file",
        "match_method",
        "has_cleaned_article",
        "has_tables",
        "has_rob_gold",
        "has_required_benchmark_fields",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
