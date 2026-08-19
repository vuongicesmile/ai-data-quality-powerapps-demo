"""Power Platform-native composition root."""

from __future__ import annotations

from functools import lru_cache

from data_quality.application import GenericDatasetWorkflow, IngestionService
from data_quality.config import Settings, get_settings
from data_quality.domain.ports import DatasetSource
from data_quality.integrations.dataverse import (
    DataverseAuth,
    DataverseBronzeStore,
    DataverseClient,
    DataverseStateRepository,
    DataverseWarehouseRepository,
)
from data_quality.integrations.local_source import LocalDatasetSource
from data_quality.integrations.microsoft_graph import (
    MicrosoftGraphAuth,
    MicrosoftGraphClient,
    SharePointListDatasetSource,
)


@lru_cache
def get_graph() -> MicrosoftGraphClient:
    settings = get_settings()
    settings.require_power_platform()
    auth = MicrosoftGraphAuth(
        settings.azure_tenant_id,
        settings.azure_client_id,
        settings.azure_client_secret,
        timeout_seconds=settings.graph_timeout_seconds,
    )
    return MicrosoftGraphClient(
        auth,
        timeout_seconds=settings.graph_timeout_seconds,
        max_retries=settings.graph_max_retries,
        maximum_items=settings.source_max_rows,
        maximum_download_bytes=settings.source_max_file_bytes,
    )


@lru_cache
def get_source() -> DatasetSource:
    settings = get_settings()
    if settings.data_source_provider == "local":
        return LocalDatasetSource(
            settings.local_dataset_path, maximum_bytes=settings.source_max_file_bytes
        )
    return SharePointListDatasetSource(
        get_graph(),
        hostname=settings.sharepoint_host,
        site_path=settings.sharepoint_site_path,
        list_names=settings.source_list_names(),
        maximum_rows=settings.source_max_rows,
    )


@lru_cache
def get_bronze_store() -> DataverseBronzeStore:
    settings = get_settings()
    return DataverseBronzeStore(
        get_dataverse(),
        maximum_rows=settings.source_max_rows,
    )


@lru_cache
def get_dataverse() -> DataverseClient:
    settings = get_settings()
    settings.require_power_platform()
    auth = DataverseAuth(
        settings.azure_tenant_id,
        settings.azure_client_id,
        settings.azure_client_secret,
        settings.dataverse_url,
        timeout_seconds=settings.dataverse_timeout_seconds,
    )
    return DataverseClient(
        auth,
        api_version=settings.dataverse_api_version,
        timeout_seconds=settings.dataverse_timeout_seconds,
        max_retries=settings.dataverse_max_retries,
        maximum_rows=settings.dataverse_maximum_rows,
    )


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService(get_source(), get_bronze_store())


@lru_cache
def get_workflow() -> GenericDatasetWorkflow:
    client = get_dataverse()
    return GenericDatasetWorkflow(
        bronze=get_bronze_store(),
        states=DataverseStateRepository(client),
        warehouse=DataverseWarehouseRepository(client),
    )


def settings_dependency() -> Settings:
    return get_settings()
