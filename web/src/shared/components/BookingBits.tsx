import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Check, ChevronRight } from "lucide-react";
import clsx from "clsx";
import type { BookingDetail, BookingStatus, BookingSummary, QuoteLine } from "../../api/types";
import { useFormat } from "../hooks/useFormat";
import { ServiceIcon } from "./Brand";
import { BookingStatusBadge } from "./StatusBadge";

export function BookingRow({ booking, to, showCustomer }: { booking: BookingSummary; to: string; showCustomer?: boolean }) {
  const fmt = useFormat();
  return (
    <Link to={to} className="booking-row">
      <ServiceIcon name={booking.service.icon} />
      <div className="grow">
        <div className="strong">{fmt.pick(booking.service, "name")}</div>
        <div className="small muted">
          {fmt.date(booking.scheduled_date)} · {fmt.time(booking.scheduled_start_time)} · {booking.area_name}
          {showCustomer && booking.customer_name ? ` · ${booking.customer_name}` : ""}
        </div>
        <div className="tiny muted num">{booking.reference}</div>
      </div>
      <div className="booking-row-end">
        <BookingStatusBadge status={booking.status} />
        <span className="row strong num" style={{ gap: 4 }}>
          {fmt.money(booking.total_amount, booking.currency)}
          <ChevronRight size={16} className="muted" aria-hidden />
        </span>
      </div>
    </Link>
  );
}

const PROGRESS: BookingStatus[] = [
  "CONFIRMED",
  "PROVIDER_ASSIGNED",
  "PROVIDER_EN_ROUTE",
  "PROVIDER_ARRIVED",
  "SERVICE_IN_PROGRESS",
  "COMPLETED_BY_PROVIDER",
  "CLOSED",
];

/** Where each status sits on the journey; the step at that index shows the live status label. */
const POSITION: Partial<Record<BookingStatus, number>> = {
  PENDING_CONFIRMATION: 0,
  CONFIRMED: 1,
  FINDING_PROVIDER: 1,
  REASSIGNMENT_REQUIRED: 1,
  PROVIDER_ASSIGNED: 1,
  PROVIDER_EN_ROUTE: 2,
  PROVIDER_ARRIVED: 3,
  SERVICE_IN_PROGRESS: 4,
  COMPLETED_BY_PROVIDER: 5,
  DISPUTED: 5,
  CUSTOMER_CONFIRMED: 6,
  CLOSED: 6,
};

/** Customer-friendly progress: the canonical journey with timestamps from the real history. */
export function ProgressTimeline({ booking }: { booking: BookingDetail }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const position = POSITION[booking.status] ?? 0;
  const when = (status: BookingStatus) => {
    const events = booking.history.filter((h) => h.to_status === status);
    return events.length ? fmt.dateTime(events[events.length - 1].created_at) : null;
  };

  if (booking.status === "CANCELLED") {
    return (
      <ol className="timeline">
        <li className="is-alert">
          <span className="timeline-dot">
            <AlertTriangle />
          </span>
          <div>
            <div className="timeline-title">{t("status.booking.CANCELLED")}</div>
            <div className="timeline-meta">
              {booking.cancelled_at && fmt.dateTime(booking.cancelled_at)}
              {booking.cancellation_reason && ` · ${booking.cancellation_reason}`}
            </div>
          </div>
        </li>
      </ol>
    );
  }

  return (
    <ol className="timeline">
      {PROGRESS.map((status, i) => {
        const done = i < position || (i === position && booking.status === "CLOSED");
        const current = i === position && !done;
        const alert = current && (booking.status === "DISPUTED" || booking.status === "REASSIGNMENT_REQUIRED");
        // The current step shows the booking's live status (e.g. "Finding a cleaner", "Issue under review").
        const label = current ? t(`status.booking.${booking.status}`) : t(`status.timeline.${status}`);
        const stamp = current ? when(booking.status) : when(status);
        return (
          <li key={status} className={clsx(!done && !current && "is-pending", current && "is-current", alert && "is-alert")}>
            <span className="timeline-dot">{done && <Check strokeWidth={3} />}</span>
            <div>
              <div className="timeline-title">{label}</div>
              {(done || current) && stamp && <div className="timeline-meta">{stamp}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function PriceBreakdown({ lines, total, currency }: { lines: QuoteLine[]; total: string; currency: string }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  return (
    <div className="price-lines">
      {lines.map((line, i) => (
        <div className="price-line" key={`${line.code}-${i}`}>
          <span>
            {fmt.pick(line, "label")}
            {line.quantity > 1 && <span className="muted"> × {line.quantity}</span>}
          </span>
          <span>{fmt.money(line.amount, currency)}</span>
        </div>
      ))}
      <div className="price-total">
        <span>{t("common.total")}</span>
        <span className="num">{fmt.money(total, currency)}</span>
      </div>
    </div>
  );
}
