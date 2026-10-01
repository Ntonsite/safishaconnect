import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { Locale } from "../../api/types";
import { useConfig } from "../../config/brand";
import { formatDate, formatDateTime, formatMoney, formatTime, pick, splitDuration } from "../utils/format";

/** Locale-aware formatters bound to the current language and currency. */
export function useFormat() {
  const { t, i18n } = useTranslation();
  const { currency } = useConfig();
  const locale = (i18n.resolvedLanguage ?? "en") as Locale;
  return useMemo(
    () => ({
      locale,
      money: (value: string | number | null | undefined, cur?: string) => formatMoney(value, cur ?? currency, locale),
      date: (iso: string, opts?: Intl.DateTimeFormatOptions) => formatDate(iso, locale, opts),
      dateLong: (iso: string) => formatDate(iso, locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" }),
      dateTime: (iso: string) => formatDateTime(iso, locale),
      time: formatTime,
      duration: (minutes: number) => {
        const d = splitDuration(minutes);
        if (d.hours === 0) return t("common.minutes", { count: d.minutes });
        return d.minutes ? t("common.duration", d) : t("common.durationHours", d);
      },
      rooms: (bedrooms: number, bathrooms: number) =>
        `${t("common.bedroomCount", { count: bedrooms })} · ${t("common.bathroomCount", { count: bathrooms })}`,
      pick: <T extends object>(obj: T, field: string) => pick(obj, field, locale),
    }),
    [locale, currency, t],
  );
}
