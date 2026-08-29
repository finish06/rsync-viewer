import {
  differenceInSeconds,
  format,
  formatDistanceStrict,
  isValid,
  parseISO,
} from "date-fns";

const UNITS = ["B", "KB", "MB", "GB", "TB", "PB"];

export function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value < 1024) return `${value} B`;
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < UNITS.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 100 ? 0 : 1)} ${UNITS[unit]}`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds))
    return "—";
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function durationBetween(start: string, end: string): number | null {
  const a = parseISO(start);
  const b = parseISO(end);
  if (!isValid(a) || !isValid(b)) return null;
  return differenceInSeconds(b, a);
}

/** "3m ago" within 24 h, otherwise a short absolute date (AC-009). */
export function formatRelative(
  iso: string | null | undefined,
  now: Date = new Date(),
): string {
  if (!iso) return "never";
  const date = parseISO(iso);
  if (!isValid(date)) return "—";
  const ageSeconds = differenceInSeconds(now, date);
  if (ageSeconds < 45) return "just now";
  if (ageSeconds < 86_400)
    return formatDistanceStrict(date, now, { addSuffix: true });
  return format(date, "MMM d, HH:mm");
}

export function formatTime(iso: string): string {
  const date = parseISO(iso);
  return isValid(date) ? format(date, "HH:mm") : "—";
}

export function formatPercent(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}%`;
}

export function episodeLabel(
  season: number | null,
  episode: number | null,
): string {
  const s = season === null ? "S??" : `S${String(season).padStart(2, "0")}`;
  const e = episode === null ? "E??" : `E${String(episode).padStart(2, "0")}`;
  return `${s}${e}`;
}

/** Local calendar day key (YYYY-MM-DD) for grouping transfers by day. */
export function localDayKey(iso: string): string {
  const date = parseISO(iso);
  return isValid(date) ? format(date, "yyyy-MM-dd") : "unknown";
}

export function dayLabel(dayKey: string, now: Date = new Date()): string {
  const today = format(now, "yyyy-MM-dd");
  const yesterday = format(new Date(now.getTime() - 86_400_000), "yyyy-MM-dd");
  if (dayKey === today) return "Today";
  if (dayKey === yesterday) return "Yesterday";
  const date = parseISO(dayKey);
  return isValid(date) ? format(date, "EEE, MMM d") : dayKey;
}
