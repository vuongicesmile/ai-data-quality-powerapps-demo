"""Power Platform worker configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    dataset_key: str = "timerapp-v1"
    data_source_provider: Literal["local", "sharepoint"] = "sharepoint"
    local_dataset_path: Path = Path("sample-data/ecommerce-v1")

    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    sharepoint_host: str = ""
    sharepoint_site_path: str = "/sites/TimerApp"
    sharepoint_source_lists: str = (
        "TimerList_AllProject01,TimerList_AllProject02,"
        "TimerList_AllProject03,TimerList_AllProject04"
    )

    graph_timeout_seconds: int = Field(default=20, ge=1, le=60)
    graph_max_retries: int = Field(default=3, ge=0, le=5)
    source_max_lists: int = Field(default=4, ge=1, le=4)
    source_max_file_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    source_max_rows: int = Field(default=5000, ge=1, le=100_000)
    maximum_evidence_rows: int = Field(default=100, ge=1, le=1000)

    dataverse_url: str = ""
    dataverse_api_version: str = "v9.2"
    dataverse_timeout_seconds: int = Field(default=20, ge=1, le=60)
    dataverse_max_retries: int = Field(default=3, ge=0, le=5)
    dataverse_maximum_rows: int = Field(default=25_000, ge=100, le=100_000)

    generic_llm_rules_enabled: bool = False
    groq_api_key: str = ""

    @field_validator("sharepoint_site_path")
    @classmethod
    def strip_slashes(cls, value: str) -> str:
        return "/" + value.strip().strip("/")

    def source_list_names(self) -> tuple[str, ...]:
        names = tuple(
            name.strip() for name in self.sharepoint_source_lists.split(",") if name.strip()
        )
        if not names or len(names) > self.source_max_lists:
            raise ValueError(
                f"SHAREPOINT_SOURCE_LISTS must contain 1-{self.source_max_lists} names"
            )
        if len(set(name.casefold() for name in names)) != len(names):
            raise ValueError("SHAREPOINT_SOURCE_LISTS contains duplicate names")
        return names

    def require_power_platform(self) -> None:
        values = {
            "AZURE_TENANT_ID": self.azure_tenant_id,
            "AZURE_CLIENT_ID": self.azure_client_id,
            "AZURE_CLIENT_SECRET": self.azure_client_secret,
            "SHAREPOINT_HOST": self.sharepoint_host,
            "SHAREPOINT_SITE_PATH": self.sharepoint_site_path,
            "SHAREPOINT_SOURCE_LISTS": self.sharepoint_source_lists,
            "DATAVERSE_URL": self.dataverse_url,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError("Missing Power Platform configuration: " + ", ".join(missing))
        self.source_list_names()


@lru_cache
def get_settings() -> Settings:
    return Settings()
