"""Punto de entrada de la API de TraceForge.

En F0-T1 solo expone ``GET /health`` y configura CORS para el frontend de
desarrollo. Los routers de módulos se registrarán aquí en tandas posteriores.
"""

from typing import TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings


class HealthResponse(TypedDict):
    """Forma de la respuesta de ``GET /health``."""

    status: str
    version: str


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    settings: Settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> HealthResponse:
        """Comprobación de salud del servicio."""
        return {"status": "ok", "version": settings.version}

    return app


app = create_app()
