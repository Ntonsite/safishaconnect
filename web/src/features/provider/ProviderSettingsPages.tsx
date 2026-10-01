import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import { providerApi, publicApi } from "../../api/endpoints";
import type { AvailabilityDay } from "../../api/types";
import { AvailabilityEditor } from "../../shared/components/AvailabilityEditor";
import { Button } from "../../shared/components/Button";
import { ChoiceCard, Counter, PageHeader } from "../../shared/components/Controls";
import { EmptyState, ErrorState, PageLoader } from "../../shared/components/Feedback";
import { Field, Input, Switch, Textarea } from "../../shared/components/Field";
import { BookingStatusBadge, SettlementBadge, VerificationBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";
import { ProfilePage } from "../customer/ProfilePage";

function useProfile() {
  return useQuery({ queryKey: ["provider", "profile"], queryFn: providerApi.profile });
}

function useSaved() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  return {
    onSuccess: () => {
      toast.success(t("common.saved"));
      void qc.invalidateQueries({ queryKey: ["provider"] });
    },
    onError: toast.error,
  };
}

export function AvailabilityPage() {
  const { t } = useTranslation();
  const profile = useProfile();
  const [days, setDays] = useState<AvailabilityDay[]>([]);
  const [accepting, setAccepting] = useState(true);
  useEffect(() => {
    if (profile.data) {
      setDays(profile.data.availability.map((d) => ({ ...d, start_time: d.start_time.slice(0, 5), end_time: d.end_time.slice(0, 5) })));
      setAccepting(profile.data.is_accepting_jobs);
    }
  }, [profile.data]);
  const saved = useSaved();
  const save = useMutation({
    mutationFn: async () => {
      await providerApi.setAvailability(days);
      return providerApi.updateProfile({ is_accepting_jobs: accepting });
    },
    ...saved,
  });

  if (profile.isLoading) return <PageLoader />;
  if (profile.error) return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />;
  return (
    <div className="stack-lg">
      <PageHeader title={t("provider.availabilityTitle")} subtitle={t("provider.availabilitySubtitle")} />
      <div className="card card-tight">
        <Switch checked={accepting} onChange={setAccepting} label={t("provider.toggleAccepting")} />
      </div>
      <div className="card">
        <AvailabilityEditor value={days} onChange={setDays} />
      </div>
      <div>
        <Button size="lg" onClick={() => save.mutate()} loading={save.isPending}>
          {t("common.save")}
        </Button>
      </div>
    </div>
  );
}

export function CoveragePage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const profile = useProfile();
  const services = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  const areas = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas });
  const [serviceIds, setServiceIds] = useState<string[]>([]);
  const [areaIds, setAreaIds] = useState<string[]>([]);
  useEffect(() => {
    if (profile.data) {
      setServiceIds(profile.data.services.map((s) => s.id));
      setAreaIds(profile.data.areas.map((a) => a.id));
    }
  }, [profile.data]);
  const saved = useSaved();
  const save = useMutation({
    mutationFn: async () => {
      await providerApi.setServices(serviceIds);
      return providerApi.setAreas(areaIds);
    },
    ...saved,
  });
  const toggle = (list: string[], set: (v: string[]) => void, id: string) =>
    set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  if (profile.isLoading || services.isLoading || areas.isLoading) return <PageLoader />;
  return (
    <div className="stack-lg">
      <PageHeader title={t("nav.provider.servicesAreas")} />
      <section className="card stack">
        <h2 className="card-title">{t("provider.servicesTitle")}</h2>
        <div className="choice-grid">
          {services.data?.map((s) => (
            <ChoiceCard
              key={s.id}
              role="checkbox"
              selected={serviceIds.includes(s.id)}
              onClick={() => toggle(serviceIds, setServiceIds, s.id)}
              title={fmt.pick(s, "name")}
            />
          ))}
        </div>
      </section>
      <section className="card stack">
        <h2 className="card-title">{t("provider.areasTitle")}</h2>
        <div className="choice-grid">
          {areas.data?.map((a) => (
            <ChoiceCard
              key={a.id}
              role="checkbox"
              selected={areaIds.includes(a.id)}
              onClick={() => toggle(areaIds, setAreaIds, a.id)}
              title={a.name}
              meta={a.city_name}
            />
          ))}
        </div>
      </section>
      <div>
        <Button size="lg" onClick={() => save.mutate()} loading={save.isPending}>
          {t("common.save")}
        </Button>
      </div>
    </div>
  );
}

export function EarningsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const query = useQuery({ queryKey: ["provider", "earnings"], queryFn: providerApi.earnings });
  if (query.isLoading) return <PageLoader />;
  if (query.error || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const e = query.data;
  return (
    <div className="stack-lg">
      <PageHeader title={t("provider.earningsTitle")} subtitle={t("provider.earningsSubtitle")} />
      <div className="grid-4">
        {[
          [t("provider.earned"), e.total_earned],
          [t("provider.settled"), e.settled],
          [t("provider.awaitingSettlement"), e.pending_settlement],
          [t("provider.awaitingCompletion"), e.awaiting_completion],
        ].map(([label, value]) => (
          <div className="card card-tight stat" key={label}>
            <span className="stat-label">{label}</span>
            <span className="stat-value stat-value-sm">{fmt.money(value, e.currency)}</span>
          </div>
        ))}
      </div>
      <div className="card card-flush">
        {e.rows.length === 0 ? (
          <EmptyState icon={Wallet} title={t("provider.noEarnings")} />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("common.reference")}</th>
                  <th>{t("common.status")}</th>
                  <th className="right">{t("provider.customerPays")}</th>
                  <th className="right">{t("provider.commission")}</th>
                  <th className="right">{t("provider.youEarn")}</th>
                  <th>{t("nav.admin.settlements")}</th>
                </tr>
              </thead>
              <tbody>
                {e.rows.map((r) => (
                  <tr key={r.booking_id}>
                    <td>
                      <div className="cell-main">{r.service_name}</div>
                      <div className="cell-sub">
                        {r.reference} · {fmt.date(r.scheduled_date)}
                      </div>
                    </td>
                    <td>
                      <BookingStatusBadge status={r.status} />
                    </td>
                    <td className="right num">{fmt.money(r.total_amount, e.currency)}</td>
                    <td className="right num muted">−{fmt.money(r.commission_amount, e.currency)}</td>
                    <td className="right num strong">{fmt.money(r.provider_earning, e.currency)}</td>
                    <td>
                      {r.settlement_status ? <SettlementBadge status={r.settlement_status} /> : <span className="muted">—</span>}
                      {r.settlement_reference && <div className="cell-sub">{r.settlement_reference}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function ProviderProfilePage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const profile = useProfile();
  const saved = useSaved();
  const [form, setForm] = useState({ display_name: "", bio: "", years_experience: 0, capacity: 1 });
  useEffect(() => {
    if (profile.data) {
      const p = profile.data;
      setForm({ display_name: p.display_name, bio: p.bio, years_experience: p.years_experience, capacity: p.capacity });
    }
  }, [profile.data]);
  const save = useMutation({ mutationFn: () => providerApi.updateProfile(form), ...saved });

  if (profile.isLoading) return <PageLoader />;
  if (profile.error || !profile.data) return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />;
  const p = profile.data;
  return (
    <div className="stack-lg">
      <PageHeader
        title={t("provider.profileTitle")}
        subtitle={p.provider_type === "COMPANY" ? t("common.company") : t("common.individual")}
        actions={<VerificationBadge status={p.verification_status} />}
      />
      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Field label={t("provider.displayName")}>
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        </Field>
        <Field label={p.provider_type === "COMPANY" ? t("join.bioCompany") : t("join.bio")}>
          <Textarea value={form.bio} maxLength={2000} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
        </Field>
        <div className="row wrap" style={{ gap: "var(--s-8)" }}>
          <div className="field">
            <span className="field-label">{t("join.years")}</span>
            <Counter value={form.years_experience} max={60} label={t("join.years")} onChange={(v) => setForm({ ...form, years_experience: v })} />
          </div>
          {p.provider_type === "COMPANY" && (
            <div className="field">
              <span className="field-label">{t("join.capacity")}</span>
              <Counter value={form.capacity} min={1} max={20} label={t("join.capacity")} onChange={(v) => setForm({ ...form, capacity: v })} />
            </div>
          )}
        </div>
        <div>
          <Button type="submit" loading={save.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>

      {p.verification_history.length > 0 && (
        <section className="card stack-sm">
          <h2 className="card-title">{t("provider.verificationHistory")}</h2>
          {p.verification_history.map((v, i) => (
            <div key={i} className="row-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
              <div>
                <div className="strong small">{t(`status.verificationDecision.${v.decision}`)}</div>
                {v.notes && <div className="small muted">{v.notes}</div>}
              </div>
              <span className="small muted">{fmt.dateTime(v.created_at)}</span>
            </div>
          ))}
        </section>
      )}

      <ProfilePage />
    </div>
  );
}
