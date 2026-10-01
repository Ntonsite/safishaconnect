import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import type { Locale } from "../api/types";

const STORAGE_KEY = "safisha.locale";
export const SUPPORTED: Locale[] = ["en", "sw"];

// English ships in the entry chunk (default + fallback). Kiswahili is a separate chunk
// fetched only for users who need it, so nobody downloads both languages up front.
const loaders: Record<Exclude<Locale, "en">, () => Promise<{ default: Record<string, unknown> }>> = {
  sw: () => import("./locales/sw.json"),
};

function initialLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "sw") return stored;
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith("sw") ? "sw" : "en";
}

/** Make sure a locale's strings are registered; safe to call repeatedly. */
export async function loadLocale(locale: Locale): Promise<void> {
  if (locale === "en" || i18n.hasResourceBundle(locale, "translation")) return;
  const { default: resources } = await loaders[locale]();
  i18n.addResourceBundle(locale, "translation", resources, true, true);
}

const startLocale = initialLocale();

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnObjects: true,
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  try {
    localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    /* ignore */
  }
});

/** Resolves once the visitor's preferred language is ready to render (no English flash for Swahili users). */
export const i18nReady: Promise<unknown> =
  startLocale === "en"
    ? Promise.resolve()
    : loadLocale(startLocale)
        .then(() => i18n.changeLanguage(startLocale))
        .catch(() => undefined); // offline/failed chunk: fall back to English rather than a blank page
document.documentElement.lang = i18n.language;

export async function setLocale(locale: Locale) {
  await loadLocale(locale);
  return i18n.changeLanguage(locale);
}

/** Warm the other language when the user shows intent to switch (hover/focus on the switch). */
export function prefetchLocale(locale: Locale) {
  void loadLocale(locale).catch(() => undefined);
}

export function currentLocale(): Locale {
  return (i18n.resolvedLanguage as Locale) ?? "en";
}

export default i18n;
