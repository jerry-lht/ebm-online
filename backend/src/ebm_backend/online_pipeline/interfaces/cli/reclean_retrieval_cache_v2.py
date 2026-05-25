#!/usr/bin/env python3
"""Re-clean retrieval_cache_v2 cleaned article JSON files into xml_content format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ebm_backend.online_pipeline.application.question_study.retrieval_cache_v2 import RetrievalCacheV2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Re-clean retrieval_cache_v2 cleaned articles into xml_content format.")
    parser.add_argument("--cache-root", default="data/retrieval_cache_v2")
    parser.add_argument("--index-path", default="data/retrieval_cache_v2/index/local_rct_index_v2.jsonl")
    parser.add_argument("--pmids", default="", help="Comma-separated PMIDs. Empty means all cleaned files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cache = RetrievalCacheV2.from_paths(
        cache_root=Path(args.cache_root),
        index_path=Path(args.index_path),
    )
    pmids = [item.strip() for item in str(args.pmids or "").split(",") if item.strip()]
    result = cache.re_clean_existing_articles(pmids=pmids or None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
