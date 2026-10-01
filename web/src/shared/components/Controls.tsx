import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Check, ChevronLeft, ChevronRight, Minus, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { Button } from "./Button";

export function PageHeader({
  title,
  subtitle,
  actions,
  back,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  back?: { to: string; label: string };
}) {
  return (
    <>
      {back && (
        <Link to={back.to} className="back-link">
          <ArrowLeft aria-hidden /> {back.label}
        </Link>
      )}
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="row wrap">{actions}</div>}
      </div>
    </>
  );
}

export function Tabs<T extends string>({
  value,
  onChange,
  items,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: string; count?: number }[];
}) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          key={item.value}
          role="tab"
          type="button"
          className="tab"
          aria-selected={value === item.value}
          onClick={() => onChange(item.value)}
        >
          {item.label}
          {!!item.count && <span className="tab-count">{item.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Counter({
  value,
  min = 0,
  max = 10,
  onChange,
  label,
}: {
  value: number;
  min?: number;
  max?: number;
  onChange: (v: number) => void;
  label: string;
}) {
  return (
    <div className="counter" role="group" aria-label={label}>
      <button type="button" onClick={() => onChange(value - 1)} disabled={value <= min} aria-label={`${label} −`}>
        <Minus size={18} />
      </button>
      <output aria-live="polite">{value}</output>
      <button type="button" onClick={() => onChange(value + 1)} disabled={value >= max} aria-label={`${label} +`}>
        <Plus size={18} />
      </button>
    </div>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const { t } = useTranslation();
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span>{t("common.results", { count: total })}</span>
      <div className="row">
        <span>{t("common.pageOf", { page, pages })}</span>
        <Button size="sm" variant="secondary" onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label={t("common.previous")}>
          <ChevronLeft />
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onChange(page + 1)} disabled={page >= pages} aria-label={t("common.nextPage")}>
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}

/** A selectable card used for radios and multi-select checkboxes. */
export function ChoiceCard({
  selected,
  onClick,
  title,
  meta,
  disabled,
  role = "radio",
  children,
}: {
  selected: boolean;
  onClick: () => void;
  title: ReactNode;
  meta?: ReactNode;
  disabled?: boolean;
  role?: "radio" | "checkbox";
  children?: ReactNode;
}) {
  return (
    <button
      type="button"
      role={role}
      aria-checked={selected}
      aria-disabled={disabled || undefined}
      className={clsx("choice", selected && "is-selected")}
      onClick={() => !disabled && onClick()}
    >
      <span className="choice-check" aria-hidden>
        {selected && <Check strokeWidth={3} />}
      </span>
      <span className="choice-title" style={{ paddingRight: 28 }}>
        {title}
      </span>
      {meta && <span className="choice-meta">{meta}</span>}
      {children}
    </button>
  );
}
