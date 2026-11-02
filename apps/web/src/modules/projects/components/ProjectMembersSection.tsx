// Gestión de miembros de un proyecto: listar, añadir, cambiar rol, quitar.
// UX: solo lead gestiona; regla guest=viewer (a un guest de workspace solo se le ofrece viewer;
// el backend responde 409 guest_must_be_viewer si se forzara).

import { Button } from "primereact/button";
import { confirmDialog } from "primereact/confirmdialog";
import { Dropdown } from "primereact/dropdown";
import { InputText } from "primereact/inputtext";
import { Tag } from "primereact/tag";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { ErrorState, InlineError } from "../../../shared/ui/states";
import { useMe } from "../../auth/hooks";
import { useWorkspaceMembers } from "../../workspaces/hooks";
import {
  useAddProjectMember,
  useProjectMembers,
  useRemoveProjectMember,
  useUpdateProjectMemberRole,
} from "../hooks";
import type { ProjectRole } from "../types";

const ALL_ROLES: ProjectRole[] = ["lead", "contributor", "viewer"];
const GUEST_ROLES: ProjectRole[] = ["viewer"];

export function ProjectMembersSection({
  workspaceId,
  projectId,
  canManage,
}: {
  workspaceId: string;
  projectId: string;
  canManage: boolean;
}) {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const membersQuery = useProjectMembers(workspaceId, projectId);
  const wsMembers = useWorkspaceMembers(workspaceId);
  const addMember = useAddProjectMember(workspaceId, projectId);
  const changeRole = useUpdateProjectMemberRole(workspaceId, projectId);
  const removeMember = useRemoveProjectMember(workspaceId, projectId);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>("viewer");

  // Mapa user_id -> rol de workspace, para aplicar guest=viewer como UX.
  const wsRoleByUser = new Map((wsMembers.data ?? []).map((m) => [m.user_id, m.role]));
  const optionsFor = (userId: string) =>
    (wsRoleByUser.get(userId) === "guest" ? GUEST_ROLES : ALL_ROLES).map((r) => ({
      label: t(`roles.project.${r}`),
      value: r,
    }));
  const addOptions = ALL_ROLES.map((r) => ({ label: t(`roles.project.${r}`), value: r }));

  const onAdd = (e: FormEvent) => {
    e.preventDefault();
    addMember.mutate(
      { email, role },
      {
        onSuccess: () => {
          setEmail("");
          setRole("viewer");
        },
      },
    );
  };

  const confirmRemove = (userId: string, name: string) => {
    confirmDialog({
      header: t("members.removeTitle"),
      message: t("members.removeConfirm", { name, scope: t("members.scopeProject") }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.remove"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () => removeMember.mutate(userId),
    });
  };

  if (membersQuery.isLoading) return <PageLoader />;
  if (membersQuery.isError)
    return <ErrorState error={membersQuery.error} onRetry={() => membersQuery.refetch()} />;
  const members = membersQuery.data ?? [];

  return (
    <div className="tf-stack">
      {canManage ? (
        <form className="tf-stack" onSubmit={onAdd}>
          <span className="tf-member-sub">{t("members.addHint")}</span>
          <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
            <InputText
              type="email"
              placeholder={t("common.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{ flex: "1 1 200px" }}
            />
            <Dropdown
              value={role}
              options={addOptions}
              onChange={(e) => setRole(e.value as ProjectRole)}
              aria-label={t("common.role")}
            />
            <Button
              type="submit"
              icon="pi pi-plus"
              label={t("common.add")}
              loading={addMember.isPending}
            />
          </div>
          {addMember.isError ? <InlineError error={addMember.error} /> : null}
        </form>
      ) : null}

      {members.length === 0 ? (
        <p className="tf-member-sub">{t("members.empty")}</p>
      ) : (
        <div>
          {members.map((m) => {
            const isSelf = m.user_id === me?.user_id;
            return (
              <div key={m.user_id} className="tf-member-row">
                <div className="tf-member-main">
                  <div className="tf-member-email">
                    {m.display_name}{" "}
                    {isSelf ? <span className="tf-member-sub">({t("common.you")})</span> : null}
                  </div>
                  <div className="tf-member-sub tf-mono">{m.email}</div>
                </div>
                <div className="tf-row-actions">
                  {canManage ? (
                    <Dropdown
                      value={m.role}
                      options={optionsFor(m.user_id)}
                      onChange={(e) =>
                        changeRole.mutate({
                          userId: m.user_id,
                          body: { role: e.value as ProjectRole },
                        })
                      }
                      disabled={changeRole.isPending}
                      aria-label={t("members.changeRole")}
                    />
                  ) : (
                    <Tag value={t(`roles.project.${m.role}`)} />
                  )}
                  {canManage ? (
                    <Button
                      type="button"
                      text
                      severity="danger"
                      icon="pi pi-times"
                      tooltip={t("common.remove")}
                      tooltipOptions={{ position: "bottom" }}
                      onClick={() => confirmRemove(m.user_id, m.display_name)}
                    />
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {changeRole.isError ? <InlineError error={changeRole.error} /> : null}
      {removeMember.isError ? <InlineError error={removeMember.error} /> : null}
    </div>
  );
}
