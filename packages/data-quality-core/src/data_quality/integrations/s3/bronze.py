"""Versioned Bronze object and manifest adapter for S3-compatible storage."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from data_quality.domain.errors import (
    BudgetExceededError,
    ResourceNotFoundError,
    UpstreamUnavailableError,
)
from data_quality.domain.models import BronzeAsset
from data_quality.domain.ports import DatasetSource


class S3BronzeStore:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        prefix: str,
        maximum_bytes: int = 25 * 1024 * 1024,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.maximum_bytes = maximum_bytes
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def publish_batch(
        self,
        dataset_key: str,
        source: DatasetSource,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        self._ensure_bucket()
        source_assets = list(source.list_files(dataset_key))
        if not source_assets:
            raise ResourceNotFoundError(f"No CSV assets found for dataset: {dataset_key}")
        previous = self._latest_manifest(optional=True)
        previous_versions = {
            item["source_id"]: item["source_version"] for item in (previous or {}).get("assets", [])
        }
        current_versions = {item.source_id: item.source_version for item in source_assets}
        if not force and previous and previous_versions == current_versions:
            return {**previous, "publication_status": "UNCHANGED"}

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        batch_id = f"batch_{timestamp.lower()}"
        published: list[dict[str, Any]] = []
        for asset in source_assets:
            content = source.get_file_content(asset.source_id)
            if len(content) > self.maximum_bytes:
                raise BudgetExceededError(f"CSV asset exceeds Bronze limit: {asset.file_name}")
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            if not rows:
                raise ValueError(f"CSV asset is empty: {asset.file_name}")
            digest = hashlib.sha256(content).hexdigest()
            bronze_key = f"{self.prefix}/objects/{timestamp}_{asset.file_name}"
            self.client.put_object(
                Bucket=self.bucket,
                Key=bronze_key,
                Body=content,
                ContentType="text/csv",
                Metadata={
                    "source-id-hash": hashlib.sha256(asset.source_id.encode()).hexdigest(),
                    "source-version-hash": hashlib.sha256(
                        asset.source_version.encode()
                    ).hexdigest(),
                },
            )
            published.append(
                BronzeAsset(
                    **asset.model_dump(),
                    bronze_key=bronze_key,
                    content_hash=digest,
                    row_count=len(rows),
                    columns=list(rows[0]),
                ).model_dump()
            )
        manifest = {
            "dataset_key": dataset_key,
            "batch_id": batch_id,
            "provider": source_assets[0].provider,
            "published_at": datetime.now(UTC).isoformat(),
            "assets": published,
            "publication_status": "PUBLISHED",
        }
        manifest_key = f"{self.prefix}/_manifests/{timestamp}.json"
        manifest["manifest_key"] = manifest_key
        self.client.put_object(
            Bucket=self.bucket,
            Key=manifest_key,
            Body=json.dumps(manifest, sort_keys=True).encode(),
            ContentType="application/json",
        )
        return manifest

    def load_latest_batch(self, dataset_key: str) -> tuple[dict[str, Any], list[BronzeAsset]]:
        manifest = self._latest_manifest(optional=False)
        if manifest.get("dataset_key") != dataset_key:
            raise ResourceNotFoundError(f"No Bronze manifest found for dataset: {dataset_key}")
        assets = [BronzeAsset.model_validate(item) for item in manifest.get("assets", [])]
        if not assets:
            raise ResourceNotFoundError("Latest Bronze manifest contains no assets")
        return manifest, assets

    def read_asset(self, asset: BronzeAsset) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=asset.bronze_key)
            length = int(response.get("ContentLength", 0))
            if length > self.maximum_bytes:
                raise BudgetExceededError(f"Bronze asset exceeds the byte limit: {asset.file_name}")
            content = response["Body"].read(self.maximum_bytes + 1)
        except BudgetExceededError:
            raise
        except (BotoCoreError, ClientError, KeyError) as exc:
            raise UpstreamUnavailableError(
                f"Bronze asset could not be read: {asset.file_name}"
            ) from exc
        if len(content) > self.maximum_bytes:
            raise BudgetExceededError(f"Bronze asset exceeds the byte limit: {asset.file_name}")
        return content

    def _latest_manifest(self, *, optional: bool) -> dict[str, Any] | None:
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=f"{self.prefix}/_manifests/",
                MaxKeys=1000,
            )
            objects = sorted(response.get("Contents", []), key=lambda item: item["Key"])
            if not objects:
                if optional:
                    return None
                raise ResourceNotFoundError("No Bronze manifest has been published")
            payload = self.client.get_object(Bucket=self.bucket, Key=objects[-1]["Key"])[
                "Body"
            ].read()
            result = json.loads(payload)
        except ResourceNotFoundError:
            raise
        except self.client.exceptions.NoSuchBucket:
            if optional:
                return None
            raise ResourceNotFoundError("Bronze bucket does not exist") from None
        except (BotoCoreError, ClientError, KeyError, json.JSONDecodeError) as exc:
            raise UpstreamUnavailableError("Bronze manifest inventory is unavailable") from exc
        if not isinstance(result, dict):
            raise UpstreamUnavailableError("Bronze manifest is invalid")
        return result

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except (BotoCoreError, ClientError) as exc:
                raise UpstreamUnavailableError("Bronze bucket could not be created") from exc
