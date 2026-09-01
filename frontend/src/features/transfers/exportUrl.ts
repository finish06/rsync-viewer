export type ExportFormat = "csv" | "json";

export interface ExportOptions {
  /** Empty = every source (no `source` parameter at all). */
  sources: string[];
  format: ExportFormat;
  includeSynthetic?: boolean;
  from?: string;
  to?: string;
}

/**
 * Query string for GET /api/v1/analytics/export (specs/csv-export-ui.md
 * AC-006). One `source` parameter per selection; dates only when set.
 */
export function buildExportUrl(options: ExportOptions): string {
  const params = new URLSearchParams();
  params.set("format", options.format);
  for (const source of options.sources) params.append("source", source);
  params.set("synthetic", options.includeSynthetic ? "show" : "hide");
  if (options.from) params.set("start", options.from);
  if (options.to) params.set("end", options.to);
  return `/api/v1/analytics/export?${params.toString()}`;
}

/** rsync-export-YYYYMMDD.csv — dated so repeat exports do not collide. */
export function exportFilename(
  format: ExportFormat,
  now: Date = new Date(),
): string {
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("");
  return `rsync-export-${stamp}.${format}`;
}

/** Browser download via a transient anchor (cookie-authenticated GET). */
export function triggerDownload(url: string, filename: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}
