import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Building2,
  Home,
  Sofa,
  Sparkles,
  Star,
  Truck,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import { useBrand } from "../../config/brand";
import { setLocale, SUPPORTED } from "../../i18n";
import type { Locale } from "../../api/types";

/** Wordmark built from the configured brand name; the last "word part" is accented. */
export function Logo({ to = "/", className }: { to?: string; className?: string }) {
  const brand = useBrand();
  const name = brand.app_name;
  const split = name.search(/[A-Z][a-z]*$/);
  const [head, tail] = split > 0 ? [name.slice(0, split), name.slice(split)] : [name, ""];
  return (
    <Link to={to} className={clsx("logo", className)} aria-label={name}>
      <img src="/brand/mark.svg" alt="" width={32} height={32} />
      <span className="logo-word">
        {head}
        {tail && <span>{tail}</span>}
      </span>
    </Link>
  );
}

export function LanguageSwitch() {
  const { i18n, t } = useTranslation();
  const current = (i18n.resolvedLanguage ?? "en") as Locale;
  return (
    <div className="segmented" role="group" aria-label={t("common.language")}>
      {SUPPORTED.map((lng) => (
        <button
          key={lng}
          type="button"
          aria-pressed={current === lng}
          onClick={() => void setLocale(lng)}
          lang={lng}
          title={lng === "en" ? "English" : "Kiswahili"}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

const ICONS: Record<string, LucideIcon> = {
  home: Home,
  sparkles: Sparkles,
  building: Building2,
  truck: Truck,
  sofa: Sofa,
};

export function ServiceIcon({ name, className }: { name: string; className?: string }) {
  const Icon = ICONS[name] ?? Sparkles;
  return (
    <span className={clsx("service-icon", className)} aria-hidden>
      <Icon />
    </span>
  );
}

export function Stars({ value, size = 16 }: { value: number; size?: number }) {
  return (
    <span className="stars" aria-label={`${value.toFixed(1)} / 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          style={{ width: size, height: size }}
          fill={i <= Math.round(value) ? "currentColor" : "none"}
          strokeWidth={1.6}
          aria-hidden
        />
      ))}
    </span>
  );
}

export function StarInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="star-input" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          role="radio"
          aria-checked={value === i}
          aria-label={`${i} / 5`}
          className={clsx(i <= value && "is-on")}
          onClick={() => onChange(i)}
        >
          <Star fill={i <= value ? "currentColor" : "none"} strokeWidth={1.5} />
        </button>
      ))}
    </div>
  );
}

export function RatingSummary({ average, count }: { average: string | number; count: number }) {
  const { t } = useTranslation();
  if (!count) return <span className="small muted">{t("common.noRatingYet")}</span>;
  return (
    <span className="row" style={{ gap: 6 }}>
      <Stars value={Number(average)} size={14} />
      <span className="small strong">{Number(average).toFixed(1)}</span>
      <span className="small muted">({t("common.reviewsCount", { count })})</span>
    </span>
  );
}
