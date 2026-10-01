import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, Banknote, CheckCircle2, ListChecks, MessageSquareWarning } from "lucide-react";
import { adminApi } from "../../api/endpoints";
import type { BookingStatus } from "../../api/types";
import { PageHeader } from "../../shared/components/Controls";
import { ErrorState, PageLoader } from "../../shared/components/Feedback";
import { BookingStatusBadge } from "../../shared/components/StatusBadge";
import { useFormat } from "../../shared/hooks/useFormat";

export function AdminOverview() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const query = useQuery({ queryKey: ["admin", "stats"], queryFn: adminApi.stats, refetchInterval: 30_000 });
  if (query.isLoading) return <PageLoader />;
  if (query.error || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const s = query.data;

  const money = [
    { label: t("admin.metrics.gbv"), value: fmt.money(s.gross_booking_value, s.currency) },
    { label: t("admin.metrics.commission"), value: fmt.money(s.platform_commission, s.currency) },
    { label: t("admin.metrics.settlementsPending"), value: fmt.money(s.settlements_pending_amount, s.currency) },
  ];
  const counts = [
    { label: t("admin.metrics.todaysBookings"), value: s.todays_bookings },
    { label: t("admin.metrics.totalBookings"), value: s.total_bookings },
    { label: t("admin.metrics.completed"), value: s.completed_bookings },
    { label: t("admin.metrics.cancelled"), value: s.cancelled_bookings },
    { label: t("admin.metrics.customers"), value: s.total_customers },
    { label: t("admin.metrics.activeProviders"), value: s.active_providers },
    { label: t("admin.metrics.pendingAssignments"), value: s.pending_assignments },
    { label: t("admin.metrics.openComplaints"), value: s.open_complaints },
  ];
  const attention = [
    { count: s.pending_assignments, text: t("admin.attention.assignment", { count: s.pending_assignments }), icon: ListChecks, to: "/admin/bookings?status=REASSIGNMENT_REQUIRED" },
    { count: s.providers_awaiting_verification, text: t("admin.attention.verification", { count: s.providers_awaiting_verification }), icon: BadgeCheck, to: "/admin/providers?status=PENDING" },
    { count: s.open_complaints, text: t("admin.attention.complaints", { count: s.open_complaints }), icon: MessageSquareWarning, to: "/admin/complaints?status=OPEN" },
    { count: s.cash_awaiting_confirmation, text: t("admin.attention.cash", { count: s.cash_awaiting_confirmation }), icon: Banknote, to: "/admin/payments?status=PENDING" },
  ].filter((a) => a.count > 0);

  const statusRows = Object.entries(s.bookings_by_status).sort((a, b) => b[1] - a[1]) as [BookingStatus, number][];
  const maxCount = Math.max(1, ...statusRows.map(([, n]) => n));

  return (
    <div className="stack-lg">
      <PageHeader title={t("admin.overviewTitle")} subtitle={t("admin.overviewSubtitle")} />

      <section className="card stack-sm">
        <h2 className="card-title">{t("admin.needsAttention")}</h2>
        {attention.length === 0 ? (
          <p className="row muted" style={{ gap: 8 }}>
            <CheckCircle2 size={18} color="var(--green-600)" aria-hidden /> {t("admin.nothingUrgent")}
          </p>
        ) : (
          attention.map((a) => (
            <Link key={a.to} to={a.to} className="row-between" style={{ padding: "10px 0", borderBottom: "1px solid var(--line)", color: "inherit" }}>
              <span className="row">
                <span className="feature-icon" style={{ width: 36, height: 36, background: "var(--amber-50)", color: "var(--amber-700)" }}>
                  <a.icon size={18} aria-hidden />
                </span>
                <span className="strong">{a.text}</span>
              </span>
              <ArrowRight size={18} className="muted" aria-hidden />
            </Link>
          ))
        )}
      </section>

      <div className="grid-3">
        {money.map((m) => (
          <div className="card stat" key={m.label}>
            <span className="stat-label">{m.label}</span>
            <span className="stat-value">{m.value}</span>
          </div>
        ))}
      </div>

      <div className="grid-4">
        {counts.map((c) => (
          <div className="card card-tight stat" key={c.label}>
            <span className="stat-label">{c.label}</span>
            <span className="stat-value stat-value-sm">{c.value}</span>
          </div>
        ))}
      </div>

      {statusRows.length > 0 && (
        <section className="card stack">
          <h2 className="card-title">{t("admin.bookingsByStatus")}</h2>
          <div className="stack-sm">
            {statusRows.map(([status, n]) => (
              <Link key={status} to={`/admin/bookings?status=${status}`} className="row" style={{ color: "inherit", gap: "var(--s-4)" }}>
                <span style={{ width: 220, flexShrink: 0 }}>
                  <BookingStatusBadge status={status} admin />
                </span>
                <span className="grow" style={{ background: "var(--surface-sunken)", borderRadius: 6, height: 10 }}>
                  <span style={{ display: "block", height: 10, borderRadius: 6, width: `${(n / maxCount) * 100}%`, background: "var(--green-500)" }} />
                </span>
                <span className="num strong" style={{ width: 40, textAlign: "right" }}>
                  {n}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
