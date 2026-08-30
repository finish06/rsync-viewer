import type { SourceHealth } from "../../api/types";

const HOUR = 3_600_000;

export interface DueInfo {
  dueAt: Date;
  /** Positive = overdue by that many hours; negative = due in -overdueHours. */
  overdueHours: number;
}

/** Median gap in hours between days that saw at least one sync; null if <2. */
function inferredIntervalHours(source: SourceHealth): number | null {
  const activeDays = source.daily
    .filter((d) => d.syncs > 0)
    .map((d) => new Date(`${d.date}T00:00:00`).getTime());
  if (activeDays.length < 2) return null;
  const gaps = activeDays
    .slice(1)
    .map((t, i) => (t - activeDays[i]) / HOUR)
    .sort((a, b) => a - b);
  return gaps[Math.floor(gaps.length / 2)];
}

/**
 * When is the next sync due? Monitor interval first, else inferred cadence
 * (specs/overview-v2.md AC-003). Null when neither is known.
 */
export function nextDue(source: SourceHealth): DueInfo | null {
  if (!source.last_sync_at) return null;
  const interval =
    source.expected_interval_hours ?? inferredIntervalHours(source);
  if (!interval) return null;
  const dueAt = new Date(
    new Date(source.last_sync_at).getTime() + interval * HOUR,
  );
  return { dueAt, overdueHours: (Date.now() - dueAt.getTime()) / HOUR };
}

/** "due in ~22h" / "overdue by ~6h", using days above 48 h. */
export function dueLabel(due: DueInfo): string {
  const hours = Math.abs(due.overdueHours);
  const span =
    hours >= 48 ? `${Math.round(hours / 24)}d` : `${Math.round(hours)}h`;
  return due.overdueHours > 0 ? `overdue by ~${span}` : `due in ~${span}`;
}
