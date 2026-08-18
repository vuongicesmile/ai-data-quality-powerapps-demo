"""Deterministic in-memory adapters for tests and local unit composition."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from typing import Any

from data_quality.domain.models import BronzeAsset, WorkflowState
from data_quality.domain.ports import DatasetSource


class InMemoryStateRepository:
    def __init__(self) -> None:
        self.states: dict[str, WorkflowState] = {}

    def load(self, dataset_key: str) -> WorkflowState | None:
        state = self.states.get(dataset_key)
        return state.model_copy(deep=True) if state else None

    def save(self, state: WorkflowState) -> None:
        self.states[state.dataset_key] = state.model_copy(deep=True)


class InMemoryBronzeStore:
    def __init__(self) -> None:
        self.manifests: dict[str, dict[str, Any]] = {}
        self.contents: dict[str, bytes] = {}

    def publish_batch(
        self, dataset_key: str, source: DatasetSource, *, force: bool = False
    ) -> dict[str, Any]:
        del force
        now = datetime.now(UTC).isoformat()
        assets = []
        for source_asset in source.list_files(dataset_key):
            content = source.get_file_content(source_asset.source_id)
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
            key = f"memory/{dataset_key}/{source_asset.file_name}"
            self.contents[key] = content
            assets.append(
                BronzeAsset(
                    **source_asset.model_dump(),
                    bronze_key=key,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    row_count=len(rows),
                    columns=list(rows[0]) if rows else [],
                ).model_dump()
            )
        manifest = {
            "dataset_key": dataset_key,
            "batch_id": "batch_memory",
            "provider": assets[0]["provider"],
            "published_at": now,
            "assets": assets,
            "publication_status": "PUBLISHED",
        }
        self.manifests[dataset_key] = manifest
        return manifest

    def load_latest_batch(self, dataset_key: str) -> tuple[dict[str, Any], list[BronzeAsset]]:
        manifest = self.manifests[dataset_key]
        return manifest, [BronzeAsset.model_validate(item) for item in manifest["assets"]]

    def read_asset(self, asset: BronzeAsset) -> bytes:
        return self.contents[asset.bronze_key]


class InMemoryWarehouseRepository:
    def __init__(self) -> None:
        self.silver: dict[str, list[dict[str, Any]]] = {}
        self.gold: dict[str, list[dict[str, Any]]] = {}

    def publish_silver(self, **kwargs: Any) -> dict[str, Any]:
        key = kwargs["asset_key"]
        rows = kwargs["rows"]
        self.silver[key] = rows
        digest = hashlib.sha256(repr(sorted(map(repr, rows))).encode()).hexdigest()
        return {"table": f"silver_{key}", "row_count": len(rows), "snapshot_hash": digest}

    def publish_gold(self, **kwargs: Any) -> dict[str, Any]:
        recipe = kwargs["recipe"]
        source = self.silver.get(recipe["source_asset"], [])
        key = recipe["target_asset"]
        self.gold[key] = source
        digest = hashlib.sha256(repr(sorted(map(repr, source))).encode()).hexdigest()
        return {"table": f"gold_{key}", "row_count": len(source), "snapshot_hash": digest}
