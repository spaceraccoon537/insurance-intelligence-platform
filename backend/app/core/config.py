from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Insurance Intelligence Platform API"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:5173"
    database_path: Path = Path("data/local/documents.sqlite3")
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    rag_top_k: int = Field(default=5, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_prefix="INSURANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
