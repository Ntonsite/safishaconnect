import { useTranslation } from "react-i18next";
import type { AvailabilityDay } from "../../api/types";
import { Switch } from "./Field";

export const DAYS = [1, 2, 3, 4, 5, 6, 7] as const;

export function defaultWeek(): AvailabilityDay[] {
  return DAYS.filter((d) => d <= 6).map((d) => ({ day_of_week: d, start_time: "08:00", end_time: "17:00" }));
}

/** Weekly working-hours editor shared by onboarding and the provider portal. */
export function AvailabilityEditor({
  value,
  onChange,
}: {
  value: AvailabilityDay[];
  onChange: (days: AvailabilityDay[]) => void;
}) {
  const { t } = useTranslation();
  const byDay = new Map(value.map((d) => [d.day_of_week, d]));

  const update = (day: number, patch: Partial<AvailabilityDay> | null) => {
    const next = new Map(byDay);
    if (patch === null) next.delete(day);
    else next.set(day, { ...(byDay.get(day) ?? { day_of_week: day, start_time: "08:00", end_time: "17:00" }), ...patch });
    onChange([...next.values()].sort((a, b) => a.day_of_week - b.day_of_week));
  };

  return (
    <div className="stack-sm">
      {DAYS.map((day) => {
        const entry = byDay.get(day);
        return (
          <div
            key={day}
            className="row-between wrap"
            style={{ padding: "10px 0", borderBottom: "1px solid var(--line)", minHeight: 56 }}
          >
            <Switch checked={!!entry} onChange={(on) => update(day, on ? {} : null)} label={t(`days.${day}`)} />
            {entry ? (
              <div className="row" style={{ gap: 8 }}>
                <input
                  type="time"
                  className="input input-sm"
                  style={{ width: 120 }}
                  aria-label={`${t(`days.${day}`)} ${t("provider.from")}`}
                  value={entry.start_time.slice(0, 5)}
                  step={1800}
                  onChange={(e) => update(day, { start_time: e.target.value })}
                />
                <span className="muted">–</span>
                <input
                  type="time"
                  className="input input-sm"
                  style={{ width: 120 }}
                  aria-label={`${t(`days.${day}`)} ${t("provider.to")}`}
                  value={entry.end_time.slice(0, 5)}
                  step={1800}
                  onChange={(e) => update(day, { end_time: e.target.value })}
                />
              </div>
            ) : (
              <span className="small muted">{t("provider.dayOff")}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
