import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CalendarDays, ChevronRight, Clock, MapPin, Timer } from "lucide-react";
import type { Job } from "../../api/types";
import { ServiceIcon } from "../../shared/components/Brand";
import { BookingStatusBadge } from "../../shared/components/StatusBadge";
import { useFormat } from "../../shared/hooks/useFormat";
import { addMinutesToTime } from "../../shared/utils/format";

export function useCountdown(expiresAt: string | null): string | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!expiresAt) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [expiresAt]);
  if (!expiresAt) return null;
  const ms = new Date(expiresAt).getTime() - now;
  if (ms <= 0) return null;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/** Summary of a job for provider lists. Offers show earnings and the response deadline. */
export function JobCard({ job, children }: { job: Job; children?: React.ReactNode }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const b = job.booking;
  const isOffer = job.assignment_status === "OFFERED";
  const countdown = useCountdown(isOffer ? job.expires_at : null);

  return (
    <article className="card stack">
      <Link to={`/provider/jobs/${b.id}`} className="row" style={{ color: "inherit", alignItems: "flex-start" }}>
        <ServiceIcon name={b.service.icon} />
        <div className="grow stack-sm" style={{ gap: 4 }}>
          <div className="row-between" style={{ alignItems: "flex-start" }}>
            <div className="strong">{fmt.pick(b.service, "name")}</div>
            {isOffer ? (
              countdown ? (
                <span className="badge tone-amber">
                  <Timer size={12} aria-hidden /> {t("provider.respondBy", { time: countdown })}
                </span>
              ) : (
                <span className="badge tone-slate">{t("provider.expired")}</span>
              )
            ) : (
              <BookingStatusBadge status={b.status} />
            )}
          </div>
          <div className="small muted row wrap" style={{ gap: "4px 14px" }}>
            <span className="row" style={{ gap: 4 }}>
              <CalendarDays size={14} aria-hidden /> {fmt.date(b.scheduled_date)}
            </span>
            <span className="row" style={{ gap: 4 }}>
              <Clock size={14} aria-hidden /> {fmt.time(b.scheduled_start_time)}–
              {addMinutesToTime(b.scheduled_start_time, b.estimated_duration_minutes)}
            </span>
            <span className="row" style={{ gap: 4 }}>
              <MapPin size={14} aria-hidden /> {b.area_name}
            </span>
          </div>
          {b.bathrooms > 0 && (
            <div className="small muted">
              {b.property_type && `${fmt.pick(b.property_type, "name")} · `}
              {t("customer.rooms", { bedrooms: b.bedrooms, bathrooms: b.bathrooms })}
            </div>
          )}
        </div>
        <ChevronRight size={18} className="muted" aria-hidden />
      </Link>
      <div className="row-between" style={{ paddingTop: 12, borderTop: "1px solid var(--line)" }}>
        <span className="small muted">{t("provider.youEarn")}</span>
        <span className="strong num" style={{ fontSize: "var(--text-lg)", color: "var(--green-800)" }}>
          {fmt.money(b.provider_earning, b.currency)}
        </span>
      </div>
      {children}
    </article>
  );
}
