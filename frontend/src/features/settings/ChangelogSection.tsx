import { useState } from "react";

import { useChangelog, useUpdateCheck } from "../../api/hooks";
import type { ChangelogVersion } from "../../api/types";
import { ErrorCard, Panel, Skeleton } from "../../components/Panel";

export function ChangelogSection() {
  const [all, setAll] = useState(false);
  const changelog = useChangelog(all);
  const [open, setOpen] = useState<string | null>(null);
  const update = useUpdateCheck();
  const newer = update.data?.update_available ? update.data : null;

  return (
    <Panel
      title="Changelog"
      testId="changelog-section"
      aside={changelog.data && `current v${changelog.data.app_version}`}
    >
      {newer && newer.release_url && (
        <p
          data-testid="update-notice"
          className="mb-3 rounded-md border border-ok/50 bg-ok/5 p-2 text-sm"
        >
          v{newer.latest} is available —{" "}
          <a
            href={newer.release_url}
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            release notes
          </a>
        </p>
      )}
      {changelog.isPending && <Skeleton className="h-24" />}
      {changelog.isError && (
        <ErrorCard
          message="Could not load the changelog."
          onRetry={() => void changelog.refetch()}
        />
      )}
      {changelog.isSuccess && (
        <ul className="divide-y divide-border">
          {changelog.data.versions.map((version) => (
            <VersionRow
              key={version.version}
              version={version}
              current={version.version === changelog.data.app_version}
              open={open === version.version}
              onToggle={() =>
                setOpen(open === version.version ? null : version.version)
              }
            />
          ))}
        </ul>
      )}
      {changelog.isSuccess && changelog.data.has_more && !all && (
        <button
          type="button"
          onClick={() => setAll(true)}
          className="mt-3 text-sm text-primary hover:underline"
        >
          Show older versions
        </button>
      )}
    </Panel>
  );
}

function VersionRow({
  version,
  current,
  open,
  onToggle,
}: {
  version: ChangelogVersion;
  current: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <li data-testid="changelog-version">
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="flex w-full items-center gap-3 py-2 text-left text-sm hover:bg-bg-secondary"
      >
        <span className="w-4 text-muted" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="font-semibold">v{version.version}</span>
        {version.date && <span className="text-muted">{version.date}</span>}
        {current && (
          <span className="rounded bg-primary/15 px-1.5 text-xs text-primary">
            current
          </span>
        )}
      </button>
      {open && (
        <div className="pb-3 pl-7 text-sm">
          {Object.entries(version.sections).map(([section, items]) => (
            <div key={section} className="mb-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">
                {section}
              </p>
              <ul className="list-disc pl-5">
                {items.map((item, i) => (
                  <li key={i}>
                    {item.text}
                    {item.children.length > 0 && (
                      <ul className="list-[circle] pl-5 text-muted">
                        {item.children.map((child, j) => (
                          <li key={j}>{child}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </li>
  );
}
