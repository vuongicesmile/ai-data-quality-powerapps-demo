"""Bounded OData client for Microsoft Dataverse Web API."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests

from data_quality.domain.errors import (
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ThrottledError,
    UpstreamUnavailableError,
)

from .auth import DataverseAuth


class DataverseClient:
    def __init__(
        self,
        auth: DataverseAuth,
        *,
        api_version: str = "v9.2",
        timeout_seconds: int = 20,
        max_retries: int = 3,
        maximum_rows: int = 25_000,
        session: requests.Session | None = None,
    ) -> None:
        self.auth = auth
        self.base_url = f"{auth.environment_url.rstrip('/')}/api/data/{api_version}"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.maximum_rows = maximum_rows
        self.session = session or requests.Session()

    def query(
        self,
        entity_set: str,
        *,
        select: list[str],
        filter: str | None = None,
        orderby: str | None = None,
        top: int = 5000,
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {"$select": ",".join(select), "$top": min(top, 5000)}
        if filter:
            params["$filter"] = filter
        if orderby:
            params["$orderby"] = orderby
        rows: list[dict[str, Any]] = []
        next_url: str | None = f"/{entity_set}"
        next_params: dict[str, str | int] | None = params
        while next_url:
            payload = self.request_json("GET", next_url, params=next_params)
            values = payload.get("value")
            if not isinstance(values, list):
                raise UpstreamUnavailableError("Dataverse returned an invalid collection")
            rows.extend(item for item in values if isinstance(item, dict))
            if len(rows) > self.maximum_rows:
                raise ValueError("Dataverse result exceeds the configured row limit")
            next_url = str(payload.get("@odata.nextLink") or "") or None
            next_params = None
        return rows

    def upsert(
        self,
        entity_set: str,
        key: dict[str, Any],
        payload: dict[str, Any],
        *,
        etag: str | None = None,
    ) -> dict[str, Any]:
        key_expression = ",".join(
            f"{name}={self._literal(value)}" for name, value in key.items()
        )
        headers = {"Prefer": "return=representation"}
        if etag:
            headers["If-Match"] = etag
        return self.request_json(
            "PATCH", f"/{entity_set}({key_expression})", json_body=payload, headers=headers
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self._request(
            method, path, params=params, json_body=json_body, headers=headers
        )
        if response.status_code == 204 or not response.content:
            response.close()
            return {}
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError("Dataverse returned non-JSON content") from exc
        finally:
            response.close()
        if not isinstance(payload, dict):
            raise UpstreamUnavailableError("Dataverse returned invalid JSON")
        return payload

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None,
        json_body: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> requests.Response:
        url = path if path.startswith("https://") else self.base_url + path
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers={
                        "Authorization": f"Bearer {self.auth.access_token()}",
                        "Accept": "application/json",
                        "OData-MaxVersion": "4.0",
                        "OData-Version": "4.0",
                        **(headers or {}),
                    },
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise UpstreamUnavailableError("Dataverse is unavailable") from exc
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code < 400:
                return response
            status = response.status_code
            detail = response.text[:500]
            response.close()
            if status == 401:
                if attempt < self.max_retries:
                    self.auth.access_token(refresh=True)
                    continue
                raise AuthenticationError("Dataverse rejected the access token")
            if status == 403:
                raise PermissionDeniedError("Dataverse application user lacks table privileges")
            if status == 404:
                raise ResourceNotFoundError("Dataverse table or record was not found")
            if status in {409, 412}:
                raise ConflictError("Dataverse record changed; refresh before retrying")
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = float(min(2**attempt, 8))
                    time.sleep(min(30.0, max(0.0, delay)))
                    continue
                if status == 429:
                    raise ThrottledError("Dataverse remained throttled after retries")
                raise UpstreamUnavailableError("Dataverse remained unavailable after retries")
            raise UpstreamUnavailableError(f"Dataverse failed with HTTP {status}: {detail}")
        raise UpstreamUnavailableError("Dataverse request failed")

    @staticmethod
    def escape(value: str) -> str:
        return value.replace("'", "''")

    @classmethod
    def _literal(cls, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return "'" + quote(cls.escape(str(value)), safe="") + "'"
