import { useState } from "react";

import type { SyncLogListItem } from "../../api/types";
import { dayLabel, formatBytes, localDayKey } from "../../lib/format";
import { isFailed, SyncRow } from "../transfers/SyncRow";

export interface DayGroup {
  key: string;
  items: SyncLogListItem[];
  syncs: number;
  failed: number;
  bytes: number;
  topSources: string[];
}

/** Group transfers by local calendar day, newest day first (AC-008). */
export function groupByDay(items: SyncLogListItem[]): DayGroup[] {
  const groups = new Map<string, DayGroup>();
  for (const item of items) {
    const key = localDayKey(item.start_time);
    let group = groups.get(key);
    if (!group) {
      group = { key, items: [], syncs: 0, failed: 0, bytes: 0, topSources: [] };
      groups.set(key, group);
    }
    group.items.push(item);
    group.syncs += 1;
    if (isFailed(item)) group.failed += 1;
    group.bytes += item.bytes_received ?? 0;
  }
  for (const group of groups.values()) {
    const counts = new Map<string, number>();
    for (const item of group.items)
      counts.set(item.source_name, (counts.get(item.source_name) ?? 0) + 1);
    group.topSources = [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([name]) => name);
  }
  return [...groups.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
}

export function ActivityStrip({ items }: { items: SyncLogListItem[] }) {
  const groups = groupByDay(items);
  const [openDay, setOpenDay] = useState<string | null>(groups[0]?.key ?? null);

  if (groups.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted">
        No transfers in the last 7 days.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-border" data-testid="activity-strip">
      {groups.map((group) => {
        const open = openDay === group.key;
        return (
          <li key={group.key} data-testid="activity-day">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpenDay(open ? null : group.key)}
              className="flex w-full items-center gap-3 px-2 py-2 text-left text-sm hover:bg-bg-secondary"
            >
              <span className="w-4 text-muted" aria-hidden>
                {open ? "▾" : "▸"}
              </span>
              <span className="w-24 font-medium">{dayLabel(group.key)}</span>
              <span className="text-muted">{group.syncs} syncs</span>
              <span className={group.failed ? "text-danger" : "text-muted"}>
                {group.failed} ✕
              </span>
              <span className="tabular-nums">{formatBytes(group.bytes)}</span>
              <span className="ml-auto hidden truncate text-xs text-muted sm:inline">
                {group.topSources.join(" · ")}
              </span>
            </button>
            {open && (
              <div className="pb-2 pl-6">
                {group.items.map((item) => (
                  <SyncRow key={item.id} item={item} />
                ))}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
