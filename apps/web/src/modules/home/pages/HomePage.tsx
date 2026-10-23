// Pantalla de inicio post-login (placeholder; sin lógica de dominio todavía).

import { useTranslation } from "react-i18next";

import { useMe } from "../../auth/hooks";

export function HomePage() {
  const { t } = useTranslation();
  const { data: user } = useMe();

  return (
    <section>
      <h1>{t("home.title")}</h1>
      {user ? (
        <p style={{ color: "var(--text-strong)" }}>
          {t("home.welcome", { name: user.display_name })}
        </p>
      ) : null}
      <p style={{ color: "var(--text-muted)" }}>{t("home.sessionOk")}</p>
      <div className="tf-card" style={{ marginTop: "var(--space-5)" }}>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>{t("home.placeholder")}</p>
        {user ? (
          <p className="tf-mono" style={{ marginBottom: 0, color: "var(--text-muted)" }}>
            {user.email}
          </p>
        ) : null}
      </div>
    </section>
  );
}
