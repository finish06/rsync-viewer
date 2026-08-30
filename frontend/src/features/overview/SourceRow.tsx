import { Link } from "react-router";

import type { SourceHealth } from "../../api/types";
import { formatBytes, formatRelative } from "../../lib/format";
import { dueLabel, nextDue } from "./cadence";
import { cardStatus } from "./SourceCard";
import { Sparkline } from "./Sparkline";

/** Compact one-line row for a healthy source (overview-v2 AC-002/AC-005). */
export function SourceRow({ source }: { source: SourceHealth }) {
  const status = cardStatus(source);
  const due = nextDue(source);
  const syncs = source.daily.reduce((n, d) => n + d.syncs, 0);
  const failures = source.daily.reduce((n, d) => n + d.failures, 0);
  const bytes = source.daily.reduce((n, d) => n + d.bytes, 0);

  return (
    <Link
      to={`/app/transfers?source=${encodeURIComponent(source.source_name)}`}
      data-testid="source-row"
      data-status={status}
      aria-label={`${source.source_name}: synced ${formatRelative(source.last_sync_at)}`}
      className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-bg-secondary"
    >
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ background: "var(--status)" }}
        aria-hidden
      />
      <span className="min-w-0 flex-1 truncate font-medium">
        {source.source_name}
      </span>
      <span className="hidden text-xs text-muted sm:inline">
        {source.last_sync_at
          ? `synced ${formatRelative(source.last_sync_at)}`
          : "never synced"}
      </span>
      {due && (
        <span
          data-testid="due-chip"
          className={`rounded-full px-2 py-0.5 text-xs ${
            due.overdueHours > 0
              ? "bg-warn/15 text-warn"
              : "bg-bg-secondary text-muted"
          }`}
        >
          {dueLabel(due)}
        </span>
      )}
      <span className="hidden w-24 md:block">
        <Sparkline daily={source.daily} />
      </span>
      <span className="w-32 text-right text-xs text-muted">
        {syncs} {syncs === 1 ? "sync" : "syncs"}
        {failures > 0 && <span className="text-danger"> · {failures} ✕</span>}
        {" · "}
        {bytes >= 1024 ? formatBytes(bytes) : "—"}
      </span>
    </Link>
  );
}
