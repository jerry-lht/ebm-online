"""OpenAI-compatible LLM backend."""

from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

DEFAULT_LLM_MODEL = "gpt-5-mini"
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm_config.json"


def _load_file_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in LLM config file: {CONFIG_PATH}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"LLM config file must contain a JSON object: {CONFIG_PATH}")
    return payload


def _config_value(file_config: dict[str, Any], file_key: str, env_name: str) -> str | None:
    value = file_config.get(file_key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    env_value = os.environ.get(env_name)
    if env_value and env_value.strip():
        return env_value.strip()
    return None


def _required_config_value(file_config: dict[str, Any], file_key: str, env_name: str) -> str:
    value = _config_value(file_config, file_key, env_name)
    if value:
        return value
    raise ValueError(
        f"Missing required LLM API config: set '{file_key}' in {CONFIG_PATH} "
        f"or environment variable {env_name}"
    )


def make_client() -> Any:
    file_config = _load_file_config()
    api_key = _required_config_value(file_config, "api_key", "META_EXTRACT_OPENAI_API_KEY")
    base_url = _config_value(file_config, "base_url", "META_EXTRACT_OPENAI_BASE_URL")

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local env
        raise ModuleNotFoundError("openai package is required for llm mode") from exc

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _extract_json_substring(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        raise JSONDecodeError("empty response", text, 0)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end != -1 and end > start:
            return stripped[start : end + 1]
    raise JSONDecodeError("no json object found", text, 0)


def response_text_to_json(text: str) -> Any:
    try:
        return json.loads(text)
    except JSONDecodeError:
        return json.loads(_extract_json_substring(text))


def repair_json_payload(*, model: str, raw_text: str) -> Any:
    client = make_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You repair malformed model outputs into strict JSON. Return JSON only. Do not explain."},
            {"role": "user", "content": raw_text},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content
    if isinstance(content, str):
        return response_text_to_json(content)
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
        return response_text_to_json("".join(texts))
    raise ValueError("Unsupported repair response content shape")


def default_model_name() -> str:
    file_config = _load_file_config()
    return _config_value(file_config, "model", "META_EXTRACT_OPENAI_MODEL") or DEFAULT_LLM_MODEL
