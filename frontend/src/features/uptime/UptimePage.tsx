import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useSyntheticHistory, useSyntheticStatus } from "../../api/hooks";
import type { SyntheticCheck } from "../../api/types";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { formatPercent, formatRelative, formatTime } from "../../lib/format";

const HISTORY = 100;

/** Uptime page (AC-004, AC-007): synthetic check history and latency. */
export function UptimePage() {
  const status = useSyntheticStatus();
  const history = useSyntheticHistory(HISTORY);

  // API returns newest first; the timeline reads oldest → newest left to right.
  const checks = useMemo(
    () => [...(history.data ?? [])].reverse(),
    [history.data],
  );
  const failures = useMemo(
    () =>
      (history.data ?? []).filter((c) => c.status === "failing").slice(0, 10),
    [history.data],
  );
  const latency = useMemo(
    () =>
      checks.map((c) => ({
        t: c.checked_at,
        ms: Math.round(c.latency_ms),
      })),
    [checks],
  );

  if (status.isPending) return <Skeleton className="h-40" />;
  if (status.isError || !status.data) {
    return (
      <ErrorCard
        message="Could not load synthetic status."
        onRetry={() => void status.refetch()}
      />
    );
  }
  const s = status.data;

  if (!s.enabled) {
    return (
      <Panel title="Synthetic check" testId="uptime-page">
        <div data-status="disabled" className="flex items-center gap-2 text-sm">
          <span
            className="h-2.5 w-2.5 rounded-full border border-neutral"
            aria-hidden
          />
          <span>Synthetic monitoring is off.</span>
        </div>
        <EmptyNote>
          The hub can post a canned rsync log to itself every few minutes and
          record whether the round trip works. Turn it on under{" "}
          <a
            href="/settings#monitoring"
            className="text-primary hover:underline"
          >
            Settings → Monitoring
          </a>{" "}
          (operator or admin).
        </EmptyNote>
      </Panel>
    );
  }

  return (
    <div className="space-y-4" data-testid="uptime-page">
      <Panel title="Synthetic check" testId="uptime-header">
        <div
          className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
          data-status={s.status}
        >
          <span
            className="inline-flex items-center gap-2 font-semibold"
            style={{ color: "var(--status)" }}
          >
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: "var(--status)" }}
              aria-hidden
            />
            {s.status.toUpperCase()}
          </span>
          <span className="text-muted">
            every {Math.round(s.interval_seconds / 60)} min
          </span>
          <span className="text-muted">
            last {formatRelative(s.last_check_at)}
          </span>
          {s.last_latency_ms !== null && (
            <span className="text-muted">
              {Math.round(s.last_latency_ms)} ms
            </span>
          )}
        </div>
        <dl
          className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4"
          data-testid="uptime-stats"
        >
          <Stat label="24h uptime" value={formatPercent(s.uptime_24h_pct)} />
          <Stat label="7d uptime" value={formatPercent(s.uptime_7d_pct)} />
          <Stat label="checks (24h)" value={String(s.checks_24h)} />
          <Stat
            label="failed (recent)"
            value={String(failures.length)}
            danger={failures.length > 0}
          />
        </dl>
      </Panel>

      <Panel
        title={`Last ${checks.length} checks`}
        aside="oldest → newest"
        testId="uptime-timeline"
      >
        {history.isPending && <Skeleton className="h-6" />}
        {history.isError && (
          <ErrorCard
            message="Could not load check history."
            onRetry={() => void history.refetch()}
          />
        )}
        {history.isSuccess && checks.length === 0 && (
          <EmptyNote>No checks recorded yet.</EmptyNote>
        )}
        {checks.length > 0 && (
          <ol className="flex flex-wrap gap-0.5" aria-label="Check timeline">
            {checks.map((c) => (
              <TimelineCell key={c.checked_at} check={c} />
            ))}
          </ol>
        )}
      </Panel>

      <Panel title="Latency (ms)" testId="uptime-latency">
        {latency.length > 1 ? (
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={latency}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="t"
                tickFormatter={(v: string) => formatTime(v)}
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
                minTickGap={24}
              />
              <YAxis width={48} tick={{ fontSize: 11 }} stroke="var(--muted)" />
              <Tooltip labelFormatter={(l) => formatRelative(String(l))} />
              <Line
                type="monotone"
                dataKey="ms"
                stroke="var(--primary)"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <EmptyNote>Not enough checks for a chart yet.</EmptyNote>
        )}
      </Panel>

      <Panel title="Recent failures" testId="uptime-failures">
        {failures.length === 0 ? (
          <EmptyNote>No failing checks in the recent history.</EmptyNote>
        ) : (
          <ul className="divide-y divide-border text-sm">
            {failures.map((f) => (
              <li key={f.checked_at} className="flex gap-3 py-1.5">
                <span className="shrink-0 tabular-nums text-muted">
                  {formatRelative(f.checked_at)}
                </span>
                <span className="font-mono text-xs text-danger">
                  {f.error ?? "unknown error"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}

function Stat({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-muted">{label}</dt>
      <dd
        className={`text-xl font-semibold tabular-nums ${danger ? "text-danger" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

function TimelineCell({ check }: { check: SyntheticCheck }) {
  const label = `${formatRelative(check.checked_at)}: ${check.status}${check.error ? ` — ${check.error}` : ""} (${Math.round(check.latency_ms)} ms)`;
  return (
    <li
      data-testid="timeline-cell"
      data-status={check.status}
      title={label}
      aria-label={label}
      className="h-5 w-2.5 rounded-sm"
      style={{ background: "var(--status)" }}
    />
  );
}
