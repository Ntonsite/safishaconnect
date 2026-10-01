import { describe, expect, it } from "vitest";
import { addMinutesToTime, formatMoney, initials, pick, toISODate } from "../shared/utils/format";
import { PASSWORD_RULE, TZ_PHONE } from "../shared/utils/validation";

describe("format helpers", () => {
  it("formats TZS amounts without decimals", () => {
    expect(formatMoney("110000.00")).toBe("TZS 110,000");
    expect(formatMoney(null)).toBe("—");
  });

  it("adds minutes to a time of day and clamps at midnight", () => {
    expect(addMinutesToTime("10:00:00", 375)).toBe("16:15");
    expect(addMinutesToTime("22:00", 300)).toBe("23:59");
  });

  it("builds local ISO dates and initials", () => {
    expect(toISODate(new Date(2026, 9, 2))).toBe("2026-10-02");
    expect(initials("Neema Mwakyusa")).toBe("NM");
  });

  it("picks the localized field with English fallback", () => {
    const svc = { name_en: "Deep Cleaning", name_sw: "Usafi wa Kina" };
    expect(pick(svc, "name", "sw")).toBe("Usafi wa Kina");
    expect(pick({ name_en: "Only English" }, "name", "sw")).toBe("Only English");
  });
});

describe("client-side validation", () => {
  it.each(["0712 345 678", "+255 754 123 456", "255712345678", "712345678"])("accepts %s", (phone) => {
    expect(TZ_PHONE.test(phone)).toBe(true);
  });
  it.each(["12345", "0812 345 678", "+254712345678"])("rejects %s", (phone) => {
    expect(TZ_PHONE.test(phone)).toBe(false);
  });
  it("requires letters and numbers in passwords", () => {
    expect(PASSWORD_RULE.test("Usafi2026")).toBe(true);
    expect(PASSWORD_RULE.test("password")).toBe(false);
  });
});
