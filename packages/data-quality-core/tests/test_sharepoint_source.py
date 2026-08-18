from typing import Any

from data_quality.integrations.microsoft_graph.source import SharePointDatasetSource


class FakeGraphClient:
    def get_site(self, hostname: str, site_path: str) -> dict[str, str]:
        assert hostname == "contoso.sharepoint.com"
        assert site_path == "/sites/AIDataQualityDev"
        return {"id": "site-id"}

    def get_drive_by_name(self, site_id: str, name: str) -> dict[str, str]:
        assert (site_id, name) == ("site-id", "DataQualityDatasets")
        return {"id": "drive-id"}

    def list_folder_children(self, drive_id: str, folder: str) -> list[dict[str, Any]]:
        assert drive_id == "drive-id"
        assert folder == "GenericDatasets/ecommerce-v1"
        return [
            {
                "id": "orders-item",
                "name": "orders.csv",
                "size": 42,
                "eTag": '"orders-v1"',
                "lastModifiedDateTime": "2026-08-18T00:00:00Z",
                "file": {"mimeType": "text/csv"},
            },
            {"id": "notes-item", "name": "notes.txt", "size": 5, "file": {}},
            {"id": "folder-item", "name": "archive.csv", "size": 0, "folder": {}},
        ]

    def download_drive_item(self, drive_id: str, item_id: str) -> bytes:
        assert (drive_id, item_id) == ("drive-id", "orders-item")
        return b"order_id\nO1001\n"


def test_sharepoint_source_discovers_and_downloads_csv_assets() -> None:
    source = SharePointDatasetSource(
        FakeGraphClient(),  # type: ignore[arg-type]
        hostname="contoso.sharepoint.com",
        site_path="/sites/AIDataQualityDev",
        library="DataQualityDatasets",
        folder="GenericDatasets/ecommerce-v1",
    )

    assets = source.list_files("ecommerce-v1")

    assert [item.asset_key for item in assets] == ["orders"]
    assert assets[0].source_version == '"orders-v1"'
    assert source.get_file_content("orders") == b"order_id\nO1001\n"
