"""Pruebas del endpoint de salud."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    """``GET /health`` responde 200 con status ok y la versión configurada."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == get_settings().version
