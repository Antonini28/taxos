"""Typed settings — the only place environment is read (Phase 6 doc 02 §3).

Tier rules (Phase 8 doc 03 §3): topology facts via env, secrets via Key Vault refs,
flags via App Config. `os.environ` access anywhere else in the codebase is banned.
"""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Two DSNs by design (Phase 6 doc 03 §1 / migration 0002).

    `dsn` is the application's non-superuser role — RLS applies to it. `migration_dsn`
    owns the schema. The app must never be handed the migration credentials: a
    superuser connection silently bypasses row-level security, turning tenant
    isolation into decoration.
    """

    dsn: SecretStr = SecretStr("postgresql+asyncpg://taxos_app:taxos_app@localhost:5432/taxos")
    migration_dsn: SecretStr = SecretStr("postgresql+asyncpg://taxos:taxos@localhost:5432/taxos")
    pool_size: int = 10
    statement_timeout_ms: int = 30_000


class RedisSettings(BaseSettings):
    url: SecretStr = SecretStr("redis://localhost:6379/0")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAXOS_", env_nested_delimiter="__", env_file=".env", extra="ignore"
    )

    env: Literal["local", "ci", "staging", "prod"] = "local"
    release: str = "dev"
    expose_openapi: bool = True
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()

    def model_post_init(self, __context: object) -> None:
        # Fail-closed prod assertions (deployment guide §4)
        if self.env == "prod" and self.expose_openapi:
            raise ValueError("prod config invalid: expose_openapi must be False")
