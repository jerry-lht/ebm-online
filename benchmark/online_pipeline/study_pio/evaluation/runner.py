"""Run the Study PIO benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ebm_backend.online_pipeline.domain.article import (
    ArticleMetadata,
    ArticleSection,
    ArticleSource,
    ArticleTable,
    ArticleXmlContent,
    CleanedArticle,
)
from ebm_backend.online_pipeline.domain.question import QuestionPICO
from ebm_backend.online_pipeline.domain.study_characteristics import StudyPIOCharacteristics

from benchmark.online_pipeline.shared.jsonl import read_jsonl, write_jsonl
from benchmark.online_pipeline.shared.method_loader import load_method
from benchmark.online_pipeline.shared.report_utils import write_json, write_summary_markdown
from benchmark.online_pipeline.shared.run_utils import default_run_id
from benchmark.online_pipeline.study_pio.evaluation.io import load_dataset
from benchmark.online_pipeline.study_pio.evaluation.judge import FIELDS, judge_predictions
from benchmark.online_pipeline.study_pio.evaluation.metrics import evaluate_match_rows


MODULE_NAME = "study_pio"
MODULE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = MODULE_DIR / "datasets" / "cochrane_study_pio" / "splits" / "smoke"


def run_benchmark(
    *,
    dataset: str | Path = DEFAULT_DATASET,
    method: str = "gold",
    run_id: str | None = None,
    runs_root: str | Path | None = None,
    limit: int | None = None,
    judge_mode: str = "llm",
    llm_config: str | Path = "llm.local.json",
    resume: bool = False,
    workers: int = 1,
) -> dict[str, Any]:
    resolved_run_id = run_id or default_run_id()
    run_dir = Path(runs_root or MODULE_DIR / "runs") / resolved_run_id
    instances, gold_by_id, articles_by_id = load_dataset(dataset)
    if limit is not None:
        instances = instances[:limit]
        gold_by_id = {str(instance["instance_id"]): gold_by_id[str(instance["instance_id"])] for instance in instances}

    completed_before_resume = _completed_instance_ids(run_dir / "judge_matches.jsonl") if resume else set()
    predictions = _predictions(
        instances=instances,
        gold_by_id=gold_by_id,
        articles_by_id=articles_by_id,
        method=method,
    )
    match_rows = judge_predictions(
        instances=instances,
        predictions=predictions,
        gold_by_id=gold_by_id,
        judge_mode=judge_mode,
        llm_config=llm_config,
        output_path=run_dir / "judge_matches.jsonl",
        failure_output_path=run_dir / "judge_failures.jsonl",
        resume=resume,
        workers=workers,
    )
    metrics = evaluate_match_rows(match_rows)
    write_jsonl(run_dir / "predictions.jsonl", predictions)
    write_json(run_dir / "metrics.json", metrics)

    completed_after_run = _completed_instance_ids(run_dir / "judge_matches.jsonl")
    failure_count = _failure_count(run_dir / "judge_failures.jsonl")
    requested_instance_ids = {str(instance["instance_id"]) for instance in instances}
    run_manifest = {
        "module_name": MODULE_NAME,
        "run_id": resolved_run_id,
        "method": method,
        "judge_mode": judge_mode,
        "limit": limit,
        "resume": resume,
        "workers": workers,
        "requested_count": len(instances),
        "completed_count": len(completed_after_run & requested_instance_ids),
        "skipped_by_resume_count": len(completed_before_resume & requested_instance_ids),
        "failed_count": failure_count or max(0, len(instances) - len(completed_after_run & requested_instance_ids)),
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    summary = {
        "module_name": MODULE_NAME,
        "run_id": resolved_run_id,
        "method": method,
        "judge_mode": judge_mode,
        "limit": limit,
        "resume": resume,
        "workers": workers,
        "instances": len(instances),
        "population_f1": metrics["population_f1"],
        "intervention_comparator_f1": metrics["intervention_comparator_f1"],
        "outcomes_f1": metrics["outcomes_f1"],
        "micro_precision": metrics["micro_precision"],
        "micro_recall": metrics["micro_recall"],
        "micro_f1": metrics["micro_f1"],
        "macro_precision": metrics["macro_precision"],
        "macro_recall": metrics["macro_recall"],
        "macro_f1": metrics["macro_f1"],
        "critical_fields_complete_rate": metrics["critical_fields_complete_rate"],
    }
    write_json(run_dir / "summary.json", summary)
    write_summary_markdown(run_dir / "summary.md", title="study_pio smoke benchmark", summary=summary)
    return {"run_id": resolved_run_id, "run_dir": str(run_dir), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--method", default="gold")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--judge-mode", choices=("llm", "normalized"), default="llm")
    parser.add_argument("--llm-config", default="llm.local.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    result = run_benchmark(
        dataset=args.dataset,
        method=args.method,
        run_id=args.run_id,
        limit=args.limit,
        judge_mode=args.judge_mode,
        llm_config=args.llm_config,
        resume=args.resume,
        workers=args.workers,
    )
    print(result["run_dir"])


def _predictions(
    *,
    instances: list[dict[str, Any]],
    gold_by_id: dict[str, dict[str, Any]],
    articles_by_id: dict[str, dict[str, Any]],
    method: str,
) -> list[dict[str, Any]]:
    if method in {"gold", "study_pio.gold"}:
        return _gold_predictions(instances=instances, gold_by_id=gold_by_id, articles_by_id=articles_by_id)
    method_obj = load_method(method, default_module="study_pio")
    return _method_predictions(instances=instances, articles_by_id=articles_by_id, method_obj=method_obj)


def _gold_predictions(
    *,
    instances: list[dict[str, Any]],
    gold_by_id: dict[str, dict[str, Any]],
    articles_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    predictions = []
    for instance in instances:
        instance_id = str(instance["instance_id"])
        missing_articles = [article_id for article_id in instance.get("article_ids", []) if article_id not in articles_by_id]
        if missing_articles:
            raise ValueError(f"Missing article fixture(s) for {instance_id}: {missing_articles}")
        gold = gold_by_id[instance_id]
        predictions.append(
            {
                "instance_id": instance_id,
                "study_id": gold["study_id"],
                "population": gold["population"],
                "intervention_comparator": gold["intervention_comparator"],
                "outcomes": gold["outcomes"],
            }
        )
    return predictions


def _method_predictions(
    *,
    instances: list[dict[str, Any]],
    articles_by_id: dict[str, dict[str, Any]],
    method_obj: Any,
) -> list[dict[str, Any]]:
    predictions = []
    for instance in instances:
        instance_id = str(instance["instance_id"])
        missing_articles = [article_id for article_id in instance.get("article_ids", []) if article_id not in articles_by_id]
        if missing_articles:
            raise ValueError(f"Missing article fixture(s) for {instance_id}: {missing_articles}")
        articles = [_cleaned_article_from_payload(articles_by_id[article_id]) for article_id in instance.get("article_ids", [])]
        result = method_obj.run(
            question_pico=_question_pico_from_instance(instance),
            included_studies=[str(study_id) for study_id in instance.get("included_studies", [])],
            articles=articles,
        )
        prediction = _prediction_from_method_result(instance_id=instance_id, result=result)
        predictions.append(prediction)
    return predictions


def _question_pico_from_instance(instance: dict[str, Any]) -> QuestionPICO:
    pico = instance.get("question_pico") or {}
    return QuestionPICO(
        P=[str(item) for item in (pico.get("P") or [])],
        I=[str(item) for item in (pico.get("I") or [])],
        C=[str(item) for item in (pico.get("C") or [])],
        O=[str(item) for item in (pico.get("O") or [])],
    )


def _cleaned_article_from_payload(payload: dict[str, Any]) -> CleanedArticle:
    metadata = payload.get("metadata") or {}
    source = payload.get("source") or {}
    return CleanedArticle(
        study_id=str(payload.get("study_id") or ""),
        metadata=ArticleMetadata(
            title=str(metadata.get("title") or ""),
            pmid=metadata.get("pmid"),
            pmc_id=metadata.get("pmc_id"),
            source_type=metadata.get("source_type"),
            publication_year=metadata.get("publication_year"),
            mesh_terms=[str(item) for item in (metadata.get("mesh_terms") or [])],
            doi=metadata.get("doi"),
        ),
        xml_content=ArticleXmlContent(
            sections=[
                ArticleSection(
                    section_id=str(section.get("section_id") or ""),
                    title=str(section.get("title") or ""),
                    text=str(section.get("text") or ""),
                )
                for section in ((payload.get("xml_content") or {}).get("sections") or [])
            ]
        ),
        tables=[
            ArticleTable(
                table_id=str(table.get("table_id") or ""),
                caption=str(table.get("caption") or ""),
                rows=table.get("rows") if isinstance(table.get("rows"), list) else [],
            )
            for table in (payload.get("tables") or [])
        ],
        source=ArticleSource(
            database=str(source.get("database") or ""),
            retrieval_rank=source.get("retrieval_rank"),
            retrieval_score=source.get("retrieval_score"),
            raw_source_url=source.get("raw_source_url"),
            raw_record_id=source.get("raw_record_id"),
        )
        if source
        else None,
    )


def _prediction_from_method_result(*, instance_id: str, result: list[StudyPIOCharacteristics]) -> dict[str, Any]:
    if not result:
        return {
            "instance_id": instance_id,
            "study_id": "",
            "population": "",
            "intervention_comparator": "",
            "outcomes": "",
        }
    item = result[0]
    interventions = [entry.description for entry in item.interventions if entry.description]
    comparators = [entry.description for entry in item.comparators if entry.description]
    outcomes = [entry.measurement for entry in item.outcomes if entry.measurement]
    return {
        "instance_id": instance_id,
        "study_id": item.study_id,
        "population": item.population.description,
        "intervention_comparator": " Comparator: ".join(
            part for part in ["; ".join(interventions), "; ".join(comparators)] if part
        ),
        "outcomes": "; ".join(outcomes),
    }


def _completed_instance_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    rows = read_jsonl(path)
    fields_by_instance: dict[str, set[str]] = {}
    for row in rows:
        fields_by_instance.setdefault(str(row.get("instance_id") or ""), set()).add(str(row.get("field") or ""))
    return {instance_id for instance_id, fields in fields_by_instance.items() if set(FIELDS).issubset(fields)}


def _failure_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_jsonl(path))


if __name__ == "__main__":
    main()
