import { screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import type { SourceHealth } from "../../api/types";
import { sourcesHealth } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { AttentionStrip } from "./AttentionStrip";
import { nextDue } from "./cadence";
import { OverviewPage } from "./OverviewPage";
import { SourceRow } from "./SourceRow";
import { VolumeTrend } from "./VolumeTrend";

const HOUR = 3_600_000;

function source(overrides: Partial<SourceHealth>): SourceHealth {
  return {
    source_name: "movies",
    last_sync_at: new Date(Date.now() - 2 * HOUR).toISOString(),
    last_status: "ok",
    last_exit_code: 0,
    consecutive_failures: 0,
    expected_interval_hours: null,
    is_stale: false,
    daily: Array.from({ length: 14 }, (_, i) => ({
      date: new Date(Date.now() - (13 - i) * 24 * HOUR)
        .toISOString()
        .slice(0, 10),
      syncs: 1,
      failures: 0,
      bytes: 2 * 1024 ** 3,
    })),
    ...overrides,
  };
}

describe("nextDue (AC-003)", () => {
  it("uses the monitor interval when present", () => {
    const due = nextDue(
      source({
        expected_interval_hours: 24,
        last_sync_at: new Date(Date.now() - 30 * HOUR).toISOString(),
      }),
    );
    expect(due).not.toBeNull();
    expect(Math.round(due!.overdueHours)).toBe(6);
  });

  it("infers a daily cadence from the history", () => {
    const due = nextDue(source({}));
    expect(due).not.toBeNull();
    expect(due!.overdueHours).toBeLessThan(0); // synced 2h ago, due in ~22h
    expect(Math.round(24 + due!.overdueHours)).toBe(2);
  });

  it("returns null without history or interval", () => {
    const active = source({}).daily.map((d, i) => ({
      ...d,
      syncs: i === 13 ? 1 : 0,
    }));
    expect(nextDue(source({ daily: active }))).toBeNull();
    expect(nextDue(source({ last_sync_at: null }))).toBeNull();
  });
});

describe("AttentionStrip (AC-001)", () => {
  it("shows one calm line when everything is healthy", async () => {
    renderWithProviders(
      <AttentionStrip sources={[source({}), source({ source_name: "tv" })]} />,
    );
    const strip = await screen.findByTestId("attention-strip");
    expect(strip).toHaveTextContent("All 2 sources healthy");
    await within(strip).findByText(/UP/);
    expect(screen.queryByTestId("attention-card")).not.toBeInTheDocument();
  });

  it("shows a loud card per problem with streak and overdue time", async () => {
    renderWithProviders(
      <AttentionStrip
        sources={[
          source({}),
          source({
            source_name: "nas-backup",
            last_status: "failed",
            consecutive_failures: 3,
            expected_interval_hours: 24,
            last_sync_at: new Date(Date.now() - 30 * HOUR).toISOString(),
          }),
        ]}
      />,
    );
    const card = await screen.findByTestId("attention-card");
    expect(card).toHaveTextContent("nas-backup");
    expect(card).toHaveTextContent("3 in a row");
    expect(card).toHaveTextContent(/overdue by ~6h/);
    expect(within(card).getByRole("link", { name: /view/i })).toHaveAttribute(
      "href",
      "/app/transfers?source=nas-backup",
    );
    expect(screen.queryByText(/sources healthy/)).not.toBeInTheDocument();
  });
});

describe("SourceRow (AC-002, AC-005)", () => {
  it("is a compact link row with due chip, sparkline, and tidy totals", () => {
    renderWithProviders(<SourceRow source={source({})} />);
    const row = screen.getByTestId("source-row");
    expect(row).toHaveAttribute("href", "/app/transfers?source=movies");
    expect(row).toHaveAttribute("data-status", "ok");
    expect(row).toHaveTextContent("movies");
    expect(row).toHaveTextContent(/due in ~22h/);
    expect(row).toHaveTextContent("14 syncs");
    expect(row).not.toHaveTextContent("0 ✕");
  });

  it("declutters: singular sync, dash under 1 KB", () => {
    const quiet = source({}).daily.map((d, i) => ({
      ...d,
      syncs: i === 13 ? 1 : 0,
      bytes: i === 13 ? 512 : 0,
    }));
    renderWithProviders(<SourceRow source={source({ daily: quiet })} />);
    const row = screen.getByTestId("source-row");
    expect(row).toHaveTextContent("1 sync");
    expect(row).not.toHaveTextContent("1 syncs");
    expect(row).toHaveTextContent("—");
  });
});

describe("VolumeTrend (AC-004)", () => {
  it("sums bytes per day across sources and labels the total", () => {
    renderWithProviders(
      <VolumeTrend sources={[source({}), source({ source_name: "tv" })]} />,
    );
    const trend = screen.getByTestId("volume-trend");
    // 2 sources × 14 days × 2 GB = 56 GB
    expect(trend).toHaveTextContent("56.0 GB");
  });
});

describe("OverviewPage split (AC-002, AC-006)", () => {
  it("renders problem cards and healthy rows from the fixtures", async () => {
    renderWithProviders(<OverviewPage />);
    // fixtures: movies ok, nas-backup failed, photos stale? — cards only for problems
    expect(await screen.findAllByTestId("attention-card")).not.toHaveLength(0);
    expect(screen.getAllByTestId("source-row").length).toBeGreaterThan(0);
    const failed = sourcesHealth.filter((s) => s.last_status === "failed");
    for (const s of failed) {
      expect(screen.queryByTestId("source-row")).not.toHaveTextContent(
        s.source_name,
      );
    }
  });

  it("keeps the calm strip when the API reports only healthy sources", async () => {
    server.use(
      http.get("/api/v1/sources/health", () =>
        HttpResponse.json([source({}), source({ source_name: "tv" })]),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByTestId("attention-strip")).toHaveTextContent(
      "All 2 sources healthy",
    );
    expect(screen.getByTestId("volume-trend")).toBeInTheDocument();
  });
});
