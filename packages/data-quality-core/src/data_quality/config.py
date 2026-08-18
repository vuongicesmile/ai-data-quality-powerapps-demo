"""Environment configuration shared by API and Airflow composition roots."""

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
    data_source_provider: Literal["local", "sharepoint"] = "local"
    orchestration_mode: Literal["local", "airflow"] = "local"
    local_dataset_path: Path = Path("sample-data/ecommerce-v1")

    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    sharepoint_host: str = ""
    sharepoint_site_path: str = "/sites/AIDataQualityDev"
    sharepoint_library: str = "DataQualityDatasets"
    sharepoint_dataset_folder: str = "GenericDatasets/ecommerce-v1"

    graph_timeout_seconds: int = Field(default=20, ge=1, le=60)
    graph_max_retries: int = Field(default=3, ge=0, le=5)
    source_max_files: int = Field(default=500, ge=1, le=5000)
    source_max_file_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)

    bronze_s3_endpoint: str = "http://localhost:8333"
    bronze_s3_bucket: str = "bronze"
    bronze_s3_access_key: str = "seaweed"
    bronze_s3_secret_key: str = "seaweed"
    bronze_prefix: str = "sharepoint/GenericDatasets/ecommerce-v1"

    clickhouse_url: str = "http://localhost:8123"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_timeout_seconds: int = Field(default=15, ge=1, le=60)

    airflow_api_url: str = "http://localhost:8080/api/v1"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    airflow_dag_id: str = "sharepoint_generic_dataset_bronze_ingestion"

    generic_llm_rules_enabled: bool = False
    groq_api_key: str = ""

    @field_validator("sharepoint_dataset_folder", "bronze_prefix")
    @classmethod
    def strip_slashes(cls, value: str) -> str:
        return value.strip().strip("/")

    def require_sharepoint(self) -> None:
        values = {
            "AZURE_TENANT_ID": self.azure_tenant_id,
            "AZURE_CLIENT_ID": self.azure_client_id,
            "AZURE_CLIENT_SECRET": self.azure_client_secret,
            "SHAREPOINT_HOST": self.sharepoint_host,
            "SHAREPOINT_SITE_PATH": self.sharepoint_site_path,
            "SHAREPOINT_LIBRARY": self.sharepoint_library,
            "SHAREPOINT_DATASET_FOLDER": self.sharepoint_dataset_folder,
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError("Missing SharePoint configuration: " + ", ".join(missing))


@lru_cache
def get_settings() -> Settings:
    return Settings()
