"""Filesystem source for deterministic zero-credential development runs."""

from __future__ import annotations

import hashlib
from pathlib import Path

from data_quality.domain.errors import BudgetExceededError, ResourceNotFoundError
from data_quality.domain.models import SourceAsset


class LocalDatasetSource:
    def __init__(self, root: Path, *, maximum_bytes: int = 25 * 1024 * 1024) -> None:
        self.root = root.resolve()
        self.maximum_bytes = maximum_bytes
        self.assets: dict[str, SourceAsset] = {}

    def list_files(self, dataset_key: str) -> list[SourceAsset]:
        del dataset_key
        if not self.root.is_dir():
            raise ResourceNotFoundError(f"Local dataset folder not found: {self.root}")
        assets = []
        for path in sorted(self.root.glob("*.csv")):
            content = path.read_bytes()
            stat = path.stat()
            asset = SourceAsset(
                provider="local",
                asset_key=path.stem,
                file_name=path.name,
                source_id=path.name,
                source_path=path.name,
                source_version=hashlib.sha256(content).hexdigest(),
                size_bytes=stat.st_size,
                last_modified_at=str(stat.st_mtime_ns),
            )
            assets.append(asset)
        self._index(assets)
        return assets

    def get_file_metadata(self, file_key: str) -> SourceAsset:
        try:
            return self.assets[file_key]
        except KeyError as exc:
            raise ResourceNotFoundError(f"Local asset was not discovered: {file_key}") from exc

    def get_file_content(self, file_key: str) -> bytes:
        asset = self.get_file_metadata(file_key)
        path = (self.root / asset.file_name).resolve()
        if path.parent != self.root:
            raise ResourceNotFoundError("Local asset escaped the dataset root")
        if path.stat().st_size > self.maximum_bytes:
            raise BudgetExceededError(f"Local asset exceeds the byte limit: {asset.file_name}")
        return path.read_bytes()

    def _index(self, assets: list[SourceAsset]) -> None:
        self.assets = {}
        for asset in assets:
            for key in (asset.source_id, asset.asset_key, asset.file_name):
                self.assets[key] = asset
