import { useState } from "react";

import type { SourceHealth } from "../../api/types";
import { cardStatus, SourceCard } from "./SourceCard";
import { SourceRow } from "./SourceRow";

/** A source earns attention by default if it did anything in the window or needs it. */
export function isActive(source: SourceHealth): boolean {
  if (cardStatus(source) !== "ok") return true;
  return source.daily.some((d) => d.syncs > 0);
}

function isProblem(source: SourceHealth): boolean {
  const status = cardStatus(source);
  return status === "failed" || status === "stale";
}

/** Problem sources get cards, healthy ones compact rows (overview-v2 AC-002). */
export function SourceGrid({ sources }: { sources: SourceHealth[] }) {
  const [showInactive, setShowInactive] = useState(false);
  const active = sources.filter(isActive);
  const inactive = sources.filter((s) => !isActive(s));
  const visible = showInactive ? sources : active;
  const problems = visible.filter(isProblem);
  const healthy = visible.filter((s) => !isProblem(s));

  return (
    <div>
      {problems.length > 0 && (
        <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {problems.map((source) => (
            <SourceCard key={source.source_name} source={source} />
          ))}
        </div>
      )}
      {healthy.length > 0 && (
        <div className="divide-y divide-border">
          {healthy.map((source) => (
            <SourceRow key={source.source_name} source={source} />
          ))}
        </div>
      )}
      {visible.length === 0 && (
        <p className="text-sm text-muted">
          No source has synced in this window.
        </p>
      )}
      {inactive.length > 0 && (
        <button
          type="button"
          data-testid="toggle-inactive"
          aria-expanded={showInactive}
          onClick={() => setShowInactive((v) => !v)}
          className="mt-3 text-xs text-muted hover:text-text"
        >
          {showInactive ? "Hide" : "Show"} {inactive.length} inactive{" "}
          {inactive.length === 1 ? "source" : "sources"} (no syncs in this
          window)
        </button>
      )}
    </div>
  );
}
