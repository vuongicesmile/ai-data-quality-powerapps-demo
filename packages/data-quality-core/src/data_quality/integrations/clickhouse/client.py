"""Small bounded HTTP client for ClickHouse queries and JSONEachRow inserts."""

from __future__ import annotations

import json
from typing import Any

import requests

from data_quality.domain.errors import UpstreamUnavailableError


class ClickHouseClient:
    def __init__(
        self,
        url: str,
        *,
        user: str = "default",
        password: str = "",
        timeout_seconds: int = 15,
    ) -> None:
        self.url = url.rstrip("/")
        self.auth = (user, password)
        self.timeout_seconds = timeout_seconds

    def execute(self, sql: str) -> str:
        try:
            response = requests.post(
                self.url,
                params={"query": sql},
                auth=self.auth,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise UpstreamUnavailableError("ClickHouse is unavailable") from exc
        if response.status_code >= 400:
            raise UpstreamUnavailableError(f"ClickHouse query failed: {response.text[:300]}")
        return response.text

    def query_json(self, sql: str, *, maximum_rows: int = 10_000) -> list[dict[str, Any]]:
        text = self.execute(sql.rstrip().rstrip(";") + " FORMAT JSONEachRow")
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if len(rows) > maximum_rows:
            raise ValueError("ClickHouse result exceeds the row limit")
        return rows

    def insert_json(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        payload = "\n".join(json.dumps(row, separators=(",", ":"), default=str) for row in rows)
        try:
            response = requests.post(
                self.url,
                params={
                    "query": f"INSERT INTO {table} FORMAT JSONEachRow",
                    # Pydantic serializes aware datetimes with an ISO-8601 offset.
                    # ClickHouse's basic parser only accepts its native timestamp
                    # representation, while best_effort safely accepts both forms.
                    "date_time_input_format": "best_effort",
                },
                data=payload.encode(),
                auth=self.auth,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise UpstreamUnavailableError("ClickHouse insert is unavailable") from exc
        if response.status_code >= 400:
            raise UpstreamUnavailableError(f"ClickHouse insert failed: {response.text[:300]}")
