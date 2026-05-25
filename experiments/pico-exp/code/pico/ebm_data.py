"""Strict EBM-NLP loader for starting-span labels and token offsets."""

from __future__ import annotations

import csv
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pico.conversions import (
    binary_token_labels_to_spans,
    describe_overlap_conflicts,
    spans_to_blurb_bio_labels,
    spans_to_multi_label_token_coverage,
)
from pico.io_utils import write_document_examples, write_json, write_jsonl
from pico.offsets import OffsetAlignmentError, align_token_offsets
from pico.schemas import DocumentExample, PICO_LABELS

LABEL_DIRECTORIES: dict[str, str] = {
    "P": "participants",
    "I": "interventions",
    "O": "outcomes",
}

SPLIT_LABEL_SUBDIRS: dict[str, str] = {
    "train": "train",
    "test": "test/gold",
}


class EBMDataError(ValueError):
    """Raised when the official EBM-NLP archive violates Phase 2 assumptions."""


@dataclass(frozen=True)
class DocumentManifestRow:
    doc_id: str
    split: str
    token_count: int
    p_span_count: int
    i_span_count: int
    o_span_count: int
    total_span_count: int
    has_overlap: bool
    overlap_token_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "split": self.split,
            "token_count": self.token_count,
            "p_span_count": self.p_span_count,
            "i_span_count": self.i_span_count,
            "o_span_count": self.o_span_count,
            "total_span_count": self.total_span_count,
            "has_overlap": self.has_overlap,
            "overlap_token_count": self.overlap_token_count,
        }


def parse_binary_ann(content: str, source_path: str = "<ann>") -> list[int]:
    """Parse newline-separated EBM-NLP binary token labels."""
    labels: list[int] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        value = line.strip()
        if value == "":
            continue
        if value not in {"0", "1"}:
            raise EBMDataError(
                f"Invalid annotation value {value!r} at {source_path}:{line_number}; expected 0 or 1"
            )
        labels.append(int(value))
    return labels


def count_positive_runs(labels: list[int]) -> int:
    """Count contiguous positive runs in a binary token-label sequence."""
    count = 0
    previous = 0
    for label in labels:
        if label == 1 and previous == 0:
            count += 1
        previous = label
    return count


def has_label_overlap(label_sets: dict[str, list[int]]) -> bool:
    return count_overlap_tokens(label_sets) > 0


def count_overlap_tokens(label_sets: dict[str, list[int]]) -> int:
    if not label_sets:
        return 0
    token_count = len(next(iter(label_sets.values())))
    count = 0
    for index in range(token_count):
        if sum(labels[index] for labels in label_sets.values()) > 1:
            count += 1
    return count


def build_document_manifest_row(
    doc_id: str,
    split: str,
    token_count: int,
    label_sets: dict[str, list[int]],
) -> DocumentManifestRow:
    p_count = count_positive_runs(label_sets["P"])
    i_count = count_positive_runs(label_sets["I"])
    o_count = count_positive_runs(label_sets["O"])
    return DocumentManifestRow(
        doc_id=doc_id,
        split=split,
        token_count=token_count,
        p_span_count=p_count,
        i_span_count=i_count,
        o_span_count=o_count,
        total_span_count=p_count + i_count + o_count,
        has_overlap=has_label_overlap(label_sets),
        overlap_token_count=count_overlap_tokens(label_sets),
    )


def build_split_summary_rows(rows: list[DocumentManifestRow]) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for split in ("train", "test"):
        split_rows = [row for row in rows if row.split == split]
        summary_rows.append(
            {
                "split": split,
                "doc_count": len(split_rows),
                "token_count": sum(row.token_count for row in split_rows),
                "p_span_count": sum(row.p_span_count for row in split_rows),
                "i_span_count": sum(row.i_span_count for row in split_rows),
                "o_span_count": sum(row.o_span_count for row in split_rows),
                "overlap_doc_count": sum(1 for row in split_rows if row.has_overlap),
                "overlap_token_count": sum(row.overlap_token_count for row in split_rows),
            }
        )
    return summary_rows


def prepare_ebm_nlp_data(ebm_tar: str | Path, output_dir: str | Path, force: bool = False) -> dict[str, Any]:
    output_path = Path(output_dir)
    paths = {
        "train_examples": output_path / "train.examples.jsonl",
        "test_examples": output_path / "test.examples.jsonl",
        "data_summary": output_path / "data_summary.json",
        "offset_failures": output_path / "offset_failures.jsonl",
        "document_manifest": output_path / "manifests" / "document_manifest.csv",
        "tables_dataset_summary": output_path.parent / "tables" / "dataset_summary.csv",
        "tables_document_manifest": output_path.parent / "tables" / "document_manifest.csv",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing and not force:
        existing_list = ", ".join(str(path) for path in existing)
        raise EBMDataError(f"Output files already exist; pass --force to overwrite: {existing_list}")

    loaded = load_ebm_nlp_archive(ebm_tar)
    train_examples = loaded["examples"]["train"]
    test_examples = loaded["examples"]["test"]
    manifest_rows = loaded["manifest_rows"]
    offset_failures = loaded["offset_failures"]
    summary_rows = build_split_summary_rows(manifest_rows)

    write_document_examples(paths["train_examples"], train_examples)
    write_document_examples(paths["test_examples"], test_examples)
    write_jsonl(paths["offset_failures"], offset_failures)
    _write_csv(paths["document_manifest"], [row.to_dict() for row in manifest_rows], _manifest_fields())
    _write_csv(paths["tables_document_manifest"], [row.to_dict() for row in manifest_rows], _manifest_fields())
    _write_csv(paths["tables_dataset_summary"], summary_rows, _summary_fields())

    data_summary = {
        "archive_path": str(Path(ebm_tar)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "phase4_gold_span_bio_conversion",
        "warning_count": len(offset_failures),
        "error_count": 0,
        "offset_failure_count": len(offset_failures),
        "offset_failure_path": str(paths["offset_failures"]),
        "label_source_paths": loaded["label_source_paths"],
        "splits": {row["split"]: {key: value for key, value in row.items() if key != "split"} for row in summary_rows},
        "outputs": {key: str(path) for key, path in paths.items()},
    }
    write_json(paths["data_summary"], data_summary)
    return data_summary


def load_ebm_nlp_archive(ebm_tar: str | Path) -> dict[str, Any]:
    archive_path = Path(ebm_tar)
    if not archive_path.exists():
        raise EBMDataError(f"EBM-NLP archive does not exist: {archive_path}")

    contents = _read_required_archive_contents(archive_path)
    root = _detect_archive_root(contents)
    examples: dict[str, list[DocumentExample]] = {"train": [], "test": []}
    manifest_rows: list[DocumentManifestRow] = []
    label_source_paths: dict[str, dict[str, str]] = {}
    offset_failures: list[dict[str, Any]] = []

    for split, label_subdir in SPLIT_LABEL_SUBDIRS.items():
        label_paths_by_label = {
            label: _annotation_paths(contents, root, directory, label_subdir)
            for label, directory in LABEL_DIRECTORIES.items()
        }
        doc_ids = sorted(set().union(*(set(paths) for paths in label_paths_by_label.values())))
        label_source_paths[split] = {
            label: f"{root}annotations/aggregated/starting_spans/{LABEL_DIRECTORIES[label]}/{label_subdir}"
            for label in PICO_LABELS
        }

        for doc_id in doc_ids:
            text_path = f"{root}documents/{doc_id}.txt"
            tokens_path = f"{root}documents/{doc_id}.tokens"
            abstract = _read_cached_text(contents, text_path)
            tokens = _read_cached_tokens(contents, tokens_path)
            label_sets: dict[str, list[int]] = {}
            source_paths: dict[str, str | None] = {
                "text": text_path,
                "tokens": tokens_path,
            }

            for label in PICO_LABELS:
                ann_path = label_paths_by_label[label].get(doc_id)
                if ann_path is None:
                    labels = [0] * len(tokens)
                    source_paths[label] = None
                else:
                    source_paths[label] = ann_path
                    labels = parse_binary_ann(_read_cached_text(contents, ann_path), ann_path)
                if len(labels) != len(tokens):
                    raise EBMDataError(
                        f"Length mismatch for {ann_path}: {len(labels)} labels vs "
                        f"{len(tokens)} official tokens in {tokens_path}"
                    )
                label_sets[label] = labels

            manifest_row = build_document_manifest_row(doc_id, split, len(tokens), label_sets)
            manifest_rows.append(manifest_row)
            try:
                token_offsets = align_token_offsets(abstract, tokens)
            except OffsetAlignmentError as exc:
                token_offsets = []
                offset_failures.append(
                    {
                        "doc_id": doc_id,
                        "split": split,
                        "token_index": exc.token_index,
                        "token": exc.token,
                        "cursor": exc.cursor,
                        "reason": exc.message,
                        "source_paths": source_paths,
                    }
                )
            gold_spans = binary_token_labels_to_spans(
                doc_id=doc_id,
                label_sets=label_sets,
                tokens=tokens,
                token_offsets=token_offsets,
                abstract=abstract,
            )
            multi_label_token_coverage = spans_to_multi_label_token_coverage(gold_spans, len(tokens))
            overlap_conflict = describe_overlap_conflicts(multi_label_token_coverage)
            bio_labels = spans_to_blurb_bio_labels(gold_spans, len(tokens))
            examples[split].append(
                DocumentExample(
                    doc_id=doc_id,
                    split=split,
                    abstract=abstract,
                    tokens=tokens,
                    token_offsets=token_offsets,
                    gold_spans=gold_spans,
                    bio_labels=bio_labels,
                    metadata={
                        "phase": "phase4_gold_span_bio_conversion",
                        "pico_token_labels": label_sets,
                        "multi_label_token_coverage": multi_label_token_coverage,
                        "overlap_conflict": overlap_conflict,
                        "source_paths": source_paths,
                        "token_count": len(tokens),
                        "span_counts": {
                            "P": manifest_row.p_span_count,
                            "I": manifest_row.i_span_count,
                            "O": manifest_row.o_span_count,
                            "total": manifest_row.total_span_count,
                        },
                        "has_overlap": manifest_row.has_overlap,
                    },
                )
            )

    return {
        "examples": examples,
        "manifest_rows": manifest_rows,
        "label_source_paths": label_source_paths,
        "offset_failures": offset_failures,
    }


def _read_required_archive_contents(archive_path: Path) -> dict[str, str]:
    contents: dict[str, str] = {}
    with tarfile.open(archive_path, "r|*") as tar:
        for member in tar:
            if not member.isfile() or not _is_required_member(member.name):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                raise EBMDataError(f"Could not read file from archive: {member.name}")
            contents[member.name] = handle.read().decode("utf-8")
    if not contents:
        raise EBMDataError(f"No required EBM-NLP files found in archive: {archive_path}")
    return contents


def _is_required_member(name: str) -> bool:
    return (
        name.startswith("ebm_nlp_2_00/documents/")
        and (name.endswith(".txt") or name.endswith(".tokens"))
    ) or (
        name.startswith("ebm_nlp_2_00/annotations/aggregated/starting_spans/")
        and name.endswith(".AGGREGATED.ann")
        and ("/train/" in name or "/test/gold/" in name)
    )


def _detect_archive_root(contents: dict[str, str]) -> str:
    roots = {name.split("/", 1)[0] for name in contents if "/" in name}
    if "ebm_nlp_2_00" not in roots:
        raise EBMDataError("Could not find official archive root 'ebm_nlp_2_00/'")
    return "ebm_nlp_2_00/"


def _annotation_paths(
    contents: dict[str, str],
    root: str,
    label_directory: str,
    split_subdir: str,
) -> dict[str, str]:
    prefix = f"{root}annotations/aggregated/starting_spans/{label_directory}/{split_subdir}/"
    suffix = ".AGGREGATED.ann"
    paths: dict[str, str] = {}
    for name in contents:
        if not name.startswith(prefix) or not name.endswith(suffix):
            continue
        filename = name.rsplit("/", 1)[-1]
        doc_id = filename[: -len(suffix)]
        if not doc_id:
            raise EBMDataError(f"Invalid annotation filename: {name}")
        paths[doc_id] = name
    if not paths:
        raise EBMDataError(f"Missing required annotation files under {prefix}")
    return paths


def _read_cached_text(contents: dict[str, str], path: str) -> str:
    content = contents.get(path)
    if content is None:
        raise EBMDataError(f"Missing required file in archive: {path}")
    return content


def _read_cached_tokens(contents: dict[str, str], path: str) -> list[str]:
    return _read_cached_text(contents, path).splitlines()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _manifest_fields() -> list[str]:
    return [
        "doc_id",
        "split",
        "token_count",
        "p_span_count",
        "i_span_count",
        "o_span_count",
        "total_span_count",
        "has_overlap",
        "overlap_token_count",
    ]


def _summary_fields() -> list[str]:
    return [
        "split",
        "doc_count",
        "token_count",
        "p_span_count",
        "i_span_count",
        "o_span_count",
        "overlap_doc_count",
        "overlap_token_count",
    ]
