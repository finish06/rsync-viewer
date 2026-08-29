import type { DailyPoint } from "../../api/types";

interface SparklineProps {
  daily: DailyPoint[];
  height?: number;
}

/** 14 bars, one per day: height = syncs, red segment = failures (AC-006). */
export function Sparkline({ daily, height = 28 }: SparklineProps) {
  const max = Math.max(1, ...daily.map((d) => d.syncs));
  const barWidth = 100 / Math.max(1, daily.length);
  return (
    <svg
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      className="block w-full"
      style={{ height }}
      role="img"
      aria-label={`Syncs per day for the last ${daily.length} days`}
    >
      {daily.map((point, i) => {
        const total = (point.syncs / max) * height;
        const failed = (Math.min(point.failures, point.syncs) / max) * height;
        const x = i * barWidth + barWidth * 0.15;
        const w = barWidth * 0.7;
        return (
          <g key={point.date}>
            <rect
              x={x}
              y={height - Math.max(total, point.syncs ? 1.5 : 0.6)}
              width={w}
              height={Math.max(total, point.syncs ? 1.5 : 0.6)}
              fill={point.syncs ? "var(--primary)" : "var(--border)"}
              opacity={point.syncs ? 0.75 : 1}
            >
              <title>{`${point.date}: ${point.syncs} syncs, ${point.failures} failed`}</title>
            </rect>
            {failed > 0 && (
              <rect
                x={x}
                y={height - failed}
                width={w}
                height={failed}
                fill="var(--danger)"
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}
