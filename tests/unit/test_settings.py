"""Smoke tests for configuration loading."""

import os

from pydantic_settings import SettingsConfigDict


def test_settings_loads_from_env(monkeypatch):
    from ebm_backend.shared.config.settings import Settings

    s = Settings(
        openai_api_key="sk-test-key",
        openai_base_url="http://localhost:8080/v1",
        llm_model="gpt-5.2",
    )
    assert s.openai_api_key == "sk-test-key"
    assert s.openai_base_url == "http://localhost:8080/v1"
    assert s.llm_model == "gpt-5.2"
    assert s.llm_temperature == 0.0
    assert s.database_url == "postgresql://ebm:ebm123@localhost:5432/ebm_online"


def test_settings_custom_values(monkeypatch):
    from ebm_backend.shared.config.settings import Settings

    s = Settings(
        openai_api_key="sk-custom",
        llm_model="gpt-4o",
        database_url="postgresql://user:pass@db:5432/mydb",
    )
    assert s.llm_model == "gpt-4o"
    assert s.database_url == "postgresql://user:pass@db:5432/mydb"


def test_settings_prefers_dotenv_over_shell_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-dotenv",
                "OPENAI_BASE_URL=https://dotenv.example/v1",
                "LLM_MODEL=dotenv-model",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-shell")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://shell.example/v1")
    monkeypatch.setenv("LLM_MODEL", "shell-model")

    from ebm_backend.shared.config.settings import Settings

    class TestSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_file),
            env_file_encoding="utf-8",
            extra="ignore",
        )

    s = TestSettings()
    assert s.openai_api_key == "sk-dotenv"
    assert s.openai_base_url == "https://dotenv.example/v1"
    assert s.llm_model == "dotenv-model"
