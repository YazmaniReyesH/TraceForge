"""Entidades de membresía: ``workspace_memberships`` y ``project_memberships``.

Vinculan un ``user`` (identidad global) con un workspace o un proyecto, con su rol.
Invariantes de ESQUEMA implementados aquí (ADR-0002, "Rol efectivo e invariantes"):

- Una sola membresía por (user, workspace) y por (user, project) — UNIQUE.
- Un solo ``owner`` por workspace — índice único PARCIAL ``WHERE role = 'owner'``.
- Rol válido — CHECK con nombre explícito (valores tomados de los StrEnum).

Invariantes de SERVICIO (guest = solo viewer, transferencia atómica de owner,
"al menos un owner") NO se implementan aquí: son de F0-T4. Ver la ficha
``docs/modulos/modelo-base.md``.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import ProjectRole, WorkspaceRole, sql_in_clause
from app.models.mixins import CreatedAtMixin
from app.models.types import StrEnumType


class WorkspaceMembership(CreatedAtMixin, Base):
    """Pertenencia de un usuario a un workspace, con su rol de workspace."""

    __tablename__ = "workspace_memberships"

    workspace_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # ON DELETE RESTRICT: no se puede borrar un usuario con membresías (ver ADR-0006).
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # ON DELETE CASCADE: borrar el workspace arrastra sus membresías.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        StrEnumType(WorkspaceRole, length=20), nullable=False
    )

    __table_args__ = (
        # Una membresía por (user, workspace). Indexa user_id como columna líder.
        UniqueConstraint("user_id", "workspace_id", name="uq_workspace_memberships_user_workspace"),
        # Rol válido (valores EXACTOS del StrEnum WorkspaceRole).
        CheckConstraint(
            f"role IN ({sql_in_clause(WorkspaceRole)})",
            name="ck_workspace_memberships_role",
        ),
        # Un solo owner por workspace: índice único PARCIAL.
        Index(
            "uq_workspace_memberships_single_owner",
            "workspace_id",
            unique=True,
            postgresql_where=text("role = 'owner'"),
        ),
    )


class ProjectMembership(CreatedAtMixin, Base):
    """Pertenencia de un usuario a un proyecto, con su rol de proyecto."""

    __tablename__ = "project_memberships"

    project_membership_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # ON DELETE RESTRICT: no se puede borrar un usuario con membresías (ver ADR-0006).
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # ON DELETE CASCADE: borrar el proyecto arrastra sus membresías.
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ProjectRole] = mapped_column(StrEnumType(ProjectRole, length=20), nullable=False)

    __table_args__ = (
        # Una membresía por (user, project). Indexa user_id como columna líder.
        UniqueConstraint("user_id", "project_id", name="uq_project_memberships_user_project"),
        # Rol válido (valores EXACTOS del StrEnum ProjectRole).
        CheckConstraint(
            f"role IN ({sql_in_clause(ProjectRole)})",
            name="ck_project_memberships_role",
        ),
    )
