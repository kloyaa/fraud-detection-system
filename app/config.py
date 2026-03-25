"""Configuration management for RAS backend.

Loads configuration from environment variables with Pydantic validation.
All settings are immutable and validated at startup.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings validated at startup (Pydantic v2)."""

    # Environment
    environment: str = Field(default="development", pattern="^(development|staging|production|testing)$")
    debug: bool = Field(default=False)

    # API
    api_title: str = "Risk Assessment System (RAS)"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # OpenAPI Documentation (Swagger)
    # Enabled in dev/staging, disabled in production for security
    enable_docs: bool = Field(default=True)

    # Database (PostgreSQL)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="ras_dev")

    @property
    def database_url(self) -> str:
        """Construct async SQLAlchemy database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # PostgreSQL read replica (analytics queries — falls back to primary if not set)
    postgres_read_host: Optional[str] = Field(default=None)
    postgres_read_port: int = Field(default=5432)

    @property
    def database_read_url(self) -> str:
        """Read replica URL; falls back to primary for local dev."""
        host = self.postgres_read_host or self.postgres_host
        port = self.postgres_read_port if self.postgres_read_host else self.postgres_port
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{host}:{port}/{self.postgres_db}"
        )

    # Redis (for idempotency, caching)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Kafka
    kafka_bootstrap_servers: str = Field(default="localhost:9092")

    # Cassandra
    cassandra_hosts: str = Field(default="localhost")
    cassandra_port: int = Field(default=9042)
    cassandra_keyspace: str = Field(default="ras_dev")

    # Vault
    vault_addr: str = Field(default="http://localhost:8200")
    vault_token: str = Field(default="dev-root-token")

    # Keycloak
    keycloak_server_url: str = Field(default="http://localhost:8080")
    keycloak_realm: str = Field(default="ras")
    keycloak_client_id: str = Field(default="ras-backend")
    keycloak_client_secret: str = Field(default="change-me")

    # Logging
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    class Config:
        """Pydantic settings config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance - loaded once at startup
settings = Settings()
