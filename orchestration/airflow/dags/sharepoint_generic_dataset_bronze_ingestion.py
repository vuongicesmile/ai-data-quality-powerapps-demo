"""SharePoint/Microsoft Graph to versioned SeaweedFS Bronze ingestion DAG."""

from __future__ import annotations

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from data_quality.application import IngestionService
from data_quality.config import Settings
from data_quality.integrations.local_source import LocalDatasetSource
from data_quality.integrations.microsoft_graph import (
    MicrosoftGraphAuth,
    MicrosoftGraphClient,
    SharePointDatasetSource,
)
from data_quality.integrations.s3 import S3BronzeStore


def ingest_to_bronze(**context):
    settings = Settings()
    if settings.data_source_provider == "sharepoint":
        settings.require_sharepoint()
        auth = MicrosoftGraphAuth(
            settings.azure_tenant_id,
            settings.azure_client_id,
            settings.azure_client_secret,
            timeout_seconds=settings.graph_timeout_seconds,
        )
        source = SharePointDatasetSource(
            MicrosoftGraphClient(
                auth,
                timeout_seconds=settings.graph_timeout_seconds,
                max_retries=settings.graph_max_retries,
                maximum_items=settings.source_max_files,
                maximum_download_bytes=settings.source_max_file_bytes,
            ),
            hostname=settings.sharepoint_host,
            site_path=settings.sharepoint_site_path,
            library=settings.sharepoint_library,
            folder=settings.sharepoint_dataset_folder,
        )
    else:
        source = LocalDatasetSource(
            settings.local_dataset_path, maximum_bytes=settings.source_max_file_bytes
        )
    bronze = S3BronzeStore(
        endpoint_url=settings.bronze_s3_endpoint,
        bucket=settings.bronze_s3_bucket,
        access_key=settings.bronze_s3_access_key,
        secret_key=settings.bronze_s3_secret_key,
        prefix=settings.bronze_prefix,
        maximum_bytes=settings.source_max_file_bytes,
    )
    conf = (context.get("dag_run").conf or {}) if context.get("dag_run") else {}
    dataset_key = str(conf.get("dataset_key") or settings.dataset_key)
    return IngestionService(source, bronze).run(dataset_key, force=bool(conf.get("force")))


with DAG(
    dag_id="sharepoint_generic_dataset_bronze_ingestion",
    description="SharePoint Online via Microsoft Graph to versioned SeaweedFS Bronze",
    schedule=None,
    start_date=days_ago(1),
    catchup=False,
    tags=["sharepoint", "microsoft_graph", "bronze", "generic_demo"],
) as dag:
    publish_bronze_batch = PythonOperator(
        task_id="publish_bronze_batch",
        python_callable=ingest_to_bronze,
    )
