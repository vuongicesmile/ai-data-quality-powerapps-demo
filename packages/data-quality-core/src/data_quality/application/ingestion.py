"""SharePoint source-to-Bronze use case invoked by the Power Automate worker API."""

from __future__ import annotations

from typing import Any

from data_quality.domain.ports import BronzeStore, DatasetSource


class IngestionService:
    def __init__(self, source: DatasetSource, bronze: BronzeStore) -> None:
        self.source = source
        self.bronze = bronze

    def run(self, dataset_key: str, *, force: bool = False) -> dict[str, Any]:
        return self.bronze.publish_batch(dataset_key, self.source, force=force)
