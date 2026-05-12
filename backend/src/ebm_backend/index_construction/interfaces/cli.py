"""Command-line helpers for Module 1 index construction."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any

from ebm_backend.index_construction.application.pipeline import (
    LocalRCTIndex,
    build_module1_local_index_from_derived,
    copy_theme_demo_subset,
    run_module1_simplified_sync,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Module 1 index construction utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    select_demo = subparsers.add_parser(
        "select-demo",
        help="Copy a theme-clustered primary RCT demo subset.",
    )
    select_demo.add_argument("--source-data-root", default="data/pmc-rct")
    select_demo.add_argument("--dest-data-root", default="data/data_for_test/data/data_for_test/data_demo_1000")
    select_demo.add_argument("--total", type=int, default=1000)

    simplified = subparsers.add_parser(
        "simplified",
        help="Run the Phase 2 simplified Module 1 path.",
    )
    simplified.add_argument("--source-data-root", default="data/data_for_test/data_demo")
    simplified.add_argument("--dest-data-root", default="data/data_for_test/data/data_for_test/data_demo_with_mesh")
    simplified.add_argument("--database-url", default=None)
    simplified.add_argument("--limit", type=int, default=100)
    simplified.add_argument("--pi-mode", choices=("llm", "local"), default="llm")
    simplified.add_argument("--mesh-mode", choices=("online", "offline"), default="offline")
    simplified.add_argument("--use-database", action="store_true")
    simplified.add_argument("--workers", type=int, default=1)
    simplified.add_argument(
        "--no-local-fallback",
        action="store_true",
        help="Fail studies instead of using local PI extraction when LLM output does not validate.",
    )
    simplified.add_argument("--no-copy-source", action="store_true")
    simplified.add_argument("--force", action="store_true", help="Reprocess studies even when derived JSON exists.")
    simplified.add_argument("--no-query-validation", action="store_true")
    simplified.add_argument("--top-k-search", type=int, default=10)
    simplified.add_argument("--verbose", action="store_true")

    index_derived = subparsers.add_parser(
        "index-derived",
        help="Build and validate the local index from existing derived JSON files.",
    )
    index_derived.add_argument("--data-root", default="data/data_for_test/data/data_for_test/data_demo_with_mesh")
    index_derived.add_argument("--export-dir", default=None)
    index_derived.add_argument("--index-path", default=None)
    index_derived.add_argument("--no-query-validation", action="store_true")
    index_derived.add_argument("--top-k-search", type=int, default=10)

    search_local = subparsers.add_parser(
        "search-local",
        help="Search the local JSONL retrieval index with a custom query.",
    )
    search_local.add_argument("--index-path", default="data/data_for_test/data_demo_1000/index/local_rct_index.jsonl")
    search_local.add_argument("--query", required=True)
    search_local.add_argument("--top-k", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "select-demo":
        result = copy_theme_demo_subset(
            source_root=args.source_data_root,
            dest_root=args.dest_data_root,
            total=args.total,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    if args.command == "simplified":
        result = run_module1_simplified_sync(
            source_data_root=args.source_data_root,
            dest_data_root=args.dest_data_root,
            database_url=args.database_url,
            limit=args.limit,
            pi_mode=args.pi_mode,
            mesh_mode=args.mesh_mode,
            use_database=args.use_database,
            workers=args.workers,
            fallback_local_on_error=not args.no_local_fallback,
            copy_source=not args.no_copy_source,
            skip_existing_derived=not args.force,
            run_query_validation=not args.no_query_validation,
            top_k_search=args.top_k_search,
            verbose=args.verbose,
        )
        print(json.dumps(_result_to_summary(result), ensure_ascii=False, indent=2))
        return 0 if result.failed == 0 else 1
    if args.command == "index-derived":
        result = build_module1_local_index_from_derived(
            data_root=args.data_root,
            export_dir=args.export_dir,
            index_path=args.index_path,
            run_query_validation=not args.no_query_validation,
            top_k_search=args.top_k_search,
        )
        print(json.dumps(_result_to_summary(result), ensure_ascii=False, indent=2))
        return 0 if result.failed == 0 else 1
    if args.command == "search-local":
        index = LocalRCTIndex(args.index_path)
        hits = index.search(args.query, top_k=args.top_k)
        print(
            json.dumps(
                {
                    "query": args.query,
                    "index_path": args.index_path,
                    "count": len(hits),
                    "hits": [_hit_to_summary(hit) for hit in hits],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


def _result_to_summary(result: Any) -> dict[str, Any]:
    payload = asdict(result)
    payload["query_validation"] = [
        {
            "query": row["query"],
            "passed": row["passed"],
            "hit_count": row["hit_count"],
            "expected_study_id": row["expected_study_id"],
            "expected_in_top_hits": row["expected_in_top_hits"],
            "top_hits": row["top_hits"][:3],
        }
        for row in payload.get("query_validation", [])
    ]
    return payload


def _hit_to_summary(hit: Any) -> dict[str, Any]:
    document = hit.document
    return {
        "study_id": hit.study_id,
        "score": hit.score,
        "matched_fields": hit.matched_fields,
        "title": hit.title,
        "pmid": document.get("pmid"),
        "pmcid": document.get("pmcid"),
        "population": document.get("population"),
        "intervention": document.get("intervention"),
        "mesh_terms": document.get("mesh_terms"),
        "mesh_population": document.get("mesh_population"),
        "mesh_intervention": document.get("mesh_intervention"),
        "article_path": document.get("article_path"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
