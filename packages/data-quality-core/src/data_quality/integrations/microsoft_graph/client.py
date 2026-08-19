"""Narrow Microsoft Graph client for SharePoint Site/Drive/DriveItem access."""

from __future__ import annotations

import time
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import requests

from data_quality.domain.errors import (
    AuthenticationError,
    BudgetExceededError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ThrottledError,
    UpstreamUnavailableError,
)

from .auth import MicrosoftGraphAuth


class MicrosoftGraphClient:
    base_url = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        auth: MicrosoftGraphAuth,
        *,
        timeout_seconds: int = 20,
        max_retries: int = 3,
        maximum_items: int = 500,
        maximum_download_bytes: int = 25 * 1024 * 1024,
        session: requests.Session | None = None,
    ) -> None:
        self.auth = auth
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.maximum_items = maximum_items
        self.maximum_download_bytes = maximum_download_bytes
        self.session = session or requests.Session()

    def get_site(self, hostname: str, site_path: str) -> dict[str, Any]:
        path = "/" + site_path.strip("/")
        return self._json(
            f"/sites/{quote(hostname, safe='.')}:{quote(path, safe='/')}",
            params={"$select": "id,displayName,webUrl"},
        )

    def list_site_drives(self, site_id: str) -> list[dict[str, Any]]:
        return self._collection(
            f"/sites/{quote(site_id, safe=',')}/drives",
            params={"$select": "id,name,webUrl,driveType"},
        )

    def get_drive_by_name(self, site_id: str, name: str) -> dict[str, Any]:
        for drive in self.list_site_drives(site_id):
            if str(drive.get("name", "")).casefold() == name.casefold():
                return drive
        raise ResourceNotFoundError(f"SharePoint document library not found: {name}")

    def list_folder_children(self, drive_id: str, folder_path: str) -> list[dict[str, Any]]:
        folder = quote(folder_path.strip("/"), safe="/")
        path = (
            f"/drives/{quote(drive_id, safe='')}/root:/{folder}:/children"
            if folder
            else f"/drives/{quote(drive_id, safe='')}/root/children"
        )
        return self._collection(
            path,
            params={"$select": "id,name,size,eTag,lastModifiedDateTime,file,folder,webUrl"},
        )

    def ensure_folder(self, drive_id: str, folder_path: str) -> dict[str, Any]:
        parent = ""
        current: dict[str, Any] = {"id": "root", "name": "root"}
        for segment in (part for part in folder_path.strip("/").split("/") if part):
            children = self.list_folder_children(drive_id, parent)
            existing = next(
                (
                    item for item in children
                    if str(item.get("name", "")).casefold() == segment.casefold()
                    and isinstance(item.get("folder"), dict)
                ),
                None,
            )
            if existing is None:
                encoded_drive = quote(drive_id, safe="")
                encoded_parent = quote(parent, safe="/")
                endpoint = (
                    f"/drives/{encoded_drive}/root:/{encoded_parent}:/children"
                    if parent else f"/drives/{encoded_drive}/root/children"
                )
                existing = self._json(
                    endpoint,
                    method="POST",
                    json_body={
                        "name": segment,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": "fail",
                    },
                )
            current = existing
            parent = f"{parent}/{segment}".strip("/")
        return current

    def upload_drive_item(
        self, drive_id: str, item_path: str, content: bytes, *, content_type: str
    ) -> dict[str, Any]:
        if len(content) > self.maximum_download_bytes:
            raise BudgetExceededError("SharePoint upload exceeds the configured byte limit")
        path = quote(item_path.strip("/"), safe="/")
        response = self._request(
            f"/drives/{quote(drive_id, safe='')}/root:/{path}:/content",
            method="PUT", data=content, headers={"Content-Type": content_type},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError("Microsoft Graph returned invalid upload metadata") from exc
        finally:
            response.close()
        if not isinstance(payload, dict):
            raise UpstreamUnavailableError("Microsoft Graph returned invalid upload metadata")
        return payload

    def get_drive_item_by_path(self, drive_id: str, item_path: str) -> dict[str, Any]:
        path = quote(item_path.strip("/"), safe="/")
        return self._json(
            f"/drives/{quote(drive_id, safe='')}/root:/{path}",
            params={"$select": "id,name,size,eTag,lastModifiedDateTime,file,webUrl"},
        )

    def download_drive_item_by_path(self, drive_id: str, item_path: str) -> bytes:
        item = self.get_drive_item_by_path(drive_id, item_path)
        return self.download_drive_item(drive_id, str(item["id"]))

    def download_drive_item(self, drive_id: str, item_id: str) -> bytes:
        response = self._request(
            f"/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}/content",
            stream=True,
        )
        length = response.headers.get("Content-Length")
        if length and int(length) > self.maximum_download_bytes:
            response.close()
            raise BudgetExceededError("SharePoint file exceeds the configured byte limit")
        parts: list[bytes] = []
        size = 0
        try:
            for part in response.iter_content(64 * 1024):
                size += len(part)
                if size > self.maximum_download_bytes:
                    raise BudgetExceededError("SharePoint file exceeds the configured byte limit")
                parts.append(part)
        finally:
            response.close()
        return b"".join(parts)

    def _collection(self, path: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = path
        current_params: dict[str, str] | None = params
        while next_url:
            payload = self._json(next_url, params=current_params)
            values = payload.get("value")
            if not isinstance(values, list):
                raise UpstreamUnavailableError("Microsoft Graph returned an invalid collection")
            items.extend(item for item in values if isinstance(item, dict))
            if len(items) > self.maximum_items:
                raise BudgetExceededError("Microsoft Graph result exceeds the item limit")
            next_url = str(payload.get("@odata.nextLink") or "") or None
            current_params = None
        return items

    def _json(
        self, path: str, *, params: dict[str, str] | None = None,
        method: str = "GET", json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(path, params=params, method=method, json_body=json_body)
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError("Microsoft Graph returned non-JSON content") from exc
        finally:
            response.close()
        if not isinstance(payload, dict):
            raise UpstreamUnavailableError("Microsoft Graph returned invalid JSON")
        return payload

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, str] | None = None,
        stream: bool = False,
        json_body: dict[str, Any] | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        url = path if path.startswith("https://") else self.base_url + path
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {self.auth.access_token()}", **(headers or {})},
                    json=json_body,
                    data=data,
                    timeout=self.timeout_seconds,
                    allow_redirects=True,
                    stream=stream,
                )
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise UpstreamUnavailableError("Microsoft Graph is unavailable") from exc
                time.sleep(min(2**attempt, 8))
                continue
            status = response.status_code
            if status < 400:
                return response
            response.close()
            if status == 401:
                if attempt < self.max_retries:
                    self.auth.access_token(refresh=True)
                    continue
                raise AuthenticationError("Microsoft Graph rejected the access token")
            if status == 403:
                raise PermissionDeniedError(
                    "Microsoft Graph denied access; verify Sites.Selected and the site grant"
                )
            if status == 404:
                raise ResourceNotFoundError("SharePoint site, library, folder, or file not found")
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    time.sleep(self._retry_after(response, attempt))
                    continue
                if status == 429:
                    raise ThrottledError("Microsoft Graph remained throttled after retries")
                raise UpstreamUnavailableError("Microsoft Graph remained unavailable after retries")
            raise UpstreamUnavailableError(f"Microsoft Graph failed with HTTP {status}")
        raise UpstreamUnavailableError("Microsoft Graph request failed")

    @staticmethod
    def _retry_after(response: requests.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After", "")
        try:
            return min(30.0, max(0.0, float(value)))
        except ValueError:
            try:
                return min(30.0, max(0.0, parsedate_to_datetime(value).timestamp() - time.time()))
            except (TypeError, ValueError, OverflowError):
                return float(min(2**attempt, 8))
