"""crear caché de análisis de contexto de sesión (ai_session_analyses)

Revision ID: a4e8c21f9b63
Revises: f3a1c9d7b2e4
Create Date: 2026-11-06 15:00:00.000000

Crea la tabla del **análisis de contexto de sesión** (F1-T4c, ADR-0017): guía efímera de 4 bloques,
cacheada **una fila por sesión** (UNIQUE ``session_id``). No es contenido aprobable (no hay
accept/edit): es caché/optimización para el *hash-guard*.

- ``state_hash``: hash del estado analizable (ítems activos: id + versión + posición, en orden) +
  versión de prompt. Si coincide con el guardado y no hay ``force``, se devuelve sin llamar al LLM.
- ``result`` (JSONB): los 4 bloques **validados** (ADR-0004).
- Procedencia (ADR-0003): proveedor, modelo, versión de prompt, ``ai_call_log_id`` (SET NULL).
- Mapeo de redacción **cifrado** (Fernet, ADR-0016) en ``redaction_ciphertext`` (NULL si no hubo
  secretos o faltaba la clave; jamás en claro). Reusa el mecanismo de ADR-0016 sin tocar la tabla
  parada ``ai_redaction_maps``.

FKs: CASCADE en workspace/project/session (ADR-0006); RESTRICT en ``created_by``; ``ai_call_log_id``
con SET NULL. Índices de aislamiento; ``session_id`` es UNIQUE (una fila por sesión).

Esta tanda **NO** borra ``ai_suggestions``/``ai_redaction_maps`` (flujo aparcado, ADR-0017): esta
migración solo AÑADE la tabla nueva.

Revisada a mano; **pendiente de aplicar por el equipo** (`alembic upgrade head`). Reversible.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores de revisión usados por Alembic.
revision: str = "a4e8c21f9b63"
down_revision: str | None = "f3a1c9d7b2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_session_analyses",
        sa.Column("ai_session_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("analyzed_item_count", sa.Integer(), nullable=False),
        # Procedencia (ADR-0003).
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("ai_call_log_id", sa.Uuid(), nullable=True),
        # Redacción (ADR-0005/0016): mapeo CIFRADO (NULL si no aplica). Nunca en claro.
        sa.Column("redaction_count", sa.Integer(), nullable=False),
        sa.Column("redaction_ciphertext", sa.Text(), nullable=True),
        sa.Column("redaction_scheme", sa.String(length=20), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ai_call_log_id"], ["ai_call_log.ai_call_log_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ai_session_analysis_id"),
    )
    op.create_index(
        op.f("ix_ai_session_analyses_workspace_id"),
        "ai_session_analyses",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_session_analyses_project_id"),
        "ai_session_analyses",
        ["project_id"],
        unique=False,
    )
    # UNIQUE: una fila por sesión (el último análisis). Se sobrescribe al re-analizar.
    op.create_index(
        op.f("ix_ai_session_analyses_session_id"),
        "ai_session_analyses",
        ["session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_session_analyses_session_id"), table_name="ai_session_analyses")
    op.drop_index(op.f("ix_ai_session_analyses_project_id"), table_name="ai_session_analyses")
    op.drop_index(op.f("ix_ai_session_analyses_workspace_id"), table_name="ai_session_analyses")
    op.drop_table("ai_session_analyses")
