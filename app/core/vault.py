"""Vault dynamic secrets reader — reads from Vault Agent-mounted files.

Per ISS-003: Vault secret rotation must not require app restart.

Pattern: Vault Agent sidecar mounts secrets to /vault/secrets/db.json and
/vault/secrets/keycloak.json. The app reads these files on each request
(or on a timer) instead of caching at startup.

Vault Agent `exec` stanza sends SIGHUP when credentials rotate, triggering
a reload on next request.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VaultSecretsReader:
    """Read dynamic secrets from Vault Agent-mounted files.

    Files are updated by Vault Agent on credential rotation.
    No caching — read fresh on each call.
    """

    def __init__(
        self,
        db_secret_path: str = "/vault/secrets/db.json",
        keycloak_secret_path: str = "/vault/secrets/keycloak.json",
    ):
        self.db_secret_path = Path(db_secret_path)
        self.keycloak_secret_path = Path(keycloak_secret_path)

    def get_db_credentials(self) -> dict:
        """Read PostgreSQL credentials from Vault Agent mount.

        Expected format (from Vault PostgreSQL engine):
        {
            "username": "v-role-...",
            "password": "...",
            "ttl": 3600
        }
        """
        if not self.db_secret_path.exists():
            # Local dev: return from env
            from app.config import settings
            return {
                "username": settings.postgres_user,
                "password": settings.postgres_password,
            }

        try:
            with open(self.db_secret_path) as f:
                data = json.load(f)
            return {"username": data["username"], "password": data["password"]}
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read DB secrets from Vault: {e}")
            from app.config import settings
            return {
                "username": settings.postgres_user,
                "password": settings.postgres_password,
            }

    def get_keycloak_client_secret(self) -> str:
        """Read Keycloak client secret from Vault Agent mount.

        Expected format:
        {
            "client_secret": "...",
            "ttl": 3600
        }
        """
        if not self.keycloak_secret_path.exists():
            # Local dev: return from env
            from app.config import settings
            return settings.keycloak_client_secret

        try:
            with open(self.keycloak_secret_path) as f:
                data = json.load(f)
            return data["client_secret"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read Keycloak secret from Vault: {e}")
            from app.config import settings
            return settings.keycloak_client_secret


# Global reader instance
_vault_reader = VaultSecretsReader()


def get_db_credentials() -> dict:
    """Get current PostgreSQL credentials (fresh from Vault Agent file)."""
    return _vault_reader.get_db_credentials()


def get_keycloak_client_secret() -> str:
    """Get current Keycloak client secret (fresh from Vault Agent file)."""
    return _vault_reader.get_keycloak_client_secret()
