"""Immutable Dataverse Bronze snapshots for bounded SharePoint list rows."""

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

from .client import DataverseClient


class DataverseBronzeStore:
    def __init__(
        self,
        client: DataverseClient,
        *,
        maximum_rows: int = 5000,
        maximum_row_bytes: int = 1024 * 1024,
    ) -> None:
        self.client = client
        self.maximum_rows = maximum_rows
        self.maximum_row_bytes = maximum_row_bytes

    def publish_batch(
        self, dataset_key: str, source: DatasetSource, *, force: bool = False
    ) -> dict[str, Any]:
        source_assets = list(source.list_files(dataset_key))
        if not source_assets:
            raise ResourceNotFoundError(f"No SharePoint lists found for dataset: {dataset_key}")
        source_versions = {
            asset.source_id: asset.source_version for asset in source_assets
        }
        version_hash = self._hash({"dataset_key": dataset_key, "versions": source_versions})
        batch_id = f"batch_{version_hash[:24]}"
        if not force and self._batch_exists(batch_id):
            manifest, _ = self._load_batch(dataset_key, batch_id)
            return {**manifest, "publication_status": "UNCHANGED"}

        captured_at = datetime.now(UTC).isoformat()
        self.client.upsert(
            "dq_batches",
            {"dq_name": batch_id},
            {
                "dq_name": batch_id,
                "dq_datasetkey": dataset_key,
                "dq_sourceversionhash": version_hash,
                "dq_publishedat": captured_at,
                "dq_status": 100000002,
            },
        )
        published: list[BronzeAsset] = []
        for source_asset in source_assets:
            content = source.get_file_content(source_asset.source_id)
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            if not rows:
                raise ValueError(f"SharePoint list is empty: {source_asset.asset_key}")
            if len(rows) > self.maximum_rows:
                raise BudgetExceededError(
                    f"SharePoint list exceeds {self.maximum_rows} rows: {source_asset.asset_key}"
                )
            columns = list(rows[0])
            content_hash = self._hash(rows)
            bronze_key = f"dataverse://dq_bronzerows/{batch_id}/{source_asset.asset_key}"
            bronze_asset = BronzeAsset(
                **source_asset.model_dump(),
                bronze_key=bronze_key,
                bronze_item_id=f"{batch_id}:{source_asset.source_id}",
                bronze_etag=source_asset.source_version,
                bronze_web_url=source_asset.source_web_url,
                content_hash=content_hash,
                row_count=len(rows),
                columns=columns,
                source_list_id=source_asset.source_id,
                source_list_name=source_asset.asset_key,
                captured_at=captured_at,
            )
            self._upsert_asset(dataset_key, batch_id, bronze_asset)
            self._upsert_rows(dataset_key, batch_id, bronze_asset, rows, captured_at)
            published.append(bronze_asset)
        return self._manifest(
            dataset_key, batch_id, version_hash, captured_at, published, "PUBLISHED"
        )

    def load_latest_batch(
        self, dataset_key: str
    ) -> tuple[dict[str, Any], list[BronzeAsset]]:
        escaped = self.client.escape(dataset_key)
        batches = self.client.query(
            "dq_batches",
            select=["dq_name"],
            filter=f"dq_datasetkey eq '{escaped}'",
            orderby="dq_publishedat desc",
            top=1,
        )
        if not batches:
            raise ResourceNotFoundError(f"No Dataverse Bronze batch found: {dataset_key}")
        return self._load_batch(dataset_key, str(batches[0]["dq_name"]))

    def read_asset(self, asset: BronzeAsset) -> bytes:
        batch_id = self._batch_from_key(asset.bronze_key)
        batch = self.client.escape(batch_id)
        asset_key = self.client.escape(asset.asset_key)
        stored = self.client.query(
            "dq_bronzerows",
            select=["dq_payloadjson"],
            filter=f"dq_batchkey eq '{batch}' and dq_assetkey eq '{asset_key}'",
            orderby="dq_sourcerownumber asc",
            top=self.maximum_rows,
        )
        if not stored:
            raise ResourceNotFoundError(
                f"Dataverse Bronze rows not found: {batch_id}/{asset.asset_key}"
            )
        rows = [self._loads(row.get("dq_payloadjson"), {}) for row in stored]
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=asset.columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode("utf-8")

    def _upsert_asset(
        self, dataset_key: str, batch_id: str, asset: BronzeAsset
    ) -> None:
        asset_key = {"dq_batchkey": batch_id, "dq_assetkey": asset.asset_key}
        self.client.upsert(
            "dq_assets",
            asset_key,
            {
                "dq_name": f"{batch_id}:{asset.asset_key}",
                "dq_batchkey": batch_id,
                "dq_batch@odata.bind": self._bind(
                    "dq_batches", {"dq_name": batch_id}
                ),
                "dq_assetkey": asset.asset_key,
                "dq_filename": asset.file_name,
                "dq_sourceitemid": asset.source_id,
                "dq_sourceetag": asset.source_version,
                "dq_sourcepath": asset.source_path,
                "dq_sourcelistid": asset.source_list_id,
                "dq_sourcelistname": asset.source_list_name,
                "dq_rowcount": asset.row_count,
                "dq_columncount": len(asset.columns),
                "dq_contenthash": asset.content_hash,
                "dq_columnsjson": self._dumps(asset.columns),
            },
        )
        self.client.upsert(
            "dq_bronzesnapshots",
            asset_key,
            {
                "dq_name": f"{batch_id}:{asset.asset_key}",
                "dq_batchkey": batch_id,
                "dq_asset@odata.bind": self._bind(
                    "dq_assets",
                    {"dq_batchkey": batch_id, "dq_assetkey": asset.asset_key},
                ),
                "dq_assetkey": asset.asset_key,
                "dq_sourcelistid": asset.source_list_id,
                "dq_sourcelistname": asset.source_list_name,
                "dq_sourceweburl": asset.source_web_url,
                "dq_rowcount": asset.row_count,
                "dq_snapshotversionhash": asset.source_version,
                "dq_capturedat": asset.captured_at,
            },
        )

    def _upsert_rows(
        self,
        dataset_key: str,
        batch_id: str,
        asset: BronzeAsset,
        rows: list[dict[str, Any]],
        captured_at: str,
    ) -> None:
        for index, row in enumerate(rows, 1):
            payload = self._dumps(row)
            if len(payload.encode()) > self.maximum_row_bytes:
                raise BudgetExceededError(
                    f"SharePoint row exceeds Dataverse payload limit: {asset.asset_key}/{index}"
                )
            source_item_id = str(row.get("_source_item_id") or index)
            row_hash = self._hash(row)
            self.client.upsert(
                "dq_bronzerows",
                {
                    "dq_batchkey": batch_id,
                    "dq_assetkey": asset.asset_key,
                    "dq_sourceitemid": source_item_id,
                },
                {
                    "dq_name": f"{asset.asset_key}:{source_item_id}",
                    "dq_datasetkey": dataset_key,
                    "dq_batchkey": batch_id,
                    "dq_assetkey": asset.asset_key,
                    "dq_bronzesnapshot@odata.bind": self._bind(
                        "dq_bronzesnapshots",
                        {"dq_batchkey": batch_id, "dq_assetkey": asset.asset_key},
                    ),
                    "dq_sourceitemid": source_item_id,
                    "dq_sourceetag": str(row.get("_source_etag", "")),
                    "dq_sourcerownumber": index,
                    "dq_rowhash": row_hash,
                    "dq_payloadjson": payload,
                    "dq_capturedat": captured_at,
                },
            )

    def _load_batch(
        self, dataset_key: str, batch_id: str
    ) -> tuple[dict[str, Any], list[BronzeAsset]]:
        batch = self.client.escape(batch_id)
        batch_rows = self.client.query(
            "dq_batches",
            select=["dq_sourceversionhash", "dq_publishedat"],
            filter=f"dq_name eq '{batch}'",
            top=1,
        )
        if not batch_rows:
            raise ResourceNotFoundError(f"Dataverse Bronze batch not found: {batch_id}")
        snapshots = {
            str(row["dq_assetkey"]): row
            for row in self.client.query(
                "dq_bronzesnapshots",
                select=[
                    "dq_assetkey", "dq_sourcelistid", "dq_sourcelistname",
                    "dq_sourceweburl", "dq_rowcount", "dq_snapshotversionhash",
                    "dq_capturedat",
                ],
                filter=f"dq_batchkey eq '{batch}'",
            )
        }
        asset_rows = self.client.query(
            "dq_assets",
            select=[
                "dq_assetkey", "dq_filename", "dq_sourceitemid", "dq_sourceetag",
                "dq_sourcepath", "dq_rowcount", "dq_contenthash", "dq_columnsjson",
                "dq_sourcelistid", "dq_sourcelistname",
            ],
            filter=f"dq_batchkey eq '{batch}'",
        )
        assets: list[BronzeAsset] = []
        for row in asset_rows:
            key = str(row["dq_assetkey"])
            snapshot = snapshots.get(key, {})
            assets.append(
                BronzeAsset(
                    provider="sharepoint-list",
                    asset_key=key,
                    file_name=str(row.get("dq_filename") or f"{key}.csv"),
                    source_id=str(
                        row.get("dq_sourceitemid")
                        or snapshot.get("dq_sourcelistid")
                        or ""
                    ),
                    source_path=str(row.get("dq_sourcepath") or ""),
                    source_version=str(
                        row.get("dq_sourceetag")
                        or snapshot.get("dq_snapshotversionhash")
                        or ""
                    ),
                    source_web_url=str(snapshot.get("dq_sourceweburl") or ""),
                    size_bytes=0,
                    last_modified_at=str(snapshot.get("dq_capturedat") or ""),
                    bronze_key=f"dataverse://dq_bronzerows/{batch_id}/{key}",
                    bronze_item_id=f"{batch_id}:{key}",
                    bronze_etag=str(snapshot.get("dq_snapshotversionhash") or ""),
                    bronze_web_url=str(snapshot.get("dq_sourceweburl") or ""),
                    content_hash=str(row.get("dq_contenthash") or ""),
                    row_count=int(row.get("dq_rowcount") or snapshot.get("dq_rowcount") or 0),
                    columns=self._loads(row.get("dq_columnsjson"), []),
                    source_list_id=str(snapshot.get("dq_sourcelistid") or ""),
                    source_list_name=str(snapshot.get("dq_sourcelistname") or key),
                    captured_at=str(snapshot.get("dq_capturedat") or ""),
                )
            )
        if not assets:
            raise ResourceNotFoundError(f"Dataverse Bronze batch has no assets: {batch_id}")
        batch_row = batch_rows[0]
        manifest = self._manifest(
            dataset_key,
            batch_id,
            str(batch_row.get("dq_sourceversionhash") or ""),
            str(batch_row.get("dq_publishedat") or ""),
            assets,
            "PUBLISHED",
        )
        return manifest, assets

    def _batch_exists(self, batch_id: str) -> bool:
        key = self.client.escape(batch_id)
        return bool(
            self.client.query(
                "dq_batches", select=["dq_name"], filter=f"dq_name eq '{key}'", top=1
            )
        )

    @staticmethod
    def _manifest(
        dataset_key: str,
        batch_id: str,
        version_hash: str,
        captured_at: str,
        assets: list[BronzeAsset],
        status: str,
    ) -> dict[str, Any]:
        return {
            "dataset_key": dataset_key,
            "batch_id": batch_id,
            "provider": "sharepoint-list",
            "bronze_provider": "dataverse",
            "source_version_hash": version_hash,
            "published_at": captured_at,
            "assets": [asset.model_dump() for asset in assets],
            "publication_status": status,
        }

    @staticmethod
    def _batch_from_key(bronze_key: str) -> str:
        parts = bronze_key.split("/")
        if len(parts) < 5 or parts[2] != "dq_bronzerows":
            raise ValueError(f"Invalid Dataverse Bronze key: {bronze_key}")
        return parts[3]

    @staticmethod
    def _dumps(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)

    @staticmethod
    def _bind(entity_set: str, key: dict[str, Any]) -> str:
        expression = ",".join(
            f"{name}='{str(value).replace(chr(39), chr(39) * 2)}'"
            for name, value in key.items()
        )
        return f"/{entity_set}({expression})"

    @classmethod
    def _loads(cls, value: Any, default: Any) -> Any:
        try:
            return json.loads(str(value)) if value else default
        except (TypeError, ValueError):
            return default

    @classmethod
    def _hash(cls, value: Any) -> str:
        return hashlib.sha256(cls._dumps(value).encode()).hexdigest()
