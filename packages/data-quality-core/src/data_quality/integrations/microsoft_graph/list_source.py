"""DatasetSource over an allowlist of existing SharePoint lists."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Any

from data_quality.domain.errors import BudgetExceededError, ResourceNotFoundError
from data_quality.domain.models import SourceAsset

from .client import MicrosoftGraphClient


_IGNORED_FIELDS = {
    "AppAuthorLookupId",
    "AppEditorLookupId",
    "Attachments",
    "AuthorLookupId",
    "ComplianceAssetId",
    "ContentType",
    "Created",
    "Edit",
    "EditedTimestamp",
    "EditorLookupId",
    "FolderChildCount",
    "ItemChildCount",
    "LinkTitle",
    "LinkTitleNoMenu",
    "Modified",
    "id",
}


class SharePointListDatasetSource:
    """Expose four tenant-owned lists as stable, virtual CSV assets."""

    def __init__(
        self,
        client: MicrosoftGraphClient,
        *,
        hostname: str,
        site_path: str,
        list_names: tuple[str, ...],
        maximum_rows: int = 5000,
    ) -> None:
        if not list_names:
            raise ValueError("At least one SharePoint source list is required")
        self.client = client
        self.hostname = hostname
        self.site_path = site_path
        self.list_names = list_names
        self.maximum_rows = maximum_rows
        self.assets: dict[str, SourceAsset] = {}
        self.contents: dict[str, bytes] = {}

    def list_files(self, dataset_key: str) -> list[SourceAsset]:
        del dataset_key
        site = self.client.get_site(self.hostname, self.site_path)
        site_id = str(site["id"])
        available = self.client.list_site_lists(site_id)
        assets: list[SourceAsset] = []
        for configured_name in self.list_names:
            expected = configured_name.casefold()
            source_list = next(
                (
                    item
                    for item in available
                    if expected
                    in {
                        str(item.get("name", "")).casefold(),
                        str(item.get("displayName", "")).casefold(),
                    }
                ),
                None,
            )
            if source_list is None:
                raise ResourceNotFoundError(
                    f"Allowlisted SharePoint list not found: {configured_name}"
                )
            items = self.client.list_list_items(site_id, str(source_list["id"]))
            if not items:
                raise ResourceNotFoundError(f"SharePoint list is empty: {configured_name}")
            if len(items) > self.maximum_rows:
                raise BudgetExceededError(
                    f"SharePoint list exceeds {self.maximum_rows} rows: {configured_name}"
                )
            rows = [self._canonical_row(item, index) for index, item in enumerate(items, 1)]
            columns = sorted({column for row in rows for column in row})
            content = self._to_csv(rows, columns)
            versions = [
                (str(item.get("id", "")), str(item.get("eTag", ""))) for item in items
            ]
            version = hashlib.sha256(
                json.dumps(sorted(versions), separators=(",", ":")).encode()
            ).hexdigest()
            name = str(source_list.get("name") or configured_name)
            asset = SourceAsset(
                provider="sharepoint-list",
                asset_key=name,
                file_name=f"{name}.csv",
                source_id=str(source_list["id"]),
                source_path=f"{self.site_path.rstrip('/')}/lists/{name}",
                source_version=version,
                source_web_url=str(source_list.get("webUrl", "")),
                size_bytes=len(content),
                last_modified_at=max(
                    (str(item.get("lastModifiedDateTime", "")) for item in items),
                    default=str(source_list.get("lastModifiedDateTime", "")),
                ),
            )
            assets.append(asset)
            self.contents[asset.source_id] = content
            self.contents[asset.asset_key] = content
            self.contents[asset.file_name] = content
        self.assets = {
            key: asset
            for asset in assets
            for key in (asset.source_id, asset.asset_key, asset.file_name)
        }
        return assets

    def get_file_metadata(self, file_key: str) -> SourceAsset:
        try:
            return self.assets[file_key]
        except KeyError as exc:
            raise ResourceNotFoundError(
                f"SharePoint list asset was not discovered: {file_key}"
            ) from exc

    def get_file_content(self, file_key: str) -> bytes:
        try:
            return self.contents[file_key]
        except KeyError as exc:
            raise ResourceNotFoundError(
                f"SharePoint list content was not captured: {file_key}"
            ) from exc

    @classmethod
    def _canonical_row(cls, item: dict[str, Any], row_number: int) -> dict[str, str]:
        raw_fields = item.get("fields")
        fields = raw_fields if isinstance(raw_fields, dict) else {}
        row = {
            str(key): cls._scalar(value)
            for key, value in fields.items()
            if not str(key).startswith("@")
            and not str(key).startswith("_")
            and str(key) not in _IGNORED_FIELDS
        }
        row["_source_item_id"] = str(item.get("id", ""))
        row["_source_etag"] = str(item.get("eTag", ""))
        row["_source_row_number"] = str(row_number)
        return row

    @staticmethod
    def _scalar(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)
        return str(value)

    @staticmethod
    def _to_csv(rows: list[dict[str, str]], columns: list[str]) -> bytes:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode("utf-8")
