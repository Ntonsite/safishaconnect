import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  BadgeCheck,
  Bell,
  Briefcase,
  CalendarClock,
  CalendarPlus,
  CheckCircle2,
  ClipboardList,
  CreditCard,
  FileClock,
  Home,
  Inbox,
  LayoutDashboard,
  ListChecks,
  MapPin,
  MessageSquareWarning,
  Settings,
  Sparkles,
  Star,
  User,
  Users,
  Wallet,
} from "lucide-react";
import { adminApi, providerApi } from "../api/endpoints";
import { AppShell } from "./AppShell";

export function CustomerLayout() {
  const { t } = useTranslation();
  return (
    <AppShell
      home="/app"
      narrow
      notificationsPath="/app/notifications"
      groups={[
        {
          items: [
            { to: "/app", label: t("nav.dashboard"), icon: Home, end: true },
            { to: "/app/book", label: t("nav.newBooking"), icon: CalendarPlus },
            { to: "/app/bookings", label: t("nav.myBookings"), icon: ClipboardList },
            { to: "/app/reviews", label: t("nav.reviews"), icon: Star },
            { to: "/app/notifications", label: t("nav.notifications"), icon: Bell },
            { to: "/app/profile", label: t("nav.profile"), icon: User },
          ],
        },
      ]}
      bottomNav={[
        { to: "/app", label: t("nav.dashboard"), icon: Home, end: true },
        { to: "/app/book", label: t("nav.newBooking"), icon: CalendarPlus },
        { to: "/app/bookings", label: t("nav.myBookings"), icon: ClipboardList },
        { to: "/app/profile", label: t("nav.profile"), icon: User },
      ]}
    />
  );
}

export function ProviderLayout() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: ["provider", "dashboard"], queryFn: providerApi.dashboard, refetchInterval: 30_000 });
  const offers = data?.open_offers ?? 0;
  return (
    <AppShell
      home="/provider"
      notificationsPath="/provider/notifications"
      groups={[
        {
          items: [
            { to: "/provider", label: t("nav.provider.dashboard"), icon: LayoutDashboard, end: true },
            { to: "/provider/offers", label: t("nav.provider.offers"), icon: Inbox, count: offers },
            { to: "/provider/jobs", label: t("nav.provider.active"), icon: Briefcase },
            { to: "/provider/completed", label: t("nav.provider.completed"), icon: CheckCircle2 },
            { to: "/provider/earnings", label: t("nav.provider.earnings"), icon: Wallet },
            { to: "/provider/ratings", label: t("nav.provider.ratings"), icon: Star },
          ],
        },
        {
          label: t("nav.provider.more"),
          items: [
            { to: "/provider/availability", label: t("nav.provider.availability"), icon: CalendarClock },
            { to: "/provider/coverage", label: t("nav.provider.servicesAreas"), icon: MapPin },
            { to: "/provider/profile", label: t("nav.provider.profile"), icon: User },
          ],
        },
      ]}
      bottomNav={[
        { to: "/provider", label: t("nav.provider.dashboard"), icon: LayoutDashboard, end: true },
        { to: "/provider/offers", label: t("nav.provider.offers"), icon: Inbox, count: offers },
        { to: "/provider/jobs", label: t("nav.provider.active"), icon: Briefcase },
        { to: "/provider/earnings", label: t("nav.provider.earnings"), icon: Wallet },
      ]}
    />
  );
}

export function AdminLayout() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: ["admin", "stats"], queryFn: adminApi.stats, refetchInterval: 60_000 });
  return (
    <AppShell
      home="/admin"
      notificationsPath="/admin/notifications"
      groups={[
        { items: [{ to: "/admin", label: t("nav.admin.overview"), icon: LayoutDashboard, end: true }] },
        {
          label: t("nav.admin.operations"),
          items: [
            { to: "/admin/bookings", label: t("nav.admin.bookings"), icon: ListChecks, count: data?.pending_assignments },
            { to: "/admin/payments", label: t("nav.admin.payments"), icon: CreditCard },
            { to: "/admin/settlements", label: t("nav.admin.settlements"), icon: Wallet },
            { to: "/admin/complaints", label: t("nav.admin.complaints"), icon: MessageSquareWarning, count: data?.open_complaints },
          ],
        },
        {
          label: t("nav.admin.people"),
          items: [
            { to: "/admin/providers", label: t("nav.admin.providers"), icon: BadgeCheck, count: data?.providers_awaiting_verification },
            { to: "/admin/customers", label: t("nav.admin.customers"), icon: Users },
            { to: "/admin/reviews", label: t("nav.admin.reviews"), icon: Star },
          ],
        },
        {
          label: t("nav.admin.catalogue"),
          items: [
            { to: "/admin/services", label: t("nav.admin.services"), icon: Sparkles },
            { to: "/admin/areas", label: t("nav.admin.areas"), icon: MapPin },
          ],
        },
        {
          label: t("nav.admin.platform"),
          items: [
            { to: "/admin/settings", label: t("nav.admin.settings"), icon: Settings },
            { to: "/admin/audit", label: t("nav.admin.audit"), icon: FileClock },
          ],
        },
      ]}
    />
  );
}
