import { format, subDays } from "date-fns";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useSourceStats, useSources, useSummary } from "../../api/hooks";
import type { SummaryDataPoint, SummaryPeriod } from "../../api/types";
import { ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { formatBytes, formatDuration, formatRelative } from "../../lib/format";

const RANGE_DAYS: Record<string, number> = { "7d": 7, "30d": 30, "90d": 90 };
const PERIODS: SummaryPeriod[] = ["daily", "weekly", "monthly"];
const SYNC_ID = "trends";

export interface TrendsState {
  period: SummaryPeriod;
  range: string;
  source: string;
}

export function trendsFromSearch(search: URLSearchParams): TrendsState {
  const period = search.get("period");
  const range = search.get("range");
  return {
    period: PERIODS.includes(period as SummaryPeriod)
      ? (period as SummaryPeriod)
      : "daily",
    range: range && range in RANGE_DAYS ? range : "30d",
    source: search.get("source") ?? "",
  };
}

export function trendsToSearch(state: TrendsState): URLSearchParams {
  const search = new URLSearchParams();
  if (state.period !== "daily") search.set("period", state.period);
  if (state.range !== "30d") search.set("range", state.range);
  if (state.source) search.set("source", state.source);
  return search;
}

export function TrendsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const state = useMemo(() => trendsFromSearch(searchParams), [searchParams]);
  const setState = (next: TrendsState) =>
    setSearchParams(trendsToSearch(next), { replace: true });

  const end = format(new Date(), "yyyy-MM-dd");
  const start = format(
    subDays(new Date(), RANGE_DAYS[state.range] - 1),
    "yyyy-MM-dd",
  );
  const summary = useSummary({
    period: state.period,
    start,
    end,
    source: state.source || undefined,
  });
  const stats = useSourceStats({ start, end });
  const sources = useSources();

  const data = useMemo(
    () =>
      (summary.data?.data ?? []).map((d) => ({
        ...d,
        label: d.date.slice(5),
        avg_duration_seconds: d.avg_duration_seconds ?? 0,
      })),
    [summary.data],
  );

  const pointAt = (index: number | string | null | undefined) =>
    index === null || index === undefined ? undefined : data[Number(index)];

  function openDay(point: SummaryDataPoint | undefined) {
    if (!point) return;
    const params = new URLSearchParams({
      range: "custom",
      from: point.date.slice(0, 10),
      to: point.date.slice(0, 10),
    });
    if (state.source) params.set("source", state.source);
    void navigate(`/app/transfers?${params.toString()}`);
  }

  return (
    <div className="space-y-4">
      <div
        className="card flex flex-wrap items-center gap-3 p-3 text-sm"
        data-testid="trend-filters"
      >
        <label className="flex items-center gap-1">
          <span className="text-muted">Period</span>
          <select
            aria-label="Period"
            value={state.period}
            onChange={(e) =>
              setState({ ...state, period: e.target.value as SummaryPeriod })
            }
            className="rounded border border-border bg-card px-2 py-1"
          >
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {p[0].toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <div role="group" aria-label="Range" className="flex gap-1">
          {Object.keys(RANGE_DAYS).map((r) => (
            <button
              key={r}
              type="button"
              aria-pressed={state.range === r}
              onClick={() => setState({ ...state, range: r })}
              className={`rounded px-2 py-1 ${state.range === r ? "bg-primary text-white" : "border border-border text-muted"}`}
            >
              {r}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1">
          <span className="text-muted">Source</span>
          <select
            aria-label="Source"
            value={state.source}
            onChange={(e) => setState({ ...state, source: e.target.value })}
            className="rounded border border-border bg-card px-2 py-1"
          >
            <option value="">All</option>
            {(sources.data ?? []).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        {state.source && (
          <button
            type="button"
            onClick={() => setState({ ...state, source: "" })}
            className="text-xs text-primary hover:underline"
          >
            × clear source
          </button>
        )}
      </div>

      {summary.isError && (
        <ErrorCard
          message="Could not load trends."
          onRetry={() => void summary.refetch()}
        />
      )}

      <div className="grid gap-4 md:grid-cols-2" data-testid="trend-charts">
        <ChartPanel title="Bytes transferred" loading={summary.isPending}>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data}
              syncId={SYNC_ID}
              onClick={(e) => openDay(pointAt(e?.activeIndex))}
            >
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <YAxis
                tickFormatter={(v: number) => formatBytes(v)}
                width={64}
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <Tooltip
                formatter={(v) => formatBytes(Number(v))}
                labelFormatter={(l) => String(l)}
              />
              <Bar
                dataKey="total_bytes_transferred"
                name="bytes"
                fill="var(--primary)"
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
        <ChartPanel title="Files transferred" loading={summary.isPending}>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data}
              syncId={SYNC_ID}
              onClick={(e) => openDay(pointAt(e?.activeIndex))}
            >
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <YAxis width={48} tick={{ fontSize: 11 }} stroke="var(--muted)" />
              <Tooltip />
              <Bar
                dataKey="total_files_transferred"
                name="files"
                fill="var(--primary)"
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
        <ChartPanel title="Duration (avg)" loading={summary.isPending}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart
              data={data}
              syncId={SYNC_ID}
              onClick={(e) => openDay(pointAt(e?.activeIndex))}
            >
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <YAxis
                tickFormatter={(v: number) => formatDuration(v)}
                width={56}
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <Tooltip formatter={(v) => formatDuration(Number(v))} />
              <Line
                type="monotone"
                dataKey="avg_duration_seconds"
                name="avg duration"
                stroke="var(--primary)"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>
        <ChartPanel title="Success / failure" loading={summary.isPending}>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data}
              syncId={SYNC_ID}
              onClick={(e) => openDay(pointAt(e?.activeIndex))}
            >
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                stroke="var(--muted)"
              />
              <YAxis width={40} tick={{ fontSize: 11 }} stroke="var(--muted)" />
              <Tooltip />
              <Bar
                dataKey="successful_syncs"
                name="successful"
                stackId="s"
                fill="var(--ok)"
              />
              <Bar
                dataKey="failed_syncs"
                name="failed"
                stackId="s"
                fill="var(--danger)"
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      <Panel title="Sources" aside={`${start} → ${end}`} testId="source-table">
        {stats.isPending && <Skeleton className="h-24" />}
        {stats.isError && (
          <ErrorCard
            message="Could not load source stats."
            onRetry={() => void stats.refetch()}
          />
        )}
        {stats.isSuccess && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted">
                <tr>
                  <th className="py-1 pr-3">source</th>
                  <th className="py-1 pr-3 text-right">syncs</th>
                  <th className="py-1 pr-3 text-right">success</th>
                  <th className="py-1 pr-3 text-right">avg duration</th>
                  <th className="py-1 pr-3 text-right">avg bytes</th>
                  <th className="py-1 pr-3">last sync</th>
                </tr>
              </thead>
              <tbody>
                {stats.data.map((s) => {
                  const selected = state.source === s.source_name;
                  return (
                    <tr
                      key={s.source_name}
                      data-testid="source-row"
                      aria-selected={selected}
                      onClick={() =>
                        setState({
                          ...state,
                          source: selected ? "" : s.source_name,
                        })
                      }
                      className={`cursor-pointer border-t border-border hover:bg-bg-secondary ${selected ? "bg-bg-secondary font-medium" : ""}`}
                    >
                      <td className="py-1.5 pr-3">{s.source_name}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">
                        {s.total_syncs}
                      </td>
                      <td
                        className={`py-1.5 pr-3 text-right tabular-nums ${s.success_rate < 0.95 ? "text-danger" : ""}`}
                      >
                        {Math.round(s.success_rate * 100)}%
                      </td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">
                        {formatDuration(s.avg_duration_seconds)}
                      </td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">
                        {formatBytes(s.avg_bytes_transferred)}
                      </td>
                      <td className="py-1.5 pr-3 text-muted">
                        {formatRelative(s.last_sync_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function ChartPanel({
  title,
  loading,
  children,
}: {
  title: string;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="card p-3" data-testid="trend-chart">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
        {title}
      </h3>
      {loading ? <Skeleton className="h-[200px]" /> : children}
    </section>
  );
}
