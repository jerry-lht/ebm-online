"""Smoke tests for configuration loading."""

import os


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8080/v1")

    from config.settings import Settings

    s = Settings()
    assert s.openai_api_key == "sk-test-key"
    assert s.openai_base_url == "http://localhost:8080/v1"
    assert s.llm_model == "gpt-5.2"
    assert s.llm_temperature == 0.0
    assert s.database_url == "postgresql://ebm:ebm123@localhost:5432/ebm_online"


def test_settings_custom_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-custom")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/mydb")

    from config.settings import Settings

    s = Settings()
    assert s.llm_model == "gpt-4o"
    assert s.database_url == "postgresql://user:pass@db:5432/mydb"
