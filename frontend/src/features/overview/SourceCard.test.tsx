import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SourceHealth } from "../../api/types";
import { renderWithProviders } from "../../test/render";
import { cardStatus, SourceCard } from "./SourceCard";

function source(overrides: Partial<SourceHealth>): SourceHealth {
  return {
    source_name: "movies",
    last_sync_at: new Date(Date.now() - 5 * 60_000).toISOString(),
    last_status: "ok",
    last_exit_code: 0,
    consecutive_failures: 0,
    expected_interval_hours: null,
    is_stale: false,
    daily: Array.from({ length: 14 }, (_, i) => ({
      date: `2026-08-${String(16 + i).padStart(2, "0")}`,
      syncs: i % 3 === 0 ? 2 : 1,
      failures: i === 13 ? 1 : 0,
      bytes: 1024 ** 3,
    })),
    ...overrides,
  };
}

describe("cardStatus (AC-006)", () => {
  it("maps health to a card colour with failure taking precedence over staleness", () => {
    expect(cardStatus(source({}))).toBe("ok");
    expect(
      cardStatus(source({ last_status: "failed", last_exit_code: 11 })),
    ).toBe("failed");
    expect(cardStatus(source({ is_stale: true }))).toBe("stale");
    expect(cardStatus(source({ last_status: "failed", is_stale: true }))).toBe(
      "failed",
    );
    expect(
      cardStatus(source({ last_status: "never", last_sync_at: null })),
    ).toBe("never");
  });
});

describe("SourceCard", () => {
  it("shows relative last-sync time, totals, and links to filtered transfers", () => {
    renderWithProviders(<SourceCard source={source({})} />);
    const card = screen.getByTestId("source-card");
    expect(card).toHaveTextContent(/synced 5 minutes ago/);
    expect(card).toHaveTextContent("19 syncs · 1 ✕");
    expect(card).toHaveTextContent("14.0 GB");
    expect(card).toHaveAttribute("href", "/app/transfers?source=movies");
  });

  it("explains a failure streak and a stale source", () => {
    renderWithProviders(
      <SourceCard
        source={source({
          source_name: "nas",
          last_status: "failed",
          consecutive_failures: 3,
        })}
      />,
    );
    expect(screen.getByTestId("source-card")).toHaveTextContent(
      /FAILED .* · 3 in a row/,
    );
  });

  it("handles a source that has never synced", () => {
    renderWithProviders(
      <SourceCard
        source={source({ last_status: "never", last_sync_at: null, daily: [] })}
      />,
    );
    expect(screen.getByTestId("source-card")).toHaveTextContent("never synced");
  });
});
