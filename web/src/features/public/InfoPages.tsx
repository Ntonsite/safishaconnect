import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Mail, MapPin, MessageCircle, Phone, SearchX } from "lucide-react";
import { publicApi } from "../../api/endpoints";
import type { Service } from "../../api/types";
import { useBrand } from "../../config/brand";
import { ButtonLink } from "../../shared/components/Button";
import { ServiceIcon } from "../../shared/components/Brand";
import { EmptyState, ErrorState, SkeletonCard } from "../../shared/components/Feedback";
import { useFormat } from "../../shared/hooks/useFormat";
import { HowSteps } from "./LandingPage";

function PageHero({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <section className="page-hero">
      <div className="container">
        <h1 className="display">{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </section>
  );
}

export function ServicesPage() {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  return (
    <>
      <PageHero title={t("servicesPage.title")} subtitle={t("servicesPage.subtitle")} />
      <section className="page-section">
        <div className="container stack-lg">
          {isLoading && <SkeletonCard lines={4} />}
          {error && <ErrorState error={error} onRetry={() => refetch()} />}
          {data?.map((s) => <ServiceDetailCard key={s.id} service={s} />)}
        </div>
      </section>
    </>
  );
}

function ServiceDetailCard({ service: s }: { service: Service }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const sizes = s.options.filter((o) => o.group === "SIZE");
  const addons = s.options.filter((o) => o.group === "ADDON");
  return (
    <article className="card" id={s.slug}>
      <div className="split" style={{ gap: "var(--s-8)", alignItems: "start" }}>
        <div className="stack">
          <div className="row">
            <ServiceIcon name={s.icon} />
            <h2>{fmt.pick(s, "name")}</h2>
          </div>
          <p style={{ color: "var(--ink-2)" }}>{fmt.pick(s, "description")}</p>
          <div className="row small muted">
            <Clock size={16} aria-hidden /> {t("servicesPage.duration")}: {fmt.duration(s.base_duration_minutes)}+
          </div>
          <div>
            <ButtonLink to={`/app/book?service=${s.slug}`}>{t("servicesPage.bookThis")}</ButtonLink>
          </div>
        </div>
        <div className="stack">
          <div className="section-label">{t("servicesPage.pricing")}</div>
          <div className="price-lines">
            <div className="price-line">
              <span>{t("servicesPage.basePrice")}</span>
              <span className="strong">{fmt.money(s.base_price)}</span>
            </div>
            {s.uses_rooms && (
              <>
                <div className="price-line small muted">
                  <span>{t("servicesPage.includes", { bedrooms: s.included_bedrooms, bathrooms: s.included_bathrooms })}</span>
                </div>
                <div className="price-line">
                  <span>{t("servicesPage.extraBedroom")}</span>
                  <span>+{fmt.money(s.price_per_extra_bedroom)}</span>
                </div>
                <div className="price-line">
                  <span>{t("servicesPage.extraBathroom")}</span>
                  <span>+{fmt.money(s.price_per_extra_bathroom)}</span>
                </div>
              </>
            )}
            {sizes.map((o) => (
              <div className="price-line" key={o.id}>
                <span>{fmt.pick(o, "name")}</span>
                <span>{Number(o.price_amount) ? `+${fmt.money(o.price_amount)}` : t("common.none")}</span>
              </div>
            ))}
          </div>
          {addons.length > 0 && (
            <>
              <div className="section-label" style={{ marginTop: "var(--s-2)" }}>
                {t("servicesPage.extras")}
              </div>
              <div className="price-lines">
                {addons.map((o) => (
                  <div className="price-line" key={o.id}>
                    <span>{fmt.pick(o, "name")}</span>
                    <span>+{fmt.money(o.price_amount)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </article>
  );
}

export function HowItWorksPage() {
  const { t } = useTranslation();
  const after = t("howPage.after", { returnObjects: true }) as string[];
  return (
    <>
      <PageHero title={t("howPage.title")} subtitle={t("howPage.subtitle")} />
      <section className="page-section">
        <div className="container stack-lg">
          <HowSteps />
          <div className="card" style={{ marginTop: "var(--s-8)" }}>
            <h2 style={{ marginBottom: "var(--s-5)" }}>{t("howPage.afterTitle")}</h2>
            <ol className="timeline">
              {after.map((line) => (
                <li key={line}>
                  <span className="timeline-dot">
                    <CheckCircle2 />
                  </span>
                  <p style={{ paddingTop: 2 }}>{line}</p>
                </li>
              ))}
            </ol>
          </div>
          <div>
            <ButtonLink to="/app/book" size="lg">
              {t("nav.bookCleaning")}
            </ButtonLink>
          </div>
        </div>
      </section>
    </>
  );
}

export function HelpPage() {
  const { t } = useTranslation();
  const brand = useBrand();
  const whatsapp = brand.support_whatsapp.replace(/[^\d]/g, "");
  const items = [
    { icon: Phone, label: t("helpPage.callUs"), value: brand.support_phone, href: `tel:${brand.support_phone.replace(/\s/g, "")}` },
    { icon: MessageCircle, label: t("helpPage.whatsapp"), value: brand.support_whatsapp, href: `https://wa.me/${whatsapp}` },
    { icon: Mail, label: t("helpPage.emailUs"), value: brand.support_email, href: `mailto:${brand.support_email}` },
    { icon: MapPin, label: t("helpPage.office"), value: brand.office_address },
  ];
  return (
    <>
      <PageHero title={t("helpPage.title")} subtitle={t("helpPage.subtitle")} />
      <section className="page-section">
        <div className="container stack-lg">
          <div className="grid-2">
            {items.map(({ icon: Icon, label, value, href }) => (
              <div className="card feature" key={label}>
                <span className="feature-icon">
                  <Icon aria-hidden />
                </span>
                <div>
                  <h3>{label}</h3>
                  {href ? (
                    <a href={href} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
                      {value}
                    </a>
                  ) : (
                    <p>{value}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
          <p className="muted">{t("helpPage.hours")}</p>
          <div className="cta-band">
            <div>
              <h2>{t("helpPage.issueTitle")}</h2>
              <p>{t("helpPage.issueBody")}</p>
            </div>
            <ButtonLink to="/app/bookings" variant="secondary">
              {t("nav.myBookings")}
            </ButtonLink>
          </div>
        </div>
      </section>
    </>
  );
}

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="container" style={{ padding: "var(--s-20) 0" }}>
      <EmptyState icon={SearchX} title={t("common.notFound")} action={<ButtonLink to="/">{t("common.goHome")}</ButtonLink>} />
    </div>
  );
}
