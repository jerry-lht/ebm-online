#!/usr/bin/env python3
"""
Stage 1: PICO extraction from clinical trial articles.

Reads each study's sr_pico + xml_content and asks an LLM to extract
participants / interventions / outcomes as prose paragraphs.

Does NOT see the ground-truth `characteristics` field.

Usage:
    python run_pico_extraction.py --max_studies 5
    python run_pico_extraction.py --model gpt-5.4-mini --resume
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

SLOT_GUIDANCE = {
    "participants": (
        "Describe the participant population that the SYSTEMATIC REVIEW targets — see "
        "the SR PICO above.\n"
        "SUBGROUP RULE: if the SR's Population is a subgroup of the trial's enrolled "
        "cohort (e.g., the trial enrolled all pregnant women but the SR is about "
        "HIV-positive pregnant women; the trial enrolled adults 18+ but the SR targets "
        "adults ≥65; the trial enrolled mixed severity but the SR targets severe cases), "
        "extract ONLY that subgroup: its sample size, eligibility, and demographics. "
        "Do NOT report the full trial's N or demographics in this case — those are not "
        "the participants the SR cares about. If the article reports the subgroup's "
        "exact N, use that. If the article does not break out the subgroup explicitly, "
        "report whatever it does state about that subgroup and note the subgroup "
        "definition in one sentence.\n"
        "If the SR's Population covers the trial's full enrolled cohort, describe the "
        "full trial population.\n"
        "Include: sample size (for the SR-relevant population), key inclusion/exclusion "
        "criteria, setting (country, hospital/community/clinic), and basic demographics "
        "(age, sex, disease stage)."
    ),
    "interventions": (
        "Describe WHAT was given: intervention name, dose/intensity, duration, frequency, "
        "delivery mode, who delivered it, and the comparator (placebo / usual care / "
        "active control). Include co-interventions if any. Do NOT report effect sizes or results."
    ),
    "outcomes": (
        "Write a PROSE PARAGRAPH describing ONLY the outcomes the trial planned to MEASURE.\n"
        "Source: the article's Methods / 'Outcomes' / 'Endpoints' section only — NOT Results.\n"
        "Include: primary vs secondary distinction (if stated), outcome name, measurement "
        "instrument/scale, and time point. Do NOT report results, effect sizes, p-values, "
        "or direction of findings.\n"
        "GOOD example: 'The primary outcome was low birth weight (<2500 g) at delivery. "
        "Secondary outcomes included maternal peripheral parasitaemia at delivery, placental "
        "malaria on histology, haemoglobin level at delivery, prematurity rate, mean birth "
        "weight, and mother-to-child HIV transmission, assessed at delivery and 8 weeks postpartum.'"
    ),
}

EXTRACTION_SYSTEM = """\
You are a clinical trial data extractor for systematic reviews.

Given a systematic review's PICO context and a clinical trial's full text, extract the **{slot}** field.

General rules:
- Base your extraction ONLY on the article full text.
- Write a PROSE PARAGRAPH (3-6 sentences). Do NOT return a list of keywords or tags.
- Do not invent or infer beyond what the article states.

Slot-specific guidance for **{slot}**:
{slot_guidance}

Output EXACTLY this JSON structure (do not change the keys):
{{"slot": "{slot}", "extracted": "<your prose paragraph here as a single string>"}}

The value of "extracted" MUST be a single string (a paragraph), NOT an array, NOT an object.
Do NOT use the slot name as the key. The key MUST be "extracted".

Output JSON only."""


def build_article_prompt(study: dict, slot: str) -> str:
    parts = [f"Study: {study.get('study_id', 'Unknown')} (PMID: {study.get('pmid', 'N/A')})"]

    pico = study.get("sr_pico", {}) or {}
    if pico:
        parts.append(
            "\n## Systematic Review PICO\n"
            f"Population: {pico.get('population', [])}\n"
            f"Intervention: {pico.get('intervention', [])}\n"
            f"Comparison: {pico.get('comparison', [])}\n"
            f"Outcome: {pico.get('outcome', [])}"
        )

    sections = study.get("xml_content", {}).get("sections", []) or []
    for sec in sections:
        name = (sec.get("section", "") or "").strip()
        text = (sec.get("text", "") or "").strip()
        if text:
            parts.append(f"\n### {name}\n{text}")

    tables = study.get("xml_content", {}).get("tables", []) or []
    for i, t in enumerate(tables[:5]):
        raw = (t.get("raw_xml", "") or "").strip()
        if raw:
            parts.append(f"\n### Table {i+1}\n{raw[:3000]}")

    full_text = "\n".join(parts)
    if len(full_text) > 150_000:
        full_text = full_text[:150_000] + "\n\n[... truncated ...]"

    tail = f"\n\nExtract the **{slot}** field as a prose paragraph following the slot-specific guidance. Output JSON only."
    if slot == "outcomes":
        tail = (
            "\n\nExtract the **outcomes** field as a prose paragraph. List the outcomes "
            "the trial planned to MEASURE (primary/secondary, name, scale, time point). "
            "Do NOT include results, effect sizes, or direction of findings. Output JSON only."
        )
    return f"{full_text}{tail}"


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


def _coerce_extraction(obj: dict, slot: str) -> str:
    if not isinstance(obj, dict):
        return ""
    for key in ("extracted", slot, "extraction", "summary", "text"):
        if key in obj:
            val = obj[key]
            if isinstance(val, str):
                return val.strip()
            if isinstance(val, list):
                return "; ".join(str(x) for x in val if x)
            if isinstance(val, dict):
                return json.dumps(val, ensure_ascii=False)
    return ""


async def extract_slot(client, model, study, slot):
    try:
        obj = await _call(
            client, model,
            EXTRACTION_SYSTEM.format(slot=slot, slot_guidance=SLOT_GUIDANCE[slot]),
            build_article_prompt(study, slot),
        )
    except Exception as e:
        return {"slot": slot, "extracted": None, "_error": str(e)}

    extracted_text = _coerce_extraction(obj, slot)
    if not extracted_text:
        return {
            "slot": slot,
            "extracted": None,
            "_error": f"stage-1 returned no usable text. Raw: {json.dumps(obj, ensure_ascii=False)[:300]}",
        }
    return {"slot": slot, "extracted": extracted_text}


async def run_study(client, model, study):
    results = await asyncio.gather(*[extract_slot(client, model, study, slot) for slot in SLOTS])
    return {
        "study_id": study.get("study_id"),
        "pmid": study.get("pmid"),
        "model": model,
        "extractions": {r["slot"]: r for r in results},
    }


async def process_all(args):
    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = AsyncOpenAI()
    files = sorted(dataset_dir.glob("*.json"))
    if args.max_studies:
        files = files[: args.max_studies]

    print(f"[EXTRACT] Model: {args.model}  Studies: {len(files)}  Concurrency: {args.concurrency}")

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
            raw = json.loads(path.read_text(encoding="utf-8"))
            study = raw[0] if isinstance(raw, list) else raw
            label = study.get("study_id") or path.stem
            try:
                result = await run_study(client, args.model, study)
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
    print(f"\n[EXTRACT] Done. OK={counters['ok']}  Skipped={counters['skipped']}  Errors={counters['errors']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_dir", default="rob_cleaned_dataset")
    parser.add_argument("--output_dir", default="results/pico_extractions")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--max_studies", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    asyncio.run(process_all(args))


if __name__ == "__main__":
    main()
