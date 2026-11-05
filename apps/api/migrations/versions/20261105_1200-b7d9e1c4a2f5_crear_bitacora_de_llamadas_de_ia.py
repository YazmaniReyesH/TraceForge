"""crear bitácora de llamadas de IA (ai_call_log)

Revision ID: b7d9e1c4a2f5
Revises: 9c3e71a2f4b8
Create Date: 2026-11-05 12:00:00.000000

Crea la tabla ``ai_call_log`` (F1-T3): auditoría de cada llamada al proveedor de IA (ADR-0005,
ADR-0015). Guarda SIEMPRE qué se envió **ya redactado** (nunca el contenido crudo, ni el mapeo
marcador→valor, ni la API key), más metadatos (proveedor, modelo, estado, tokens, usuario,
workspace/project para aislamiento). ``status`` es ``VARCHAR(20)`` + CHECK nombrado (mismo patrón
que ``kind``/roles). FKs: CASCADE en workspace/project (coherente con el borrado del contenido del
project, ADR-0006); RESTRICT en ``created_by``. Índices en ``workspace_id`` y ``project_id``
(columnas de aislamiento/filtrado).

Revisada a mano; **pendiente de aplicar por el equipo** (`alembic upgrade head`). Reversible.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores de revisión usados por Alembic.
revision: str = "b7d9e1c4a2f5"
down_revision: str | None = "9c3e71a2f4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_call_log",
        sa.Column("ai_call_log_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        # status se mapea en el ORM con StrEnumType (impl VARCHAR); en la BD es String(20) + CHECK.
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        # Lo enviado YA REDACTADO (nunca el crudo); None si no se llegó a enviar (not_configured).
        sa.Column("redacted_prompt", sa.Text(), nullable=True),
        sa.Column("redacted_prompt_sha256", sa.String(length=64), nullable=True),
        sa.Column("redaction_count", sa.Integer(), nullable=False),
        # Código de error de dominio (estable); NUNCA un mensaje con secretos.
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'error', 'not_configured')",
            name="ck_ai_call_log_status",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ai_call_log_id"),
    )
    op.create_index(
        op.f("ix_ai_call_log_workspace_id"), "ai_call_log", ["workspace_id"], unique=False
    )
    op.create_index(op.f("ix_ai_call_log_project_id"), "ai_call_log", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_call_log_project_id"), table_name="ai_call_log")
    op.drop_index(op.f("ix_ai_call_log_workspace_id"), table_name="ai_call_log")
    op.drop_table("ai_call_log")
