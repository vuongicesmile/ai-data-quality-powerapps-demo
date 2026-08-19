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
    dataset_key: str = "ecommerce-v1"
    data_source_provider: Literal["local", "sharepoint"] = "sharepoint"
    local_dataset_path: Path = Path("sample-data/ecommerce-v1")

    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    sharepoint_host: str = ""
    sharepoint_site_path: str = "/sites/AIDataQualityDev"
    sharepoint_library: str = "DataQualityDatasets"
    sharepoint_dataset_folder: str = "GenericDatasets/ecommerce-v1"
    sharepoint_bronze_library: str = "DataQualityBronze"
    sharepoint_bronze_prefix: str = "GenericDatasets"

    graph_timeout_seconds: int = Field(default=20, ge=1, le=60)
    graph_max_retries: int = Field(default=3, ge=0, le=5)
    source_max_files: int = Field(default=100, ge=1, le=100)
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

    @field_validator("sharepoint_dataset_folder", "sharepoint_bronze_prefix")
    @classmethod
    def strip_slashes(cls, value: str) -> str:
        return value.strip().strip("/")

    def require_power_platform(self) -> None:
        values = {
            "AZURE_TENANT_ID": self.azure_tenant_id,
            "AZURE_CLIENT_ID": self.azure_client_id,
            "AZURE_CLIENT_SECRET": self.azure_client_secret,
            "SHAREPOINT_HOST": self.sharepoint_host,
            "SHAREPOINT_SITE_PATH": self.sharepoint_site_path,
            "SHAREPOINT_LIBRARY": self.sharepoint_library,
            "SHAREPOINT_DATASET_FOLDER": self.sharepoint_dataset_folder,
            "SHAREPOINT_BRONZE_LIBRARY": self.sharepoint_bronze_library,
            "DATAVERSE_URL": self.dataverse_url,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError("Missing Power Platform configuration: " + ", ".join(missing))


@lru_cache
def get_settings() -> Settings:
    return Settings()
