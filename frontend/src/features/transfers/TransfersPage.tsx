import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";

import { useInfiniteSyncLogs, useSources } from "../../api/hooks";
import type { SyncLogListItem } from "../../api/types";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { dayLabel, formatBytes, localDayKey } from "../../lib/format";
import {
  DEFAULT_FILTERS,
  filtersFromSearch,
  filtersToParams,
  filtersToSearch,
  type RangeKey,
  type TransferFilters,
} from "./filters";
import { ExportPanel } from "./ExportPanel";
import { isFailed, SyncRow } from "./SyncRow";

interface SourceGroup {
  source: string;
  items: SyncLogListItem[];
  failed: number;
  bytes: number;
}
interface DayGroup {
  key: string;
  sources: SourceGroup[];
  syncs: number;
  failed: number;
  bytes: number;
  files: number;
}

/** day → source → sync (AC-009), newest day first. */
export function groupDaySource(items: SyncLogListItem[]): DayGroup[] {
  const days = new Map<string, DayGroup>();
  for (const item of items) {
    const key = localDayKey(item.start_time);
    let day = days.get(key);
    if (!day) {
      day = { key, sources: [], syncs: 0, failed: 0, bytes: 0, files: 0 };
      days.set(key, day);
    }
    let group = day.sources.find((s) => s.source === item.source_name);
    if (!group) {
      group = { source: item.source_name, items: [], failed: 0, bytes: 0 };
      day.sources.push(group);
    }
    const failed = isFailed(item);
    group.items.push(item);
    group.failed += failed ? 1 : 0;
    group.bytes += item.bytes_received ?? 0;
    day.syncs += 1;
    day.failed += failed ? 1 : 0;
    day.bytes += item.bytes_received ?? 0;
    day.files += item.file_count ?? 0;
  }
  return [...days.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
}

const RANGES: RangeKey[] = ["7d", "30d", "90d", "custom"];

export function TransfersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = useMemo(
    () => filtersFromSearch(searchParams),
    [searchParams],
  );
  const setFilters = (next: TransferFilters) =>
    setSearchParams(filtersToSearch(next), { replace: true });

  const sources = useSources();
  const [exportOpen, setExportOpen] = useState(false);
  const params = filtersToParams(filters);
  const query = useInfiniteSyncLogs(params);
  const items = useMemo(() => {
    const all = query.data?.pages.flatMap((p) => p.items) ?? [];
    return all.filter(
      (i) =>
        (filters.dryRuns || !i.is_dry_run) &&
        (filters.status === "all" || isFailed(i)),
    );
  }, [query.data, filters.dryRuns, filters.status]);
  const groups = useMemo(() => groupDaySource(items), [items]);

  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = sentinel.current;
    if (
      !node ||
      !query.hasNextPage ||
      typeof IntersectionObserver === "undefined"
    )
      return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && !query.isFetchingNextPage)
        void query.fetchNextPage();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [query]);

  return (
    <div className="space-y-4">
      <div
        className="card flex flex-wrap items-center gap-3 p-3 text-sm"
        data-testid="transfer-filters"
      >
        <label className="flex items-center gap-1">
          <span className="text-muted">Source</span>
          <select
            aria-label="Source"
            value={filters.source}
            onChange={(e) => setFilters({ ...filters, source: e.target.value })}
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
        <div role="group" aria-label="Range" className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              aria-pressed={filters.range === r}
              onClick={() => setFilters({ ...filters, range: r })}
              className={`rounded px-2 py-1 ${filters.range === r ? "bg-primary text-white" : "border border-border text-muted"}`}
            >
              {r === "custom" ? "Custom" : r}
            </button>
          ))}
        </div>
        {filters.range === "custom" && (
          <span className="flex items-center gap-1">
            <input
              type="date"
              aria-label="From"
              value={filters.from}
              onChange={(e) => setFilters({ ...filters, from: e.target.value })}
              className="rounded border border-border bg-card px-2 py-1"
            />
            <span className="text-muted">→</span>
            <input
              type="date"
              aria-label="To"
              value={filters.to}
              onChange={(e) => setFilters({ ...filters, to: e.target.value })}
              className="rounded border border-border bg-card px-2 py-1"
            />
          </span>
        )}
        <div role="group" aria-label="Status" className="flex gap-1">
          {(["all", "failed"] as const).map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={filters.status === s}
              onClick={() => setFilters({ ...filters, status: s })}
              className={`rounded px-2 py-1 ${filters.status === s ? "bg-primary text-white" : "border border-border text-muted"}`}
            >
              {s === "all" ? "All" : "Failed"}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1 text-muted">
          <input
            type="checkbox"
            checked={filters.dryRuns}
            onChange={(e) =>
              setFilters({ ...filters, dryRuns: e.target.checked })
            }
          />
          dry runs
        </label>
        <div className="relative ml-auto">
          <button
            type="button"
            onClick={() => setExportOpen((v) => !v)}
            aria-expanded={exportOpen}
            className="rounded border border-border px-2 py-1 text-muted hover:text-text"
          >
            Export
          </button>
          {exportOpen && (
            <ExportPanel
              from={params.start_date}
              to={params.end_date}
              onClose={() => setExportOpen(false)}
            />
          )}
        </div>
        {searchParams.toString() !== "" && (
          <button
            type="button"
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className="text-xs text-primary hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      <Panel title="Transfers" testId="transfers-page">
        {query.isPending && (
          <div className="space-y-2">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-8" />
            ))}
          </div>
        )}
        {query.isError && (
          <ErrorCard
            message="Could not load transfers."
            onRetry={() => void query.refetch()}
          />
        )}
        {query.isSuccess && groups.length === 0 && (
          <EmptyNote>
            No transfers match.{" "}
            <button
              type="button"
              className="text-primary hover:underline"
              onClick={() => setFilters(DEFAULT_FILTERS)}
            >
              Clear filters
            </button>
          </EmptyNote>
        )}
        {groups.map((day) => (
          <DaySection key={day.key} day={day} />
        ))}
        <div ref={sentinel} />
        {query.hasNextPage && (
          <button
            type="button"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
            className="mt-3 w-full rounded border border-border py-1.5 text-sm text-muted hover:text-text"
          >
            {query.isFetchingNextPage ? "Loading…" : "Load more"}
          </button>
        )}
      </Panel>
    </div>
  );
}

function DaySection({ day }: { day: DayGroup }) {
  const [open, setOpen] = useState(true);
  return (
    <section
      data-testid="transfer-day"
      className="border-t border-border first:border-t-0"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 py-2 text-left text-sm hover:bg-bg-secondary"
      >
        <span className="w-4 text-muted" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="font-semibold">{dayLabel(day.key)}</span>
        <span className="text-muted">
          {day.syncs} syncs ·{" "}
          <span className={day.failed ? "text-danger" : ""}>
            {day.failed} failed
          </span>{" "}
          · {formatBytes(day.bytes)} · {day.files.toLocaleString()} files
        </span>
      </button>
      {open &&
        day.sources.map((group) => (
          <SourceSection key={group.source} group={group} />
        ))}
    </section>
  );
}

function SourceSection({ group }: { group: SourceGroup }) {
  const [open, setOpen] = useState(true);
  return (
    <div data-testid="transfer-source" className="pl-4">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 py-1 text-left text-sm hover:bg-bg-secondary"
      >
        <span className="w-4 text-muted" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="font-medium">{group.source}</span>
        <span className="text-muted">
          {group.items.length} {group.items.length === 1 ? "sync" : "syncs"}
          {group.failed > 0 && (
            <span className="text-danger"> · {group.failed} failed</span>
          )}{" "}
          · {formatBytes(group.bytes)}
        </span>
      </button>
      {open && (
        <div className="pl-4">
          {group.items.map((item) => (
            <SyncRow key={item.id} item={item} showSource={false} />
          ))}
        </div>
      )}
    </div>
  );
}
