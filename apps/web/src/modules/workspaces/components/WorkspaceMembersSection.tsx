// Gestión de miembros de un workspace: listar, añadir, cambiar rol, quitar y transferir.
// Permisos como UX (el backend manda): añadir/cambiar/quitar => owner/admin; transferir => owner.

import { confirmDialog } from "primereact/confirmdialog";
import { Dropdown } from "primereact/dropdown";
import { InputText } from "primereact/inputtext";
import { Button } from "primereact/button";
import { Tag } from "primereact/tag";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { PageLoader } from "../../../shared/ui/PageLoader";
import { ErrorState, InlineError } from "../../../shared/ui/states";
import { useMe } from "../../auth/hooks";
import {
  useAddWorkspaceMember,
  useRemoveWorkspaceMember,
  useTransferWorkspaceOwnership,
  useUpdateWorkspaceMemberRole,
  useWorkspaceMembers,
} from "../hooks";
import type { WorkspaceRole } from "../types";

const ASSIGNABLE: WorkspaceRole[] = ["admin", "member", "guest"];

export function WorkspaceMembersSection({
  workspaceId,
  myRole,
}: {
  workspaceId: string;
  myRole: WorkspaceRole | undefined;
}) {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const membersQuery = useWorkspaceMembers(workspaceId);
  const addMember = useAddWorkspaceMember(workspaceId);
  const changeRole = useUpdateWorkspaceMemberRole(workspaceId);
  const removeMember = useRemoveWorkspaceMember(workspaceId);
  const transfer = useTransferWorkspaceOwnership(workspaceId);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("member");

  const canManage = myRole === "owner" || myRole === "admin";
  const canTransfer = myRole === "owner";

  const roleOptions = ASSIGNABLE.map((r) => ({ label: t(`roles.workspace.${r}`), value: r }));

  const onAdd = (e: FormEvent) => {
    e.preventDefault();
    addMember.mutate(
      { email, role },
      {
        onSuccess: () => {
          setEmail("");
          setRole("member");
        },
      },
    );
  };

  const confirmRemove = (userId: string, name: string) => {
    confirmDialog({
      header: t("members.removeTitle"),
      message: t("members.removeConfirm", { name, scope: t("members.scopeWorkspace") }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("common.remove"),
      rejectLabel: t("common.cancel"),
      acceptClassName: "p-button-danger",
      accept: () => removeMember.mutate(userId),
    });
  };

  const confirmTransfer = (userId: string, name: string) => {
    confirmDialog({
      header: t("members.transferTitle"),
      message: t("members.transferConfirm", { name }),
      icon: "pi pi-exclamation-triangle",
      acceptLabel: t("members.transferAction"),
      rejectLabel: t("common.cancel"),
      accept: () => transfer.mutate({ new_owner_user_id: userId }),
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
              options={roleOptions}
              onChange={(e) => setRole(e.value as WorkspaceRole)}
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
            const isOwnerRow = m.role === "owner";
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
                  {canManage && !isOwnerRow ? (
                    <Dropdown
                      value={m.role}
                      options={roleOptions}
                      onChange={(e) =>
                        changeRole.mutate({
                          userId: m.user_id,
                          body: { role: e.value as WorkspaceRole },
                        })
                      }
                      disabled={changeRole.isPending}
                      aria-label={t("members.changeRole")}
                    />
                  ) : (
                    <Tag value={t(`roles.workspace.${m.role}`)} />
                  )}
                  {canTransfer && !isOwnerRow ? (
                    <Button
                      type="button"
                      text
                      icon="pi pi-crown"
                      tooltip={t("members.transfer")}
                      tooltipOptions={{ position: "bottom" }}
                      onClick={() => confirmTransfer(m.user_id, m.display_name)}
                    />
                  ) : null}
                  {canManage && !isOwnerRow ? (
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
      {transfer.isError ? <InlineError error={transfer.error} /> : null}
    </div>
  );
}
