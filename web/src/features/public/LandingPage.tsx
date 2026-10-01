import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Banknote,
  Building2,
  CheckCircle2,
  Headset,
  MapPin,
  Plus,
  ShieldCheck,
  SprayCan,
  Tag,
  User,
} from "lucide-react";
import { publicApi } from "../../api/endpoints";
import { useBrand, useConfig } from "../../config/brand";
import { ButtonLink } from "../../shared/components/Button";
import { ServiceIcon, Stars } from "../../shared/components/Brand";
import { Skeleton } from "../../shared/components/Feedback";
import { useFormat } from "../../shared/hooks/useFormat";

export function LandingPage() {
  const { t } = useTranslation();
  const brand = useBrand();
  return (
    <>
      <Hero />
      <PopularServices />
      <section className="section section-alt" aria-labelledby="how-title">
        <div className="container">
          <div className="section-head">
            <h2 id="how-title" className="display">
              {t("landing.howTitle", { brand: brand.app_name })}
            </h2>
            <p>{t("landing.howSubtitle")}</p>
          </div>
          <HowSteps />
        </div>
      </section>
      <TrustSection />
      <ProvidersSection />
      <AreasSection />
      <Testimonials />
      <section className="section-tight">
        <div className="container">
          <div className="cta-band">
            <div>
              <h2 className="display">{t("landing.providerCtaTitle")}</h2>
              <p>{t("landing.providerCtaBody")}</p>
            </div>
            <ButtonLink to="/join" size="lg" icon={<ArrowRight />}>
              {t("landing.providerCtaButton")}
            </ButtonLink>
          </div>
        </div>
      </section>
      <Faq />
    </>
  );
}

function Hero() {
  const { t } = useTranslation();
  const brand = useBrand();
  return (
    <section className="hero">
      <div className="container hero-grid">
        <div>
          <span className="eyebrow">
            <MapPin aria-hidden /> {t("landing.eyebrow")}
          </span>
          <h1 className="display">{t("landing.heroTitle")}</h1>
          <p className="hero-lead">{t("landing.heroSubtitle", { brand: brand.app_name })}</p>
          <div className="hero-ctas">
            <ButtonLink to="/app/book" size="lg" icon={<ArrowRight />}>
              {t("landing.ctaBook")}
            </ButtonLink>
            <ButtonLink to="/join" size="lg" variant="secondary">
              {t("landing.ctaProvider")}
            </ButtonLink>
          </div>
        </div>
        <HeroPanel />
      </div>
    </section>
  );
}

/** What every booking includes, with the real lowest starting price from the catalogue. */
function HeroPanel() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const { data } = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  const items = t("landing.heroPanel.items", { returnObjects: true }) as string[];
  const icons = [ShieldCheck, SprayCan, Tag, Banknote];
  const lowest = data?.length ? Math.min(...data.map((s) => Number(s.base_price))) : null;
  return (
    <aside className="hero-panel" aria-labelledby="hero-panel-title">
      <h2 id="hero-panel-title">{t("landing.heroPanel.title")}</h2>
      <ul>
        {items.map((item, i) => {
          const Icon = icons[i] ?? CheckCircle2;
          return (
            <li key={item}>
              <span className="feature-icon" aria-hidden>
                <Icon />
              </span>
              {item}
            </li>
          );
        })}
      </ul>
      <div className="hero-panel-foot">
        {lowest !== null ? <strong>{t("landing.heroPanel.from", { price: fmt.money(lowest) })}</strong> : <Skeleton width={140} />}
        <Link to="/services" className="row strong" style={{ gap: 6 }}>
          {t("landing.heroPanel.seeServices")} <ArrowRight size={16} aria-hidden />
        </Link>
      </div>
    </aside>
  );
}

function PopularServices() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const { data, isLoading } = useQuery({ queryKey: ["services"], queryFn: publicApi.services });
  return (
    <section className="section" aria-labelledby="services-title">
      <div className="container">
        <div className="row-between wrap" style={{ alignItems: "flex-end", marginBottom: "var(--s-10)" }}>
          <div className="section-head" style={{ marginBottom: 0 }}>
            <h2 id="services-title" className="display">
              {t("landing.servicesTitle")}
            </h2>
            <p>{t("landing.servicesSubtitle")}</p>
          </div>
          <Link to="/services" className="row strong" style={{ gap: 6 }}>
            {t("common.viewAll")} <ArrowRight size={16} />
          </Link>
        </div>
        <div className="grid-3">
          {isLoading &&
            Array.from({ length: 3 }, (_, i) => (
              <div className="card stack" key={i}>
                <Skeleton height={48} width={48} />
                <Skeleton height={20} width="60%" />
                <Skeleton />
              </div>
            ))}
          {data?.slice(0, 6).map((s) => (
            <Link key={s.id} to={`/app/book?service=${s.slug}`} className="card link-card service-card">
              <ServiceIcon name={s.icon} />
              <h3>{fmt.pick(s, "name")}</h3>
              <p>{fmt.pick(s, "summary")}</p>
              <div className="service-card-foot">
                <span>{t("landing.fromPrice", { price: fmt.money(s.base_price) })}</span>
                <ArrowRight aria-hidden />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export function HowSteps() {
  const { t } = useTranslation();
  const steps = ["choose", "schedule", "assign", "relax"] as const;
  return (
    <ol className="how-steps">
      {steps.map((s) => (
        <li key={s}>
          <h3>{t(`landing.steps.${s}.title`)}</h3>
          <p>{t(`landing.steps.${s}.body`)}</p>
        </li>
      ))}
    </ol>
  );
}

function TrustSection() {
  const { t } = useTranslation();
  const brand = useBrand();
  const items = [
    { key: "verified", icon: ShieldCheck },
    { key: "equipment", icon: SprayCan },
    { key: "pricing", icon: Tag },
    { key: "support", icon: Headset },
  ] as const;
  return (
    <section className="section" aria-labelledby="trust-title">
      <div className="container">
        <div className="section-head">
          <h2 id="trust-title" className="display">
            {t("landing.trustTitle", { brand: brand.app_name })}
          </h2>
        </div>
        <div className="grid-2" style={{ gap: "var(--s-8) var(--s-10)" }}>
          {items.map(({ key, icon: Icon }) => (
            <div className="feature" key={key}>
              <span className="feature-icon">
                <Icon aria-hidden />
              </span>
              <div>
                <h3>{t(`landing.trust.${key}.title`)}</h3>
                <p>{t(`landing.trust.${key}.body`)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProvidersSection() {
  const { t } = useTranslation();
  const points = t("landing.providersPoints", { returnObjects: true }) as string[];
  return (
    <section className="section section-alt" aria-labelledby="providers-title">
      <div className="container split">
        <div>
          <h2 id="providers-title" className="display" style={{ fontSize: "clamp(1.6rem, 2.8vw, 2.2rem)" }}>
            {t("landing.providersTitle")}
          </h2>
          <p className="muted" style={{ marginTop: "var(--s-4)", fontSize: "var(--text-lg)" }}>
            {t("landing.providersBody")}
          </p>
          <ul className="check-list">
            {points.map((p) => (
              <li key={p}>
                <CheckCircle2 aria-hidden /> {p}
              </li>
            ))}
          </ul>
        </div>
        <div className="provider-types">
          <div className="provider-type">
            <span className="feature-icon">
              <User aria-hidden />
            </span>
            <div>
              <h3 style={{ fontSize: "var(--text-md)" }}>{t("join.individual")}</h3>
              <p className="muted">{t("join.individualBody")}</p>
            </div>
          </div>
          <div className="provider-type">
            <span className="feature-icon">
              <Building2 aria-hidden />
            </span>
            <div>
              <h3 style={{ fontSize: "var(--text-md)" }}>{t("join.company")}</h3>
              <p className="muted">{t("join.companyBody")}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function AreasSection() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: ["areas"], queryFn: publicApi.areas });
  if (!data?.length) return null;
  return (
    <section className="section" aria-labelledby="areas-title">
      <div className="container">
        <div className="section-head">
          <h2 id="areas-title" className="display">
            {t("landing.areasTitle")}
          </h2>
          <p>{t("landing.areasSubtitle")}</p>
        </div>
        <div className="area-chips">
          {data.map((a) => (
            <span className="chip" key={a.id}>
              <MapPin aria-hidden /> {a.name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Testimonials() {
  const { t } = useTranslation();
  const { demo_mode } = useConfig();
  const { data } = useQuery({ queryKey: ["public-reviews"], queryFn: publicApi.reviews });
  if (!data?.length) return null;
  const uniqueReviews = data.filter((review, index, all) =>
    all.findIndex((candidate) =>
      candidate.customer_first_name === review.customer_first_name &&
      candidate.service_name === review.service_name &&
      candidate.comment === review.comment
    ) === index
  );
  return (
    <section className="section section-alt" aria-labelledby="reviews-title">
      <div className="container">
        <div className="row-between wrap" style={{ marginBottom: "var(--s-8)" }}>
          <h2 id="reviews-title" className="display" style={{ fontSize: "clamp(1.75rem, 3vw, 2.35rem)" }}>
            {t("landing.testimonialsTitle")}
          </h2>
          {demo_mode && <span className="demo-flag">{t("common.demoData")}</span>}
        </div>
        <div className="grid-3">
          {uniqueReviews.slice(0, 3).map((r, i) => (
            <figure className="card quote-card" key={i} style={{ margin: 0 }}>
              <Stars value={r.rating} />
              <blockquote>“{r.comment}”</blockquote>
              <figcaption className="small muted">
                <strong style={{ color: "var(--ink)" }}>{r.customer_first_name}</strong> · {r.area_name} · {r.service_name}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq() {
  const { t } = useTranslation();
  const items = t("landing.faq", { returnObjects: true }) as { q: string; a: string }[];
  return (
    <section className="section" aria-labelledby="faq-title">
      <div className="container">
        <div className="section-head">
          <h2 id="faq-title" className="display">
            {t("landing.faqTitle")}
          </h2>
        </div>
        <div className="faq">
          {items.map((item) => (
            <details key={item.q}>
              <summary>
                {item.q}
                <Plus aria-hidden />
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
