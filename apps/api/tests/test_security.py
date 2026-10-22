"""Pruebas unitarias (puras, sin BD) de la autorización: rol efectivo y matriz."""

import pytest

from app.core.security import (
    Permission,
    effective_project_role,
    has_permission,
    has_project_permission,
)
from app.models.enums import ProjectRole, WorkspaceRole


@pytest.mark.parametrize(
    ("workspace_role", "project_role", "expected"),
    [
        # owner/admin: piso implícito = lead, aunque no tengan (o tengan menor) rol de proyecto.
        (WorkspaceRole.OWNER, None, ProjectRole.LEAD),
        (WorkspaceRole.ADMIN, None, ProjectRole.LEAD),
        (WorkspaceRole.ADMIN, ProjectRole.VIEWER, ProjectRole.LEAD),  # el piso gana; no resta
        (WorkspaceRole.OWNER, ProjectRole.CONTRIBUTOR, ProjectRole.LEAD),
        # member/guest: solo por membresía explícita.
        (WorkspaceRole.MEMBER, ProjectRole.CONTRIBUTOR, ProjectRole.CONTRIBUTOR),
        (WorkspaceRole.MEMBER, None, None),
        (WorkspaceRole.GUEST, ProjectRole.VIEWER, ProjectRole.VIEWER),
        (WorkspaceRole.GUEST, None, None),
    ],
)
def test_effective_project_role(
    workspace_role: WorkspaceRole,
    project_role: ProjectRole | None,
    expected: ProjectRole | None,
) -> None:
    assert effective_project_role(workspace_role, project_role) == expected


def test_matrix_owner_has_all() -> None:
    assert has_permission(WorkspaceRole.OWNER, Permission.WORKSPACES_DELETE)
    assert has_permission(WorkspaceRole.OWNER, Permission.WORKSPACES_READ)
    assert has_permission(WorkspaceRole.OWNER, Permission.WORKSPACES_MANAGE_MEMBERS)


def test_matrix_admin_manages_but_not_deletes() -> None:
    assert has_permission(WorkspaceRole.ADMIN, Permission.WORKSPACES_MANAGE_MEMBERS)
    assert has_permission(WorkspaceRole.ADMIN, Permission.WORKSPACES_UPDATE)
    assert not has_permission(WorkspaceRole.ADMIN, Permission.WORKSPACES_DELETE)


def test_matrix_member_reads_only() -> None:
    assert has_permission(WorkspaceRole.MEMBER, Permission.WORKSPACES_READ)
    assert not has_permission(WorkspaceRole.MEMBER, Permission.WORKSPACES_UPDATE)
    assert not has_permission(WorkspaceRole.MEMBER, Permission.WORKSPACES_MANAGE_MEMBERS)


def test_matrix_guest_has_no_workspace_overview() -> None:
    # guest no ve el overview del workspace (ADR-0002): sin permisos a nivel workspace.
    assert not has_permission(WorkspaceRole.GUEST, Permission.WORKSPACES_READ)


def test_workspace_matrix_project_create_and_transfer() -> None:
    # Crear proyectos: owner/admin sí; member/guest no. Transferir propiedad: solo owner.
    assert has_permission(WorkspaceRole.OWNER, Permission.PROJECTS_CREATE)
    assert has_permission(WorkspaceRole.ADMIN, Permission.PROJECTS_CREATE)
    assert not has_permission(WorkspaceRole.MEMBER, Permission.PROJECTS_CREATE)
    assert has_permission(WorkspaceRole.OWNER, Permission.WORKSPACES_TRANSFER_OWNERSHIP)
    assert not has_permission(WorkspaceRole.ADMIN, Permission.WORKSPACES_TRANSFER_OWNERSHIP)


def test_project_matrix_by_role() -> None:
    assert has_project_permission(ProjectRole.LEAD, Permission.PROJECTS_DELETE)
    assert has_project_permission(ProjectRole.LEAD, Permission.PROJECTS_MANAGE_MEMBERS)
    assert has_project_permission(ProjectRole.CONTRIBUTOR, Permission.PROJECTS_UPDATE)
    assert not has_project_permission(ProjectRole.CONTRIBUTOR, Permission.PROJECTS_DELETE)
    assert not has_project_permission(ProjectRole.CONTRIBUTOR, Permission.PROJECTS_MANAGE_MEMBERS)
    assert has_project_permission(ProjectRole.VIEWER, Permission.PROJECTS_READ)
    assert not has_project_permission(ProjectRole.VIEWER, Permission.PROJECTS_UPDATE)


def test_owner_admin_get_full_project_access_via_floor() -> None:
    # owner/admin: piso efectivo = lead -> todos los permisos de proyecto, sin membresía.
    for ws_role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        effective = effective_project_role(ws_role, None)
        assert effective is ProjectRole.LEAD
        assert has_project_permission(effective, Permission.PROJECTS_DELETE)
        assert has_project_permission(effective, Permission.PROJECTS_MANAGE_MEMBERS)
