import { Link } from "react-router";

import { useSyntheticStatus } from "../../api/hooks";
import type { SourceHealth } from "../../api/types";
import { formatRelative } from "../../lib/format";
import { dueLabel, nextDue } from "./cadence";
import { cardStatus } from "./SourceCard";
import { VolumeTrend } from "./VolumeTrend";

/** The first glance answers "is anything broken?" (overview-v2 AC-001). */
export function AttentionStrip({ sources }: { sources: SourceHealth[] }) {
  const synthetic = useSyntheticStatus();
  const problems = sources.filter((s) => {
    const status = cardStatus(s);
    return status === "failed" || status === "stale";
  });
  const livenessBad =
    synthetic.data?.enabled && synthetic.data.status === "failing";

  if (problems.length === 0 && !livenessBad) {
    return (
      <div
        data-testid="attention-strip"
        className="card flex flex-wrap items-center gap-x-4 gap-y-2 border-l-4 border-l-ok p-3"
      >
        <span className="text-sm font-medium">
          ✓ All {sources.length} {sources.length === 1 ? "source" : "sources"}{" "}
          healthy
        </span>
        {synthetic.data?.enabled && (
          <span className="text-xs text-muted">
            <b className="uppercase text-ok">
              {synthetic.data.status === "passing"
                ? "UP"
                : synthetic.data.status}
            </b>
            {synthetic.data.uptime_7d_pct != null &&
              ` ${synthetic.data.uptime_7d_pct}%`}
            {" · checked "}
            {formatRelative(synthetic.data.last_check_at)}
          </span>
        )}
        <div className="ml-auto">
          <VolumeTrend sources={sources} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="attention-strip-problems">
      {livenessBad && (
        <div
          data-testid="attention-card"
          className="card flex items-center gap-3 border-l-4 border-l-danger p-3 text-sm"
        >
          <span className="font-semibold text-danger">
            ✕ Synthetic check failing
          </span>
          <span className="text-muted">
            last check {formatRelative(synthetic.data?.last_check_at ?? null)}
          </span>
          <Link
            to="/app/uptime"
            className="ml-auto text-primary hover:underline"
          >
            view →
          </Link>
        </div>
      )}
      {problems.map((source) => {
        const due = nextDue(source);
        const status = cardStatus(source);
        return (
          <div
            key={source.source_name}
            data-testid="attention-card"
            data-status={status}
            className="card flex flex-wrap items-center gap-x-3 gap-y-1 border-l-4 p-3 text-sm"
            style={{ borderLeftColor: "var(--status)" }}
          >
            <span className="font-semibold" style={{ color: "var(--status)" }}>
              {status === "failed" ? "✕" : "▲"} {source.source_name}{" "}
              {status === "failed" ? "FAILED" : "STALE"}
            </span>
            <span className="text-muted">
              {formatRelative(source.last_sync_at)}
            </span>
            {source.consecutive_failures > 1 && (
              <span className="text-danger">
                {source.consecutive_failures} in a row
              </span>
            )}
            {due && due.overdueHours > 0 && (
              <span className="text-warn">{dueLabel(due)}</span>
            )}
            <Link
              to={`/app/transfers?source=${encodeURIComponent(source.source_name)}`}
              className="ml-auto text-primary hover:underline"
            >
              view →
            </Link>
          </div>
        );
      })}
    </div>
  );
}
