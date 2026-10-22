"""Configuración de la aplicación.

Lee variables de entorno (y de un archivo ``.env`` en desarrollo) con
``pydantic-settings``. La identidad, el aislamiento por workspace y los secretos
reales viven aquí a partir de tandas posteriores; en F0-T1 solo lo mínimo.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la API leídos del entorno / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TF_",
        extra="ignore",
    )

    # Metadatos de la app
    app_name: str = "TraceForge API"
    version: str = "0.1.0"
    environment: str = "development"

    # CORS: orígenes del frontend en desarrollo (Vite -> 5173).
    # Lista separada por comas en la variable TF_CORS_ORIGINS.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ── PostgreSQL (único servicio cableado en código en F0-T2) ──
    # Driver async: SQLAlchemy 2 + asyncpg. Apunta a la infra de `task up`.
    database_url: str = "postgresql+asyncpg://tf:tf_dev_password@127.0.0.1:5432/traceforge"

    # ── Redis (configuración lista, SIN uso en código todavía — fase posterior) ──
    redis_url: str = "redis://127.0.0.1:6379/0"

    # ── Almacenamiento S3 / MinIO — RESERVADO, SIN uso en código todavía ──
    # MinIO quedó DIFERIDO en F0-T2 (ver compose.yaml): no hay servicio de
    # almacenamiento levantado aún. Estos campos se conservan ya definidos para no
    # reescribir la config cuando se implemente el almacenamiento; sus valores por
    # defecto son solo placeholders hasta entonces.
    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_access_key: str = "tf_minio"
    s3_secret_key: str = "tf_minio_dev_password"
    s3_bucket: str = "traceforge"

    # ── Autenticación (F0-T4a) ──
    # JWT (HS256). El secreto de DEV es inseguro a propósito: en staging/producción
    # DEBE sobreescribirse con TF_JWT_SECRET. La caducidad del token es configurable.
    jwt_secret: str = "dev-insecure-change-me-set-TF_JWT_SECRET-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # Cookie de sesión (httpOnly). `secure=True` en prod (requiere HTTPS).
    auth_cookie_name: str = "tf_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"

    # Argon2id: factor de costo configurable (ver app/auth/hashing.py).
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # KiB (64 MiB)
    argon2_parallelism: int = 4

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Acepta ``TF_CORS_ORIGINS`` como lista separada por comas (no solo JSON)."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de ``Settings``."""
    return Settings()
