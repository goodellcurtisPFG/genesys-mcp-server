"""Loads Genesys Cloud connection settings from environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    environment: str  # e.g. "mypurecloud.com", "usw2.pure.cloud"

    @classmethod
    def from_env(cls) -> "Settings":
        client_id = os.environ.get("GENESYS_CLIENT_ID")
        client_secret = os.environ.get("GENESYS_CLIENT_SECRET")
        environment = os.environ.get("GENESYS_ENVIRONMENT", "mypurecloud.com")

        if not client_id or not client_secret:
            raise RuntimeError(
                "GENESYS_CLIENT_ID and GENESYS_CLIENT_SECRET must be set. "
                "Copy .env.example to .env and fill them in."
            )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
        )
