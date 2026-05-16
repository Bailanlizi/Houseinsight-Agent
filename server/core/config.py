from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="qwen-turbo", validation_alias="OPENAI_MODEL")
    answer_llm_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        validation_alias="ANSWER_LLM_TEMPERATURE",
    )

    max_iterations: int = Field(default=10, ge=1, validation_alias="MAX_ITERATIONS")
    max_cleaning_iterations: int = Field(
        default=4,
        ge=1,
        validation_alias="MAX_CLEANING_ITERATIONS",
    )
    max_search_text_per_run: int = Field(
        default=1,
        ge=0,
        validation_alias="MAX_SEARCH_TEXT_PER_RUN",
    )
    max_get_basic_stats_per_run: int = Field(
        default=1,
        ge=0,
        validation_alias="MAX_GET_BASIC_STATS_PER_RUN",
    )
    max_filter_rows_per_run: int = Field(
        default=3,
        ge=0,
        validation_alias="MAX_FILTER_ROWS_PER_RUN",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        ge=10.0,
        le=600.0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    llm_max_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        validation_alias="LLM_MAX_RETRIES",
    )
    hi_mock_llm: bool = Field(default=False, validation_alias="HI_MOCK_LLM")
    log_llm_io: bool = Field(default=False, validation_alias="LOG_LLM_IO")

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    max_csv_rows: int = Field(default=200_000, validation_alias="MAX_CSV_ROWS")

    max_prior_transcript_chars: int = Field(
        default=4000,
        ge=500,
        le=50_000,
        validation_alias="MAX_PRIOR_TRANSCRIPT_CHARS",
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
