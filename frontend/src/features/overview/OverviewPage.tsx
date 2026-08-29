import { format, subDays } from "date-fns";

import { useSourcesHealth, useSyncLogs } from "../../api/hooks";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { ActivityStrip } from "./ActivityStrip";
import { NewThisWeek } from "./NewThisWeek";
import { SourceCard } from "./SourceCard";

const ACTIVITY_DAYS = 7;

/** Overview (AC-006, AC-008, AC-026): is everything OK, and what happened? */
export function OverviewPage() {
  const health = useSourcesHealth(14);
  const since = format(subDays(new Date(), ACTIVITY_DAYS - 1), "yyyy-MM-dd");
  const activity = useSyncLogs({
    start_date: since,
    limit: 100,
    synthetic: "hide",
  });

  const noSourcesEver = health.isSuccess && health.data.length === 0;

  return (
    <div className="space-y-6">
      <Panel title="Sources" aside="last 14 days" testId="sources-panel">
        {health.isPending && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
        )}
        {health.isError && (
          <ErrorCard
            message="Could not load source health."
            onRetry={() => void health.refetch()}
          />
        )}
        {noSourcesEver && <WaitingForFirstSync />}
        {health.isSuccess && health.data.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {health.data.map((source) => (
              <SourceCard key={source.source_name} source={source} />
            ))}
          </div>
        )}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Panel title="New this week" testId="media-panel">
          <NewThisWeek />
        </Panel>
        <Panel
          title="Activity"
          aside={`last ${ACTIVITY_DAYS} days`}
          testId="activity-panel"
        >
          {activity.isPending && (
            <div className="space-y-2">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-8" />
              ))}
            </div>
          )}
          {activity.isError && (
            <ErrorCard
              message="Could not load recent transfers."
              onRetry={() => void activity.refetch()}
            />
          )}
          {activity.isSuccess && (
            <ActivityStrip
              items={activity.data.items.filter((i) => !i.is_dry_run)}
            />
          )}
        </Panel>
      </div>
    </div>
  );
}

function WaitingForFirstSync() {
  return (
    <div data-testid="empty-overview" className="py-4 text-center">
      <p className="text-lg font-semibold">Waiting for your first sync</p>
      <EmptyNote>
        Point an rsync job at this hub and its source will appear here.{" "}
        <a href="/settings#monitoring" className="text-primary hover:underline">
          Open monitoring setup
        </a>
      </EmptyNote>
    </div>
  );
}
