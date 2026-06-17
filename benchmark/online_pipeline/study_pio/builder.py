"""Build Study PIO benchmark datasets from frozen Cochrane sources."""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
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
    write_json,
)
from benchmark.online_pipeline.shared.jsonl import write_jsonl
from benchmark.online_pipeline.shared.xml_cleaning import extract_xml_content


MODULE = "study_pio"
SOURCE = "cochrane_study_pio"
SMOKE_SIZE = 5
UPSTREAM_CLEANED_SR = Path("sr-cleaned/code/external/cleaned-pico/cleaned_sr")
UPSTREAM_FULL_TEXT_INDEX = Path(
    "sr-cleaned/data/intermediate/study_level_meta_analysis/task1/intermediate/study_cleaned_full_text_index.csv"
)
UPSTREAM_PMC_XML = Path("sr-cleaned/data/raw/full_text_xml/pmc_xml")
UPSTREAM_CLEANED_ARTICLES = Path("sr-cleaned/data/final/rob_cleaned_dataset")


def build_dataset(
    *,
    source: str,
    dataset_name: str,
    sample_size: int | None = None,
    seed: str = DEFAULT_SEED,
    source_url: str | None = None,
) -> dict[str, Any]:
    if source != SOURCE:
        raise ValueError(f"Unsupported study_pio source: {source}")
    raw_root = Path(source_url) if source_url else RAW_DATA_DIR
    if not _raw_snapshot_exists(raw_root):
        freeze_raw_snapshot(raw_root=raw_root)

    records, articles, manifest = load_source(raw_root=raw_root)
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
        source_record_count=len(records),
    )
    return {
        "dataset_dir": str(dataset_dir),
        "source_manifest": manifest,
        "build_manifest": json.loads((dataset_dir / "build_manifest.json").read_text(encoding="utf-8")),
        "split_manifest": json.loads((dataset_dir / "split_manifest.json").read_text(encoding="utf-8")),
    }


def freeze_raw_snapshot(*, raw_root: Path = RAW_DATA_DIR) -> dict[str, Any]:
    cleaned_sr_dir = raw_root / "cleaned_sr"
    cleaned_articles_dir = raw_root / "cleaned_articles"
    pmc_xml_dir = raw_root / "pmc_xml"
    indexes_dir = raw_root / "indexes"
    cleaned_sr_dir.mkdir(parents=True, exist_ok=True)
    cleaned_articles_dir.mkdir(parents=True, exist_ok=True)
    pmc_xml_dir.mkdir(parents=True, exist_ok=True)
    indexes_dir.mkdir(parents=True, exist_ok=True)

    characteristic_by_key = _load_characteristics_from_upstream()
    cleaned_article_sources = _load_cleaned_article_source_index(UPSTREAM_CLEANED_ARTICLES)
    usable_rows: list[dict[str, str]] = []
    for row in _read_csv(UPSTREAM_FULL_TEXT_INDEX):
        key = (row.get("cd_number") or "", row.get("study_id") or "")
        pmcid = row.get("pmcid") or ""
        xml_path = UPSTREAM_PMC_XML / f"{pmcid}.xml"
        if row.get("cleaned_full_text_available") == "true" and key in characteristic_by_key and pmcid and xml_path.exists():
            usable_rows.append(row)

    copied_cleaned_sr: set[Path] = set()
    copied_xml: set[Path] = set()
    copied_cleaned_articles: set[Path] = set()
    inventory_rows: list[dict[str, Any]] = []
    for row in usable_rows:
        key = (row["cd_number"], row["study_id"])
        sr_path = characteristic_by_key[key]["cleaned_sr_path"]
        xml_path = UPSTREAM_PMC_XML / f"{row['pmcid']}.xml"
        article_id = f"pmc::{row['pmcid']}"
        target_sr = cleaned_sr_dir / sr_path.name
        target_xml = pmc_xml_dir / xml_path.name
        target_article = cleaned_articles_dir / f"{_article_filename(article_id)}.json"
        if target_sr not in copied_cleaned_sr:
            shutil.copy2(sr_path, target_sr)
            copied_cleaned_sr.add(target_sr)
        if target_xml not in copied_xml:
            shutil.copy2(xml_path, target_xml)
            copied_xml.add(target_xml)
        if target_article not in copied_cleaned_articles:
            source_article = _resolve_cleaned_article_source(row=row, source_index=cleaned_article_sources)
            if source_article is not None:
                payload = _normalize_static_cleaned_article(
                    payload=json.loads(source_article.read_text(encoding="utf-8")),
                    article_id=article_id,
                    study_id=row["study_id"],
                    pmcid=row["pmcid"],
                    source_kind="sr_cleaned_static",
                    raw_record_id=row["pmcid"],
                )
            else:
                payload = build_article_from_xml(article_id=article_id, study_id=row["study_id"], xml_path=xml_path, pmcid=row["pmcid"])
                payload["source"]["database"] = "PMC XML reference-cleaned snapshot"
            _write_article_json(target_article, payload)
            copied_cleaned_articles.add(target_article)
        inventory_rows.append(
            {
                "cd_number": row["cd_number"],
                "review_id": row["review_id"],
                "study_id": row["study_id"],
                "study_reference_id": row.get("study_reference_id") or "",
                "pmcid": row["pmcid"],
                "cleaned_sr_file": target_sr.name,
                "cleaned_article_file": target_article.name,
                "pmc_xml_file": target_xml.name,
            }
        )

    _write_csv(indexes_dir / "study_cleaned_full_text_index.csv", usable_rows)
    _write_csv(indexes_dir / "study_pio_source_inventory.csv", inventory_rows)
    summary = {
        "source": SOURCE,
        "usable_record_count": len(usable_rows),
        "cleaned_sr_file_count": len(copied_cleaned_sr),
        "cleaned_article_file_count": len(copied_cleaned_articles),
        "pmc_xml_file_count": len(copied_xml),
        "cleaned_article_source": str(UPSTREAM_CLEANED_ARTICLES),
        "upstream_cleaned_sr": str(UPSTREAM_CLEANED_SR),
        "upstream_full_text_index": str(UPSTREAM_FULL_TEXT_INDEX),
        "upstream_pmc_xml": str(UPSTREAM_PMC_XML),
    }
    write_json(indexes_dir / "study_pio_source_manifest.json", summary)
    return summary


def load_source(*, raw_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    inventory_path = raw_root / "indexes" / "study_pio_source_inventory.csv"
    cleaned_sr_dir = raw_root / "cleaned_sr"
    cleaned_articles_dir = raw_root / "cleaned_articles"
    characteristic_by_key = _load_characteristics(cleaned_sr_dir)
    records: list[dict[str, Any]] = []
    articles: dict[str, dict[str, Any]] = {}

    for row in _read_csv(inventory_path):
        key = (row["cd_number"], row["study_id"])
        characteristic = characteristic_by_key[key]
        pmcid = row["pmcid"]
        article_id = f"pmc::{pmcid}"
        article_path = cleaned_articles_dir / row["cleaned_article_file"]
        if article_id not in articles:
            articles[article_id] = json.loads(article_path.read_text(encoding="utf-8"))
        instance_id = f"study-pio::{row['cd_number']}::{_slug(row['study_id'])}"
        question_pico = characteristic["question_pico"]
        records.append(
            {
                "source_id": instance_id,
                "source_split": None,
                "article_ids": [article_id],
                "instance": {
                    "instance_id": instance_id,
                    "review_id": row["review_id"],
                    "cd_number": row["cd_number"],
                    "study_id": row["study_id"],
                    "question_pico": {
                        "P": question_pico.get("P", []),
                        "I": question_pico.get("I", []),
                        "C": question_pico.get("C", []),
                        "O": question_pico.get("O", []),
                    },
                    "included_studies": [row["study_id"]],
                    "article_ids": [article_id],
                    "source": {
                        "dataset": SOURCE,
                        "cleaned_sr_file": row["cleaned_sr_file"],
                        "pmcid": pmcid,
                    },
                },
                "gold": {
                    "instance_id": instance_id,
                    "study_id": row["study_id"],
                    "population": characteristic["participants"],
                    "intervention_comparator": characteristic["interventions"],
                    "outcomes": characteristic["outcomes"],
                    "source": {
                        "dataset": SOURCE,
                        "cleaned_sr_file": row["cleaned_sr_file"],
                        "pmcid": pmcid,
                    },
                },
                "strata": {
                    "cd_number": row["cd_number"],
                    "has_population": bool(characteristic["participants"]),
                    "has_intervention_comparator": bool(characteristic["interventions"]),
                    "has_outcomes": bool(characteristic["outcomes"]),
                },
            }
        )

    manifest = source_manifest(
        source=SOURCE,
        records=records,
        source_url=str(raw_root),
        raw_sha256=_raw_snapshot_sha256(raw_root),
        extra={
            "loader": "local_frozen_cochrane_study_pio",
            "cleaned_sr_dir": str(cleaned_sr_dir),
            "cleaned_articles_dir": str(cleaned_articles_dir),
            "inventory": str(inventory_path),
            "article_count": len(articles),
        },
    )
    return records, articles, manifest


def build_article_from_xml(*, article_id: str, study_id: str, xml_path: Path, pmcid: str) -> dict[str, Any]:
    cleaned = extract_xml_content(xml_path)
    meta = cleaned["article_meta"]
    return _normalize_static_cleaned_article(
        payload={
            "study_id": study_id,
            "pmid": meta.get("pmid") or None,
            "pmcid": pmcid,
            "doi": meta.get("doi") or None,
            "xml_content": {
                "sections": cleaned.get("sections") or [],
                "tables": cleaned.get("tables") or [],
            },
            "title": meta.get("title") or "",
            "cleaning": {
                "paragraph_count": cleaned.get("paragraph_count"),
                "section_count": cleaned.get("section_count"),
                "table_count": cleaned.get("table_count"),
            },
        },
        article_id=article_id,
        study_id=study_id,
        pmcid=pmcid,
        source_kind="reference_xml_cleaner",
        raw_record_id=pmcid,
    )


def _normalize_static_cleaned_article(
    *,
    payload: dict[str, Any],
    article_id: str,
    study_id: str,
    pmcid: str,
    source_kind: str,
    raw_record_id: str,
) -> dict[str, Any]:
    xml_content = payload.get("xml_content") or {}
    sections = xml_content.get("sections") or []
    tables = xml_content.get("tables") or []
    title = (
        payload.get("title")
        or (payload.get("metadata") or {}).get("title")
        or _title_from_sections(sections)
        or ""
    )
    normalized_sections = [
        {
            "title": str(section.get("section") or section.get("title") or "Section"),
            "section_id": str(section.get("section_id") or f"s{index}"),
            "text": str(section.get("text") or ""),
        }
        for index, section in enumerate(sections, start=1)
        if isinstance(section, dict) and str(section.get("text") or "").strip()
    ]
    normalized_tables = [
        {
            "caption": str(table.get("caption") or " ".join(table.get("section_path") or [])),
            "table_id": str(table.get("table_id") or f"t{index}"),
            "rows": table.get("rows") if isinstance(table.get("rows"), list) else [],
            "raw_xml": str(table.get("raw_xml") or ""),
        }
        for index, table in enumerate(tables, start=1)
        if isinstance(table, dict)
    ]
    return {
        "article_id": article_id,
        "study_id": study_id,
        "metadata": {
            "title": title,
            "pmid": payload.get("pmid") or (payload.get("metadata") or {}).get("pmid") or None,
            "pmc_id": pmcid,
            "source_type": "static cleaned article",
            "publication_year": payload.get("publication_year") or None,
            "mesh_terms": payload.get("mesh_terms") if isinstance(payload.get("mesh_terms"), list) else [],
            "doi": payload.get("doi") or (payload.get("metadata") or {}).get("doi") or None,
        },
        "xml_content": {"sections": normalized_sections},
        "tables": normalized_tables,
        "source": {
            "database": source_kind,
            "retrieval_rank": None,
            "retrieval_score": None,
            "raw_source_url": None,
            "raw_record_id": raw_record_id,
        },
        "cleaning": {
            "paragraph_count": (payload.get("cleaning") or {}).get("paragraph_count"),
            "section_count": len(normalized_sections),
            "table_count": len(normalized_tables),
        },
    }


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
) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    articles_dir = dataset_dir / "articles"
    if articles_dir.exists():
        shutil.rmtree(articles_dir)
    articles_dir.mkdir(parents=True, exist_ok=True)
    article_index = []
    for article_id, article in articles.items():
        article_path = articles_dir / f"{_article_filename(article_id)}.json"
        _write_article_json(article_path, article)
        article_index.append(
            {
                "article_id": article_id,
                "study_id": article["study_id"],
                "pmcid": article["metadata"]["pmc_id"],
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
    write_json(dataset_dir / "dataset_analysis.json", dataset_analysis(records, articles))
    _write_schema(dataset_dir / "schema.md")


def build_splits(records: list[dict[str, Any]], *, seed: str = DEFAULT_SEED) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str((record.get("strata") or {}).get("cd_number") or "unknown")].append(record)
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for cd_number in sorted(grouped):
        items = stable_order(grouped[cd_number], seed=f"{seed}:study_pio:split:{cd_number}", module=MODULE)
        dev_count = max(1, round(len(items) * 0.4)) if items else 0
        if len(items) > 1:
            dev_count = min(dev_count, len(items) - 1)
        dev.extend(items[:dev_count])
        test.extend(items[dev_count:])
    dev = sorted(dev, key=lambda record: record["source_id"])
    test = sorted(test, key=lambda record: record["source_id"])
    smoke = stable_order(dev or test, seed=f"{seed}:study_pio:smoke", module=MODULE)[: min(SMOKE_SIZE, len(dev or test))]
    return {"smoke": sorted(smoke, key=lambda record: record["source_id"]), "dev": dev, "test": test}


def dataset_analysis(records: list[dict[str, Any]], articles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cd_counts: dict[str, int] = defaultdict(int)
    for record in records:
        cd_counts[str((record.get("strata") or {}).get("cd_number") or "unknown")] += 1
    return {
        "record_count": len(records),
        "article_count": len(articles),
        "cd_number_counts": dict(sorted(cd_counts.items())),
    }


def _load_characteristics_from_upstream() -> dict[tuple[str, str], dict[str, Any]]:
    return _load_characteristics(UPSTREAM_CLEANED_SR)


def _load_characteristics(cleaned_sr_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(cleaned_sr_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        cd_number = str(payload.get("cd_number") or path.name.split("_")[0])
        pico = payload.get("pico") or {}
        question_pico = {
            "P": _list_field(pico.get("population")),
            "I": _list_field(pico.get("intervention")),
            "C": _list_field(pico.get("comparison")),
            "O": _list_field(pico.get("outcome")),
        }
        for study in ((payload.get("characteristics_of_studies") or {}).get("included") or []):
            study_id = str(study.get("study_id") or "").strip()
            participants = str(study.get("participants") or "").strip()
            interventions = str(study.get("interventions") or "").strip()
            outcomes = str(study.get("outcomes") or "").strip()
            if not study_id or not participants or not interventions or not outcomes:
                continue
            by_key[(cd_number, study_id)] = {
                "cleaned_sr_path": path,
                "question_pico": question_pico,
                "participants": participants,
                "interventions": interventions,
                "outcomes": outcomes,
            }
    return by_key


def _load_cleaned_article_source_index(cleaned_articles_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    if not cleaned_articles_dir.exists():
        return index
    for path in sorted(cleaned_articles_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        pmid = str(payload.get("pmid") or (payload.get("metadata") or {}).get("pmid") or "").strip()
        pmcid = str(payload.get("pmcid") or (payload.get("metadata") or {}).get("pmc_id") or "").strip()
        cd_number = str(payload.get("cd_number") or "").strip()
        study_id = str(payload.get("study_id") or "").strip()
        for key in _cleaned_article_keys(pmid=pmid, pmcid=pmcid, cd_number=cd_number, study_id=study_id):
            index.setdefault(key, path)
    return index


def _resolve_cleaned_article_source(*, row: dict[str, str], source_index: dict[str, Path]) -> Path | None:
    for key in _cleaned_article_keys(
        pmid=str(row.get("study_reference_id") or ""),
        pmcid=str(row.get("pmcid") or ""),
        cd_number=str(row.get("cd_number") or ""),
        study_id=str(row.get("study_id") or ""),
    ):
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
        keys.append(f"study:{cd_number}:{study_id}")
    return keys


def _write_records(directory: Path, records: list[dict[str, Any]]) -> None:
    write_jsonl(directory / "instances.jsonl", [record["instance"] for record in records], sort_keys=False)
    write_jsonl(directory / "gold.jsonl", [record["gold"] for record in records], sort_keys=False)


def _write_schema(path: Path) -> None:
    path.write_text(
        "# study_pio benchmark dataset\n\n"
        "Generated by `benchmark/online_pipeline/benchmark.py build`.\n\n"
        "- `instances.jsonl`: Study PIO inputs with `article_ids`, no embedded article text\n"
        "- `gold.jsonl`: population, intervention/comparator, and outcomes gold text\n"
        "- `article_index.jsonl`: article id to de-duplicated cleaned article file\n"
        "- `articles/*.json`: cleaned article fixtures\n"
        "- `source_manifest.json`: frozen raw source metadata\n"
        "- `build_manifest.json`: reproducible build metadata\n"
        "- `split_manifest.json`: split IDs and strategy\n",
        encoding="utf-8",
    )


def _write_article_json(path: Path, article: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(article, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _raw_snapshot_exists(raw_root: Path) -> bool:
    return (
        (raw_root / "cleaned_sr").is_dir()
        and (raw_root / "cleaned_articles").is_dir()
        and (raw_root / "indexes" / "study_pio_source_inventory.csv").exists()
    )


def _raw_snapshot_sha256(raw_root: Path) -> str:
    values = []
    for path in sorted((raw_root / "indexes").glob("*")):
        if path.is_file():
            values.append((str(path.relative_to(raw_root)), sha256_file(path)))
    for path in sorted((raw_root / "cleaned_articles").glob("*.json")):
        if path.is_file():
            values.append((str(path.relative_to(raw_root)), sha256_file(path)))
    return sha256_json(values)


def _article_filename(article_id: str) -> str:
    return article_id.replace("::", "__").replace(":", "_")


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value).strip("-")


def _list_field(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _title_from_sections(sections: Any) -> str:
    if not isinstance(sections, list):
        return ""
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("section") or section.get("title") or "").strip()
        if title and title.lower() not in {"front", "abstract", "introduction"}:
            return title
    return ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
