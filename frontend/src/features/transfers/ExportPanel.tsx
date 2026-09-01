import { useState } from "react";

import { useSources } from "../../api/hooks";
import {
  buildExportUrl,
  type ExportFormat,
  exportFilename,
  triggerDownload,
} from "./exportUrl";

const MAX_ROWS_NOTE = "up to 10,000 rows, newest first";

export interface ExportPanelProps {
  /** Prefilled from the page's current filters; both editable here. */
  from?: string;
  to?: string;
  onClose: () => void;
  /** Injected in tests; defaults to a real browser download. */
  onDownload?: (url: string, filename: string) => void;
}

/** Export dialog for the Transfers page (specs/csv-export-ui.md AC-004..007). */
export function ExportPanel({
  from = "",
  to = "",
  onClose,
  onDownload = triggerDownload,
}: ExportPanelProps) {
  const sources = useSources();
  const known = sources.data ?? [];
  const [all, setAll] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [includeSynthetic, setIncludeSynthetic] = useState(false);
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [fromDate, setFromDate] = useState(from);
  const [toDate, setToDate] = useState(to);

  const chosen = all ? [] : selected;
  const nothingSelected = !all && selected.length === 0;

  function toggleSource(name: string) {
    setSelected((current) =>
      current.includes(name)
        ? current.filter((s) => s !== name)
        : [...current, name],
    );
  }

  function download() {
    const url = buildExportUrl({
      sources: chosen,
      format,
      includeSynthetic,
      from: fromDate,
      to: toDate,
    });
    onDownload(url, exportFilename(format));
    onClose();
  }

  return (
    <div
      data-testid="export-panel"
      className="card absolute right-0 z-20 mt-1 w-72 space-y-3 p-3 text-sm shadow-lg"
    >
      <p className="font-medium">Export transfers</p>

      <div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={all}
            onChange={(e) => setAll(e.target.checked)}
          />
          All sources
        </label>
        {!all && (
          <div
            data-testid="export-sources"
            className="mt-1 max-h-40 space-y-1 overflow-y-auto border-l border-border pl-3"
          >
            {known.map((name) => (
              <label key={name} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selected.includes(name)}
                  onChange={() => toggleSource(name)}
                />
                <span className="truncate">{name}</span>
              </label>
            ))}
            {known.length === 0 && (
              <p className="text-xs text-muted">No sources yet.</p>
            )}
          </div>
        )}
      </div>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={includeSynthetic}
          onChange={(e) => setIncludeSynthetic(e.target.checked)}
        />
        Include synthetic checks
      </label>

      <div className="flex items-center gap-2">
        <label className="flex flex-1 flex-col gap-1 text-xs text-muted">
          From
          <input
            type="date"
            aria-label="Export from"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className="rounded border border-border bg-card px-2 py-1 text-sm text-text"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1 text-xs text-muted">
          To
          <input
            type="date"
            aria-label="Export to"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            className="rounded border border-border bg-card px-2 py-1 text-sm text-text"
          />
        </label>
      </div>

      <label className="flex items-center gap-2">
        <span className="text-muted">Format</span>
        <select
          aria-label="Format"
          value={format}
          onChange={(e) => setFormat(e.target.value as ExportFormat)}
          className="rounded border border-border bg-card px-2 py-1"
        >
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
        </select>
      </label>

      <p className="text-xs text-muted">
        {nothingSelected
          ? "Select at least one source."
          : `Exports ${MAX_ROWS_NOTE}.`}
      </p>

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-border px-2 py-1 text-muted"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={download}
          disabled={nothingSelected}
          className="rounded bg-primary px-2 py-1 text-white disabled:opacity-50"
        >
          Download
        </button>
      </div>
    </div>
  );
}
