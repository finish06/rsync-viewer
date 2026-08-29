import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";

import { useSyncLog } from "../../api/hooks";
import { ErrorCard, Skeleton } from "../../components/Panel";
import { formatBytes } from "../../lib/format";

const VIRTUALISE_ABOVE = 200;
const RAW_TAIL_LINES = 12;

interface SyncDetailProps {
  id: string;
  failed: boolean;
}

/** Inline detail: failure output tail, stats, and the (virtualised) file list. */
export function SyncDetail({ id, failed }: SyncDetailProps) {
  const { data, isPending, isError, refetch } = useSyncLog(id);

  if (isPending) {
    return (
      <div className="space-y-2 px-4 py-3" data-testid="sync-detail-loading">
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="px-4 py-3">
        <ErrorCard
          message="Could not load transfer details."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const files = data.file_list ?? [];
  const rawTail = data.raw_content
    .trim()
    .split("\n")
    .slice(-RAW_TAIL_LINES)
    .join("\n");

  return (
    <div
      data-testid="sync-detail"
      className="space-y-3 bg-bg-secondary/60 px-4 py-3 text-sm"
    >
      {failed && (
        <pre className="overflow-x-auto rounded-md bg-code-bg p-3 font-mono text-xs text-code-text">
          {rawTail}
        </pre>
      )}
      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted">
        <div>
          <dt className="inline">sent </dt>
          <dd className="inline text-text">{formatBytes(data.bytes_sent)}</dd>
        </div>
        <div>
          <dt className="inline">received </dt>
          <dd className="inline text-text">
            {formatBytes(data.bytes_received)}
          </dd>
        </div>
        <div>
          <dt className="inline">total size </dt>
          <dd className="inline text-text">
            {formatBytes(data.total_size_bytes)}
          </dd>
        </div>
        {data.speedup_ratio !== null && (
          <div>
            <dt className="inline">speedup </dt>
            <dd className="inline text-text">
              {data.speedup_ratio.toFixed(2)}×
            </dd>
          </div>
        )}
      </dl>
      <FileList files={files} />
    </div>
  );
}

function FileList({ files }: { files: string[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtual = files.length > VIRTUALISE_ABOVE;
  const rowVirtualizer = useVirtualizer({
    count: files.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 22,
    overscan: 20,
    enabled: virtual,
  });

  if (files.length === 0) {
    return <p className="text-xs text-muted">No files transferred.</p>;
  }

  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted">
        files ({files.length.toLocaleString()})
      </p>
      <div
        ref={parentRef}
        data-testid="file-list"
        className="max-h-64 overflow-auto rounded-md border border-border bg-card font-mono text-xs"
      >
        {virtual ? (
          <div
            style={{
              height: rowVirtualizer.getTotalSize(),
              position: "relative",
            }}
          >
            {rowVirtualizer.getVirtualItems().map((row) => (
              <div
                key={row.key}
                className="truncate px-2 leading-[22px]"
                style={{
                  position: "absolute",
                  top: 0,
                  transform: `translateY(${row.start}px)`,
                  width: "100%",
                }}
                title={files[row.index]}
              >
                {files[row.index]}
              </div>
            ))}
          </div>
        ) : (
          files.map((file) => (
            <div
              key={file}
              className="truncate px-2 leading-[22px]"
              title={file}
            >
              {file}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
