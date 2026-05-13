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

    max_iterations: int = Field(default=15, ge=1, validation_alias="MAX_ITERATIONS")
    hi_mock_llm: bool = Field(default=False, validation_alias="HI_MOCK_LLM")
    log_llm_io: bool = Field(default=False, validation_alias="LOG_LLM_IO")

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    max_csv_rows: int = Field(default=200_000, validation_alias="MAX_CSV_ROWS")

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
