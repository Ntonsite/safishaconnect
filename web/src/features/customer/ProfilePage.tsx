import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery } from "@tanstack/react-query";
import { authApi, publicApi } from "../../api/endpoints";
import type { Locale } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { setLocale } from "../../i18n";
import { Button } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/Controls";
import { Field, Input, Select } from "../../shared/components/Field";
import { useToast } from "../../shared/components/Toast";
import { PASSWORD_RULE } from "../../shared/utils/validation";

/** Account settings shared by every role; the location block only shows for customers. */
export function ProfilePage() {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const isCustomer = user?.role === "CUSTOMER";
  const areas = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas, enabled: isCustomer });

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [locale, setLocaleValue] = useState<Locale>(user?.preferred_locale ?? "en");
  const [areaId, setAreaId] = useState(user?.default_area_id ?? "");
  const [address, setAddress] = useState(user?.default_address ?? "");

  const save = useMutation({
    mutationFn: () =>
      authApi.updateMe({
        full_name: fullName.trim(),
        email: email.trim() || undefined,
        phone: phone.trim(),
        preferred_locale: locale,
        ...(isCustomer ? { default_area_id: areaId || undefined, default_address: address } : {}),
      }),
    onSuccess: async () => {
      await refreshUser();
      void setLocale(locale);
      toast.success(t("customer.profileSaved"));
    },
    onError: toast.error,
  });

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(current, next),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      toast.success(t("customer.passwordChanged"));
    },
    onError: toast.error,
  });

  return (
    <div className="stack-lg">
      <PageHeader title={t("customer.profileTitle")} />
      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <div className="grid-2">
          <Field label={t("auth.fullName")}>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
          </Field>
          <Field label={t("auth.phone")}>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" autoComplete="tel" />
          </Field>
          <Field label={t("auth.email")}>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" />
          </Field>
          <Field label={t("common.language")}>
            <Select value={locale} onChange={(e) => setLocaleValue(e.target.value as Locale)}>
              <option value="en">English</option>
              <option value="sw">Kiswahili</option>
            </Select>
          </Field>
        </div>
        {isCustomer && (
          <>
            <div className="section-label" style={{ marginTop: "var(--s-2)" }}>
              {t("customer.defaultLocation")}
            </div>
            <div className="grid-2">
              <Field label={t("booking.areaLabel")}>
                <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
                  <option value="">{t("booking.areaPlaceholder")}</option>
                  {areas.data?.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("booking.address")}>
                <Input value={address} onChange={(e) => setAddress(e.target.value)} maxLength={255} />
              </Field>
            </div>
          </>
        )}
        <div>
          <Button type="submit" loading={save.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>

      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          changePassword.mutate();
        }}
      >
        <h2 className="card-title">{t("customer.security")}</h2>
        <div className="grid-2">
          <Field label={t("customer.currentPassword")}>
            <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          </Field>
          <Field
            label={t("customer.newPassword")}
            hint={t("auth.passwordHint")}
            error={next && !PASSWORD_RULE.test(next) ? t("validation.password") : undefined}
          >
            <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          </Field>
        </div>
        <div>
          <Button type="submit" variant="secondary" disabled={!current || !PASSWORD_RULE.test(next)} loading={changePassword.isPending}>
            {t("customer.changePassword")}
          </Button>
        </div>
      </form>
    </div>
  );
}
