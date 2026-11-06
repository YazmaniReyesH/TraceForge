"""crear sugerencias de IA y mapeo de redacción cifrado (ai_suggestions, ai_redaction_maps)

Revision ID: f3a1c9d7b2e4
Revises: b7d9e1c4a2f5
Create Date: 2026-11-06 09:00:00.000000

Crea las tablas de la primera función de IA de producto (F1-T4a):

- ``ai_suggestions``: sugerencias de IA (``kind`` description|next_step; ``status``
  pending|accepted|edited, ambos ``VARCHAR(20)`` + CHECK nombrado) con el contenido sugerido, el
  editado (humano) y la **procedencia completa** (ADR-0003): proveedor, modelo, versión de prompt,
  ``ai_call_log_id`` (la llamada que la originó), ``input_refs`` (la evidencia usada, ya redactada),
  conteo de redacción y si se guardó el mapeo cifrado, más la auditoría de la transición.
- ``ai_redaction_maps``: mapeo marcador→valor **cifrado** (Fernet, ADR-0016) para rehidratación
  futura; nunca en claro.

FKs: CASCADE en workspace/project/session (coherente con el borrado del contenido del project,
ADR-0006); RESTRICT en ``created_by``/``reviewed_by``; ``ai_call_log_id`` con SET NULL (purgar la
bitácora no borra la sugerencia). Índices en las columnas de aislamiento/filtrado.

Revisada a mano; **pendiente de aplicar por el equipo** (`alembic upgrade head`). Reversible.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores de revisión usados por Alembic.
revision: str = "f3a1c9d7b2e4"
down_revision: str | None = "b7d9e1c4a2f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_suggestions",
        sa.Column("ai_suggestion_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        # kind/status: VARCHAR(20) + CHECK (mismo patrón que roles / kind de evidencia).
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("suggested_content", sa.Text(), nullable=False),
        sa.Column("suggested_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("edited_content", sa.Text(), nullable=True),
        # Procedencia (ADR-0003).
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("ai_call_log_id", sa.Uuid(), nullable=True),
        sa.Column("input_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("redaction_count", sa.Integer(), nullable=False),
        sa.Column("redaction_map_stored", sa.Boolean(), nullable=False),
        # Auditoría de la transición (ADR-0003).
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("kind IN ('description', 'next_step')", name="ck_ai_suggestions_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'edited')", name="ck_ai_suggestions_status"
        ),
        sa.ForeignKeyConstraint(
            ["ai_call_log_id"], ["ai_call_log.ai_call_log_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ai_suggestion_id"),
    )
    op.create_index(
        op.f("ix_ai_suggestions_workspace_id"), "ai_suggestions", ["workspace_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_suggestions_project_id"), "ai_suggestions", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_suggestions_session_id"), "ai_suggestions", ["session_id"], unique=False
    )

    op.create_table(
        "ai_redaction_maps",
        sa.Column("ai_redaction_map_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ai_suggestion_id", sa.Uuid(), nullable=False),
        # Token CIFRADO del JSON {marcador: valor}. NUNCA en claro.
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("scheme", sa.String(length=20), nullable=False),
        sa.Column("marker_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ai_suggestion_id"], ["ai_suggestions.ai_suggestion_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.workspace_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ai_redaction_map_id"),
    )
    op.create_index(
        op.f("ix_ai_redaction_maps_workspace_id"),
        "ai_redaction_maps",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_redaction_maps_project_id"), "ai_redaction_maps", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_redaction_maps_session_id"), "ai_redaction_maps", ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_redaction_maps_ai_suggestion_id"),
        "ai_redaction_maps",
        ["ai_suggestion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_redaction_maps_ai_suggestion_id"), table_name="ai_redaction_maps")
    op.drop_index(op.f("ix_ai_redaction_maps_session_id"), table_name="ai_redaction_maps")
    op.drop_index(op.f("ix_ai_redaction_maps_project_id"), table_name="ai_redaction_maps")
    op.drop_index(op.f("ix_ai_redaction_maps_workspace_id"), table_name="ai_redaction_maps")
    op.drop_table("ai_redaction_maps")
    op.drop_index(op.f("ix_ai_suggestions_session_id"), table_name="ai_suggestions")
    op.drop_index(op.f("ix_ai_suggestions_project_id"), table_name="ai_suggestions")
    op.drop_index(op.f("ix_ai_suggestions_workspace_id"), table_name="ai_suggestions")
    op.drop_table("ai_suggestions")
