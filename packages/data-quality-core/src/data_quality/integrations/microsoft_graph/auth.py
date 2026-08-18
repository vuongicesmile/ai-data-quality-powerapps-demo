"""App-only Microsoft Entra authentication with bounded token caching."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import quote

import requests

from data_quality.domain.errors import AuthenticationError, UpstreamUnavailableError


@dataclass
class MicrosoftGraphAuth:
    tenant_id: str
    client_id: str
    client_secret: str
    timeout_seconds: int = 20
    session: requests.Session = field(default_factory=requests.Session)
    _token: str = field(default="", init=False, repr=False)
    _expires_at: float = field(default=0, init=False, repr=False)

    def access_token(self, *, refresh: bool = False) -> str:
        now = time.monotonic()
        if not refresh and self._token and now < self._expires_at:
            return self._token
        try:
            response = self.session.post(
                "https://login.microsoftonline.com/"
                f"{quote(self.tenant_id, safe='')}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise UpstreamUnavailableError("Microsoft Entra token endpoint is unavailable") from exc
        if response.status_code != 200:
            raise AuthenticationError("Microsoft Entra rejected the backend credentials")
        try:
            payload = response.json()
            self._token = str(payload["access_token"])
            expires_in = max(60, int(payload.get("expires_in", 3600)))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Microsoft Entra returned an invalid token response") from exc
        self._expires_at = now + max(30, expires_in - 60)
        return self._token
