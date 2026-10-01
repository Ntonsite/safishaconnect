import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Briefcase, CheckCircle2, Inbox, MapPin, Phone, Star, Wallet } from "lucide-react";
import { providerApi } from "../../api/endpoints";
import { RatingSummary, Stars } from "../../shared/components/Brand";
import { Button, ButtonLink } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/Controls";
import { Alert, EmptyState, ErrorState, PageLoader, SkeletonCard } from "../../shared/components/Feedback";
import { Switch } from "../../shared/components/Field";
import { ConfirmDialog } from "../../shared/components/Modal";
import { BookingStatusBadge, PaymentStatusBadge, VerificationBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";
import { addMinutesToTime } from "../../shared/utils/format";
import { JobCard } from "./JobCard";
import { useJobActions } from "./useJobActions";

export function ProviderDashboard() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const toast = useToast();
  const qc = useQueryClient();
  const dashboard = useQuery({ queryKey: ["provider", "dashboard"], queryFn: providerApi.dashboard, refetchInterval: 30_000 });
  const profile = useQuery({ queryKey: ["provider", "profile"], queryFn: providerApi.profile });
  const offers = useQuery({ queryKey: ["provider", "jobs", "offers"], queryFn: () => providerApi.jobs("offers"), refetchInterval: 20_000 });
  const toggle = useMutation({
    mutationFn: (value: boolean) => providerApi.updateProfile({ is_accepting_jobs: value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["provider"] }),
    onError: toast.error,
  });

  if (dashboard.isLoading || profile.isLoading) return <PageLoader />;
  if (dashboard.error || !dashboard.data) return <ErrorState error={dashboard.error} onRetry={() => dashboard.refetch()} />;
  const d = dashboard.data;
  const verified = d.verification_status === "VERIFIED";

  const stats = [
    { label: t("provider.stats.offers"), value: d.open_offers, icon: Inbox, to: "/provider/offers" },
    { label: t("provider.stats.active"), value: d.active_jobs, icon: Briefcase, to: "/provider/jobs" },
    { label: t("provider.stats.completed"), value: d.completed_jobs, icon: CheckCircle2, to: "/provider/completed" },
    {
      label: t("provider.stats.rating"),
      value: d.rating_count ? Number(d.rating_average).toFixed(1) : "—",
      icon: Star,
      to: "/provider/ratings",
    },
  ];

  return (
    <div className="stack-lg">
      <PageHeader
        title={t("provider.welcome", { name: profile.data?.display_name.split(" ")[0] ?? "" })}
        subtitle={<VerificationBadge status={d.verification_status} />}
      />

      {!verified && <Alert tone={d.verification_status === "PENDING" ? "info" : "danger"}>{t(`provider.verification.${d.verification_status}`)}</Alert>}
      {!d.setup_complete && (
        <Alert tone="warning">
          {t("provider.setupMissing")}{" "}
          {d.missing_setup.map((m, i) => (
            <span key={m}>
              {i > 0 && ", "}
              <Link to={m === "AVAILABILITY" ? "/provider/availability" : "/provider/coverage"}>{t(`provider.setup.${m}`)}</Link>
            </span>
          ))}
        </Alert>
      )}

      {verified && (
        <div className="card card-tight row-between">
          <Switch checked={d.is_accepting_jobs} onChange={(v) => toggle.mutate(v)} label={t("provider.toggleAccepting")} disabled={toggle.isPending} />
          <span className={`badge ${d.is_accepting_jobs ? "tone-green" : "tone-slate"} badge-dot`}>
            {d.is_accepting_jobs ? t("provider.accepting") : t("provider.notAccepting")}
          </span>
        </div>
      )}

      <div className="grid-4">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className="card card-tight link-card stat">
            <span className="stat-label row" style={{ gap: 6 }}>
              <s.icon size={16} aria-hidden /> {s.label}
            </span>
            <span className="stat-value">{s.value}</span>
          </Link>
        ))}
      </div>

      <div className="grid-2">
        <Link to="/provider/earnings" className="card link-card stat">
          <span className="stat-label row" style={{ gap: 6 }}>
            <Wallet size={16} aria-hidden /> {t("provider.stats.earned")}
          </span>
          <span className="stat-value">{fmt.money(d.earnings_total, d.currency)}</span>
        </Link>
        <Link to="/provider/earnings" className="card link-card stat">
          <span className="stat-label">{t("provider.stats.pending")}</span>
          <span className="stat-value">{fmt.money(d.earnings_pending, d.currency)}</span>
        </Link>
      </div>

      <section className="stack-sm">
        <div className="row-between">
          <h2 className="section-label">{t("provider.newRequests")}</h2>
          {!!offers.data?.length && (
            <ButtonLink to="/provider/offers" variant="ghost" size="sm">
              {t("common.viewAll")}
            </ButtonLink>
          )}
        </div>
        {offers.data?.length ? (
          <OfferList jobs={offers.data.slice(0, 2)} />
        ) : (
          <div className="card">
            <EmptyState icon={Inbox} title={t("provider.noOffers")} body={t("provider.noOffersBody")} />
          </div>
        )}
      </section>
    </div>
  );
}

function OfferList({ jobs }: { jobs: Awaited<ReturnType<typeof providerApi.jobs>> }) {
  const { t } = useTranslation();
  const actions = useJobActions();
  const [rejecting, setRejecting] = useState<string | null>(null);
  return (
    <div className="stack">
      {jobs.map((job) => (
        <JobCard job={job} key={job.assignment_id}>
          <p className="small muted">{t("provider.addressHidden")}</p>
          <div className="grid-2" style={{ gap: 8 }}>
            <Button variant="secondary" size="lg" onClick={() => setRejecting(job.assignment_id)}>
              {t("provider.actions.REJECT")}
            </Button>
            <Button
              size="lg"
              loading={actions.accept.isPending && actions.accept.variables === job.assignment_id}
              onClick={() => actions.accept.mutate(job.assignment_id)}
            >
              {t("provider.actions.ACCEPT")}
            </Button>
          </div>
        </JobCard>
      ))}
      <ConfirmDialog
        open={!!rejecting}
        title={t("provider.rejectTitle")}
        confirmLabel={t("provider.actions.REJECT")}
        tone="danger"
        withReason={t("provider.rejectReason")}
        loading={actions.reject.isPending}
        onClose={() => setRejecting(null)}
        onConfirm={(reason) =>
          actions.reject.mutate({ assignmentId: rejecting!, reason }, { onSettled: () => setRejecting(null) })
        }
      />
    </div>
  );
}

export function OffersPage() {
  const { t } = useTranslation();
  const query = useQuery({ queryKey: ["provider", "jobs", "offers"], queryFn: () => providerApi.jobs("offers"), refetchInterval: 15_000 });
  return (
    <div className="stack">
      <PageHeader title={t("nav.provider.offers")} />
      {query.isLoading && <SkeletonCard />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.length === 0 && (
        <div className="card">
          <EmptyState icon={Inbox} title={t("provider.noOffers")} body={t("provider.noOffersBody")} />
        </div>
      )}
      {!!query.data?.length && <OfferList jobs={query.data} />}
    </div>
  );
}

export function JobsListPage({ scope }: { scope: "active" | "completed" }) {
  const { t } = useTranslation();
  const query = useQuery({ queryKey: ["provider", "jobs", scope], queryFn: () => providerApi.jobs(scope), refetchInterval: 30_000 });
  const title = scope === "active" ? t("nav.provider.active") : t("nav.provider.completed");
  return (
    <div className="stack">
      <PageHeader title={title} />
      {query.isLoading && <SkeletonCard />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.length === 0 && (
        <div className="card">
          <EmptyState
            icon={scope === "active" ? Briefcase : CheckCircle2}
            title={scope === "active" ? t("provider.noActive") : t("provider.noCompleted")}
            body={scope === "active" ? t("provider.noActiveBody") : undefined}
          />
        </div>
      )}
      {query.data?.map((job) => <JobCard key={job.assignment_id} job={job} />)}
    </div>
  );
}

export function JobDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const fmt = useFormat();
  const navigate = useNavigate();
  const actions = useJobActions();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [cashOpen, setCashOpen] = useState(false);
  const query = useQuery({ queryKey: ["provider", "job", id], queryFn: () => providerApi.job(id), refetchInterval: 20_000 });

  if (query.isLoading) return <PageLoader />;
  if (query.error || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const job = query.data;
  const b = job.booking;
  const can = (a: string) => b.allowed_actions.includes(a);
  const progressAction = ["MARK_EN_ROUTE", "MARK_ARRIVED", "START_SERVICE", "COMPLETE_SERVICE"].find(can);
  const busy = actions.advance.isPending || actions.accept.isPending || actions.confirmCash.isPending;

  return (
    <div className="stack-lg">
      <PageHeader
        back={{ to: job.assignment_status === "OFFERED" ? "/provider/offers" : "/provider/jobs", label: t("common.back") }}
        title={fmt.pick(b.service, "name")}
        subtitle={b.reference}
        actions={<BookingStatusBadge status={b.status} />}
      />

      <div className="detail-grid">
        <div className="stack-lg">
          {(progressAction || can("ACCEPT") || can("CONFIRM_CASH")) && (
            <div className="action-bar is-sticky">
              {can("ACCEPT") && (
                <div className="grid-2" style={{ gap: 8 }}>
                  <Button variant="secondary" size="lg" onClick={() => setRejectOpen(true)}>
                    {t("provider.actions.REJECT")}
                  </Button>
                  <Button size="lg" loading={busy} onClick={() => actions.accept.mutate(job.assignment_id, { onSuccess: () => query.refetch() })}>
                    {t("provider.actions.ACCEPT")}
                  </Button>
                </div>
              )}
              {progressAction && (
                <Button
                  size="lg"
                  block
                  loading={busy}
                  onClick={() => actions.advance.mutate({ bookingId: b.id, action: progressAction }, { onSuccess: () => query.refetch() })}
                >
                  {t(`provider.actions.${progressAction}`)}
                </Button>
              )}
              {can("CONFIRM_CASH") && (
                <Button size="lg" block variant={progressAction ? "secondary" : "primary"} onClick={() => setCashOpen(true)}>
                  {t("provider.actions.CONFIRM_CASH")}
                </Button>
              )}
            </div>
          )}

          <section className="card stack">
            <h2 className="card-title">{t("provider.jobDetails")}</h2>
            <dl className="dl">
              <dt>{t("booking.when")}</dt>
              <dd>
                {fmt.dateLong(b.scheduled_date)}
                <div className="small muted">
                  {fmt.time(b.scheduled_start_time)}–{addMinutesToTime(b.scheduled_start_time, b.estimated_duration_minutes)} ·{" "}
                  {fmt.duration(b.estimated_duration_minutes)}
                </div>
              </dd>
              <dt>{t("booking.where")}</dt>
              <dd>
                {b.address_line ? (
                  <>
                    {b.address_line}
                    {b.landmark && <div className="small muted">{b.landmark}</div>}
                    <div className="small muted">{b.area_name}</div>
                    <a
                      className="small"
                      target="_blank"
                      rel="noreferrer"
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${b.address_line}, ${b.area_name}, Dar es Salaam`)}`}
                    >
                      <MapPin size={12} style={{ display: "inline", verticalAlign: -1 }} aria-hidden /> Google Maps
                    </a>
                  </>
                ) : (
                  <>
                    {b.area_name}
                    <div className="small muted">{t("provider.addressHidden")}</div>
                  </>
                )}
              </dd>
              <dt>{t("customer.property")}</dt>
              <dd>
                {[b.property_type && fmt.pick(b.property_type, "name"), b.size && fmt.pick(b.size, "name")].filter(Boolean).join(" · ") ||
                  fmt.pick(b.service, "name")}
                {b.bathrooms > 0 && <div className="small muted">{t("customer.rooms", { bedrooms: b.bedrooms, bathrooms: b.bathrooms })}</div>}
              </dd>
              {b.price_items.some((i) => i.kind === "ADDON") && (
                <>
                  <dt>{t("booking.addons")}</dt>
                  <dd>
                    {b.price_items
                      .filter((i) => i.kind === "ADDON")
                      .map((i) => `${fmt.pick(i, "label")}${i.quantity > 1 ? ` × ${i.quantity}` : ""}`)
                      .join(", ")}
                  </dd>
                </>
              )}
              {b.special_instructions && (
                <>
                  <dt>{t("customer.instructions")}</dt>
                  <dd>{b.special_instructions}</dd>
                </>
              )}
            </dl>
          </section>

          {can("WITHDRAW") && (
            <div>
              <Button variant="ghost" icon={<AlertTriangle />} onClick={() => setWithdrawOpen(true)}>
                {t("provider.actions.WITHDRAW")}
              </Button>
            </div>
          )}
        </div>

        <aside className="detail-aside">
          {b.customer && (
            <section className="card stack-sm">
              <div className="card-title">{t("provider.customerContact")}</div>
              <div className="strong">{b.customer.full_name}</div>
              {b.customer.phone && (
                <a className="btn btn-soft" href={`tel:${b.customer.phone}`}>
                  <Phone /> {b.customer.phone}
                </a>
              )}
            </section>
          )}
          <section className="card stack-sm">
            <div className="price-lines">
              <div className="price-line">
                <span>{t("provider.customerPays")}</span>
                <span>{fmt.money(b.total_amount, b.currency)}</span>
              </div>
              <div className="price-line muted">
                <span>
                  {t("provider.commission")} ({Number(b.commission_percent)}%)
                </span>
                <span>−{fmt.money(b.commission_amount, b.currency)}</span>
              </div>
              <div className="price-total">
                <span>{t("provider.youEarn")}</span>
                <span style={{ color: "var(--green-800)" }}>{fmt.money(b.provider_earning, b.currency)}</span>
              </div>
            </div>
            {b.payment && (
              <div className="row-between" style={{ paddingTop: 8 }}>
                <span className="small muted">{t(`booking.methods.${b.payment.method}`)}</span>
                <PaymentStatusBadge status={b.payment.status} />
              </div>
            )}
          </section>
        </aside>
      </div>

      <ConfirmDialog
        open={rejectOpen}
        title={t("provider.rejectTitle")}
        confirmLabel={t("provider.actions.REJECT")}
        tone="danger"
        withReason={t("provider.rejectReason")}
        loading={actions.reject.isPending}
        onClose={() => setRejectOpen(false)}
        onConfirm={(reason) =>
          actions.reject.mutate({ assignmentId: job.assignment_id, reason }, { onSuccess: () => navigate("/provider/offers") })
        }
      />
      <ConfirmDialog
        open={withdrawOpen}
        title={t("provider.withdrawTitle")}
        description={t("provider.withdrawBody")}
        confirmLabel={t("provider.actions.WITHDRAW")}
        tone="danger"
        withReason={t("provider.rejectReason")}
        loading={actions.withdraw.isPending}
        onClose={() => setWithdrawOpen(false)}
        onConfirm={(reason) => actions.withdraw.mutate({ bookingId: b.id, reason }, { onSuccess: () => navigate("/provider/jobs") })}
      />
      <ConfirmDialog
        open={cashOpen}
        title={t("provider.cashTitle")}
        description={t("provider.cashBody", { amount: fmt.money(b.total_amount, b.currency) })}
        confirmLabel={t("common.confirm")}
        loading={actions.confirmCash.isPending}
        onClose={() => setCashOpen(false)}
        onConfirm={() =>
          actions.confirmCash.mutate(b.id, {
            onSuccess: () => {
              setCashOpen(false);
              void query.refetch();
            },
          })
        }
      />
    </div>
  );
}

export function RatingsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const profile = useQuery({ queryKey: ["provider", "profile"], queryFn: providerApi.profile });
  const reviews = useQuery({ queryKey: ["provider", "reviews"], queryFn: providerApi.reviews });
  return (
    <div className="stack">
      <PageHeader title={t("provider.ratingsTitle")} />
      {profile.data && (
        <div className="card row">
          <span className="stat-value">{profile.data.rating_count ? Number(profile.data.rating_average).toFixed(1) : "—"}</span>
          <RatingSummary average={profile.data.rating_average} count={profile.data.rating_count} />
        </div>
      )}
      {reviews.isLoading && <SkeletonCard />}
      {reviews.data?.length === 0 && (
        <div className="card">
          <EmptyState icon={Star} title={t("provider.noReviews")} />
        </div>
      )}
      {reviews.data?.map((r) => (
        <article key={r.id} className="card stack-sm">
          <div className="row-between wrap">
            <Stars value={r.rating} />
            <span className="small muted">{fmt.dateTime(r.created_at)}</span>
          </div>
          {r.comment && <p>“{r.comment}”</p>}
          <div className="small muted">
            {r.customer_name.split(" ")[0]} · {r.service_name} · {r.booking_reference}
          </div>
        </article>
      ))}
    </div>
  );
}
