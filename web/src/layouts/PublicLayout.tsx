import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, X } from "lucide-react";
import { homeFor, useAuth } from "../auth/AuthContext";
import { useBrand } from "../config/brand";
import { ButtonLink } from "../shared/components/Button";
import { LanguageSwitch, Logo } from "../shared/components/Brand";

export function PublicLayout() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const links = [
    { to: "/services", label: t("nav.services") },
    { to: "/how-it-works", label: t("nav.howItWorks") },
    { to: "/join", label: t("nav.becomeProvider") },
    { to: "/help", label: t("nav.help") },
  ];

  return (
    <>
      <a href="#main" className="skip-link">
        {t("common.skipToContent")}
      </a>
      <header className="site-header">
        <div className="container">
          <Logo />
          <nav className="site-nav" aria-label="Main">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="header-actions">
            <LanguageSwitch />
            {user ? (
              <ButtonLink to={homeFor(user.role)} variant="secondary" className="desktop-only">
                {t("nav.dashboard")}
              </ButtonLink>
            ) : (
              <ButtonLink to="/login" variant="ghost" className="desktop-only">
                {t("nav.login")}
              </ButtonLink>
            )}
            {(!user || user.role === "CUSTOMER") && (
              <ButtonLink to="/app/book" className="desktop-only">
                {t("nav.bookCleaning")}
              </ButtonLink>
            )}
            <button
              className="icon-btn mobile-only"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={open ? t("nav.closeMenu") : t("nav.openMenu")}
            >
              {open ? <X /> : <Menu />}
            </button>
          </div>
        </div>
      </header>
      {open && (
        <nav className="mobile-menu" aria-label="Mobile">
          {links.map((l) => (
            <Link key={l.to} to={l.to}>
              {l.label}
            </Link>
          ))}
          {user ? (
            <Link to={homeFor(user.role)}>{t("nav.dashboard")}</Link>
          ) : (
            <Link to="/login">{t("nav.login")}</Link>
          )}
          {(!user || user.role === "CUSTOMER") && (
            <ButtonLink to="/app/book" size="lg" block>
              {t("nav.bookCleaning")}
            </ButtonLink>
          )}
        </nav>
      )}
      <main id="main">
        <Outlet />
      </main>
      <SiteFooter />
    </>
  );
}

function SiteFooter() {
  const { t } = useTranslation();
  const brand = useBrand();
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand stack">
            <Logo />
            <p className="small" style={{ maxWidth: 320 }}>
              {t("landing.footerTagline")}
            </p>
          </div>
          <div>
            <h4>{t("nav.services")}</h4>
            <ul>
              <li>
                <Link to="/services">{t("nav.services")}</Link>
              </li>
              <li>
                <Link to="/how-it-works">{t("nav.howItWorks")}</Link>
              </li>
              <li>
                <Link to="/app/book">{t("nav.bookCleaning")}</Link>
              </li>
            </ul>
          </div>
          <div>
            <h4>{t("landing.footerCompany")}</h4>
            <ul>
              <li>
                <Link to="/join">{t("nav.becomeProvider")}</Link>
              </li>
              <li>
                <Link to="/login">{t("nav.login")}</Link>
              </li>
            </ul>
          </div>
          <div>
            <h4>{t("landing.footerSupport")}</h4>
            <ul>
              <li>
                <Link to="/help">{t("nav.help")}</Link>
              </li>
              <li>
                <a href={`tel:${brand.support_phone.replace(/\s/g, "")}`}>{brand.support_phone}</a>
              </li>
              <li>
                <a href={`mailto:${brand.support_email}`}>{brand.support_email}</a>
              </li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>{t("landing.footerRights", { year: new Date().getFullYear(), brand: brand.app_name })}</span>
          <span>{brand.office_address}</span>
        </div>
      </div>
    </footer>
  );
}
