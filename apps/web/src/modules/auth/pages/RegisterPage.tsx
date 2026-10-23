// Pantalla de registro (crea cuenta e inicia sesión). Textos por i18n; errores por code.

import { Button } from "primereact/button";
import { InputText } from "primereact/inputtext";
import { Message } from "primereact/message";
import { Password } from "primereact/password";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../../../shared/api/errors";
import { useMe, useRegister } from "../hooks";

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const register = useRegister();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    register.mutate(
      { display_name: displayName, email, password },
      { onSuccess: () => navigate("/", { replace: true }) },
    );
  };

  return (
    <div className="tf-auth">
      <div className="tf-auth-card tf-card">
        <h1>{t("auth.registerTitle")}</h1>
        <p className="tf-auth-tagline">{t("app.tagline")}</p>

        {register.isError ? (
          <Message severity="error" text={apiErrorMessage(register.error)} className="tf-field" />
        ) : null}

        <form onSubmit={onSubmit} noValidate>
          <div className="tf-field">
            <label htmlFor="displayName">{t("common.displayName")}</label>
            <InputText
              id="displayName"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
              required
            />
          </div>
          <div className="tf-field">
            <label htmlFor="email">{t("common.email")}</label>
            <InputText
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="tf-field">
            <label htmlFor="password">{t("common.password")}</label>
            <Password
              inputId="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              toggleMask
              autoComplete="new-password"
              promptLabel={t("auth.passwordHint")}
              required
            />
          </div>
          <Button
            type="submit"
            label={register.isPending ? t("auth.registerLoading") : t("auth.registerSubmit")}
            loading={register.isPending}
            disabled={register.isPending}
            style={{ width: "100%" }}
          />
        </form>

        <p className="tf-form-footer">
          <Link to="/login">{t("auth.toLogin")}</Link>
        </p>
      </div>
    </div>
  );
}
