"""Semantic match judges for Q2PICO smoke evaluation."""

from __future__ import annotations

import json
import re
import concurrent.futures
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
BACKEND_SRC = ROOT / "backend" / "src"
if BACKEND_SRC.exists() and str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from ebm_backend.online_pipeline.infrastructure.llm import call_llm_json
from ebm_backend.online_pipeline.infrastructure.llm import load_llm_config as load_online_llm_config
from benchmark.online_pipeline.shared.jsonl import append_jsonl, read_jsonl, write_jsonl
from benchmark.online_pipeline.shared.prompts import render_prompt_template


SLOTS = ("P", "I", "C", "O")
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
JUDGE_PROMPT = PROMPT_DIR / "judge_semantic_match_v1.txt"


def judge_predictions(
    *,
    instances: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    gold_by_id: dict[str, dict[str, Any]],
    judge_mode: str,
    llm_config: str | Path,
    output_path: str | Path | None = None,
    failure_output_path: str | Path | None = None,
    resume: bool = False,
    workers: int = 1,
) -> list[dict[str, Any]]:
    if judge_mode == "normalized":
        rows = normalized_match_judge(instances=instances, predictions=predictions, gold_by_id=gold_by_id)
        if output_path is not None:
            write_jsonl(output_path, rows)
        return rows
    if judge_mode == "llm":
        return llm_match_judge(
            instances=instances,
            predictions=predictions,
            gold_by_id=gold_by_id,
            llm_config=llm_config,
            output_path=output_path,
            failure_output_path=failure_output_path,
            resume=resume,
            workers=workers,
        )
    raise ValueError("judge_mode must be 'llm' or 'normalized'")


def normalized_match_judge(
    *,
    instances: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    gold_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    rows: list[dict[str, Any]] = []
    for instance in instances:
        instance_id = str(instance["instance_id"])
        prediction = predictions_by_id[instance_id]
        gold = gold_by_id[instance_id]
        for slot in SLOTS:
            rows.append(_normalized_slot_match_row(instance_id=instance_id, slot=slot, gold=gold, prediction=prediction))
    return rows


def llm_match_judge(
    *,
    instances: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    gold_by_id: dict[str, dict[str, Any]],
    llm_config: str | Path,
    output_path: str | Path | None = None,
    failure_output_path: str | Path | None = None,
    resume: bool = False,
    workers: int = 1,
) -> list[dict[str, Any]]:
    config = load_llm_config(llm_config)
    if workers <= 0:
        raise ValueError("workers must be positive")
    predictions_by_id = {str(row["instance_id"]): row for row in predictions}
    existing_rows = _completed_resume_rows(output_path) if resume and output_path is not None else []
    completed_instance_ids = _complete_instance_ids(existing_rows)
    if output_path is not None:
        write_jsonl(output_path, existing_rows)
    pending_instances = [instance for instance in instances if str(instance["instance_id"]) not in completed_instance_ids]
    rows: list[dict[str, Any]] = list(existing_rows)

    def judge_one(instance: dict[str, Any]) -> list[dict[str, Any]]:
        instance_id = str(instance["instance_id"])
        prediction = predictions_by_id[instance_id]
        gold = gold_by_id[instance_id]
        prompt = _build_match_prompt(
            question_text=str(instance["question_text"]),
            gold={slot: list(gold.get(slot) or []) for slot in SLOTS},
            predicted={slot: list(prediction.get(slot) or []) for slot in SLOTS},
        )
        parsed = _call_llm_json(config=config, prompt=prompt)
        return _coerce_llm_match_rows(instance_id=instance_id, parsed=parsed, gold=gold, prediction=prediction)

    max_workers = min(workers, max(1, len(pending_instances)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_instance_id = {
            executor.submit(judge_one, instance): str(instance["instance_id"])
            for instance in pending_instances
        }
        for future in concurrent.futures.as_completed(future_to_instance_id):
            instance_id = future_to_instance_id[future]
            try:
                instance_rows = future.result()
            except Exception as exc:
                if failure_output_path is not None:
                    append_jsonl(
                        failure_output_path,
                        [
                            {
                                "instance_id": instance_id,
                                "error_type": type(exc).__name__,
                                "message": str(exc),
                                "judge_mode": "llm",
                            }
                        ],
                    )
                continue
            rows.extend(instance_rows)
            if output_path is not None:
                append_jsonl(output_path, instance_rows)
    return rows


def load_llm_config(path: str | Path) -> dict[str, str]:
    config = load_online_llm_config(path, required=True)
    if config is None:
        raise ValueError(f"Missing LLM config: {path}")
    return config.to_dict()


def _normalized_slot_match_row(
    *,
    instance_id: str,
    slot: str,
    gold: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    gold_items = [str(item) for item in (gold.get(slot) or [])]
    predicted_items = [str(item) for item in (prediction.get(slot) or [])]
    unmatched_gold = set(range(len(gold_items)))
    unmatched_predicted = set(range(len(predicted_items)))
    matches: list[dict[str, Any]] = []
    for gold_index, gold_item in enumerate(gold_items):
        for predicted_index, predicted_item in enumerate(predicted_items):
            if predicted_index not in unmatched_predicted:
                continue
            if _normalize(gold_item) == _normalize(predicted_item):
                matches.append(
                    {
                        "gold_index": gold_index,
                        "predicted_index": predicted_index,
                        "rationale": "Normalized exact match.",
                    }
                )
                unmatched_gold.discard(gold_index)
                unmatched_predicted.discard(predicted_index)
                break
    return {
        "instance_id": instance_id,
        "slot": slot,
        "gold_items": gold_items,
        "predicted_items": predicted_items,
        "matches": matches,
        "unmatched_gold_indices": sorted(unmatched_gold),
        "unmatched_predicted_indices": sorted(unmatched_predicted),
        "judge_mode": "normalized",
    }


def _completed_resume_rows(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    resolved = Path(path)
    if not resolved.exists():
        return []
    rows = read_jsonl(resolved)
    complete_ids = _complete_instance_ids(rows)
    return [row for row in rows if str(row.get("instance_id")) in complete_ids]


def _complete_instance_ids(rows: list[dict[str, Any]]) -> set[str]:
    slots_by_instance: dict[str, set[str]] = {}
    for row in rows:
        instance_id = str(row.get("instance_id") or "")
        slot = str(row.get("slot") or "")
        if instance_id and slot in SLOTS:
            slots_by_instance.setdefault(instance_id, set()).add(slot)
    return {instance_id for instance_id, slots in slots_by_instance.items() if set(SLOTS).issubset(slots)}


def _build_match_prompt(*, question_text: str, gold: dict[str, list[str]], predicted: dict[str, list[str]]) -> str:
    return render_prompt_template(
        JUDGE_PROMPT,
        {
            "question_text": question_text,
            "gold_json": json.dumps(gold, ensure_ascii=False),
            "predicted_json": json.dumps(predicted, ensure_ascii=False),
        },
    )


def _call_llm_json(*, config: dict[str, str], prompt: str) -> dict[str, Any]:
    return call_llm_json(
        config=config,
        system="You are a strict clinical PICO semantic matching judge. Return only valid JSON.",
        prompt=prompt,
    )


def _coerce_llm_match_rows(
    *,
    instance_id: str,
    parsed: dict[str, Any],
    gold: dict[str, Any],
    prediction: dict[str, Any],
) -> list[dict[str, Any]]:
    slots_payload = parsed.get("slots")
    if not isinstance(slots_payload, dict):
        raise ValueError("LLM judge response must contain a 'slots' object")
    rows: list[dict[str, Any]] = []
    for slot in SLOTS:
        slot_payload = slots_payload.get(slot) or {}
        if not isinstance(slot_payload, dict):
            raise ValueError(f"LLM judge slot {slot} must be an object")
        gold_items = [str(item) for item in (gold.get(slot) or [])]
        predicted_items = [str(item) for item in (prediction.get(slot) or [])]
        matches = _coerce_matches(slot_payload.get("matches") or [], len(gold_items), len(predicted_items))
        matched_gold = {match["gold_index"] for match in matches}
        matched_predicted = {match["predicted_index"] for match in matches}
        rows.append(
            {
                "instance_id": instance_id,
                "slot": slot,
                "gold_items": gold_items,
                "predicted_items": predicted_items,
                "matches": matches,
                "unmatched_gold_indices": [
                    index for index in range(len(gold_items)) if index not in matched_gold
                ],
                "unmatched_predicted_indices": [
                    index for index in range(len(predicted_items)) if index not in matched_predicted
                ],
                "judge_mode": "llm",
            }
        )
    return rows


def _coerce_matches(value: Any, gold_count: int, predicted_count: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("LLM judge matches must be a list")
    seen_gold: set[int] = set()
    seen_predicted: set[int] = set()
    matches: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each LLM judge match must be an object")
        gold_index = int(item.get("gold_index"))
        predicted_index = int(item.get("predicted_index"))
        if gold_index < 0 or gold_index >= gold_count:
            raise ValueError(f"gold_index out of range: {gold_index}")
        if predicted_index < 0 or predicted_index >= predicted_count:
            raise ValueError(f"predicted_index out of range: {predicted_index}")
        if gold_index in seen_gold or predicted_index in seen_predicted:
            continue
        seen_gold.add(gold_index)
        seen_predicted.add(predicted_index)
        matches.append(
            {
                "gold_index": gold_index,
                "predicted_index": predicted_index,
                "rationale": str(item.get("rationale") or ""),
            }
        )
    return matches


def _parse_json_object(text: str) -> dict[str, Any]:
    candidate = _extract_json_object_text(text)
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _extract_json_object_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return stripped
    return stripped[start : end + 1]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())
