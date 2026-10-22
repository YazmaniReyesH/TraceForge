"""Punto de entrada de la API de TraceForge.

Expone dos chequeos de salud:

- ``GET /health``        → *liveness*: responde sin tocar dependencias externas.
- ``GET /health/ready``  → *readiness*: hace ``SELECT 1`` contra PostgreSQL;
  200 si la base responde, 503 si no.

Los routers de módulos se registrarán aquí a partir de F0-T3.
"""

from typing import TypedDict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings, get_settings
from app.core.db import database_ready, get_engine


class HealthResponse(TypedDict):
    """Forma de la respuesta de ``GET /health``."""

    status: str
    version: str


class ReadyResponse(TypedDict):
    """Forma de la respuesta de ``GET /health/ready``."""

    status: str


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
        """Liveness: el proceso está vivo. No toca la base ni dependencias."""
        return {"status": "ok", "version": settings.version}

    @app.get("/health/ready", response_model=None)
    async def health_ready(
        engine: AsyncEngine = Depends(get_engine),
    ) -> ReadyResponse | JSONResponse:
        """Readiness: la base responde. 200 si hay conexión, 503 si no.

        ``response_model=None`` evita que FastAPI intente derivar un modelo de
        respuesta de la unión (200 dict / 503 JSONResponse).
        """
        if await database_ready(engine):
            return {"status": "ready"}
        return JSONResponse(status_code=503, content={"status": "not ready"})

    return app


app = create_app()
