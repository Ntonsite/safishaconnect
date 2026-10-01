import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { Banknote, CalendarDays, Clock, CreditCard, MapPin, ShieldCheck, Smartphone, SprayCan } from "lucide-react";
import clsx from "clsx";
import { customerApi, publicApi } from "../../api/endpoints";
import type { PaymentMethod, QuoteRequest, Service } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { useConfig } from "../../config/brand";
import { PriceBreakdown } from "../../shared/components/BookingBits";
import { ServiceIcon } from "../../shared/components/Brand";
import { Button } from "../../shared/components/Button";
import { ChoiceCard, Counter, PageHeader } from "../../shared/components/Controls";
import { Alert, ErrorState, PageLoader, Skeleton } from "../../shared/components/Feedback";
import { Field, Input, Select, Textarea } from "../../shared/components/Field";
import { useToast } from "../../shared/components/Toast";
import { useErrorMessage } from "../../shared/hooks/useErrorMessage";
import { useFormat } from "../../shared/hooks/useFormat";
import { addMinutesToTime, toISODate } from "../../shared/utils/format";

type Step = 0 | 1 | 2 | 3 | 4;
const STEP_KEYS = ["service", "details", "location", "schedule", "review"] as const;
const PAYMENT_ICONS = { CASH: Banknote, MOBILE_MONEY: Smartphone, CARD: CreditCard };

function upcomingDays(count: number): Date[] {
  const today = new Date();
  return Array.from({ length: count }, (_, i) => new Date(today.getFullYear(), today.getMonth(), today.getDate() + i));
}

export function NewBookingPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const navigate = useNavigate();
  const toast = useToast();
  const toMessage = useErrorMessage();
  const { user } = useAuth();
  const config = useConfig();
  const [params] = useSearchParams();

  const services = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  const areas = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas });

  const [step, setStep] = useState<Step>(0);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [propertyTypeId, setPropertyTypeId] = useState<string | null>(null);
  const [sizeId, setSizeId] = useState<string | null>(null);
  const [bedrooms, setBedrooms] = useState(2);
  const [bathrooms, setBathrooms] = useState(1);
  const [addons, setAddons] = useState<Record<string, number>>({});
  const [areaId, setAreaId] = useState(user?.default_area_id ?? "");
  const [address, setAddress] = useState(user?.default_address ?? "");
  const [landmark, setLandmark] = useState("");
  const [instructions, setInstructions] = useState("");
  const [date, setDate] = useState(() => toISODate(upcomingDays(2)[1]));
  const [startTime, setStartTime] = useState<string | null>(null);
  const [payment, setPayment] = useState<PaymentMethod>("CASH");
  const [touched, setTouched] = useState(false);

  const service: Service | undefined = services.data?.find((s) => s.id === serviceId);

  const chooseService = (s: Service, advance = true) => {
    setServiceId(s.id);
    setPropertyTypeId(s.options.find((o) => o.group === "PROPERTY_TYPE")?.id ?? null);
    setSizeId(s.options.find((o) => o.group === "SIZE")?.id ?? null);
    setBedrooms(Math.max(s.included_bedrooms, 1));
    setBathrooms(Math.max(s.included_bathrooms, 1));
    setAddons({});
    setStartTime(null);
    if (advance) setStep(1);
  };

  // Deep link: /app/book?service=deep-cleaning
  const preselect = params.get("service");
  useEffect(() => {
    if (!preselect || serviceId || !services.data) return;
    const match = services.data.find((s) => s.slug === preselect);
    if (match) chooseService(match);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preselect, services.data]);

  const quoteRequest: QuoteRequest | null = service
    ? {
        service_id: service.id,
        property_type_option_id: propertyTypeId,
        size_option_id: sizeId,
        bedrooms: service.uses_rooms ? bedrooms : 0,
        bathrooms: service.uses_rooms ? bathrooms : 0,
        addons: Object.entries(addons)
          .filter(([, q]) => q > 0)
          .map(([option_id, quantity]) => ({ option_id, quantity })),
      }
    : null;

  const quote = useQuery({
    queryKey: ["quote", quoteRequest],
    queryFn: () => publicApi.quote(quoteRequest!),
    enabled: !!quoteRequest,
    placeholderData: keepPreviousData,
  });
  const duration = quote.data?.estimated_duration_minutes;

  const availability = useQuery({
    queryKey: ["availability", serviceId, areaId, date, duration],
    queryFn: () => publicApi.availability({ service_id: serviceId!, area_id: areaId, date, duration_minutes: duration! }),
    enabled: step >= 3 && !!serviceId && !!areaId && !!duration,
  });

  // Drop a chosen time that is no longer available after inputs change.
  useEffect(() => {
    if (!startTime || !availability.data) return;
    const slot = availability.data.slots.find((s) => s.start_time.startsWith(startTime));
    if (!slot?.available) setStartTime(null);
  }, [availability.data, startTime]);

  const create = useMutation({
    mutationFn: () =>
      customerApi.createBooking({
        ...quoteRequest!,
        area_id: areaId,
        address_line: address.trim(),
        landmark: landmark.trim() || null,
        special_instructions: instructions.trim() || null,
        scheduled_date: date,
        scheduled_start_time: startTime!,
        payment_method: payment,
      }),
    onSuccess: (booking) => navigate(`/app/bookings/${booking.id}?new=1`, { replace: true }),
    onError: (e) => toast.error(e),
  });

  const area = areas.data?.find((a) => a.id === areaId);
  const days = useMemo(() => upcomingDays(14), []);

  const stepValid = (s: Step): boolean => {
    if (s === 0) return !!service;
    if (s === 1) return !!quote.data && !quote.isError;
    if (s === 2) return !!areaId && address.trim().length >= 3;
    if (s === 3) return !!startTime;
    return true;
  };

  const next = () => {
    setTouched(true);
    if (!stepValid(step)) return;
    setTouched(false);
    if (step < 4) setStep((step + 1) as Step);
    else create.mutate();
  };

  if (services.isLoading || areas.isLoading) return <PageLoader />;
  if (services.error) return <ErrorState error={services.error} onRetry={() => services.refetch()} />;

  const propertyTypes = service?.options.filter((o) => o.group === "PROPERTY_TYPE") ?? [];
  const sizes = service?.options.filter((o) => o.group === "SIZE") ?? [];
  const addonOptions = service?.options.filter((o) => o.group === "ADDON") ?? [];

  return (
    <>
      <PageHeader title={t("booking.title")} />
      <ol className="steps" style={{ marginBottom: "var(--s-6)" }} aria-label={t("booking.title")}>
        {STEP_KEYS.map((key, i) => (
          <li key={key} className={clsx(i < step && "is-done", i === step && "is-current")} aria-current={i === step ? "step" : undefined}>
            <span>{t(`booking.steps.${key}`)}</span>
          </li>
        ))}
      </ol>

      <div className="detail-grid">
        <div className="stack-lg">
          {step === 0 && (
            <section className="stack">
              <h2>{t("booking.chooseService")}</h2>
              <div className="stack-sm">
                {services.data?.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className={clsx("choice", serviceId === s.id && "is-selected")}
                    aria-pressed={serviceId === s.id}
                    onClick={() => chooseService(s)}
                    style={{ flexDirection: "row", alignItems: "center", gap: "var(--s-4)" }}
                  >
                    <ServiceIcon name={s.icon} />
                    <span className="grow stack-sm" style={{ gap: 2 }}>
                      <span className="choice-title">{fmt.pick(s, "name")}</span>
                      <span className="choice-meta">{fmt.pick(s, "summary")}</span>
                    </span>
                    <span className="small strong nowrap">{t("landing.fromPrice", { price: fmt.money(s.base_price) })}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {step === 1 && service && (
            <section className="card stack-lg">
              <div className="row">
                <ServiceIcon name={service.icon} />
                <div>
                  <h2>{fmt.pick(service, "name")}</h2>
                  <button type="button" className="btn btn-ghost btn-sm" style={{ paddingLeft: 0 }} onClick={() => setStep(0)}>
                    {t("common.edit")}
                  </button>
                </div>
              </div>
              {propertyTypes.length > 0 && (
                <div className="stack-sm">
                  <span className="field-label">{t("booking.propertyType")}</span>
                  <div className="choice-grid" role="radiogroup">
                    {propertyTypes.map((o) => (
                      <ChoiceCard
                        key={o.id}
                        selected={propertyTypeId === o.id}
                        onClick={() => setPropertyTypeId(o.id)}
                        title={fmt.pick(o, "name")}
                        meta={Number(o.price_amount) ? `+${fmt.money(o.price_amount)}` : undefined}
                      />
                    ))}
                  </div>
                </div>
              )}
              {sizes.length > 0 && (
                <div className="stack-sm">
                  <span className="field-label">{t("booking.size")}</span>
                  <div className="choice-grid" role="radiogroup">
                    {sizes.map((o) => (
                      <ChoiceCard
                        key={o.id}
                        selected={sizeId === o.id}
                        onClick={() => setSizeId(o.id)}
                        title={fmt.pick(o, "name")}
                        meta={Number(o.price_amount) ? `+${fmt.money(o.price_amount)}` : undefined}
                      />
                    ))}
                  </div>
                </div>
              )}
              {service.uses_rooms && (
                <div className="row wrap" style={{ gap: "var(--s-8)" }}>
                  <div className="field">
                    <span className="field-label">{t("booking.bedrooms")}</span>
                    <Counter value={bedrooms} min={0} max={service.max_rooms} onChange={setBedrooms} label={t("booking.bedrooms")} />
                  </div>
                  <div className="field">
                    <span className="field-label">{t("booking.bathrooms")}</span>
                    <Counter value={bathrooms} min={1} max={service.max_rooms} onChange={setBathrooms} label={t("booking.bathrooms")} />
                  </div>
                </div>
              )}
              {addonOptions.length > 0 && (
                <div className="stack-sm">
                  <span className="field-label">
                    {t("booking.addons")} <span className="muted">({t("booking.addonsHint")})</span>
                  </span>
                  <div className="stack-sm">
                    {addonOptions.map((o) => {
                      const qty = addons[o.id] ?? 0;
                      return (
                        <div key={o.id} className={clsx("choice", qty > 0 && "is-selected")} style={{ flexDirection: "row", alignItems: "center", cursor: "default" }}>
                          <div className="grow">
                            <div className="choice-title">{fmt.pick(o, "name")}</div>
                            <div className="choice-meta">
                              +{fmt.money(o.price_amount)}
                              {o.max_quantity > 1 && ` ${t("common.each")}`}
                            </div>
                          </div>
                          {o.max_quantity > 1 ? (
                            <Counter
                              value={qty}
                              min={0}
                              max={o.max_quantity}
                              label={fmt.pick(o, "name")}
                              onChange={(v) => setAddons((a) => ({ ...a, [o.id]: v }))}
                            />
                          ) : (
                            <input
                              type="checkbox"
                              className="checkbox"
                              style={{ width: 22, height: 22, accentColor: "var(--green-700)" }}
                              checked={qty > 0}
                              aria-label={fmt.pick(o, "name")}
                              onChange={(e) => setAddons((a) => ({ ...a, [o.id]: e.target.checked ? 1 : 0 }))}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {quote.error && <Alert tone="danger">{toMessage(quote.error)}</Alert>}
            </section>
          )}

          {step === 2 && (
            <section className="card stack">
              <h2>{t("booking.steps.location")}</h2>
              <Field label={t("booking.areaLabel")} error={touched && !areaId ? t("validation.chooseOne") : undefined}>
                <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
                  <option value="">{t("booking.areaPlaceholder")}</option>
                  {areas.data?.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}, {a.city_name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field
                label={t("booking.address")}
                error={touched && address.trim().length < 3 ? t("validation.required") : undefined}
              >
                <Input value={address} placeholder={t("booking.addressPlaceholder")} maxLength={255} onChange={(e) => setAddress(e.target.value)} />
              </Field>
              <Field label={t("booking.landmark")} optional={t("common.optional")}>
                <Input value={landmark} placeholder={t("booking.landmarkPlaceholder")} maxLength={255} onChange={(e) => setLandmark(e.target.value)} />
              </Field>
              <Field label={t("booking.specialInstructions")} optional={t("common.optional")}>
                <Textarea
                  value={instructions}
                  placeholder={t("booking.specialPlaceholder")}
                  maxLength={1000}
                  onChange={(e) => setInstructions(e.target.value)}
                />
              </Field>
            </section>
          )}

          {step === 3 && (
            <section className="card stack-lg">
              <div className="stack-sm">
                <span className="field-label">{t("booking.dateLabel")}</span>
                <div className="row" style={{ overflowX: "auto", paddingBottom: 4, gap: 8 }}>
                  {days.map((d) => {
                    const iso = toISODate(d);
                    const selected = iso === date;
                    return (
                      <button
                        key={iso}
                        type="button"
                        className={clsx("choice", selected && "is-selected")}
                        aria-pressed={selected}
                        onClick={() => {
                          setDate(iso);
                          setStartTime(null);
                        }}
                        style={{ minWidth: 72, alignItems: "center", padding: "10px 8px", flexShrink: 0 }}
                      >
                        <span className="tiny muted">{d.toLocaleDateString(fmt.locale === "sw" ? "sw-TZ" : "en-GB", { weekday: "short" })}</span>
                        <span className="strong" style={{ fontSize: "var(--text-lg)" }}>
                          {d.getDate()}
                        </span>
                        <span className="tiny muted">{d.toLocaleDateString(fmt.locale === "sw" ? "sw-TZ" : "en-GB", { month: "short" })}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="stack-sm">
                <span className="field-label">{t("booking.timeLabel")}</span>
                {availability.isLoading && (
                  <div className="choice-grid">
                    {Array.from({ length: 6 }, (_, i) => (
                      <Skeleton key={i} height={52} />
                    ))}
                  </div>
                )}
                {availability.data && !availability.data.slots.some((s) => s.available) && (
                  <Alert tone="warning">{t("booking.noSlots")}</Alert>
                )}
                {availability.data && (
                  <div className="choice-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))" }} role="radiogroup">
                    {availability.data.slots.map((slot) => {
                      const value = slot.start_time.slice(0, 5);
                      return (
                        <ChoiceCard
                          key={value}
                          selected={startTime === value}
                          disabled={!slot.available}
                          onClick={() => setStartTime(value)}
                          title={value}
                          meta={slot.available ? `– ${slot.end_time.slice(0, 5)}` : t("booking.slotTaken")}
                        />
                      );
                    })}
                  </div>
                )}
                {touched && !startTime && <span className="field-error">{t("validation.chooseOne")}</span>}
              </div>
            </section>
          )}

          {step === 4 && (
            <section className="card stack-lg">
              <div className="stack-sm">
                <h2>{t("booking.paymentMethod")}</h2>
                <div className="stack-sm" role="radiogroup">
                  {config.payment_methods.map((m) => {
                    const Icon = PAYMENT_ICONS[m.method];
                    return (
                      <ChoiceCard
                        key={m.method}
                        selected={payment === m.method}
                        disabled={!m.available}
                        onClick={() => setPayment(m.method)}
                        title={
                          <span className="row" style={{ gap: 10 }}>
                            <Icon size={18} aria-hidden /> {t(`booking.methods.${m.method}`)}
                            {!m.available && <span className="badge tone-slate">{t("common.comingSoon")}</span>}
                          </span>
                        }
                        meta={t(`booking.methodHints.${m.method}`)}
                      />
                    );
                  })}
                </div>
              </div>
              <Alert tone="success">
                <span className="row" style={{ gap: 8 }}>
                  <SprayCan size={16} aria-hidden /> {t("booking.materialsIncluded")}
                </span>
              </Alert>
            </section>
          )}

          <div className="row-between">
            {step > 0 ? (
              <Button variant="secondary" onClick={() => setStep((step - 1) as Step)}>
                {t("common.back")}
              </Button>
            ) : (
              <span />
            )}
            {step > 0 && (
              <Button size="lg" onClick={next} loading={create.isPending} disabled={step === 1 && quote.isFetching && !quote.data}>
                {step === 4
                  ? t("booking.confirmButton", { price: fmt.money(quote.data?.total_amount) })
                  : t("common.next")}
              </Button>
            )}
          </div>
        </div>

        <aside className="detail-aside">
          <div className="card stack">
            <div className="card-title">{t("booking.summary")}</div>
            {!service && <p className="muted small">{t("booking.chooseService")}</p>}
            {service && (
              <>
                <div className="row">
                  <ServiceIcon name={service.icon} />
                  <div className="grow">
                    <div className="strong">{fmt.pick(service, "name")}</div>
                    {service.uses_rooms && (
                      <div className="small muted">{t("customer.rooms", { bedrooms, bathrooms })}</div>
                    )}
                  </div>
                </div>
                <dl className="dl">
                  {area && (
                    <>
                      <dt>
                        <MapPin size={14} aria-hidden style={{ display: "inline", verticalAlign: -2 }} /> {t("booking.where")}
                      </dt>
                      <dd>{area.name}</dd>
                    </>
                  )}
                  {step >= 3 && (
                    <>
                      <dt>
                        <CalendarDays size={14} aria-hidden style={{ display: "inline", verticalAlign: -2 }} /> {t("booking.when")}
                      </dt>
                      <dd>
                        {fmt.date(date)}
                        {startTime && duration && ` · ${startTime}–${addMinutesToTime(startTime, duration)}`}
                      </dd>
                    </>
                  )}
                  {duration && (
                    <>
                      <dt>
                        <Clock size={14} aria-hidden style={{ display: "inline", verticalAlign: -2 }} /> {t("booking.estimatedDuration")}
                      </dt>
                      <dd>{fmt.duration(duration)}</dd>
                    </>
                  )}
                </dl>
                <hr className="divider" style={{ margin: 0 }} />
                {quote.isLoading && <p className="muted small">{t("booking.calculating")}</p>}
                {quote.data && (
                  <div style={{ opacity: quote.isFetching ? 0.6 : 1, transition: "opacity .15s" }}>
                    <PriceBreakdown lines={quote.data.lines} total={quote.data.total_amount} currency={quote.data.currency} />
                  </div>
                )}
                <p className="small muted row" style={{ gap: 6, alignItems: "flex-start" }}>
                  <ShieldCheck size={16} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} /> {t("booking.priceNote")}
                </p>
              </>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
