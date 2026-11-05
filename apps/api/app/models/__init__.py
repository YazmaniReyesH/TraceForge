"""Modelos del dominio de TraceForge.

Importar este paquete (``import app.models``) registra TODAS las tablas en
``Base.metadata``, que es lo que Alembic usa para el autogenerate (ver
``migrations/env.py``). ``Base`` se reexporta desde ``app.core.db``.
"""

from app.core.db import Base
from app.models.ai_call_log import AICallLog
from app.models.credential import UserCredential
from app.models.enums import AICallStatus, EvidenceKind, ProjectRole, WorkspaceRole
from app.models.evidence import EvidenceItem, EvidenceItemVersion
from app.models.membership import ProjectMembership, WorkspaceMembership
from app.models.project import Project
from app.models.session import Session
from app.models.user import User
from app.models.workspace import Workspace

__all__ = [
    "AICallLog",
    "AICallStatus",
    "Base",
    "EvidenceItem",
    "EvidenceItemVersion",
    "EvidenceKind",
    "Project",
    "ProjectMembership",
    "ProjectRole",
    "Session",
    "User",
    "UserCredential",
    "Workspace",
    "WorkspaceMembership",
    "WorkspaceRole",
]
