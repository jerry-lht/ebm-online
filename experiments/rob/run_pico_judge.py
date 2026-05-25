#!/usr/bin/env python3
"""
Stage 2: LLM-as-judge consistency check.

Reads extractions from results/pico_extractions/ and ground-truth
characteristics from rob_cleaned_dataset/, then asks an LLM to judge
whether each extraction is consistent / inconsistent / unclear.

Usage:
    python run_pico_judge.py --max_studies 5
    python run_pico_judge.py --judge_model gpt-5.4-mini --resume
"""

import asyncio
import json
import argparse
import os
from pathlib import Path
from openai import AsyncOpenAI
import json_repair


def _load_dotenv(path: Path = Path(__file__).with_name(".env")) -> None:
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

SLOTS = ["participants", "interventions", "outcomes"]

JUDGE_SYSTEM = """\
You compare an LLM's extraction of a clinical trial's **{slot}** field against
the Cochrane review's official Characteristics entry for the same study.

OFFICIAL is an abridged Cochrane summary. EXTRACTED comes from the full article
and is usually longer and more detailed.

Classify as "consistent" or "inconsistent" using ONLY these rules:

INCONSISTENT — EXTRACTED states a fact that DIRECTLY CONTRADICTS a specific fact
in OFFICIAL. Hard examples:
  - OFFICIAL says N=207 HIV-positive women; EXTRACTED says all women regardless
    of HIV status (N=940). → inconsistent (different population)
  - OFFICIAL says drug A vs placebo; EXTRACTED says drug A vs drug B. → inconsistent
  - OFFICIAL says primary outcome is X; EXTRACTED says primary outcome is Y. → inconsistent

CONSISTENT — everything else, including:
  - EXTRACTED mentions outcomes / criteria / details that OFFICIAL does not list.
    Cochrane summaries are abridged; extra items in EXTRACTED are EXPECTED and are
    NOT contradictions.
  - EXTRACTED uses different but compatible terminology ("ALRI" vs "LRTI",
    "usual care" vs "routine consultation", "dependency" vs "disability").
  - EXTRACTED reports a finer breakdown of a number OFFICIAL aggregates
    (e.g., OFFICIAL N=609 is a subgroup of EXTRACTED N=940 total enrolled).
  - EXTRACTED includes results or effect sizes — ignore those; judge only study facts.
  - OFFICIAL is truncated or sparse and EXTRACTED simply has more detail.
  - Naming/wording differences that describe the same underlying construct.

Output JSON only:
{{
  "slot": "{slot}",
  "judgement": "consistent" | "inconsistent",
  "reason": "<one sentence: the single most important fact that drove your decision>"
}}"""


async def _call(client, model, system, user, max_retries=5):
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            if isinstance(resp, str):
                raise RuntimeError(f"API returned raw string: {resp[:200]}")
            content = resp.choices[0].message.content
            return json_repair.loads(content)
        except (json.JSONDecodeError, RuntimeError, AttributeError) as e:
            last_error = e
            await asyncio.sleep(2 ** attempt * 2)
        except Exception as e:
            last_error = e
            await asyncio.sleep(min(2 ** attempt * 3, 60))
    raise RuntimeError(f"failed after {max_retries} retries: {last_error}")


def _coerce_judgement(obj: dict) -> tuple[str | None, str]:
    if not isinstance(obj, dict):
        return None, ""
    j = obj.get("judgement") or obj.get("verdict") or obj.get("label")
    if isinstance(j, str):
        jl = j.strip().lower()
        for canon in ("inconsistent", "consistent"):
            if canon in jl:
                j = canon
                break
    reason = obj.get("reason") or obj.get("notes") or obj.get("reasoning") or ""
    if isinstance(reason, list):
        reason = "; ".join(str(x) for x in reason)
    return j, str(reason).strip()


async def judge_slot(client, model, slot, extracted, official):
    if not extracted:
        return {"slot": slot, "judgement": None, "reasoning": None,
                "contradictions": [], "coverage": "", "_error": "no extraction"}
    if not official:
        return {"slot": slot, "judgement": None, "reasoning": None,
                "contradictions": [], "coverage": "", "_error": "no ground truth"}

    user = (
        f"## EXTRACTED ({slot})\n{extracted}\n\n"
        f"## OFFICIAL ({slot})\n{official}\n\n"
        f'Respond with exactly this JSON and no other keys: {{"judgement": "consistent" or "inconsistent", "reason": "one sentence"}}'
    )
    try:
        obj = await _call(client, model, JUDGE_SYSTEM.format(slot=slot), user)
    except Exception as e:
        return {"slot": slot, "judgement": None, "reasoning": None, "_error": str(e)}

    j, reasoning = _coerce_judgement(obj)
    return {"slot": slot, "judgement": j, "reasoning": reasoning}


async def judge_study(client, model, extraction_doc, gt_study):
    extractions = extraction_doc.get("extractions", {})
    characteristics = gt_study.get("characteristics", {}) or {}

    tasks = []
    for slot in SLOTS:
        extracted = extractions.get(slot, {}).get("extracted")
        official = characteristics.get(slot, "") or ""
        tasks.append(judge_slot(client, model, slot, extracted, official))
    results = await asyncio.gather(*tasks)

    return {
        "study_id": extraction_doc.get("study_id"),
        "pmid": extraction_doc.get("pmid"),
        "extraction_model": extraction_doc.get("model"),
        "judge_model": model,
        "judgements": {
            r["slot"]: {
                **r,
                "extracted": extractions.get(r["slot"], {}).get("extracted"),
                "official": (characteristics.get(r["slot"], "") or "")[:500],
            }
            for r in results
        },
    }


async def process_all(args):
    extractions_dir = Path(args.extractions_dir)
    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = AsyncOpenAI()
    files = sorted(extractions_dir.glob("*.json"))
    if args.max_studies:
        files = files[: args.max_studies]

    print(f"[JUDGE] Model: {args.judge_model}  Studies: {len(files)}  Concurrency: {args.concurrency}")

    semaphore = asyncio.Semaphore(args.concurrency)
    counters = {"ok": 0, "skipped": 0, "errors": 0}
    lock = asyncio.Lock()

    async def worker(path):
        out_path = output_dir / path.name
        if args.resume and out_path.exists():
            async with lock:
                counters["skipped"] += 1
            return
        async with semaphore:
            extraction_doc = json.loads(path.read_text(encoding="utf-8"))
            gt_path = dataset_dir / path.name
            if not gt_path.exists():
                async with lock:
                    counters["errors"] += 1
                    print(f"  WARN: no ground truth for {path.name}, skipping")
                return
            gt_raw = json.loads(gt_path.read_text(encoding="utf-8"))
            gt_study = gt_raw[0] if isinstance(gt_raw, list) else gt_raw
            label = extraction_doc.get("study_id") or path.stem
            try:
                result = await judge_study(client, args.judge_model, extraction_doc, gt_study)
                out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
                async with lock:
                    counters["ok"] += 1
                    done = counters["ok"] + counters["skipped"] + counters["errors"]
                    print(f"[{done}/{len(files)}] {label} ... OK")
            except Exception as e:
                async with lock:
                    counters["errors"] += 1
                    done = counters["ok"] + counters["skipped"] + counters["errors"]
                    print(f"[{done}/{len(files)}] {label} ... ERROR: {e}")

    await asyncio.gather(*(worker(p) for p in files))
    print(f"\n[JUDGE] Done. OK={counters['ok']}  Skipped={counters['skipped']}  Errors={counters['errors']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractions_dir", default="results/pico_extractions")
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--output_dir", default="results/pico_judgements")
    parser.add_argument("--judge_model", default="gpt-5.4-mini")
    parser.add_argument("--max_studies", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    asyncio.run(process_all(args))


if __name__ == "__main__":
    main()
