"""Nombres de constraints de la base, centralizados.

Se usan para mapear ``IntegrityError`` → errores de dominio (ver ``app/core/integrity.py``)
sin strings mágicos repartidos. Deben coincidir con los nombres reales en la base
(migraciones / modelos). Los de membresía/owner los consumirá F0-T4b-2.
"""

# users
USERS_EMAIL_UNIQUE = "users_email_key"  # UNIQUE(email) — nombre por defecto de Postgres

# workspace_memberships
WORKSPACE_MEMBERSHIP_UNIQUE = "uq_workspace_memberships_user_workspace"
WORKSPACE_SINGLE_OWNER = "uq_workspace_memberships_single_owner"
WORKSPACE_ROLE_CHECK = "ck_workspace_memberships_role"

# project_memberships
PROJECT_MEMBERSHIP_UNIQUE = "uq_project_memberships_user_project"
PROJECT_ROLE_CHECK = "ck_project_memberships_role"
