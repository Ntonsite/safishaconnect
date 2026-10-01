import type { Locale } from "../../api/types";

const intlLocale = (locale: Locale) => (locale === "sw" ? "sw-TZ" : "en-TZ");

/** Money arrives from the API as a decimal string; TZS has no minor unit in practice. */
export function formatMoney(value: string | number | null | undefined, currency = "TZS", locale: Locale = "en"): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "string" ? Number(value) : value;
  const digits = new Intl.NumberFormat(intlLocale(locale), { maximumFractionDigits: 0 }).format(amount);
  return `${currency} ${digits}`;
}

export function parseISODate(iso: string): Date {
  // Date-only strings are local calendar dates, not UTC midnights.
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(iso);
}

export function formatDate(iso: string, locale: Locale = "en", opts: Intl.DateTimeFormatOptions = {}): string {
  return parseISODate(iso).toLocaleDateString(intlLocale(locale), {
    weekday: "short",
    day: "numeric",
    month: "short",
    ...opts,
  });
}

export function formatDateTime(iso: string, locale: Locale = "en"): string {
  return new Date(iso).toLocaleString(intlLocale(locale), {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** "10:00:00" → "10:00" */
export function formatTime(value: string): string {
  return value.slice(0, 5);
}

export function addMinutesToTime(value: string, minutes: number): string {
  const [h, m] = value.split(":").map(Number);
  const total = Math.min(h * 60 + m + minutes, 23 * 60 + 59);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function splitDuration(minutes: number): { hours: number; minutes: number } {
  return { hours: Math.floor(minutes / 60), minutes: minutes % 60 };
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

/** Pick the localized variant of a bilingual API field: pick(service, "name", "sw"). */
export function pick<T extends object>(obj: T, field: string, locale: Locale): string {
  const record = obj as Record<string, unknown>;
  const value = record[`${field}_${locale}`] ?? record[`${field}_en`];
  return typeof value === "string" ? value : "";
}
