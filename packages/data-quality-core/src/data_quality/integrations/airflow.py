"""Airflow REST adapter used by provider-neutral ingestion endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import requests

from data_quality.domain.errors import ResourceNotFoundError, UpstreamUnavailableError


class AirflowClient:
    def __init__(
        self,
        base_url: str,
        *,
        username: str,
        password: str,
        timeout_seconds: int = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timeout_seconds = timeout_seconds

    def trigger(self, dag_id: str, *, conf: dict[str, Any]) -> dict[str, Any]:
        run_id = f"manual__{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}__{uuid4().hex[:8]}"
        try:
            response = requests.post(
                f"{self.base_url}/dags/{dag_id}/dagRuns",
                json={"dag_run_id": run_id, "conf": conf},
                auth=self.auth,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise UpstreamUnavailableError("Airflow API is unavailable") from exc
        if response.status_code >= 400:
            raise UpstreamUnavailableError(
                f"Airflow rejected the ingestion run: {response.text[:200]}"
            )
        return {"dag_id": dag_id, "run_id": run_id, "status": "QUEUED", "progress": 0}

    def status(self, dag_id: str, run_id: str) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}/dags/{dag_id}/dagRuns/{run_id}",
                auth=self.auth,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise UpstreamUnavailableError("Airflow API is unavailable") from exc
        if response.status_code == 404:
            raise ResourceNotFoundError(f"Airflow run not found: {run_id}")
        if response.status_code >= 400:
            raise UpstreamUnavailableError(f"Airflow status failed: {response.text[:200]}")
        payload = response.json()
        state = str(payload.get("state", "queued")).upper()
        progress = 100 if state == "SUCCESS" else 0
        return {"dag_id": dag_id, "run_id": run_id, "status": state, "progress": progress}
