import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, MessageSquareWarning, Phone, Search, ShieldCheck } from "lucide-react";
import { customerApi } from "../../api/endpoints";
import type { BookingDetail, ComplaintCategory } from "../../api/types";
import { useBrand } from "../../config/brand";
import { PriceBreakdown, ProgressTimeline } from "../../shared/components/BookingBits";
import { RatingSummary, StarInput, Stars } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/Controls";
import { Alert, ErrorState, PageLoader } from "../../shared/components/Feedback";
import { Field, Select, Textarea } from "../../shared/components/Field";
import { ConfirmDialog, Modal } from "../../shared/components/Modal";
import { BookingStatusBadge, PaymentStatusBadge } from "../../shared/components/StatusBadge";
import { useToast } from "../../shared/components/Toast";
import { useFormat } from "../../shared/hooks/useFormat";
import { addMinutesToTime, initials } from "../../shared/utils/format";

const LIVE = new Set(["FINDING_PROVIDER", "REASSIGNMENT_REQUIRED", "PROVIDER_ASSIGNED", "PROVIDER_EN_ROUTE", "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER", "CUSTOMER_CONFIRMED"]);
const CATEGORIES: ComplaintCategory[] = ["QUALITY", "LATE_OR_NO_SHOW", "DAMAGE", "CONDUCT", "PAYMENT", "OTHER"];

export function BookingDetailPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const { t } = useTranslation();
  const fmt = useFormat();
  const brand = useBrand();
  const toast = useToast();
  const qc = useQueryClient();
  const [cancelOpen, setCancelOpen] = useState(false);
  const [issueOpen, setIssueOpen] = useState(false);

  const query = useQuery({
    queryKey: ["booking", id],
    queryFn: () => customerApi.booking(id),
    refetchInterval: (q) => (q.state.data && LIVE.has(q.state.data.status) ? 15_000 : false),
  });

  const onDone = (b: BookingDetail, message?: string) => {
    qc.setQueryData(["booking", id], b);
    void qc.invalidateQueries({ queryKey: ["bookings"] });
    void qc.invalidateQueries({ queryKey: ["notifications"] });
    if (message) toast.success(message);
  };

  const confirm = useMutation({ mutationFn: () => customerApi.confirm(id), onSuccess: (b) => onDone(b), onError: toast.error });
  const cancel = useMutation({
    mutationFn: (reason?: string) => customerApi.cancel(id, reason),
    onSuccess: (b) => {
      setCancelOpen(false);
      onDone(b);
    },
    onError: toast.error,
  });
  const complete = useMutation({
    mutationFn: () => customerApi.confirmCompletion(id),
    onSuccess: (b) => onDone(b),
    onError: toast.error,
  });

  if (query.isLoading) return <PageLoader />;
  if (query.error || !query.data) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const b = query.data;
  const can = (action: string) => b.allowed_actions.includes(action);
  const isNew = params.get("new") === "1" && (b.status === "FINDING_PROVIDER" || b.status === "REASSIGNMENT_REQUIRED");

  return (
    <div className="stack-lg">
      <PageHeader
        back={{ to: "/app/bookings", label: t("nav.myBookings") }}
        title={fmt.pick(b.service, "name")}
        subtitle={`${b.reference} · ${fmt.dateLong(b.scheduled_date)}`}
        actions={<BookingStatusBadge status={b.status} />}
      />

      {isNew && (
        <Alert tone="success">
          <strong>{t("booking.confirmedTitle")}</strong> — {t("booking.confirmedBody")}
        </Alert>
      )}

      <div className="detail-grid">
        <div className="stack-lg">
          <section className="card stack">
            <div className="row-between wrap">
              <h2 className="card-title">{t("customer.progress")}</h2>
            </div>
            <p className="muted">{t(`status.bookingHelp.${b.status}`, { brand: brand.app_name })}</p>
            <ProgressTimeline booking={b} />
          </section>

          {(can("CONFIRM") || can("CONFIRM_COMPLETION") || can("REVIEW") || b.has_open_complaint) && (
            <section className="card stack">
              {can("CONFIRM") && (
                <Button size="lg" onClick={() => confirm.mutate()} loading={confirm.isPending}>
                  {t("customer.confirmBooking")}
                </Button>
              )}
              {can("CONFIRM_COMPLETION") && (
                <>
                  <p>{t("customer.confirmCompletionBody")}</p>
                  <div className="row wrap">
                    <Button size="lg" icon={<CheckCircle2 />} onClick={() => complete.mutate()} loading={complete.isPending}>
                      {t("customer.confirmCompletion")}
                    </Button>
                    {can("REPORT_ISSUE") && (
                      <Button size="lg" variant="secondary" icon={<MessageSquareWarning />} onClick={() => setIssueOpen(true)}>
                        {t("customer.reportIssue")}
                      </Button>
                    )}
                  </div>
                </>
              )}
              {b.has_open_complaint && <Alert tone="warning">{t("customer.issueOpen")}</Alert>}
              {can("REVIEW") && <ReviewForm bookingId={b.id} onSaved={() => query.refetch()} />}
            </section>
          )}

          {b.review && (
            <section className="card stack-sm">
              <div className="card-title">{t("customer.yourReview")}</div>
              <Stars value={b.review.rating} size={20} />
              {b.review.comment && <p>{b.review.comment}</p>}
            </section>
          )}

          <section className="card stack">
            <h2 className="card-title">{t("customer.bookingDetails")}</h2>
            <dl className="dl">
              <dt>{t("booking.when")}</dt>
              <dd>
                {fmt.dateLong(b.scheduled_date)}, {fmt.time(b.scheduled_start_time)}–
                {addMinutesToTime(b.scheduled_start_time, b.estimated_duration_minutes)}
              </dd>
              <dt>{t("booking.where")}</dt>
              <dd>
                {b.address_line}
                {b.landmark && <div className="small muted">{b.landmark}</div>}
                <div className="small muted">{b.area_name}</div>
              </dd>
              <dt>{t("customer.property")}</dt>
              <dd>
                {[b.property_type && fmt.pick(b.property_type, "name"), b.size && fmt.pick(b.size, "name")]
                  .filter(Boolean)
                  .join(" · ") || fmt.pick(b.service, "name")}
                {b.bathrooms > 0 && <div className="small muted">{t("customer.rooms", { bedrooms: b.bedrooms, bathrooms: b.bathrooms })}</div>}
              </dd>
              {b.special_instructions && (
                <>
                  <dt>{t("customer.instructions")}</dt>
                  <dd>{b.special_instructions}</dd>
                </>
              )}
            </dl>
          </section>
        </div>

        <aside className="detail-aside">
          <section className="card stack">
            <div className="card-title">{t("customer.yourCleaner")}</div>
            {b.provider ? (
              <div className="row">
                <span className="avatar avatar-lg">{initials(b.provider.display_name)}</span>
                <div className="grow stack-sm" style={{ gap: 2 }}>
                  <div className="strong">{b.provider.display_name}</div>
                  <RatingSummary average={b.provider.rating_average} count={b.provider.rating_count} />
                  <div className="small muted row" style={{ gap: 4 }}>
                    <ShieldCheck size={14} aria-hidden /> {t("status.verification.VERIFIED")} ·{" "}
                    {b.provider.provider_type === "COMPANY" ? t("common.company") : t("common.individual")}
                  </div>
                </div>
                {b.provider.phone && (
                  <a className="btn btn-soft btn-sm" href={`tel:${b.provider.phone}`}>
                    <Phone /> {t("customer.callCleaner")}
                  </a>
                )}
              </div>
            ) : (
              <div className="row muted" style={{ alignItems: "flex-start" }}>
                <Search size={20} aria-hidden style={{ flexShrink: 0 }} />
                <p className="small">{t("customer.awaitingCleaner")}</p>
              </div>
            )}
          </section>

          <section className="card stack">
            <div className="card-title">{t("customer.priceBreakdown")}</div>
            <PriceBreakdown lines={b.price_items} total={b.total_amount} currency={b.currency} />
            {b.payment && (
              <div className="row-between" style={{ paddingTop: 8 }}>
                <span className="small muted">
                  {t("customer.payment")}: {t(`booking.methods.${b.payment.method}`)}
                  {b.payment.paid_at && <div>{t("customer.paidOn", { date: fmt.dateTime(b.payment.paid_at) })}</div>}
                </span>
                <PaymentStatusBadge status={b.payment.status} />
              </div>
            )}
          </section>

          {(can("CANCEL") || (can("REPORT_ISSUE") && !can("CONFIRM_COMPLETION"))) && (
            <div className="stack-sm">
              {can("REPORT_ISSUE") && !can("CONFIRM_COMPLETION") && (
                <Button variant="secondary" icon={<MessageSquareWarning />} onClick={() => setIssueOpen(true)}>
                  {t("customer.reportIssue")}
                </Button>
              )}
              {can("CANCEL") && (
                <Button variant="danger" onClick={() => setCancelOpen(true)}>
                  {t("customer.cancelBooking")}
                </Button>
              )}
            </div>
          )}
        </aside>
      </div>

      <ConfirmDialog
        open={cancelOpen}
        title={t("customer.cancelConfirm")}
        description={t("customer.cancelBody")}
        confirmLabel={t("customer.cancelBooking")}
        tone="danger"
        withReason={t("customer.cancelReason")}
        loading={cancel.isPending}
        onConfirm={(reason) => cancel.mutate(reason)}
        onClose={() => setCancelOpen(false)}
      />
      <IssueDialog
        open={issueOpen}
        bookingId={b.id}
        onClose={() => setIssueOpen(false)}
        onSaved={() => {
          setIssueOpen(false);
          void query.refetch();
        }}
      />
    </div>
  );
}

function ReviewForm({ bookingId, onSaved }: { bookingId: string; onSaved: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const save = useMutation({
    mutationFn: () => customerApi.review(bookingId, rating, comment.trim() || undefined),
    onSuccess: () => {
      toast.success(t("customer.reviewThanks"));
      onSaved();
    },
    onError: toast.error,
  });
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (rating) save.mutate();
      }}
    >
      <h3>{t("customer.reviewTitle")}</h3>
      <StarInput value={rating} onChange={setRating} />
      <Field label={t("customer.reviewComment")}>
        <Textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} rows={3} />
      </Field>
      <div>
        <Button type="submit" disabled={!rating} loading={save.isPending}>
          {t("customer.reviewSubmit")}
        </Button>
      </div>
    </form>
  );
}

function IssueDialog({
  open,
  bookingId,
  onClose,
  onSaved,
}: {
  open: boolean;
  bookingId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [category, setCategory] = useState<ComplaintCategory>("QUALITY");
  const [description, setDescription] = useState("");
  const save = useMutation({
    mutationFn: () => customerApi.complain(bookingId, category, description.trim()),
    onSuccess: () => {
      toast.success(t("customer.issueSent"));
      setDescription("");
      onSaved();
    },
    onError: toast.error,
  });
  const tooShort = description.trim().length < 10;
  return (
    <Modal
      open={open}
      title={t("customer.issueTitle")}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={() => save.mutate()} disabled={tooShort} loading={save.isPending}>
            {t("common.submit")}
          </Button>
        </>
      }
    >
      <div className="stack">
        <Field label={t("customer.issueCategory")}>
          <Select value={category} onChange={(e) => setCategory(e.target.value as ComplaintCategory)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`complaintCategory.${c}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("customer.issueDescription")} hint={t("validation.minLength", { count: 10 })}>
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} rows={4} />
        </Field>
      </div>
    </Modal>
  );
}
