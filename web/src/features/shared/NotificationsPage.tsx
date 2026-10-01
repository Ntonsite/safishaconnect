import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import clsx from "clsx";
import { notificationsApi } from "../../api/endpoints";
import type { Notification, Role } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../shared/components/Button";
import { PageHeader } from "../../shared/components/Controls";
import { EmptyState, ErrorState, SkeletonCard } from "../../shared/components/Feedback";
import { useFormat } from "../../shared/hooks/useFormat";

function bookingPath(role: Role, n: Notification): string | null {
  if (!n.booking_id) return role === "ADMIN" && n.type === "ADMIN_PROVIDER_PENDING" ? "/admin/providers?status=PENDING" : null;
  if (role === "ADMIN") return `/admin/bookings/${n.booking_id}`;
  if (role === "PROVIDER") return n.type === "JOB_OFFERED" ? "/provider/offers" : `/provider/jobs/${n.booking_id}`;
  return `/app/bookings/${n.booking_id}`;
}

export function NotificationsPage() {
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["notifications"], queryFn: notificationsApi.list });

  const readAll = useMutation({
    mutationFn: notificationsApi.readAll,
    onSuccess: (data) => qc.setQueryData(["notifications"], data),
  });

  const open = async (n: Notification) => {
    if (!n.is_read) {
      await notificationsApi.read(n.id).catch(() => undefined);
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    }
    const path = user && bookingPath(user.role, n);
    if (path) navigate(path);
  };

  const text = (n: Notification) => {
    const key = `notifications.types.${n.type}`;
    return i18n.exists(key) ? t(key, { ref: n.booking_reference ?? "" }) : n.body;
  };

  return (
    <div className="stack">
      <PageHeader
        title={t("notifications.title")}
        actions={
          !!query.data?.unread && (
            <Button variant="secondary" size="sm" icon={<CheckCheck />} onClick={() => readAll.mutate()} loading={readAll.isPending}>
              {t("notifications.markAllRead")}
            </Button>
          )
        }
      />
      {query.isLoading && <SkeletonCard />}
      {query.error && <ErrorState error={query.error} onRetry={() => query.refetch()} />}
      {query.data && (
        <div className="card card-flush">
          {query.data.items.length === 0 ? (
            <EmptyState icon={Bell} title={t("notifications.empty")} />
          ) : (
            query.data.items.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => open(n)}
                className={clsx("booking-row")}
                style={{
                  width: "100%",
                  border: 0,
                  borderBottom: "1px solid var(--line)",
                  background: n.is_read ? "transparent" : "var(--green-25)",
                  textAlign: "left",
                  cursor: "pointer",
                  gridTemplateColumns: "12px minmax(0,1fr) auto",
                }}
              >
                <span
                  aria-hidden
                  style={{ width: 8, height: 8, borderRadius: 4, background: n.is_read ? "transparent" : "var(--green-600)" }}
                />
                <span className="grow">
                  <span className={clsx("block", !n.is_read && "strong")} style={{ display: "block" }}>
                    {text(n)}
                  </span>
                  <span className="small muted">{fmt.dateTime(n.created_at)}</span>
                </span>
                <span />
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
