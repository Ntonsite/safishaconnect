import { useTranslation } from "react-i18next";
import clsx from "clsx";
import type {
  AssignmentStatus,
  BookingStatus,
  ComplaintStatus,
  PaymentStatus,
  SettlementStatus,
  VerificationStatus,
} from "../../api/types";

type Tone = "green" | "amber" | "red" | "teal" | "slate";

const BOOKING_TONES: Record<BookingStatus, Tone> = {
  PENDING_CONFIRMATION: "slate",
  CONFIRMED: "teal",
  FINDING_PROVIDER: "amber",
  REASSIGNMENT_REQUIRED: "amber",
  PROVIDER_ASSIGNED: "teal",
  PROVIDER_EN_ROUTE: "teal",
  PROVIDER_ARRIVED: "teal",
  SERVICE_IN_PROGRESS: "green",
  COMPLETED_BY_PROVIDER: "green",
  CUSTOMER_CONFIRMED: "green",
  CLOSED: "slate",
  CANCELLED: "red",
  DISPUTED: "red",
};

const PAYMENT_TONES: Record<PaymentStatus, Tone> = {
  PENDING: "amber",
  PAID: "green",
  FAILED: "red",
  REFUNDED: "slate",
  CANCELLED: "slate",
};

const ASSIGNMENT_TONES: Record<AssignmentStatus, Tone> = {
  OFFERED: "amber",
  ACCEPTED: "green",
  REJECTED: "red",
  EXPIRED: "slate",
  CANCELLED: "slate",
  WITHDRAWN: "slate",
};

const VERIFICATION_TONES: Record<VerificationStatus, Tone> = {
  PENDING: "amber",
  VERIFIED: "green",
  REJECTED: "red",
  SUSPENDED: "red",
};

const COMPLAINT_TONES: Record<ComplaintStatus, Tone> = { OPEN: "red", IN_REVIEW: "amber", RESOLVED: "green", REJECTED: "slate" };
const SETTLEMENT_TONES: Record<SettlementStatus, Tone> = { PENDING: "amber", SETTLED: "green" };

export function Badge({ tone = "slate", children, dot }: { tone?: Tone; children: React.ReactNode; dot?: boolean }) {
  return <span className={clsx("badge", `tone-${tone}`, dot && "badge-dot")}>{children}</span>;
}

export function BookingStatusBadge({ status, admin }: { status: BookingStatus; admin?: boolean }) {
  const { t, i18n } = useTranslation();
  const adminKey = `status.adminBooking.${status}`;
  const label = admin && i18n.exists(adminKey) ? t(adminKey) : t(`status.booking.${status}`);
  return (
    <Badge tone={BOOKING_TONES[status]} dot>
      {label}
    </Badge>
  );
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const { t } = useTranslation();
  return <Badge tone={PAYMENT_TONES[status]}>{t(`status.payment.${status}`)}</Badge>;
}

export function AssignmentStatusBadge({ status }: { status: AssignmentStatus }) {
  const { t } = useTranslation();
  return <Badge tone={ASSIGNMENT_TONES[status]}>{t(`status.assignment.${status}`)}</Badge>;
}

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const { t } = useTranslation();
  return (
    <Badge tone={VERIFICATION_TONES[status]} dot>
      {t(`status.verification.${status}`)}
    </Badge>
  );
}

export function ComplaintStatusBadge({ status }: { status: ComplaintStatus }) {
  const { t } = useTranslation();
  return <Badge tone={COMPLAINT_TONES[status]}>{t(`status.complaint.${status}`)}</Badge>;
}

export function SettlementBadge({ status }: { status: SettlementStatus }) {
  const { t } = useTranslation();
  return <Badge tone={SETTLEMENT_TONES[status]}>{t(`status.settlement.${status}`)}</Badge>;
}
