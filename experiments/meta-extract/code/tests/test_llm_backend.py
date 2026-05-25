import json
import sys
import types

import pytest

from meta_extract import llm_backend


def test_default_model_name_prefers_file_config(tmp_path: pytest.TempPathFactory, monkeypatch):
    config_path = tmp_path / "llm_config.json"
    config_path.write_text(json.dumps({"model": "file-model"}), encoding="utf-8")
    monkeypatch.setattr(llm_backend, "CONFIG_PATH", config_path)
    monkeypatch.setenv("META_EXTRACT_OPENAI_MODEL", "env-model")

    assert llm_backend.default_model_name() == "file-model"


def test_make_client_prefers_file_config_over_env(tmp_path: pytest.TempPathFactory, monkeypatch):
    config_path = tmp_path / "llm_config.json"
    config_path.write_text(
        json.dumps(
            {
                "api_key": "file-key",
                "base_url": "https://file.example/v1",
                "model": "file-model",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(llm_backend, "CONFIG_PATH", config_path)
    monkeypatch.setenv("META_EXTRACT_OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("META_EXTRACT_OPENAI_BASE_URL", "https://env.example/v1")

    calls = []

    class DummyOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))

    llm_backend.make_client()

    assert calls == [{"api_key": "file-key", "base_url": "https://file.example/v1"}]


def test_make_client_falls_back_to_env_when_file_missing(tmp_path: pytest.TempPathFactory, monkeypatch):
    monkeypatch.setattr(llm_backend, "CONFIG_PATH", tmp_path / "missing.json")
    monkeypatch.setenv("META_EXTRACT_OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("META_EXTRACT_OPENAI_BASE_URL", "https://env.example/v1")

    calls = []

    class DummyOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))

    llm_backend.make_client()

    assert calls == [{"api_key": "env-key", "base_url": "https://env.example/v1"}]


def test_make_client_requires_api_key_in_file_or_env(tmp_path: pytest.TempPathFactory, monkeypatch):
    config_path = tmp_path / "llm_config.json"
    config_path.write_text(json.dumps({"base_url": "https://file.example/v1"}), encoding="utf-8")
    monkeypatch.setattr(llm_backend, "CONFIG_PATH", config_path)
    monkeypatch.delenv("META_EXTRACT_OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing required LLM API config"):
        llm_backend.make_client()
