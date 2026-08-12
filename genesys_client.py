"""Thin wrapper around the Genesys Cloud Platform API using an OAuth2
Client Credentials grant.

This client only ever issues HTTP calls that the tools in server.py tell it
to. Read-only enforcement lives in Genesys Cloud itself: the OAuth client
this uses must be assigned a role with view-only permissions. Nothing here
stops you from pointing it at a write endpoint, so don't add tools that do.
"""

from __future__ import annotations

import base64
import time

import httpx


class GenesysAuthError(RuntimeError):
    pass


class GenesysApiError(RuntimeError):
    pass


class GenesysClient:
    def __init__(self, client_id: str, client_secret: str, environment: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._login_base = f"https://login.{environment}"
        self._api_base = f"https://api.{environment}"
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._http = httpx.Client(timeout=30.0)

    def _fetch_token(self) -> None:
        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        resp = self._http.post(
            f"{self._login_base}/oauth/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code != 200:
            raise GenesysAuthError(
                f"Genesys OAuth token request failed: {resp.status_code} {resp.text}"
            )
        payload = resp.json()
        self._token = payload["access_token"]
        # Refresh a minute early so we don't race the actual expiry.
        self._token_expiry = time.time() + payload.get("expires_in", 3600) - 60

    def _ensure_token(self) -> str:
        if not self._token or time.time() >= self._token_expiry:
            self._fetch_token()
        assert self._token is not None
        return self._token

    def request(self, method: str, path: str, **kwargs) -> dict:
        token = self._ensure_token()
        resp = self._http.request(
            method,
            f"{self._api_base}{path}",
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )
        if resp.status_code == 401:
            # Token may have been revoked/expired server-side; refresh once and retry.
            self._fetch_token()
            resp = self._http.request(
                method,
                f"{self._api_base}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
                **kwargs,
            )
        if resp.status_code >= 400:
            raise GenesysApiError(
                f"Genesys API error on {method} {path}: {resp.status_code} {resp.text}"
            )
        return resp.json() if resp.content else {}
