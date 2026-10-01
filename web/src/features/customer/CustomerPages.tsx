import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { CalendarPlus, ClipboardList, Star } from "lucide-react";
import { customerApi } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { BookingRow } from "../../shared/components/BookingBits";
import { Stars } from "../../shared/components/Brand";
import { ButtonLink } from "../../shared/components/Button";
import { PageHeader, Tabs } from "../../shared/components/Controls";
import { EmptyState, ErrorState, SkeletonCard } from "../../shared/components/Feedback";
import { useFormat } from "../../shared/hooks/useFormat";

export function CustomerDashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const active = useQuery({ queryKey: ["bookings", "active"], queryFn: () => customerApi.bookings("active"), refetchInterval: 20_000 });
  const history = useQuery({ queryKey: ["bookings", "history"], queryFn: () => customerApi.bookings("history") });
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="stack-lg">
      <PageHeader
        title={t("customer.greeting", { name: firstName })}
        subtitle={t("customer.dashboardSubtitle")}
        actions={
          <ButtonLink to="/app/book" icon={<CalendarPlus />}>
            {t("nav.bookCleaning")}
          </ButtonLink>
        }
      />
      <section className="stack-sm">
        <h2 className="section-label">{t("customer.upcoming")}</h2>
        {active.isLoading && <SkeletonCard />}
        {active.error && <ErrorState error={active.error} onRetry={() => active.refetch()} />}
        {active.data && (
          <div className="card card-flush">
            {active.data.length === 0 ? (
              <EmptyState
                icon={CalendarPlus}
                title={t("customer.noActive")}
                body={t("customer.noActiveBody")}
                action={<ButtonLink to="/app/book">{t("nav.bookCleaning")}</ButtonLink>}
              />
            ) : (
              active.data.map((b) => <BookingRow key={b.id} booking={b} to={`/app/bookings/${b.id}`} />)
            )}
          </div>
        )}
      </section>
      {!!history.data?.length && (
        <section className="stack-sm">
          <div className="row-between">
            <h2 className="section-label">{t("customer.recent")}</h2>
            <ButtonLink to="/app/bookings" variant="ghost" size="sm">
              {t("common.viewAll")}
            </ButtonLink>
          </div>
          <div className="card card-flush">
            {history.data.slice(0, 3).map((b) => (
              <BookingRow key={b.id} booking={b} to={`/app/bookings/${b.id}`} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export function BookingsPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"active" | "history">("active");
  const query = useQuery({ queryKey: ["bookings", tab], queryFn: () => customerApi.bookings(tab) });
  return (
    <div className="stack">
      <PageHeader
        title={t("nav.myBookings")}
        actions={
          <ButtonLink to="/app/book" icon={<CalendarPlus />}>
            {t("nav.newBooking")}
          </ButtonLink>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "active", label: t("customer.tabs.active") },
          { value: "history", label: t("customer.tabs.history") },
        ]}
      />
      {query.isLoading && <SkeletonCard />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          {query.data.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title={tab === "active" ? t("customer.noActive") : t("customer.noHistory")}
              action={tab === "active" ? <ButtonLink to="/app/book">{t("nav.bookCleaning")}</ButtonLink> : undefined}
            />
          ) : (
            query.data.map((b) => <BookingRow key={b.id} booking={b} to={`/app/bookings/${b.id}`} />)
          )}
        </div>
      )}
    </div>
  );
}

export function MyReviewsPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const query = useQuery({ queryKey: ["my-reviews"], queryFn: customerApi.myReviews });
  return (
    <div className="stack">
      <PageHeader title={t("nav.reviews")} />
      {query.isLoading && <SkeletonCard />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data?.length === 0 && (
        <div className="card">
          <EmptyState icon={Star} title={t("customer.myReviewsEmpty")} />
        </div>
      )}
      {query.data?.map((r) => (
        <article key={r.id} className="card stack-sm">
          <div className="row-between wrap">
            <div>
              <div className="strong">{r.service_name}</div>
              <div className="small muted">
                {r.provider_name} · {r.booking_reference} · {fmt.dateTime(r.created_at)}
              </div>
            </div>
            <Stars value={r.rating} />
          </div>
          {r.comment && <p>{r.comment}</p>}
        </article>
      ))}
    </div>
  );
}
