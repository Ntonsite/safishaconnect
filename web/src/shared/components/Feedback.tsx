import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, CheckCircle2, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import clsx from "clsx";
import { Button } from "./Button";
import { useErrorMessage } from "../hooks/useErrorMessage";

export function Spinner({ label }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label ?? "Loading"} />;
}

export function FullPageSpinner() {
  return (
    <div className="page-loader" style={{ minHeight: "100vh" }}>
      <Spinner />
    </div>
  );
}

export function PageLoader() {
  const { t } = useTranslation();
  return (
    <div className="page-loader">
      <Spinner label={t("common.loading")} />
    </div>
  );
}

export function Skeleton({ height = 16, width = "100%", style }: { height?: number; width?: number | string; style?: React.CSSProperties }) {
  return <div className="skeleton" style={{ height, width, ...style }} aria-hidden />;
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card stack-sm" aria-busy>
      <Skeleton height={20} width="40%" />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} width={`${90 - i * 15}%`} />
      ))}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon: LucideIcon;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon aria-hidden />
      </div>
      <p className="empty-title">{title}</p>
      {body && <p style={{ maxWidth: 380 }}>{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const message = useErrorMessage()(error);
  return (
    <div className="empty" role="alert">
      <div className="empty-icon" style={{ background: "var(--red-50)", color: "var(--red-600)" }}>
        <AlertCircle aria-hidden />
      </div>
      <p className="empty-title">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}

const ALERT_ICONS = { info: Info, success: CheckCircle2, warning: TriangleAlert, danger: AlertCircle };

export function Alert({
  tone = "info",
  children,
  className,
}: {
  tone?: keyof typeof ALERT_ICONS;
  children: ReactNode;
  className?: string;
}) {
  const Icon = ALERT_ICONS[tone];
  return (
    <div className={clsx("alert", `alert-${tone}`, className)} role={tone === "danger" ? "alert" : "status"}>
      <Icon aria-hidden />
      <div className="grow">{children}</div>
    </div>
  );
}
