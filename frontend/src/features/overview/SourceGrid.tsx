import { useState } from "react";

import type { SourceHealth } from "../../api/types";
import { cardStatus, SourceCard } from "./SourceCard";

/** A source earns a card by default if it did anything in the window or needs attention. */
export function isActive(source: SourceHealth): boolean {
  if (cardStatus(source) !== "ok") return true;
  return source.daily.some((d) => d.syncs > 0);
}

export function SourceGrid({ sources }: { sources: SourceHealth[] }) {
  const [showInactive, setShowInactive] = useState(false);
  const active = sources.filter(isActive);
  const inactive = sources.filter((s) => !isActive(s));
  const visible = showInactive ? sources : active;

  return (
    <div>
      {visible.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {visible.map((source) => (
            <SourceCard key={source.source_name} source={source} />
          ))}
        </div>
      ) : (
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
