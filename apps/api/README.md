# tf-api — Backend de TraceForge

API de TraceForge: Python 3.12 + FastAPI + (SQLAlchemy 2 / Alembic en tandas posteriores),
gestionada con **uv**.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestiona también Python 3.12; no necesitas instalarlo aparte).

## Puesta en marcha (desde la raíz del monorepo)

```bash
task setup     # instala dependencias de api y web
task dev-api   # levanta la API en http://127.0.0.1:8000
```

O directamente dentro de `apps/api`:

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health` → `{"status": "ok", "version": "<versión>"}`
- Docs OpenAPI: `http://127.0.0.1:8000/docs`

## Calidad

```bash
uv run ruff check .      # lint
uv run ruff format .     # formato
uv run mypy              # tipos (estricto)
uv run pytest            # pruebas
```

## Estructura

```
apps/api/
  app/
    main.py            # app FastAPI + GET /health + CORS
    core/
      config.py        # Settings (pydantic-settings, lee de .env)
  tests/
    test_health.py
  pyproject.toml
  .python-version      # 3.12
  .env.example
```
