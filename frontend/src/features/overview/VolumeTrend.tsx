import { Area, AreaChart, Tooltip } from "recharts";

import type { SourceHealth } from "../../api/types";
import { formatBytes } from "../../lib/format";

/** Ambient bytes/day mini-chart summed across sources (overview-v2 AC-004). */
export function VolumeTrend({ sources }: { sources: SourceHealth[] }) {
  const byDate = new Map<string, number>();
  for (const source of sources) {
    for (const day of source.daily) {
      byDate.set(day.date, (byDate.get(day.date) ?? 0) + day.bytes);
    }
  }
  const data = [...byDate.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, bytes]) => ({ date, bytes }));
  const total = data.reduce((n, d) => n + d.bytes, 0);

  return (
    <div
      data-testid="volume-trend"
      className="flex items-center gap-2"
      title="Transferred per day across all sources"
    >
      <AreaChart width={140} height={32} data={data}>
        <Tooltip
          formatter={(value) => [formatBytes(Number(value)), "transferred"]}
          labelFormatter={(label) => String(label)}
        />
        <Area
          dataKey="bytes"
          stroke="var(--primary)"
          fill="var(--primary)"
          fillOpacity={0.25}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
      </AreaChart>
      <span className="text-xs text-muted">
        {formatBytes(total)}
        <span className="hidden sm:inline"> / 14d</span>
      </span>
    </div>
  );
}
