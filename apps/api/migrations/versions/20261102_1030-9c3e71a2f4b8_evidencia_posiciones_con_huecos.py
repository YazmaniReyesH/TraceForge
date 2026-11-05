"""evidencia: posiciones con huecos (índice no único + backfill)

Cambia la estrategia de orden de ``evidence_items`` (ADR-0013): de posiciones contiguas 0,1,2…
con UNIQUE(session_id, position) a una **escala con huecos** (múltiplos de ~1000) ordenada por un
**índice no único** con desempate determinista por (position, created_at, evidence_item_id).

- Reemplaza la UNIQUE por un índice NO único (permite colisiones transitorias al renumerar/reordenar
  de forma optimista; la unicidad de la posición no era un invariante de negocio).
- **Rellena** (backfill) las posiciones existentes con la nueva escala: por sesión, en el orden
  actual, asigna 1000, 2000, 3000, …

Reversible: el downgrade reconstruye posiciones contiguas 0-based por sesión (compatibles con la
UNIQUE) y restaura la UNIQUE. Revisada a mano; **pendiente de aplicar por el equipo**.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identificadores de revisión usados por Alembic.
revision: str = "9c3e71a2f4b8"
down_revision: str | None = "58cdba920ffa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Quitar la unicidad de (session_id, position): deja de ser un invariante (ADR-0013).
    op.drop_constraint("uq_evidence_items_session_position", "evidence_items", type_="unique")

    # 2) Backfill a escala con huecos: por sesión, en el orden actual, 1000·n (n=1,2,3…).
    #    Incluye ítems borrados (soft-delete) para mantener posiciones distintas y ordenadas.
    op.execute(
        sa.text(
            """
            UPDATE evidence_items AS ei
            SET position = sub.rn * 1000
            FROM (
                SELECT evidence_item_id,
                       row_number() OVER (
                           PARTITION BY session_id
                           ORDER BY position, created_at, evidence_item_id
                       ) AS rn
                FROM evidence_items
            ) AS sub
            WHERE ei.evidence_item_id = sub.evidence_item_id
            """
        )
    )

    # 3) Índice NO único de orden (cubre el filtro por session_id como columna líder).
    op.create_index(
        "ix_evidence_items_session_position",
        "evidence_items",
        ["session_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    # 1) Quitar el índice no único.
    op.drop_index("ix_evidence_items_session_position", table_name="evidence_items")

    # 2) Backfill inverso: posiciones contiguas 0-based por sesión (compatibles con la UNIQUE).
    op.execute(
        sa.text(
            """
            UPDATE evidence_items AS ei
            SET position = sub.rn - 1
            FROM (
                SELECT evidence_item_id,
                       row_number() OVER (
                           PARTITION BY session_id
                           ORDER BY position, created_at, evidence_item_id
                       ) AS rn
                FROM evidence_items
            ) AS sub
            WHERE ei.evidence_item_id = sub.evidence_item_id
            """
        )
    )

    # 3) Restaurar la UNIQUE(session_id, position).
    op.create_unique_constraint(
        "uq_evidence_items_session_position",
        "evidence_items",
        ["session_id", "position"],
    )
