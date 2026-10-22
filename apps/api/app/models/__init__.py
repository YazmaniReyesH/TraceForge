"""Modelos del dominio de TraceForge.

Importar este paquete (``import app.models``) registra TODAS las tablas en
``Base.metadata``, que es lo que Alembic usa para el autogenerate (ver
``migrations/env.py``). ``Base`` se reexporta desde ``app.core.db``.
"""

from app.core.db import Base
from app.models.enums import ProjectRole, WorkspaceRole
from app.models.membership import ProjectMembership, WorkspaceMembership
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace

__all__ = [
    "Base",
    "Project",
    "ProjectMembership",
    "ProjectRole",
    "User",
    "Workspace",
    "WorkspaceMembership",
    "WorkspaceRole",
]
