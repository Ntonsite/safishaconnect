import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, KeyRound } from "lucide-react";
import { ApiError } from "../../api/client";
import { homeFor, useAuth } from "../../auth/AuthContext";
import { useConfig } from "../../config/brand";
import { currentLocale } from "../../i18n";
import { Button } from "../../shared/components/Button";
import { Alert } from "../../shared/components/Feedback";
import { Field, Input } from "../../shared/components/Field";
import { useErrorMessage } from "../../shared/hooks/useErrorMessage";
import { TZ_PHONE, PASSWORD_RULE } from "../../shared/utils/validation";

function safeNext(next: string | null): string | null {
  // Only allow same-site relative paths to avoid open redirects.
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}

function AuthAside() {
  const { t } = useTranslation();
  return (
    <aside className="auth-aside" aria-hidden>
      <blockquote>{t("landing.heroTitle")}</blockquote>
      <ul>
        <li>
          <CheckCircle2 /> {t("landing.heroPoints.verified")}
        </li>
        <li>
          <CheckCircle2 /> {t("landing.heroPoints.fixedPrice")}
        </li>
        <li>
          <CheckCircle2 /> {t("landing.heroPoints.cash")}
        </li>
      </ul>
    </aside>
  );
}

const loginSchema = z.object({
  identifier: z.string().trim().min(3),
  password: z.string().min(1),
});
type LoginValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const { demo_accounts } = useConfig();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const toMessage = useErrorMessage();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, setValue, formState } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  if (user) return <Navigate to={next ?? homeFor(user.role)} replace />;

  const onSubmit = handleSubmit(async ({ identifier, password }) => {
    setError(null);
    try {
      const me = await login(identifier, password);
      navigate(next && me.role === "CUSTOMER" ? next : homeFor(me.role), { replace: true });
    } catch (e) {
      setError(toMessage(e));
    }
  });

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-panel-inner stack-lg">
          <div className="stack-sm">
            <h1 className="display" style={{ fontSize: "var(--text-3xl)" }}>
              {t("auth.loginTitle")}
            </h1>
            <p className="muted">{t("auth.loginSubtitle")}</p>
          </div>
          {error && <Alert tone="danger">{error}</Alert>}
          <form className="stack" onSubmit={onSubmit} noValidate>
            <Field label={t("auth.identifier")} error={formState.errors.identifier && t("validation.required")}>
              <Input autoComplete="username" inputMode="email" {...register("identifier")} />
            </Field>
            <Field label={t("auth.password")} error={formState.errors.password && t("validation.required")}>
              <Input type="password" autoComplete="current-password" {...register("password")} />
            </Field>
            <Button type="submit" size="lg" block loading={formState.isSubmitting}>
              {t("auth.loginButton")}
            </Button>
          </form>
          <p className="muted">
            {t("auth.noAccount")} <Link to={`/register${next ? `?next=${encodeURIComponent(next)}` : ""}`}>{t("auth.createAccount")}</Link>
            {" · "}
            <Link to="/join">{t("nav.becomeProvider")}</Link>
          </p>

          {demo_accounts.length > 0 && (
            <div className="demo-accounts">
              <div className="row" style={{ gap: 8 }}>
                <KeyRound size={18} aria-hidden />
                <strong>{t("auth.demoTitle")}</strong>
              </div>
              <p className="small muted" style={{ marginTop: 4 }}>
                {t("auth.demoBody")}
              </p>
              <div className="demo-accounts-grid">
                {demo_accounts.map((acc) => (
                  <button
                    key={acc.email}
                    type="button"
                    onClick={() => {
                      setValue("identifier", acc.email);
                      setValue("password", acc.password);
                    }}
                  >
                    <strong>{t(`auth.demoRoles.${acc.role}`)}</strong>
                    <span>{acc.email}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      <AuthAside />
    </div>
  );
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { user, register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const toMessage = useErrorMessage();
  const [error, setError] = useState<string | null>(null);

  const schema = z.object({
    full_name: z.string().trim().min(2, t("validation.minLength", { count: 2 })),
    phone: z.string().trim().regex(TZ_PHONE, t("validation.phone")),
    email: z.union([z.literal(""), z.string().trim().email(t("validation.email"))]),
    password: z.string().regex(PASSWORD_RULE, t("validation.password")),
  });
  type Values = z.infer<typeof schema>;
  const { register, handleSubmit, formState, setError: setFieldError } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      await registerUser({ ...values, email: values.email || null, preferred_locale: currentLocale() });
      navigate(next ?? "/app", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.code === "PHONE_TAKEN") setFieldError("phone", { message: toMessage(e) });
      else if (e instanceof ApiError && e.code === "EMAIL_TAKEN") setFieldError("email", { message: toMessage(e) });
      else setError(toMessage(e));
    }
  });

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-panel-inner stack-lg">
          <div className="stack-sm">
            <h1 className="display" style={{ fontSize: "var(--text-3xl)" }}>
              {t("auth.registerTitle")}
            </h1>
            <p className="muted">{t("auth.registerSubtitle")}</p>
          </div>
          {error && <Alert tone="danger">{error}</Alert>}
          <form className="stack" onSubmit={onSubmit} noValidate>
            <Field label={t("auth.fullName")} error={formState.errors.full_name?.message}>
              <Input autoComplete="name" {...register("full_name")} />
            </Field>
            <Field label={t("auth.phone")} hint={t("auth.phoneHint")} error={formState.errors.phone?.message}>
              <Input type="tel" autoComplete="tel" inputMode="tel" {...register("phone")} />
            </Field>
            <Field label={t("auth.email")} optional={t("common.optional")} error={formState.errors.email?.message}>
              <Input type="email" autoComplete="email" {...register("email")} />
            </Field>
            <Field label={t("auth.password")} hint={t("auth.passwordHint")} error={formState.errors.password?.message}>
              <Input type="password" autoComplete="new-password" {...register("password")} />
            </Field>
            <Button type="submit" size="lg" block loading={formState.isSubmitting}>
              {t("auth.registerButton")}
            </Button>
          </form>
          <p className="muted">
            {t("auth.haveAccount")} <Link to={`/login${next ? `?next=${encodeURIComponent(next)}` : ""}`}>{t("nav.login")}</Link>
          </p>
          <p className="small muted">
            {t("auth.providerPrompt")} <Link to="/join">{t("nav.becomeProvider")}</Link>
          </p>
        </div>
      </div>
      <AuthAside />
    </div>
  );
}
