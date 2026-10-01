import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Users } from "lucide-react";
import { adminApi } from "../../api/endpoints";
import type { CustomerRow, ProviderType, VerificationStatus } from "../../api/types";
import { BookingRow } from "../../shared/components/BookingBits";
import { RatingSummary, Stars } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { PageHeader, Pagination, Tabs } from "../../shared/components/Controls";
import { EmptyState, ErrorState, PageLoader, SkeletonCard } from "../../shared/components/Feedback";
import { Field, Input, Select, Switch, Textarea } from "../../shared/components/Field";
import { Modal } from "../../shared/components/Modal";
import { VerificationBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";

export function AdminProvidersPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const status = (params.get("status") ?? "") as VerificationStatus | "";
  const [type, setType] = useState<ProviderType | "">("");
  useEffect(() => setPage(1), [q, status, type]);
  const query = useQuery({
    queryKey: ["admin", "providers", { q, status, type, page }],
    queryFn: () => adminApi.providers({ q: q || undefined, verification_status: status, provider_type: type, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.providers")} />
      <div className="toolbar">
        <Field label={t("common.search")} className="grow">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("common.searchPlaceholder")} />
        </Field>
        <Field label={t("common.status")}>
          <Select
            value={status}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("status", e.target.value);
              else next.delete("status");
              setParams(next, { replace: true });
            }}
          >
            <option value="">{t("admin.allStatuses")}</option>
            {(["PENDING", "VERIFIED", "REJECTED", "SUSPENDED"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.verification.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("join.typeTitle")}>
          <Select value={type} onChange={(e) => setType(e.target.value as ProviderType | "")}>
            <option value="">{t("admin.allTypes")}</option>
            <option value="INDIVIDUAL">{t("common.individual")}</option>
            <option value="COMPANY">{t("common.company")}</option>
          </Select>
        </Field>
      </div>
      {query.isLoading && <SkeletonCard lines={5} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.items.length === 0 && (
        <div className="card">
          <EmptyState
            icon={BadgeCheck}
            title={status === "PENDING" ? t("admin.noPendingProviders") : t("admin.noMatchingProviders")}
            body={status === "PENDING" ? t("admin.noPendingProvidersBody") : undefined}
          />
        </div>
      )}
      {!!query.data?.items.length && (
        <div className="card card-flush">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("common.provider")}</th>
                  <th>{t("common.status")}</th>
                  <th>{t("common.rating")}</th>
                  <th>{t("admin.providerAreas")}</th>
                  <th className="right">{t("admin.metrics.completed")}</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((p) => (
                  <tr key={p.id} className="is-clickable" onClick={() => navigate(`/admin/providers/${p.id}`)}>
                    <td>
                      <div className="cell-main">{p.display_name}</div>
                      <div className="cell-sub">
                        {p.provider_type === "COMPANY" ? t("common.company") : t("common.individual")} · {p.phone}
                      </div>
                    </td>
                    <td>
                      <VerificationBadge status={p.verification_status} />
                      {!p.is_active && <div className="cell-sub">{t("common.inactive")}</div>}
                    </td>
                    <td>
                      <RatingSummary average={p.rating_average} count={p.rating_count} />
                    </td>
                    <td className="small" style={{ maxWidth: 260 }}>
                      {p.area_names.join(", ") || "—"}
                    </td>
                    <td className="right num">{p.completed_jobs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={20} total={query.data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}

const VERIFY_ACTIONS: Record<VerificationStatus, string[]> = {
  PENDING: ["APPROVE", "REJECT"],
  REJECTED: ["APPROVE"],
  VERIFIED: ["SUSPEND"],
  SUSPENDED: ["REACTIVATE"],
};

export function AdminProviderDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"jobs" | "reviews">("jobs");
  const [action, setAction] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const profile = useQuery({ queryKey: ["admin", "provider", id], queryFn: () => adminApi.provider(id) });
  const jobs = useQuery({ queryKey: ["admin", "provider", id, "jobs"], queryFn: () => adminApi.providerBookings(id) });
  const reviews = useQuery({ queryKey: ["admin", "provider", id, "reviews"], queryFn: () => adminApi.providerReviews(id) });

  const refresh = () => qc.invalidateQueries({ queryKey: ["admin"] });
  const verify = useMutation({
    mutationFn: () => adminApi.verifyProvider(id, action!, notes || undefined),
    onSuccess: () => {
      setAction(null);
      setNotes("");
      toast.success(t("admin.verify.done"));
      void refresh();
    },
    onError: toast.error,
  });
  const toggle = useMutation({
    mutationFn: (active: boolean) => adminApi.setProviderActive(id, active),
    onSuccess: () => void refresh(),
    onError: toast.error,
  });

  if (profile.isLoading) return <PageLoader />;
  if (profile.error || !profile.data) return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />;
  const p = profile.data;

  return (
    <div className="stack-lg">
      <PageHeader
        back={{ to: "/admin/providers", label: t("nav.admin.providers") }}
        title={p.display_name}
        subtitle={`${p.provider_type === "COMPANY" ? t("common.company") : t("common.individual")} · ${p.phone} · ${p.email ?? ""}`}
        actions={
          <>
            <VerificationBadge status={p.verification_status} />
            {VERIFY_ACTIONS[p.verification_status].map((a) => (
              <Button key={a} variant={a === "REJECT" || a === "SUSPEND" ? "danger" : "primary"} onClick={() => setAction(a)}>
                {t(`admin.verify.${a}`)}
              </Button>
            ))}
          </>
        }
      />

      <div className="detail-grid">
        <div className="stack-lg">
          <section className="card stack">
            {p.contact_person && (
              <div className="small muted">
                {t("join.contactPerson")}: <strong>{p.contact_person}</strong>
              </div>
            )}
            {p.bio && <p>{p.bio}</p>}
            <div className="row wrap small muted" style={{ gap: 16 }}>
              <span>{t("common.yearsExperience", { count: p.years_experience })}</span>
              {p.provider_type === "COMPANY" && (
                <span>
                  {t("join.capacity")}: {p.capacity}
                </span>
              )}
              {p.registration_number && <span>{p.registration_number}</span>}
            </div>
            <RatingSummary average={p.rating_average} count={p.rating_count} />
          </section>

          <Tabs
            value={tab}
            onChange={setTab}
            items={[
              { value: "jobs", label: t("admin.providerJobs"), count: jobs.data?.length },
              { value: "reviews", label: t("nav.admin.reviews"), count: reviews.data?.length },
            ]}
          />
          {tab === "jobs" && (
            <div className="card card-flush">
              {jobs.data?.length === 0 && <EmptyState icon={Users} title={t("provider.noCompleted")} />}
              {jobs.data?.map((b) => <BookingRow key={b.id} booking={b} to={`/admin/bookings/${b.id}`} showCustomer />)}
            </div>
          )}
          {tab === "reviews" &&
            (reviews.data?.length ? (
              reviews.data.map((r) => (
                <article key={r.id} className="card stack-sm">
                  <div className="row-between">
                    <Stars value={r.rating} />
                    <span className="small muted">{fmt.dateTime(r.created_at)}</span>
                  </div>
                  {r.comment && <p>{r.comment}</p>}
                  <div className="small muted">
                    {r.customer_name} · {r.booking_reference}
                    {r.is_hidden && ` · ${t("admin.hidden")}`}
                  </div>
                </article>
              ))
            ) : (
              <div className="card">
                <EmptyState icon={Users} title={t("provider.noReviews")} />
              </div>
            ))}
        </div>

        <aside className="detail-aside">
          <section className="card stack-sm">
            <Switch checked={p.is_active} onChange={(v) => toggle.mutate(v)} label={t("admin.accountActive")} disabled={toggle.isPending} />
          </section>
          <section className="card stack-sm">
            <div className="card-title">{t("admin.providerServices")}</div>
            <div className="row wrap" style={{ gap: 6 }}>
              {p.services.map((s) => (
                <span className="chip" key={s.id}>
                  {fmt.pick(s, "name")}
                </span>
              ))}
            </div>
            <div className="card-title" style={{ marginTop: 12 }}>
              {t("admin.providerAreas")}
            </div>
            <div className="row wrap" style={{ gap: 6 }}>
              {p.areas.map((a) => (
                <span className="chip" key={a.id}>
                  {a.name}
                </span>
              ))}
            </div>
            <div className="card-title" style={{ marginTop: 12 }}>
              {t("admin.providerHours")}
            </div>
            {p.availability.map((d) => (
              <div className="row-between small" key={d.day_of_week}>
                <span>{t(`days.${d.day_of_week}`)}</span>
                <span className="num">
                  {d.start_time.slice(0, 5)}–{d.end_time.slice(0, 5)}
                </span>
              </div>
            ))}
          </section>
          <section className="card stack-sm">
            <div className="card-title">{t("provider.verificationHistory")}</div>
            {p.verification_history.map((v, i) => (
              <div key={i} className="small">
                <strong>{t(`status.verificationDecision.${v.decision}`)}</strong> · <span className="muted">{fmt.dateTime(v.created_at)}</span>
                {v.notes && <div className="muted">{v.notes}</div>}
              </div>
            ))}
          </section>
        </aside>
      </div>

      <Modal
        open={!!action}
        title={action ? t(`admin.verify.${action}`) : ""}
        onClose={() => setAction(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAction(null)}>
              {t("common.cancel")}
            </Button>
            <Button variant={action === "REJECT" || action === "SUSPEND" ? "danger-solid" : "primary"} loading={verify.isPending} onClick={() => verify.mutate()}>
              {action ? t(`admin.verify.${action}`) : ""}
            </Button>
          </>
        }
      >
        <Field label={t("admin.verify.notes")} optional={t("common.optional")}>
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={1000} />
        </Field>
      </Modal>
    </div>
  );
}

export function AdminCustomersPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CustomerRow | null>(null);
  useEffect(() => setPage(1), [q]);
  const query = useQuery({
    queryKey: ["admin", "customers", { q, page }],
    queryFn: () => adminApi.customers({ q: q || undefined, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });
  const bookings = useQuery({
    queryKey: ["admin", "customer", selected?.id, "bookings"],
    queryFn: () => adminApi.customerBookings(selected!.id),
    enabled: !!selected,
  });
  const toggle = useMutation({
    mutationFn: (active: boolean) => adminApi.setCustomerActive(selected!.id, active),
    onSuccess: (row) => {
      setSelected(row);
      void qc.invalidateQueries({ queryKey: ["admin", "customers"] });
    },
    onError: toast.error,
  });

  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.customers")} />
      <div className="toolbar">
        <Field label={t("common.search")} className="grow">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("common.searchPlaceholder")} />
        </Field>
      </div>
      {query.isLoading && <SkeletonCard lines={5} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("common.customer")}</th>
                  <th>{t("common.phone")}</th>
                  <th className="right">{t("nav.admin.bookings")}</th>
                  <th className="right">{t("common.total")}</th>
                  <th>{t("common.status")}</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((c) => (
                  <tr key={c.id} className="is-clickable" onClick={() => setSelected(c)}>
                    <td>
                      <div className="cell-main">{c.full_name}</div>
                      <div className="cell-sub">{c.email ?? "—"}</div>
                    </td>
                    <td className="num">{c.phone}</td>
                    <td className="right num">{c.bookings_count}</td>
                    <td className="right num">{fmt.money(c.total_spent)}</td>
                    <td>
                      <span className={`badge ${c.is_active ? "tone-green" : "tone-slate"}`}>
                        {c.is_active ? t("common.active") : t("common.inactive")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={20} total={query.data.total} onChange={setPage} />
        </div>
      )}
      <Modal open={!!selected} wide title={selected?.full_name} description={`${selected?.phone} · ${selected?.email ?? ""}`} onClose={() => setSelected(null)}>
        {selected && (
          <div className="stack">
            <Switch checked={selected.is_active} onChange={(v) => toggle.mutate(v)} label={t("admin.accountActive")} disabled={toggle.isPending} />
            <div className="section-label">{t("admin.customerBookings")}</div>
            <div className="card card-flush">
              {bookings.isLoading && <SkeletonCard />}
              {bookings.data?.length === 0 && <EmptyState icon={Users} title={t("customer.noHistory")} />}
              {bookings.data?.map((b) => <BookingRow key={b.id} booking={b} to={`/admin/bookings/${b.id}`} />)}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
