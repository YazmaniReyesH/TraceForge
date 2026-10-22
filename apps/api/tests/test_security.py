"""Pruebas unitarias (puras, sin BD) de la autorización: rol efectivo y matriz."""

import pytest

from app.core.security import Permission, effective_project_role, has_permission
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
