#!/usr/bin/env python3
"""
RoB Experiment Runner - 5-domain per-study extraction.

For each study, makes 5 parallel API calls (one per RoB domain) and saves
the combined predictions to results/predictions/<pmid>.json.

Inputs (per study):
    - review_title:  the parent systematic review title
    - sr_pico:       structured PICO from the parent SR
    - xml_content:   article sections + tables (full text + JATS XML tables)

Output (per study):
    JSON with 5-domain RoB predictions.

Usage:
    python run_experiment.py                          # all studies
    python run_experiment.py --max_studies 20         # quick test run
    python run_experiment.py --model gpt-4o-mini      # specify model
    python run_experiment.py --resume                 # skip already-done files
    python run_experiment.py --concurrency 5          # parallel studies
"""

import asyncio
import json
import argparse
import os
from pathlib import Path
from openai import AsyncOpenAI

from domain_specs import SPECS, DomainSpec, build_system_prompt


def _load_dotenv(path: Path = Path(__file__).with_name(".env")) -> None:
    """Tiny dotenv loader - no third-party dep needed."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().lstrip("export").strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_dotenv()


def build_user_prompt(study: dict) -> str:
    """Build the study-evidence section of the user prompt.

    Uses only three input fields:
        - review_title
        - sr_pico        (population / intervention / comparison / outcome)
        - xml_content    (sections + tables)
    """
    parts = [f"Study: {study.get('study_id', 'Unknown')} (PMID: {study.get('pmid', 'N/A')})"]

    # Parent SR context
    review_title = (study.get("review_title") or "").strip()
    if review_title:
        parts.append(f"\n## Parent Systematic Review\n{review_title}")

    pico = study.get("sr_pico", {}) or {}
    if pico:
        parts.append(
            "\n## Systematic Review PICO Context\n"
            f"Population: {pico.get('population', [])}\n"
            f"Intervention: {pico.get('intervention', [])}\n"
            f"Comparison: {pico.get('comparison', [])}\n"
            f"Outcome: {pico.get('outcome', [])}"
        )

    # Full text - categorise sections by RoB relevance
    sections = study.get("xml_content", {}).get("sections", []) or []
    methods_secs: list[tuple[str, str]] = []
    results_secs: list[tuple[str, str]] = []
    front_secs: list[tuple[str, str]] = []
    other_secs: list[tuple[str, str]] = []

    for sec in sections:
        name = (sec.get("section", "") or "").strip()
        text = (sec.get("text", "") or "").strip()
        if not text:
            continue
        nl = name.lower()
        if any(k in nl for k in ("method", "material")):
            methods_secs.append((name, text))
        elif "result" in nl:
            results_secs.append((name, text))
        elif nl in ("front", "abstract"):
            front_secs.append((name, text))
        else:
            other_secs.append((name, text))

    if front_secs:
        parts.append("\n## Abstract / Front matter")
        for name, text in front_secs:
            parts.append(f"### {name}\n{text}")

    if methods_secs:
        parts.append("\n## Methods (full text - primary evidence for RoB)")
        for name, text in methods_secs:
            parts.append(f"### {name}\n{text}")

    if results_secs:
        parts.append("\n## Results (full text - for attrition / CONSORT data)")
        for name, text in results_secs:
            parts.append(f"### {name}\n{text}")

    if other_secs:
        parts.append("\n## Other sections (Discussion / Conclusions / etc.)")
        for name, text in other_secs:
            parts.append(f"### {name}\n{text[:5000]}")

    # Tables - raw JATS XML
    tables = study.get("xml_content", {}).get("tables", []) or []
    if tables:
        parts.append("\n## Tables (JATS XML - includes CONSORT flow, baseline characteristics)")
        for i, t in enumerate(tables[:10]):
            raw = (t.get("raw_xml", "") or "").strip()
            if not raw:
                continue
            section_path = t.get("section_path", []) or []
            loc = " > ".join(section_path) if section_path else ""
            header = f"Table {i+1}" + (f" (in {loc})" if loc else "")
            parts.append(f"### {header}\n{raw[:6000]}")

    full_text = "\n".join(parts)

    MAX_CHARS = 200_000
    if len(full_text) > MAX_CHARS:
        full_text = full_text[:MAX_CHARS] + "\n\n[... truncated due to length ...]"
    return full_text


async def call_slot(
    client: AsyncOpenAI,
    model: str,
    spec: DomainSpec,
    user_evidence: str,
    max_retries: int = 3,
) -> dict:
    """Run a single domain-slot extraction. Returns the parsed JSON object."""
    system_prompt = build_system_prompt(spec)
    user_prompt = (
        f"{user_evidence}\n\n"
        f"Assess **{spec.domain_label}**. Output JSON only."
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            parsed["_slot_id"] = spec.slot_id
            return parsed
        except Exception as e:
            last_error = e
            await asyncio.sleep(2 ** attempt * 2)

    return {
        "_slot_id": spec.slot_id,
        "domain": spec.domain_label,
        "judgement": None,
        "support_text": None,
        "source": None,
        "_error": f"failed after {max_retries} retries: {last_error}",
    }


async def run_study(client: AsyncOpenAI, model: str, study: dict) -> dict:
    """Make 5 parallel slot calls for one study, return combined prediction."""
    user_evidence = build_user_prompt(study)
    tasks = [call_slot(client, model, spec, user_evidence) for spec in SPECS]
    slot_results = await asyncio.gather(*tasks)

    return {
        "study_id": study.get("study_id"),
        "pmid": study.get("pmid"),
        "model": model,
        "prediction": {
            "risk_of_bias": [
                {k: v for k, v in r.items() if k != "_slot_id"} for r in slot_results
            ],
        },
        "slot_map": {r["_slot_id"]: r.get("judgement") for r in slot_results},
    }


async def process_all(args) -> None:
    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = AsyncOpenAI()

    files = sorted(dataset_dir.glob("*.json"))
    if args.max_studies:
        files = files[: args.max_studies]

    print(f"Model       : {args.model}")
    print(f"Studies     : {len(files)}")
    print(f"Concurrency : {args.concurrency} studies in parallel x 5 slots each")
    print(f"Output      : {output_dir}\n")

    semaphore = asyncio.Semaphore(args.concurrency)
    counters = {"ok": 0, "skipped": 0, "errors": 0}
    lock = asyncio.Lock()

    async def worker(i: int, path: Path) -> None:
        out_path = output_dir / path.name
        if args.resume and out_path.exists():
            async with lock:
                counters["skipped"] += 1
            return

        async with semaphore:
            raw = json.loads(path.read_text(encoding="utf-8"))
            study = raw[0] if isinstance(raw, list) else raw
            label = study.get("study_id") or path.stem
            try:
                result = await run_study(client, args.model, study)
                out_path.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                async with lock:
                    counters["ok"] += 1
                    done = counters["ok"] + counters["skipped"] + counters["errors"]
                    print(f"[{done}/{len(files)}] {label} ... OK")
            except Exception as e:
                async with lock:
                    counters["errors"] += 1
                    done = counters["ok"] + counters["skipped"] + counters["errors"]
                    print(f"[{done}/{len(files)}] {label} ... ERROR: {e}")

    await asyncio.gather(*(worker(i, p) for i, p in enumerate(files, 1)))

    print(
        f"\nDone. OK={counters['ok']}  "
        f"Skipped={counters['skipped']}  Errors={counters['errors']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 5-domain RoB extraction")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--output_dir", default="results/predictions")
    parser.add_argument("--model", default="gpt-5.4-mini",
                        help="OpenAI model (e.g. gpt-4o-mini, gpt-5.4-mini)")
    parser.add_argument("--max_studies", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    asyncio.run(process_all(args))


if __name__ == "__main__":
    main()
