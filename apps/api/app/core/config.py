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
