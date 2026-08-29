import { Link } from "react-router";

import { useSyntheticStatus } from "../../api/hooks";
import { formatPercent, formatRelative } from "../../lib/format";

/**
 * Header liveness pill (AC-001, AC-007): synthetic status, 24h uptime, and
 * the age of the last check. Always visible; links to the Uptime page.
 */
export function LivenessPill() {
  const { data, isPending, isError } = useSyntheticStatus();

  if (isPending) {
    return (
      <span
        data-testid="liveness-pill"
        data-status="unknown"
        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-sm text-muted"
      >
        <span className="skeleton h-2 w-2 rounded-full" aria-hidden />
        checking…
      </span>
    );
  }

  if (isError || !data) {
    return (
      <span
        data-testid="liveness-pill"
        data-status="unknown"
        className="inline-flex items-center rounded-full border border-danger/50 px-3 py-1 text-sm text-danger"
      >
        status unavailable
      </span>
    );
  }

  if (!data.enabled) {
    return (
      <Link
        to="/app/uptime"
        data-testid="liveness-pill"
        data-status="disabled"
        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-sm text-muted hover:border-primary"
      >
        <span
          className="h-2 w-2 rounded-full border border-neutral"
          aria-hidden
        />
        Synthetic check off
      </Link>
    );
  }

  const up = data.status === "passing";
  const label = up ? "UP" : data.status === "failing" ? "DOWN" : "UNKNOWN";

  return (
    <Link
      to="/app/uptime"
      data-testid="liveness-pill"
      data-status={data.status}
      aria-label={`Synthetic check ${label}, uptime ${formatPercent(data.uptime_24h_pct)} over 24 hours, last checked ${formatRelative(data.last_check_at)}`}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-sm hover:border-primary"
    >
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ background: "var(--status)" }}
        aria-hidden
      />
      <span className="font-semibold" style={{ color: "var(--status)" }}>
        {label}
      </span>
      <span className="text-text">{formatPercent(data.uptime_24h_pct)}</span>
      <span className="hidden text-muted sm:inline">
        · checked {formatRelative(data.last_check_at)}
      </span>
    </Link>
  );
}
