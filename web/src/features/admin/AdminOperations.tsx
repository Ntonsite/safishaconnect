import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileClock, MessageSquareWarning, Star, Wallet } from "lucide-react";
import { adminApi } from "../../api/endpoints";
import type { Complaint, ComplaintStatus, PaymentStatus, SettlementRow } from "../../api/types";
import { Stars } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { PageHeader, Pagination } from "../../shared/components/Controls";
import { EmptyState, ErrorState, PageLoader, SkeletonCard } from "../../shared/components/Feedback";
import { Field, Input, Select, Textarea } from "../../shared/components/Field";
import { Modal } from "../../shared/components/Modal";
import { BookingStatusBadge, ComplaintStatusBadge, PaymentStatusBadge, SettlementBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";

function useStatusParam<T extends string>() {
  const [params, setParams] = useSearchParams();
  const value = (params.get("status") ?? "") as T | "";
  const set = (v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set("status", v);
    else next.delete("status");
    setParams(next, { replace: true });
  };
  return [value, set] as const;
}

export function AdminPaymentsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const navigate = useNavigate();
  const [status, setStatus] = useStatusParam<PaymentStatus>();
  const [method, setMethod] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [status, method]);
  const query = useQuery({
    queryKey: ["admin", "payments", { status, method, page }],
    queryFn: () => adminApi.payments({ status, method: method || undefined, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.payments")} />
      <div className="toolbar">
        <Field label={t("common.status")}>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("admin.allStatuses")}</option>
            {(["PENDING", "PAID", "FAILED", "REFUNDED", "CANCELLED"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.payment.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("customer.payment")}>
          <Select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="">{t("common.all")}</option>
            {(["CASH", "MOBILE_MONEY", "CARD"] as const).map((m) => (
              <option key={m} value={m}>
                {t(`booking.methods.${m}`)}
              </option>
            ))}
          </Select>
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
                  <th>{t("common.reference")}</th>
                  <th>{t("common.customer")}</th>
                  <th>{t("customer.payment")}</th>
                  <th>{t("common.status")}</th>
                  <th className="right">{t("common.amount")}</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((p) => (
                  <tr key={p.id} className="is-clickable" onClick={() => navigate(`/admin/bookings/${p.booking_id}`)}>
                    <td>
                      <div className="cell-main num">{p.booking_reference}</div>
                      <div className="cell-sub">
                        <BookingStatusBadge status={p.booking_status} admin />
                      </div>
                    </td>
                    <td>
                      <div>{p.customer_name}</div>
                      <div className="cell-sub">{p.provider_name ?? "—"}</div>
                    </td>
                    <td>{t(`booking.methods.${p.method}`)}</td>
                    <td>
                      <PaymentStatusBadge status={p.status} />
                      {p.paid_at && (
                        <div className="cell-sub">
                          {fmt.dateTime(p.paid_at)} · {p.confirmed_by_name}
                        </div>
                      )}
                    </td>
                    <td className="right num strong">{fmt.money(p.amount, p.currency)}</td>
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

export function AdminSettlementsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const [status, setStatus] = useStatusParam<"PENDING" | "SETTLED">();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<SettlementRow | null>(null);
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => setPage(1), [status]);
  const query = useQuery({
    queryKey: ["admin", "settlements", { status, page }],
    queryFn: () => adminApi.settlements({ status: status || undefined, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });
  const settle = useMutation({
    mutationFn: () => adminApi.settle(selected!.id, reference || undefined, note || undefined),
    onSuccess: () => {
      setSelected(null);
      setReference("");
      setNote("");
      toast.success(t("common.saved"));
      void qc.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: toast.error,
  });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.settlements")} />
      <div className="toolbar">
        <Field label={t("common.status")}>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("admin.allStatuses")}</option>
            <option value="PENDING">{t("status.settlement.PENDING")}</option>
            <option value="SETTLED">{t("status.settlement.SETTLED")}</option>
          </Select>
        </Field>
      </div>
      {query.isLoading && <SkeletonCard lines={5} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          {query.data.items.length === 0 ? (
            <EmptyState icon={Wallet} title={t("common.results", { count: 0 })} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("common.provider")}</th>
                    <th className="right">{t("provider.customerPays")}</th>
                    <th className="right">{t("provider.commission")}</th>
                    <th className="right">{t("provider.youEarn")}</th>
                    <th>{t("common.status")}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <div className="cell-main">{s.provider_name}</div>
                        <div className="cell-sub">
                          {s.booking_reference}
                          {s.cash_collected_by_provider && ` · ${t("admin.cashWithProvider")}`}
                        </div>
                      </td>
                      <td className="right num">{fmt.money(s.gross_amount)}</td>
                      <td className="right num">{fmt.money(s.commission_amount)}</td>
                      <td className="right num strong">{fmt.money(s.provider_earning)}</td>
                      <td>
                        <SettlementBadge status={s.status} />
                        {s.settled_at && (
                          <div className="cell-sub">
                            {fmt.dateTime(s.settled_at)}
                            {s.reference && ` · ${s.reference}`}
                          </div>
                        )}
                      </td>
                      <td className="right">
                        {s.status === "PENDING" && (
                          <Button size="sm" variant="secondary" onClick={() => setSelected(s)}>
                            {t("admin.settle")}
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={page} pageSize={20} total={query.data.total} onChange={setPage} />
        </div>
      )}
      <Modal
        open={!!selected}
        title={t("admin.settleTitle")}
        description={selected ? `${selected.provider_name} · ${selected.booking_reference} · ${fmt.money(selected.provider_earning)}` : undefined}
        onClose={() => setSelected(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSelected(null)}>
              {t("common.cancel")}
            </Button>
            <Button loading={settle.isPending} onClick={() => settle.mutate()}>
              {t("admin.settle")}
            </Button>
          </>
        }
      >
        <div className="stack">
          <Field label={t("admin.settleReference")} optional={t("common.optional")}>
            <Input value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} />
          </Field>
          <Field label={t("common.notes")} optional={t("common.optional")}>
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

export function AdminComplaintsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const navigate = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const [status, setStatus] = useStatusParam<ComplaintStatus>();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [form, setForm] = useState({ status: "IN_REVIEW" as ComplaintStatus, admin_notes: "", resolution: "" });
  useEffect(() => setPage(1), [status]);
  useEffect(() => {
    if (selected) setForm({ status: selected.status, admin_notes: selected.admin_notes ?? "", resolution: selected.resolution ?? "" });
  }, [selected]);
  const query = useQuery({
    queryKey: ["admin", "complaints", { status, page }],
    queryFn: () => adminApi.complaints({ status, page, page_size: 20 }),
    placeholderData: keepPreviousData,
  });
  const save = useMutation({
    mutationFn: () => adminApi.updateComplaint(selected!.id, form),
    onSuccess: () => {
      setSelected(null);
      toast.success(t("common.saved"));
      void qc.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: toast.error,
  });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.complaints")} />
      <div className="toolbar">
        <Field label={t("common.status")}>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("admin.allStatuses")}</option>
            {(["OPEN", "IN_REVIEW", "RESOLVED", "REJECTED"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`status.complaint.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      {query.isLoading && <SkeletonCard lines={4} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.items.length === 0 && (
        <div className="card">
          <EmptyState icon={MessageSquareWarning} title={t("common.results", { count: 0 })} />
        </div>
      )}
      {query.data?.items.map((c) => (
        <article key={c.id} className="card stack-sm">
          <div className="row-between wrap">
            <div className="row wrap" style={{ gap: 8 }}>
              <ComplaintStatusBadge status={c.status} />
              <span className="strong">{t(`complaintCategory.${c.category}`)}</span>
            </div>
            <span className="small muted">{fmt.dateTime(c.created_at)}</span>
          </div>
          <p>{c.description}</p>
          <div className="small muted">
            {c.customer_name} · {c.provider_name ?? "—"} · {c.booking_reference}
          </div>
          {c.resolution && (
            <div className="alert alert-success small">
              <div>{c.resolution}</div>
            </div>
          )}
          <div className="row">
            <Button size="sm" onClick={() => setSelected(c)}>
              {t("admin.complaint.manage")}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => navigate(`/admin/bookings/${c.booking_id}`)}>
              {t("common.view")} {c.booking_reference}
            </Button>
          </div>
        </article>
      ))}
      {query.data && query.data.total > 20 && <Pagination page={page} pageSize={20} total={query.data.total} onChange={setPage} />}
      <Modal
        open={!!selected}
        title={t("admin.complaint.manage")}
        description={selected ? `${selected.booking_reference} · ${t(`complaintCategory.${selected.category}`)}` : undefined}
        onClose={() => setSelected(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSelected(null)}>
              {t("common.cancel")}
            </Button>
            <Button loading={save.isPending} onClick={() => save.mutate()}>
              {t("common.save")}
            </Button>
          </>
        }
      >
        <div className="stack">
          <Field label={t("common.status")}>
            <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ComplaintStatus })}>
              {(["OPEN", "IN_REVIEW", "RESOLVED", "REJECTED"] as const).map((s) => (
                <option key={s} value={s}>
                  {t(`status.complaint.${s}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("admin.complaint.adminNotes")}>
            <Textarea rows={3} value={form.admin_notes} onChange={(e) => setForm({ ...form, admin_notes: e.target.value })} />
          </Field>
          <Field label={t("admin.complaint.resolution")}>
            <Textarea rows={3} value={form.resolution} onChange={(e) => setForm({ ...form, resolution: e.target.value })} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

export function AdminReviewsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["admin", "reviews", page], queryFn: () => adminApi.reviews({ page, page_size: 20 }), placeholderData: keepPreviousData });
  const moderate = useMutation({
    mutationFn: ({ id, hidden }: { id: string; hidden: boolean }) => adminApi.moderateReview(id, hidden),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "reviews"] }),
    onError: toast.error,
  });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.reviews")} />
      {query.isLoading && <SkeletonCard lines={4} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.items.length === 0 && (
        <div className="card">
          <EmptyState icon={Star} title={t("provider.noReviews")} />
        </div>
      )}
      {query.data?.items.map((r) => (
        <article key={r.id} className="card stack-sm" style={{ opacity: r.is_hidden ? 0.6 : 1 }}>
          <div className="row-between wrap">
            <div className="row wrap" style={{ gap: 10 }}>
              <Stars value={r.rating} />
              <span className="strong">{r.provider_name}</span>
              {r.is_hidden && <span className="badge tone-slate">{t("admin.hidden")}</span>}
            </div>
            <span className="small muted">{fmt.dateTime(r.created_at)}</span>
          </div>
          {r.comment && <p>{r.comment}</p>}
          <div className="row-between wrap">
            <span className="small muted">
              {r.customer_name} · {r.service_name} · {r.booking_reference}
            </span>
            <Button size="sm" variant="secondary" onClick={() => moderate.mutate({ id: r.id, hidden: !r.is_hidden })}>
              {r.is_hidden ? t("admin.showReview") : t("admin.hideReview")}
            </Button>
          </div>
        </article>
      ))}
      {query.data && query.data.total > 20 && <Pagination page={page} pageSize={20} total={query.data.total} onChange={setPage} />}
    </div>
  );
}

export function AdminAuditPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["admin", "audit", page], queryFn: () => adminApi.audit({ page, page_size: 30 }), placeholderData: keepPreviousData });
  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.audit")} />
      {query.isLoading && <SkeletonCard lines={6} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          {query.data.items.length === 0 ? (
            <EmptyState icon={FileClock} title={t("common.results", { count: 0 })} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("common.date")}</th>
                    <th>{t("admin.auditActor")}</th>
                    <th>{t("admin.auditAction")}</th>
                    <th>{t("admin.auditEntity")}</th>
                    <th>{t("admin.auditDetails")}</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((a) => (
                    <tr key={a.id}>
                      <td className="nowrap small">{fmt.dateTime(a.created_at)}</td>
                      <td>{a.actor_name ?? t("admin.system")}</td>
                      <td>
                        <code className="small">{a.action}</code>
                      </td>
                      <td className="small">{a.entity_type}</td>
                      <td className="small muted" style={{ maxWidth: 420 }}>
                        {a.details &&
                          Object.entries(a.details)
                            .filter(([, v]) => v !== null && v !== undefined)
                            .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
                            .join(" · ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={page} pageSize={30} total={query.data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}

export function AdminSettingsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["admin", "settings"], queryFn: adminApi.settings });
  const [values, setValues] = useState<Record<string, string>>({});
  useEffect(() => {
    if (query.data) setValues(Object.fromEntries(query.data.map((s) => [s.key, s.value])));
  }, [query.data]);
  const save = useMutation({
    mutationFn: async () => {
      for (const s of query.data ?? []) {
        if (values[s.key] !== s.value) await adminApi.updateSetting(s.key, values[s.key]);
      }
    },
    onSuccess: () => {
      toast.success(t("common.saved"));
      void qc.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
    onError: toast.error,
  });
  if (query.isLoading) return <PageLoader />;
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  return (
    <div className="stack-lg">
      <PageHeader title={t("admin.settingsTitle")} subtitle={t("admin.settingsSubtitle")} />
      <form
        className="card stack"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <div className="grid-2">
          {query.data?.map((s) => (
            <Field key={s.key} label={t(`admin.settingKeys.${s.key}`)} hint={s.description}>
              <Input type="number" step="any" value={values[s.key] ?? ""} onChange={(e) => setValues({ ...values, [s.key]: e.target.value })} />
            </Field>
          ))}
        </div>
        <div>
          <Button type="submit" loading={save.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </div>
  );
}
