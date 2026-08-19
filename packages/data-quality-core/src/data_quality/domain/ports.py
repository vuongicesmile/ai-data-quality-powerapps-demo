"""Dependency inversion ports for source, Bronze, state, and medallion stores."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from .models import BronzeAsset, SourceAsset, WorkflowState


class DatasetSource(Protocol):
    def list_files(self, dataset_key: str) -> Sequence[SourceAsset]: ...
    def get_file_metadata(self, file_key: str) -> SourceAsset: ...
    def get_file_content(self, file_key: str) -> bytes: ...


class BronzeStore(Protocol):
    def publish_batch(
        self,
        dataset_key: str,
        source: DatasetSource,
        *,
        force: bool = False,
    ) -> dict[str, Any]: ...

    def load_latest_batch(self, dataset_key: str) -> tuple[dict[str, Any], list[BronzeAsset]]: ...
    def read_asset(self, asset: BronzeAsset) -> bytes: ...


class StateRepository(Protocol):
    def load(self, dataset_key: str) -> WorkflowState | None: ...
    def save(self, state: WorkflowState) -> None: ...


class WarehouseRepository(Protocol):
    def publish_silver(
        self,
        *,
        dataset_id: str,
        asset_key: str,
        mapping: dict[str, Any],
        rows: list[dict[str, Any]],
        rejected_rows: list[dict[str, Any]],
        batch_id: str,
    ) -> dict[str, Any]: ...

    def publish_gold(
        self,
        *,
        dataset_id: str,
        recipe: dict[str, Any],
        silver: dict[str, dict[str, Any]],
        batch_id: str,
    ) -> dict[str, Any]: ...
