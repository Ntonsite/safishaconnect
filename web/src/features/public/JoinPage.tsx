import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Building2, User } from "lucide-react";
import { publicApi } from "../../api/endpoints";
import { ApiError } from "../../api/client";
import type { AvailabilityDay, ProviderType } from "../../api/types";
import { homeFor, useAuth } from "../../auth/AuthContext";
import { useBrand } from "../../config/brand";
import { currentLocale } from "../../i18n";
import { AvailabilityEditor, defaultWeek } from "../../shared/components/AvailabilityEditor";
import { Button } from "../../shared/components/Button";
import { ChoiceCard, Counter } from "../../shared/components/Controls";
import { Alert, PageLoader } from "../../shared/components/Feedback";
import { Field, Input, Textarea } from "../../shared/components/Field";
import { useErrorMessage } from "../../shared/hooks/useErrorMessage";
import { useFormat } from "../../shared/hooks/useFormat";
import { PASSWORD_RULE, TZ_PHONE } from "../../shared/utils/validation";

type Step = 0 | 1 | 2;

interface Draft {
  provider_type: ProviderType;
  full_name: string;
  business_name: string;
  phone: string;
  email: string;
  password: string;
  bio: string;
  years_experience: number;
  registration_number: string;
  capacity: number;
  service_ids: string[];
  area_ids: string[];
  availability: AvailabilityDay[];
}

export function JoinPage() {
  const { t } = useTranslation();
  const brand = useBrand();
  const fmt = useFormat();
  const { user, registerProvider } = useAuth();
  const navigate = useNavigate();
  const toMessage = useErrorMessage();
  const services = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  const areas = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas });

  const [step, setStep] = useState<Step>(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [draft, setDraft] = useState<Draft>({
    provider_type: "INDIVIDUAL",
    full_name: "",
    business_name: "",
    phone: "",
    email: "",
    password: "",
    bio: "",
    years_experience: 1,
    registration_number: "",
    capacity: 1,
    service_ids: [],
    area_ids: [],
    availability: defaultWeek(),
  });

  if (user) return <Navigate to={homeFor(user.role)} replace />;
  if (services.isLoading || areas.isLoading) return <PageLoader />;

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }));
  const toggle = (key: "service_ids" | "area_ids", id: string) =>
    set(key, draft[key].includes(id) ? draft[key].filter((x) => x !== id) : [...draft[key], id]);
  const isCompany = draft.provider_type === "COMPANY";

  const validate = (s: Step): boolean => {
    const e: Record<string, string> = {};
    if (s === 0) {
      if (draft.full_name.trim().length < 2) e.full_name = t("validation.minLength", { count: 2 });
      if (isCompany && draft.business_name.trim().length < 2) e.business_name = t("validation.required");
      if (!TZ_PHONE.test(draft.phone.trim())) e.phone = t("validation.phone");
      if (!/^\S+@\S+\.\S+$/.test(draft.email.trim())) e.email = t("validation.email");
      if (!PASSWORD_RULE.test(draft.password)) e.password = t("validation.password");
    }
    if (s === 1) {
      if (!draft.service_ids.length) e.service_ids = t("join.selectAtLeastOne");
      if (!draft.area_ids.length) e.area_ids = t("join.selectAtLeastOne");
    }
    if (s === 2 && !draft.availability.length) e.availability = t("join.selectAtLeastOne");
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async () => {
    if (!validate(2)) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await registerProvider({
        ...draft,
        business_name: isCompany ? draft.business_name.trim() : null,
        registration_number: draft.registration_number.trim() || null,
        capacity: isCompany ? draft.capacity : 1,
        preferred_locale: currentLocale(),
      });
      navigate("/provider", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && (e.code === "PHONE_TAKEN" || e.code === "EMAIL_TAKEN")) {
        setStep(0);
        setErrors({ [e.code === "PHONE_TAKEN" ? "phone" : "email"]: toMessage(e) });
      } else {
        setSubmitError(toMessage(e));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const steps = [t("join.stepAccount"), t("join.stepWork"), t("join.stepHours")];

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <h1 className="display">{t("join.title", { brand: brand.app_name })}</h1>
          <p>{t("join.subtitle")}</p>
        </div>
      </section>
      <section className="page-section">
        <div className="container" style={{ maxWidth: 760 }}>
          <ol className="steps" style={{ marginBottom: "var(--s-6)" }}>
            {steps.map((label, i) => (
              <li key={label} className={i < step ? "is-done" : i === step ? "is-current" : undefined}>
                <span>{label}</span>
              </li>
            ))}
          </ol>

          <div className="card stack-lg">
            {submitError && <Alert tone="danger">{submitError}</Alert>}

            {step === 0 && (
              <>
                <div className="stack-sm">
                  <h2>{t("join.typeTitle")}</h2>
                  <div className="grid-2">
                    <ChoiceCard
                      selected={!isCompany}
                      onClick={() => set("provider_type", "INDIVIDUAL")}
                      title={
                        <span className="row" style={{ gap: 8 }}>
                          <User size={18} /> {t("join.individual")}
                        </span>
                      }
                      meta={t("join.individualBody")}
                    />
                    <ChoiceCard
                      selected={isCompany}
                      onClick={() => set("provider_type", "COMPANY")}
                      title={
                        <span className="row" style={{ gap: 8 }}>
                          <Building2 size={18} /> {t("join.company")}
                        </span>
                      }
                      meta={t("join.companyBody")}
                    />
                  </div>
                </div>
                <div className="grid-2">
                  {isCompany && (
                    <Field label={t("join.businessName")} error={errors.business_name}>
                      <Input value={draft.business_name} onChange={(e) => set("business_name", e.target.value)} />
                    </Field>
                  )}
                  <Field label={isCompany ? t("join.contactPerson") : t("auth.fullName")} error={errors.full_name}>
                    <Input autoComplete="name" value={draft.full_name} onChange={(e) => set("full_name", e.target.value)} />
                  </Field>
                  <Field label={t("auth.phone")} hint={t("auth.phoneHint")} error={errors.phone}>
                    <Input type="tel" inputMode="tel" value={draft.phone} onChange={(e) => set("phone", e.target.value)} />
                  </Field>
                  <Field label={t("auth.email")} error={errors.email}>
                    <Input type="email" value={draft.email} onChange={(e) => set("email", e.target.value)} />
                  </Field>
                  <Field label={t("auth.password")} hint={t("auth.passwordHint")} error={errors.password}>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      value={draft.password}
                      onChange={(e) => set("password", e.target.value)}
                    />
                  </Field>
                  {isCompany && (
                    <Field label={t("join.registrationNumber")} optional={t("common.optional")}>
                      <Input value={draft.registration_number} onChange={(e) => set("registration_number", e.target.value)} />
                    </Field>
                  )}
                </div>
                <Field label={isCompany ? t("join.bioCompany") : t("join.bio")} optional={t("common.optional")}>
                  <Textarea
                    value={draft.bio}
                    placeholder={t("join.bioPlaceholder")}
                    maxLength={2000}
                    onChange={(e) => set("bio", e.target.value)}
                  />
                </Field>
                <div className="row wrap" style={{ gap: "var(--s-8)" }}>
                  <div className="field">
                    <span className="field-label">{t("join.years")}</span>
                    <Counter value={draft.years_experience} max={60} onChange={(v) => set("years_experience", v)} label={t("join.years")} />
                  </div>
                  {isCompany && (
                    <div className="field">
                      <span className="field-label">{t("join.capacity")}</span>
                      <Counter value={draft.capacity} min={1} max={20} onChange={(v) => set("capacity", v)} label={t("join.capacity")} />
                      <span className="field-hint">{t("join.capacityHint")}</span>
                    </div>
                  )}
                </div>
              </>
            )}

            {step === 1 && (
              <>
                <div className="stack-sm">
                  <h2>{t("join.servicesLabel")}</h2>
                  {errors.service_ids && <span className="field-error">{errors.service_ids}</span>}
                  <div className="choice-grid">
                    {services.data?.map((s) => (
                      <ChoiceCard
                        key={s.id}
                        role="checkbox"
                        selected={draft.service_ids.includes(s.id)}
                        onClick={() => toggle("service_ids", s.id)}
                        title={fmt.pick(s, "name")}
                      />
                    ))}
                  </div>
                </div>
                <div className="stack-sm">
                  <h2>{t("join.areasLabel")}</h2>
                  {errors.area_ids && <span className="field-error">{errors.area_ids}</span>}
                  <div className="choice-grid">
                    {areas.data?.map((a) => (
                      <ChoiceCard
                        key={a.id}
                        role="checkbox"
                        selected={draft.area_ids.includes(a.id)}
                        onClick={() => toggle("area_ids", a.id)}
                        title={a.name}
                        meta={a.city_name}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}

            {step === 2 && (
              <div className="stack-sm">
                <h2>{t("join.hoursLabel")}</h2>
                {errors.availability && <span className="field-error">{errors.availability}</span>}
                <AvailabilityEditor value={draft.availability} onChange={(v) => set("availability", v)} />
              </div>
            )}

            <div className="row-between">
              {step > 0 ? (
                <Button variant="secondary" onClick={() => setStep((s) => (s - 1) as Step)}>
                  {t("common.back")}
                </Button>
              ) : (
                <span />
              )}
              {step < 2 ? (
                <Button onClick={() => validate(step) && setStep((s) => (s + 1) as Step)}>{t("common.next")}</Button>
              ) : (
                <Button onClick={submit} loading={submitting}>
                  {t("join.submit")}
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
