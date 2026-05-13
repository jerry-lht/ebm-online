"""Application settings using pydantic-settings v2."""

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Prefer project .env over inherited shell variables for reproducible runs."""
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    # LLM
    openai_api_key: str = Field("", description="OpenAI API key")
    openai_base_url: str = Field(
        "https://api.openai.com/v1", description="OpenAI-compatible base URL"
    )
    llm_model: str = Field("gpt-5.2", description="Default LLM model name")
    llm_temperature: float = Field(0.0, description="Default temperature")

    # Elasticsearch
    es_host: str = Field(
        "http://localhost:9200", description="Elasticsearch host URL"
    )

    # Redis
    redis_url: str = Field(
        "redis://localhost:6379/0", description="Redis connection URL"
    )

    # Database
    database_url: str = Field(
        "postgresql://ebm:ebm123@localhost:5432/ebm_online",
        description="PostgreSQL connection URL",
    )

    # Pricing (per 1M tokens, USD)
    llm_input_price_per_1m: float = Field(
        2.0, description="Input token price per 1M tokens"
    )
    llm_output_price_per_1m: float = Field(
        8.0, description="Output token price per 1M tokens"
    )


settings = Settings()
