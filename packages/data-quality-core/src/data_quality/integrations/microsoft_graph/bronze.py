"""Immutable SharePoint document-library Bronze store."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from data_quality.domain.errors import BudgetExceededError, ResourceNotFoundError
from data_quality.domain.models import BronzeAsset
from data_quality.domain.ports import DatasetSource

from .client import MicrosoftGraphClient


class SharePointBronzeStore:
    def __init__(
        self, client: MicrosoftGraphClient, *, hostname: str, site_path: str,
        library: str, prefix: str = "GenericDatasets", maximum_bytes: int = 25 * 1024 * 1024,
        maximum_rows: int = 5000,
    ) -> None:
        self.client = client
        self.hostname = hostname
        self.site_path = site_path
        self.library = library
        self.prefix = prefix.strip("/")
        self.maximum_bytes = maximum_bytes
        self.maximum_rows = maximum_rows
        self._drive_id = ""

    def publish_batch(
        self, dataset_key: str, source: DatasetSource, *, force: bool = False
    ) -> dict[str, Any]:
        source_assets = list(source.list_files(dataset_key))
        if not source_assets:
            raise ResourceNotFoundError(f"No CSV assets found for dataset: {dataset_key}")
        previous = self._latest_manifest(dataset_key, optional=True)
        previous_versions = {
            item["source_id"]: item["source_version"] for item in (previous or {}).get("assets", [])
        }
        current_versions = {item.source_id: item.source_version for item in source_assets}
        if not force and previous and previous_versions == current_versions:
            return {**previous, "publication_status": "UNCHANGED"}

        drive_id = self._resolve_drive()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        batch_id = f"batch_{timestamp.lower()}"
        batch_path = f"{self.prefix}/{dataset_key}/batches/{batch_id}"
        self.client.ensure_folder(drive_id, batch_path)
        published: list[dict[str, Any]] = []
        for asset in source_assets:
            content = source.get_file_content(asset.source_id)
            if len(content) > self.maximum_bytes:
                raise BudgetExceededError(f"CSV asset exceeds Bronze limit: {asset.file_name}")
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            if not rows:
                raise ValueError(f"CSV asset is empty: {asset.file_name}")
            if len(rows) > self.maximum_rows:
                raise BudgetExceededError(f"CSV asset exceeds row limit: {asset.file_name}")
            bronze_key = f"{batch_path}/{asset.file_name}"
            uploaded = self.client.upload_drive_item(
                drive_id, bronze_key, content, content_type="text/csv"
            )
            published.append(
                BronzeAsset(
                    **asset.model_dump(), bronze_key=bronze_key,
                    bronze_item_id=str(uploaded.get("id", "")),
                    bronze_etag=str(uploaded.get("eTag", "")),
                    bronze_web_url=str(uploaded.get("webUrl", "")),
                    content_hash=hashlib.sha256(content).hexdigest(),
                    row_count=len(rows), columns=list(rows[0]),
                ).model_dump()
            )
        manifest_path = f"{self.prefix}/{dataset_key}/_manifests"
        self.client.ensure_folder(drive_id, manifest_path)
        manifest: dict[str, Any] = {
            "dataset_key": dataset_key, "batch_id": batch_id,
            "provider": source_assets[0].provider, "bronze_provider": "sharepoint",
            "bronze_library": self.library, "published_at": datetime.now(UTC).isoformat(),
            "assets": published, "publication_status": "PUBLISHED",
            "manifest_key": f"{manifest_path}/{timestamp}.json",
        }
        uploaded_manifest = self.client.upload_drive_item(
            drive_id, str(manifest["manifest_key"]), dumps(manifest), content_type="application/json"
        )
        manifest["manifest_item_id"] = str(uploaded_manifest.get("id", ""))
        manifest["manifest_etag"] = str(uploaded_manifest.get("eTag", ""))
        manifest["manifest_web_url"] = str(uploaded_manifest.get("webUrl", ""))
        return manifest

    def load_latest_batch(self, dataset_key: str) -> tuple[dict[str, Any], list[BronzeAsset]]:
        manifest = self._latest_manifest(dataset_key, optional=False)
        if not manifest:
            raise ResourceNotFoundError(f"No Bronze manifest found for dataset: {dataset_key}")
        assets = [BronzeAsset.model_validate(item) for item in manifest.get("assets", [])]
        if not assets:
            raise ResourceNotFoundError("Latest Bronze manifest contains no assets")
        return manifest, assets

    def read_asset(self, asset: BronzeAsset) -> bytes:
        return self.client.download_drive_item_by_path(self._resolve_drive(), asset.bronze_key)

    def _latest_manifest(self, dataset_key: str, *, optional: bool) -> dict[str, Any] | None:
        folder = f"{self.prefix}/{dataset_key}/_manifests"
        try:
            items = self.client.list_folder_children(self._resolve_drive(), folder)
        except ResourceNotFoundError:
            if optional:
                return None
            raise
        manifests = sorted(
            (item for item in items if str(item.get("name", "")).endswith(".json")),
            key=lambda item: str(item.get("name", "")),
        )
        if not manifests:
            if optional:
                return None
            raise ResourceNotFoundError(f"No Bronze manifest found for dataset: {dataset_key}")
        latest = manifests[-1]
        content = self.client.download_drive_item(self._resolve_drive(), str(latest["id"]))
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("SharePoint Bronze manifest is invalid")
        # Item metadata belongs to SharePoint and is refreshed on every read; it is
        # intentionally not embedded into the immutable manifest body itself.
        result["manifest_item_id"] = str(latest.get("id", ""))
        result["manifest_etag"] = str(latest.get("eTag", ""))
        result["manifest_web_url"] = str(latest.get("webUrl", ""))
        return result

    def _resolve_drive(self) -> str:
        if not self._drive_id:
            site = self.client.get_site(self.hostname, self.site_path)
            drive = self.client.get_drive_by_name(str(site["id"]), self.library)
            self._drive_id = str(drive["id"])
        return self._drive_id


def dumps(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
