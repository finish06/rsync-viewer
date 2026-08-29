import { useState } from "react";

import type { SyncLogListItem } from "../../api/types";
import {
  durationBetween,
  formatBytes,
  formatDuration,
  formatTime,
} from "../../lib/format";
import { StatusDot } from "../../components/StatusDot";
import { SyncDetail } from "./SyncDetail";

export function isFailed(item: {
  exit_code?: number | null;
  status?: string;
}): boolean {
  return (item.exit_code ?? 0) !== 0 || item.status === "failed";
}

interface SyncRowProps {
  item: SyncLogListItem;
  showSource?: boolean;
  defaultOpen?: boolean;
}

/** One transfer; expands inline to files and failure detail (AC-010). */
export function SyncRow({
  item,
  showSource = true,
  defaultOpen = false,
}: SyncRowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const failed = isFailed(item);
  const duration = durationBetween(item.start_time, item.end_time);

  return (
    <div
      data-testid="sync-row"
      data-status={failed ? "failed" : "ok"}
      className="border-t border-border"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[auto_1fr_auto_auto_auto] items-center gap-3 px-2 py-1.5 text-left text-sm hover:bg-bg-secondary"
      >
        <StatusDot
          status={failed ? "failed" : "ok"}
          label={failed ? "failed" : "ok"}
          size="sm"
        />
        <span className="truncate">
          {showSource && (
            <span className="font-medium">{item.source_name} · </span>
          )}
          <span className="text-muted">{formatTime(item.start_time)}</span>
          {item.is_dry_run && (
            <span className="ml-2 rounded bg-warn/20 px-1 text-xs">
              dry run
            </span>
          )}
        </span>
        <span className="text-muted">{formatDuration(duration)}</span>
        <span className="tabular-nums">{formatBytes(item.bytes_received)}</span>
        <span className="tabular-nums text-muted">
          {failed ? `exit ${item.exit_code}` : `${item.file_count} files`}
        </span>
      </button>
      {open && <SyncDetail id={item.id} failed={failed} />}
    </div>
  );
}
