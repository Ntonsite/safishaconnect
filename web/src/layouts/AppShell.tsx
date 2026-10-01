import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Bell, LogOut, Menu, type LucideIcon } from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../auth/AuthContext";
import { notificationsApi } from "../api/endpoints";
import { useConfig } from "../config/brand";
import { LanguageSwitch, Logo } from "../shared/components/Brand";
import { initials } from "../shared/utils/format";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  count?: number;
  end?: boolean;
}

export interface NavGroup {
  label?: string;
  items: NavItem[];
}

interface AppShellProps {
  home: string;
  groups: NavGroup[];
  bottomNav?: NavItem[];
  notificationsPath: string;
  narrow?: boolean;
  topbarExtra?: ReactNode;
}

export function useUnreadCount() {
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
    refetchInterval: 30_000,
  });
  return data?.unread ?? 0;
}

export function AppShell({ home, groups, bottomNav, notificationsPath, narrow, topbarExtra }: AppShellProps) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { demo_mode } = useConfig();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawer, setDrawer] = useState(false);
  const unread = useUnreadCount();

  useEffect(() => setDrawer(false), [location.pathname]);

  const signOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className={clsx("app-shell", bottomNav && "has-bottom-nav")}>
      <a href="#main" className="skip-link">
        {t("common.skipToContent")}
      </a>
      {drawer && <div className="sidebar-scrim" onClick={() => setDrawer(false)} />}
      <aside className={clsx("app-sidebar", drawer && "is-open")} aria-label="Sidebar">
        <Logo to={home} />
        {groups.map((group, i) => (
          <nav className="side-nav" key={i} aria-label={group.label}>
            {group.label && <div className="side-nav-group">{group.label}</div>}
            {group.items.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <item.icon aria-hidden />
                <span>{item.label}</span>
                {!!item.count && <span className="count">{item.count}</span>}
              </NavLink>
            ))}
          </nav>
        ))}
        <div className="sidebar-footer">
          {demo_mode && <span className="demo-flag">{t("common.demoData")}</span>}
          {user && (
            <div className="user-chip">
              <span className="avatar" aria-hidden>
                {initials(user.full_name)}
              </span>
              <div className="grow">
                <div className="user-chip-name">{user.full_name}</div>
                <div className="tiny muted">{user.email ?? user.phone}</div>
              </div>
            </div>
          )}
          <button className="btn btn-ghost btn-sm" onClick={signOut} style={{ justifyContent: "flex-start" }}>
            <LogOut /> {t("common.signOut")}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <button className="icon-btn mobile-only" onClick={() => setDrawer(true)} aria-label={t("nav.openMenu")}>
            <Menu />
          </button>
          <Logo to={home} />
          <div className="grow" />
          {topbarExtra}
          <LanguageSwitch />
          <Link to={notificationsPath} className="icon-btn" aria-label={`${t("nav.notifications")} (${unread})`}>
            <Bell />
            {unread > 0 && <span className="dot-count">{unread > 9 ? "9+" : unread}</span>}
          </Link>
        </header>
        <main id="main" className={clsx("app-content", narrow && "app-content-narrow")}>
          <Outlet />
        </main>
      </div>

      {bottomNav && (
        <nav className="bottom-nav" aria-label="Quick navigation">
          {bottomNav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <item.icon aria-hidden />
              <span>{item.label}</span>
              {!!item.count && <span className="count">{item.count}</span>}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
