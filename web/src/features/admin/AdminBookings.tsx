import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, UserCheck } from "lucide-react";
import { adminApi, publicApi } from "../../api/endpoints";
import type { BookingStatus, PaymentStatus } from "../../api/types";
import { Stars } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { PageHeader, Pagination } from "../../shared/components/Controls";
import { EmptyState, ErrorState, PageLoader, SkeletonCard } from "../../shared/components/Feedback";
import { Field, Input, Select, Switch, Textarea } from "../../shared/components/Field";
import { Modal } from "../../shared/components/Modal";
import { AssignmentStatusBadge, BookingStatusBadge, PaymentStatusBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";
import { addMinutesToTime } from "../../shared/utils/format";

const ALL_STATUSES: BookingStatus[] = [
  "PENDING_CONFIRMATION",
  "CONFIRMED",
  "FINDING_PROVIDER",
  "REASSIGNMENT_REQUIRED",
  "PROVIDER_ASSIGNED",
  "PROVIDER_EN_ROUTE",
  "PROVIDER_ARRIVED",
  "SERVICE_IN_PROGRESS",
  "COMPLETED_BY_PROVIDER",
  "CUSTOMER_CONFIRMED",
  "DISPUTED",
  "CLOSED",
  "CANCELLED",
];

export function AdminBookingsPage() {
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const status = params.get("status") ?? "";
  const serviceId = params.get("service") ?? "";
  const areaId = params.get("area") ?? "";
  const dateFrom = params.get("from") ?? "";
  const dateTo = params.get("to") ?? "";
  const services = useQuery({ queryKey: ["admin", "services"], queryFn: adminApi.services });
  const areas = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas });

  useEffect(() => setPage(1), [status, serviceId, areaId, dateFrom, dateTo, q]);

  const query = useQuery({
    queryKey: ["admin", "bookings", { page, status, serviceId, areaId, dateFrom, dateTo, q }],
    queryFn: () =>
      adminApi.bookings({
        page,
        page_size: 20,
        status: status ? [status as BookingStatus] : undefined,
        service_id: serviceId || undefined,
        area_id: areaId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        q: q || undefined,
      }),
    placeholderData: keepPreviousData,
  });

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="stack">
      <PageHeader title={t("nav.admin.bookings")} />
      <div className="toolbar">
        <Field label={t("common.search")} className="grow">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`${t("common.reference")}, ${t("common.customer")}…`} />
        </Field>
        <Field label={t("common.status")}>
          <Select value={status} onChange={(e) => setParam("status", e.target.value)}>
            <option value="">{t("admin.allStatuses")}</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {i18n.exists(`status.adminBooking.${s}`) ? t(`status.adminBooking.${s}`) : t(`status.booking.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("common.service")}>
          <Select value={serviceId} onChange={(e) => setParam("service", e.target.value)}>
            <option value="">{t("admin.allServices")}</option>
            {services.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {fmt.pick(s, "name")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("common.area")}>
          <Select value={areaId} onChange={(e) => setParam("area", e.target.value)}>
            <option value="">{t("admin.allAreas")}</option>
            {areas.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("admin.dateFrom")}>
          <Input type="date" value={dateFrom} onChange={(e) => setParam("from", e.target.value)} />
        </Field>
        <Field label={t("admin.dateTo")}>
          <Input type="date" value={dateTo} onChange={(e) => setParam("to", e.target.value)} />
        </Field>
      </div>
      {query.isLoading && <SkeletonCard lines={6} />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          {query.data.items.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title={t("admin.noMatchingBookings")}
              body={t("admin.noMatchingBookingsBody")}
              action={(status || serviceId || areaId || dateFrom || dateTo || q) && (
                <Button variant="secondary" onClick={() => { setParams(new URLSearchParams(), { replace: true }); setQ(""); }}>
                  {t("admin.clearFilters")}
                </Button>
              )}
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("common.reference")}</th>
                    <th>{t("common.service")}</th>
                    <th>{t("booking.when")}</th>
                    <th>{t("common.customer")}</th>
                    <th>{t("common.provider")}</th>
                    <th>{t("common.status")}</th>
                    <th className="right">{t("common.amount")}</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((b) => (
                    <tr key={b.id} className="is-clickable" onClick={() => navigate(`/admin/bookings/${b.id}`)}>
                      <td className="cell-main num">{b.reference}</td>
                      <td>
                        <div>{fmt.pick(b.service, "name")}</div>
                        <div className="cell-sub">{b.area_name}</div>
                      </td>
                      <td className="nowrap">
                        <div>{fmt.date(b.scheduled_date)}</div>
                        <div className="cell-sub">{fmt.time(b.scheduled_start_time)}</div>
                      </td>
                      <td>{b.customer_name}</td>
                      <td>{b.provider_name ?? <span className="muted">—</span>}</td>
                      <td>
                        <BookingStatusBadge status={b.status} admin />
                      </td>
                      <td className="right num">
                        <div>{fmt.money(b.total_amount, b.currency)}</div>
                        {b.payment_status && <div className="cell-sub">{t(`status.payment.${b.payment_status}`)}</div>}
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
    </div>
  );
}

export function AdminBookingDetailPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const [assignOpen, setAssignOpen] = useState(false);
  const [statusTarget, setStatusTarget] = useState<BookingStatus | "">("");
  const [statusNote, setStatusNote] = useState("");
  const query = useQuery({ queryKey: ["admin", "booking", id], queryFn: () => adminApi.booking(id), refetchInterval: 20_000 });

  const after = (message: string) => () => {
    toast.success(message);
    void qc.invalidateQueries({ queryKey: ["admin"] });
  };
  const setStatus = useMutation({
    mutationFn: () => adminApi.setStatus(id, statusTarget as BookingStatus, statusNote || undefined),
    onSuccess: () => {
      setStatusTarget("");
      setStatusNote("");
      after(t("admin.booking.statusChanged"))();
    },
    onError: toast.error,
  });
  const setPayment = useMutation({
    mutationFn: (status: PaymentStatus) => adminApi.setPayment(id, status),
    onSuccess: after(t("common.saved")),
    onError: toast.error,
  });

  if (query.isLoading) return <PageLoader />;
  if (query.error || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const b = query.data;
  const statusTargets = b.allowed_actions.filter((a) => a.startsWith("SET_STATUS:")).map((a) => a.split(":")[1] as BookingStatus);
  const canAssign = b.allowed_actions.includes("ASSIGN");
  const payment = b.payment;

  return (
    <div className="stack-lg">
      <PageHeader
        back={{ to: "/admin/bookings", label: t("nav.admin.bookings") }}
        title={`${b.reference} · ${fmt.pick(b.service, "name")}`}
        subtitle={`${fmt.dateLong(b.scheduled_date)}, ${fmt.time(b.scheduled_start_time)}–${addMinutesToTime(b.scheduled_start_time, b.estimated_duration_minutes)} · ${b.area_name}`}
        actions={
          <>
            <BookingStatusBadge status={b.status} admin />
            {canAssign && (
              <Button icon={<UserCheck />} onClick={() => setAssignOpen(true)}>
                {b.provider ? t("admin.booking.reassign") : t("admin.booking.assign")}
              </Button>
            )}
          </>
        }
      />

      <div className="detail-grid">
        <div className="stack-lg">
          <section className="card stack">
            <h2 className="card-title">{t("admin.booking.timeline")}</h2>
            <ol className="timeline">
              {b.history.map((h, i) => (
                <li key={i} className={h.to_status === "CANCELLED" || h.to_status === "DISPUTED" || h.to_status === "REASSIGNMENT_REQUIRED" ? "is-alert" : undefined}>
                  <span className="timeline-dot" />
                  <div>
                    <div className="timeline-title">
                      {i18n.exists(`status.timeline.${h.to_status}`) ? t(`status.timeline.${h.to_status}`) : t(`status.booking.${h.to_status}`)}
                    </div>
                    <div className="timeline-meta">
                      {fmt.dateTime(h.created_at)} · {h.actor_name ?? t("admin.system")}
                      {h.actor_role && h.actor_name ? ` (${h.actor_role})` : ""}
                      {h.note && ` · ${h.note}`}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {!!b.assignments?.length && (
            <section className="card card-flush">
              <div style={{ padding: "var(--s-5) var(--s-6) var(--s-3)" }}>
                <h2 className="card-title">{t("admin.booking.assignments")}</h2>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t("common.provider")}</th>
                      <th>{t("common.status")}</th>
                      <th>{t("common.created")}</th>
                      <th>{t("common.notes")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {b.assignments.map((a) => (
                      <tr key={a.id}>
                        <td className="cell-main">
                          {a.provider_name}
                          {a.is_manual && <div className="cell-sub">{t("admin.booking.manual")}</div>}
                        </td>
                        <td>
                          <AssignmentStatusBadge status={a.status} />
                        </td>
                        <td className="nowrap small">{fmt.dateTime(a.offered_at)}</td>
                        <td className="small muted">{a.response_note ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {statusTargets.length > 0 && (
            <section className="card stack">
              <h2 className="card-title">{t("admin.booking.changeStatus")}</h2>
              <div className="grid-2">
                <Field label={t("common.status")}>
                  <Select value={statusTarget} onChange={(e) => setStatusTarget(e.target.value as BookingStatus)}>
                    <option value="">—</option>
                    {statusTargets.map((s) => (
                      <option key={s} value={s}>
                        {t(`status.booking.${s}`)}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label={t("common.notes")} optional={t("common.optional")}>
                  <Input value={statusNote} onChange={(e) => setStatusNote(e.target.value)} maxLength={255} />
                </Field>
              </div>
              <div>
                <Button variant="secondary" disabled={!statusTarget} loading={setStatus.isPending} onClick={() => setStatus.mutate()}>
                  {t("common.confirm")}
                </Button>
              </div>
            </section>
          )}

          <section className="card stack">
            <h2 className="card-title">{t("customer.bookingDetails")}</h2>
            <dl className="dl">
              <dt>{t("booking.where")}</dt>
              <dd>
                {b.address_line}
                {b.landmark && <div className="small muted">{b.landmark}</div>}
              </dd>
              <dt>{t("customer.property")}</dt>
              <dd>
                {[b.property_type && fmt.pick(b.property_type, "name"), b.size && fmt.pick(b.size, "name")].filter(Boolean).join(" · ") || "—"}
                {b.bathrooms > 0 && <div className="small muted">{fmt.rooms(b.bedrooms, b.bathrooms)}</div>}
              </dd>
              {b.special_instructions && (
                <>
                  <dt>{t("customer.instructions")}</dt>
                  <dd>{b.special_instructions}</dd>
                </>
              )}
              {b.cancellation_reason && (
                <>
                  <dt>{t("status.booking.CANCELLED")}</dt>
                  <dd>{b.cancellation_reason}</dd>
                </>
              )}
            </dl>
          </section>
        </div>

        <aside className="detail-aside">
          <section className="card stack-sm">
            <div className="card-title">{t("common.customer")}</div>
            <div className="strong">{b.customer?.full_name}</div>
            <div className="small">{b.customer?.phone}</div>
            <div className="small muted">{b.customer?.email}</div>
          </section>
          <section className="card stack-sm">
            <div className="card-title">{t("common.provider")}</div>
            {b.provider ? (
              <>
                <div className="strong">{b.provider.display_name}</div>
                <div className="small">{b.provider.phone}</div>
              </>
            ) : (
              <span className="muted small">—</span>
            )}
          </section>
          <section className="card stack-sm">
            <div className="card-title">{t("admin.booking.economics")}</div>
            <div className="price-lines">
              {b.price_items.map((line, i) => (
                <div className="price-line small" key={i}>
                  <span>
                    {fmt.pick(line, "label")}
                    {line.quantity > 1 && ` × ${line.quantity}`}
                  </span>
                  <span>{fmt.money(line.amount, b.currency)}</span>
                </div>
              ))}
              <div className="price-total">
                <span>{t("common.total")}</span>
                <span>{fmt.money(b.total_amount, b.currency)}</span>
              </div>
              <div className="price-line">
                <span>
                  {t("admin.metrics.commission")} ({Number(b.commission_percent)}%)
                </span>
                <span>{fmt.money(b.commission_amount, b.currency)}</span>
              </div>
              <div className="price-line strong">
                <span>{t("admin.booking.providerEarning")}</span>
                <span>{fmt.money(b.provider_earning, b.currency)}</span>
              </div>
            </div>
          </section>
          {payment && (
            <section className="card stack-sm">
              <div className="row-between">
                <div className="card-title">{t("admin.booking.paymentActions")}</div>
                <PaymentStatusBadge status={payment.status} />
              </div>
              <div className="small muted">
                {t(`booking.methods.${payment.method}`)} · {fmt.money(payment.amount, payment.currency)}
                {payment.paid_at && (
                  <div>
                    {fmt.dateTime(payment.paid_at)} · {payment.confirmed_by_name}
                  </div>
                )}
              </div>
              <div className="row wrap" style={{ gap: 8 }}>
                {b.allowed_actions.includes("CONFIRM_CASH") && (
                  <Button size="sm" onClick={() => setPayment.mutate("PAID")} loading={setPayment.isPending}>
                    {t("admin.booking.confirmCash")}
                  </Button>
                )}
                {payment.status === "PENDING" && (
                  <Button size="sm" variant="danger" onClick={() => setPayment.mutate("FAILED")}>
                    {t("admin.booking.markFailed")}
                  </Button>
                )}
                {payment.status === "FAILED" && (
                  <Button size="sm" variant="secondary" onClick={() => setPayment.mutate("PENDING")}>
                    {t("admin.booking.retryPayment")}
                  </Button>
                )}
                {payment.status === "PAID" && (
                  <Button size="sm" variant="secondary" onClick={() => setPayment.mutate("REFUNDED")}>
                    {t("admin.booking.markRefunded")}
                  </Button>
                )}
              </div>
            </section>
          )}
          {b.review && (
            <section className="card stack-sm">
              <div className="card-title">{t("nav.admin.reviews")}</div>
              <Stars value={b.review.rating} />
              {b.review.comment && <p className="small">{b.review.comment}</p>}
            </section>
          )}
        </aside>
      </div>

      <AssignDialog open={assignOpen} bookingId={b.id} onClose={() => setAssignOpen(false)} onDone={after(t("admin.booking.assigned"))} />
    </div>
  );
}

function AssignDialog({ open, bookingId, onClose, onDone }: { open: boolean; bookingId: string; onClose: () => void; onDone: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [includeOffHours, setIncludeOffHours] = useState(false);
  const [providerId, setProviderId] = useState("");
  const [direct, setDirect] = useState(true);
  const [note, setNote] = useState("");
  const eligible = useQuery({
    queryKey: ["admin", "eligible", bookingId, includeOffHours],
    queryFn: () => adminApi.eligibleProviders(bookingId, includeOffHours),
    enabled: open,
  });
  const assign = useMutation({
    mutationFn: () => adminApi.assign(bookingId, providerId, direct, note || undefined),
    onSuccess: () => {
      onClose();
      onDone();
    },
    onError: toast.error,
  });
  return (
    <Modal
      open={open}
      wide
      title={t("admin.booking.assign")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button disabled={!providerId} loading={assign.isPending} onClick={() => assign.mutate()}>
            {direct ? t("admin.booking.assign") : t("admin.booking.offer")}
          </Button>
        </>
      }
    >
      <div className="stack">
        <Switch checked={includeOffHours} onChange={setIncludeOffHours} label={t("admin.booking.includeOffHours")} />
        <div className="section-label">{t("admin.booking.eligible")}</div>
        {eligible.isLoading && <SkeletonCard lines={2} />}
        {eligible.data?.length === 0 && <p className="muted small">{t("admin.booking.noEligible")}</p>}
        <div className="stack-sm" role="radiogroup">
          {eligible.data?.map((p) => (
            <label key={p.id} className={`choice ${providerId === p.id ? "is-selected" : ""}`} style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
              <input type="radio" name="provider" checked={providerId === p.id} onChange={() => setProviderId(p.id)} style={{ accentColor: "var(--green-700)" }} />
              <span className="grow">
                <span className="choice-title">{p.display_name}</span>
                <span className="choice-meta" style={{ display: "block" }}>
                  {p.provider_type === "COMPANY" ? t("common.company") : t("common.individual")} ·{" "}
                  {p.rating_count ? `★ ${Number(p.rating_average).toFixed(1)} (${p.rating_count})` : t("common.noRatingYet")} ·{" "}
                  {t("admin.booking.jobsThatDay", { count: p.jobs_that_day })}
                </span>
              </span>
            </label>
          ))}
        </div>
        <div className="grid-2">
          <label className="checkbox">
            <input type="radio" checked={direct} onChange={() => setDirect(true)} /> {t("admin.booking.direct")}
          </label>
          <label className="checkbox">
            <input type="radio" checked={!direct} onChange={() => setDirect(false)} /> {t("admin.booking.offer")}
          </label>
        </div>
        <Field label={t("common.notes")} optional={t("common.optional")}>
          <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={255} />
        </Field>
      </div>
    </Modal>
  );
}
