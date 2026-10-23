// Pantalla de inicio de sesión. Estados de carga/error manejados; textos por i18n.

import { Button } from "primereact/button";
import { InputText } from "primereact/inputtext";
import { Message } from "primereact/message";
import { Password } from "primereact/password";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../../../shared/api/errors";
import { useLogin, useMe } from "../hooks";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate("/", { replace: true }) });
  };

  return (
    <div className="tf-auth">
      <div className="tf-auth-card tf-card">
        <h1>{t("auth.loginTitle")}</h1>
        <p className="tf-auth-tagline">{t("app.tagline")}</p>

        {login.isError ? (
          <Message severity="error" text={apiErrorMessage(login.error)} className="tf-field" />
        ) : null}

        <form onSubmit={onSubmit} noValidate>
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
              feedback={false}
              toggleMask
              autoComplete="current-password"
              required
            />
          </div>
          <Button
            type="submit"
            label={login.isPending ? t("auth.loginLoading") : t("auth.loginSubmit")}
            loading={login.isPending}
            disabled={login.isPending}
            style={{ width: "100%" }}
          />
        </form>

        <p className="tf-form-footer">
          <Link to="/register">{t("auth.toRegister")}</Link>
        </p>
      </div>
    </div>
  );
}
