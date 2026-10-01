import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import sw from "./locales/sw.json";
import type { Locale } from "../api/types";

const STORAGE_KEY = "safisha.locale";
export const SUPPORTED: Locale[] = ["en", "sw"];

function initialLocale(): Locale {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "sw") return stored;
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith("sw") ? "sw" : "en";
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, sw: { translation: sw } },
  lng: initialLocale(),
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
document.documentElement.lang = i18n.language;

export function setLocale(locale: Locale) {
  return i18n.changeLanguage(locale);
}

export function currentLocale(): Locale {
  return (i18n.resolvedLanguage as Locale) ?? "en";
}

export default i18n;
