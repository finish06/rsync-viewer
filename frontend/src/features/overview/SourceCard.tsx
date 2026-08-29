import { Link } from "react-router";

import type { SourceHealth } from "../../api/types";
import { formatBytes, formatRelative } from "../../lib/format";
import { Sparkline } from "./Sparkline";

export type CardStatus = "ok" | "failed" | "stale" | "never";

export function cardStatus(source: SourceHealth): CardStatus {
  if (source.last_status === "never") return "never";
  if (source.last_status === "failed") return "failed";
  if (source.is_stale) return "stale";
  return "ok";
}

const HEADLINE: Record<CardStatus, (s: SourceHealth) => string> = {
  ok: (s) => `synced ${formatRelative(s.last_sync_at)}`,
  failed: (s) => `FAILED ${formatRelative(s.last_sync_at)}`,
  stale: (s) => `STALE · last ${formatRelative(s.last_sync_at)}`,
  never: () => "never synced",
};

const GLYPH: Record<CardStatus, string> = {
  ok: "●",
  failed: "✕",
  stale: "▲",
  never: "○",
};

export function SourceCard({ source }: { source: SourceHealth }) {
  const status = cardStatus(source);
  const syncs = source.daily.reduce((n, d) => n + d.syncs, 0);
  const failures = source.daily.reduce((n, d) => n + d.failures, 0);
  const bytes = source.daily.reduce((n, d) => n + d.bytes, 0);

  return (
    <Link
      to={`/app/transfers?source=${encodeURIComponent(source.source_name)}`}
      data-testid="source-card"
      data-status={status}
      aria-label={`${source.source_name}: ${HEADLINE[status](source)}`}
      className="card block p-3 transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
      style={{ borderLeft: "4px solid var(--status)" }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-semibold">{source.source_name}</span>
        <span
          className="text-sm"
          style={{ color: "var(--status)" }}
          aria-hidden
        >
          {GLYPH[status]}
        </span>
      </div>
      <div
        className="mt-0.5 text-xs"
        style={{ color: status === "ok" ? "var(--muted)" : "var(--status)" }}
      >
        {HEADLINE[status](source)}
        {status === "failed" && source.consecutive_failures > 1 && (
          <span> · {source.consecutive_failures} in a row</span>
        )}
      </div>
      <div className="mt-2">
        <Sparkline daily={source.daily} />
      </div>
      <div className="mt-1.5 flex justify-between text-xs text-muted">
        <span>
          {syncs} syncs · {failures} ✕
        </span>
        <span>{formatBytes(bytes)}</span>
      </div>
    </Link>
  );
}
