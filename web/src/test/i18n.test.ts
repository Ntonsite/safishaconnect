import { describe, expect, it } from "vitest";
import en from "../i18n/locales/en.json";
import sw from "../i18n/locales/sw.json";

function keys(obj: unknown, prefix = ""): string[] {
  if (Array.isArray(obj)) return [`${prefix}[${obj.length}]`, ...obj.flatMap((v, i) => keys(v, `${prefix}[${i}]`))];
  if (obj && typeof obj === "object") {
    return Object.entries(obj).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
  }
  return [prefix];
}

describe("translations", () => {
  it("English and Kiswahili define exactly the same keys", () => {
    const missingInSw = keys(en).filter((k) => !keys(sw).includes(k));
    const extraInSw = keys(sw).filter((k) => !keys(en).includes(k));
    expect(missingInSw).toEqual([]);
    expect(extraInSw).toEqual([]);
  });

  it("has no empty strings", () => {
    const empty = (o: unknown): boolean =>
      typeof o === "string" ? o.trim() === "" : o && typeof o === "object" ? Object.values(o).some(empty) : false;
    expect(empty(en)).toBe(false);
    expect(empty(sw)).toBe(false);
  });

  it("covers every booking status", () => {
    const statuses = [
      "PENDING_CONFIRMATION", "CONFIRMED", "FINDING_PROVIDER", "PROVIDER_ASSIGNED", "PROVIDER_EN_ROUTE",
      "PROVIDER_ARRIVED", "SERVICE_IN_PROGRESS", "COMPLETED_BY_PROVIDER", "CUSTOMER_CONFIRMED", "CLOSED",
      "CANCELLED", "REASSIGNMENT_REQUIRED", "DISPUTED",
    ];
    for (const s of statuses) {
      expect(sw.status.booking).toHaveProperty(s);
      expect(sw.status.bookingHelp).toHaveProperty(s);
    }
  });
});
