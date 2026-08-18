"""SharePoint DatasetSource implemented through Microsoft Graph only."""

from __future__ import annotations

from data_quality.domain.errors import ResourceNotFoundError
from data_quality.domain.models import SourceAsset

from .client import MicrosoftGraphClient


class SharePointDatasetSource:
    def __init__(
        self,
        client: MicrosoftGraphClient,
        *,
        hostname: str,
        site_path: str,
        library: str,
        folder: str,
    ) -> None:
        self.client = client
        self.hostname = hostname
        self.site_path = site_path
        self.library = library
        self.folder = folder.strip("/")
        self.drive_id = ""
        self.assets: dict[str, SourceAsset] = {}

    def list_files(self, dataset_key: str) -> list[SourceAsset]:
        del dataset_key
        site = self.client.get_site(self.hostname, self.site_path)
        drive = self.client.get_drive_by_name(str(site["id"]), self.library)
        self.drive_id = str(drive["id"])
        assets = []
        for item in self.client.list_folder_children(self.drive_id, self.folder):
            name = str(item.get("name", ""))
            if not name.lower().endswith(".csv") or not isinstance(item.get("file"), dict):
                continue
            asset = SourceAsset(
                provider="sharepoint",
                asset_key=name[:-4],
                file_name=name,
                source_id=str(item["id"]),
                source_path=f"{self.folder}/{name}",
                source_version=str(item.get("eTag", "")),
                size_bytes=max(0, int(item.get("size", 0))),
                last_modified_at=str(item.get("lastModifiedDateTime", "")),
            )
            assets.append(asset)
        assets.sort(key=lambda item: item.file_name.casefold())
        self._index(assets)
        return assets

    def get_file_metadata(self, file_key: str) -> SourceAsset:
        try:
            return self.assets[file_key]
        except KeyError as exc:
            raise ResourceNotFoundError(f"SharePoint asset was not discovered: {file_key}") from exc

    def get_file_content(self, file_key: str) -> bytes:
        asset = self.get_file_metadata(file_key)
        if not self.drive_id:
            raise ResourceNotFoundError("SharePoint drive must be discovered before download")
        return self.client.download_drive_item(self.drive_id, asset.source_id)

    def _index(self, assets: list[SourceAsset]) -> None:
        self.assets = {}
        for asset in assets:
            for key in (asset.source_id, asset.asset_key, asset.file_name):
                self.assets[key] = asset
