"""Composition root: the only place infrastructure implementations are selected."""

from __future__ import annotations

from functools import lru_cache

from data_quality.application import GenericDatasetWorkflow, IngestionService
from data_quality.config import Settings, get_settings
from data_quality.domain.ports import DatasetSource
from data_quality.integrations.airflow import AirflowClient
from data_quality.integrations.clickhouse import (
    ClickHouseClient,
    ClickHouseStateRepository,
    ClickHouseWarehouseRepository,
)
from data_quality.integrations.local_source import LocalDatasetSource
from data_quality.integrations.microsoft_graph import (
    MicrosoftGraphAuth,
    MicrosoftGraphClient,
    SharePointDatasetSource,
)
from data_quality.integrations.s3 import S3BronzeStore


@lru_cache
def get_source() -> DatasetSource:
    settings = get_settings()
    if settings.data_source_provider == "local":
        return LocalDatasetSource(
            settings.local_dataset_path, maximum_bytes=settings.source_max_file_bytes
        )
    settings.require_sharepoint()
    auth = MicrosoftGraphAuth(
        settings.azure_tenant_id,
        settings.azure_client_id,
        settings.azure_client_secret,
        timeout_seconds=settings.graph_timeout_seconds,
    )
    client = MicrosoftGraphClient(
        auth,
        timeout_seconds=settings.graph_timeout_seconds,
        max_retries=settings.graph_max_retries,
        maximum_items=settings.source_max_files,
        maximum_download_bytes=settings.source_max_file_bytes,
    )
    return SharePointDatasetSource(
        client,
        hostname=settings.sharepoint_host,
        site_path=settings.sharepoint_site_path,
        library=settings.sharepoint_library,
        folder=settings.sharepoint_dataset_folder,
    )


@lru_cache
def get_bronze_store() -> S3BronzeStore:
    settings = get_settings()
    return S3BronzeStore(
        endpoint_url=settings.bronze_s3_endpoint,
        bucket=settings.bronze_s3_bucket,
        access_key=settings.bronze_s3_access_key,
        secret_key=settings.bronze_s3_secret_key,
        prefix=settings.bronze_prefix,
        maximum_bytes=settings.source_max_file_bytes,
    )


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService(get_source(), get_bronze_store())


@lru_cache
def get_clickhouse() -> ClickHouseClient:
    settings = get_settings()
    return ClickHouseClient(
        settings.clickhouse_url,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        timeout_seconds=settings.clickhouse_timeout_seconds,
    )


@lru_cache
def get_workflow() -> GenericDatasetWorkflow:
    client = get_clickhouse()
    return GenericDatasetWorkflow(
        bronze=get_bronze_store(),
        states=ClickHouseStateRepository(client),
        warehouse=ClickHouseWarehouseRepository(client),
    )


@lru_cache
def get_airflow() -> AirflowClient:
    settings = get_settings()
    return AirflowClient(
        settings.airflow_api_url,
        username=settings.airflow_username,
        password=settings.airflow_password,
    )


def settings_dependency() -> Settings:
    return get_settings()
