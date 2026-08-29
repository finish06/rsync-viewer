import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { SourceHealth } from "../../api/types";
import { renderWithProviders } from "../../test/render";
import { isActive, SourceGrid } from "./SourceGrid";

function source(
  name: string,
  overrides: Partial<SourceHealth> = {},
): SourceHealth {
  return {
    source_name: name,
    last_sync_at: "2026-03-19T22:33:00Z",
    last_status: "ok",
    last_exit_code: 0,
    consecutive_failures: 0,
    expected_interval_hours: null,
    is_stale: false,
    daily: Array.from({ length: 14 }, (_, i) => ({
      date: `2026-08-${String(16 + i).padStart(2, "0")}`,
      syncs: 0,
      failures: 0,
      bytes: 0,
    })),
    ...overrides,
  };
}

const busy = source("movies", {
  daily: [{ date: "2026-08-29", syncs: 2, failures: 0, bytes: 10 }],
});
const failed = source("nas", { last_status: "failed", last_exit_code: 11 });
const stale = source("photos", { is_stale: true });
const quiet1 = source("e2e-old-1");
const quiet2 = source("e2e-old-2");

describe("isActive", () => {
  it("keeps sources with activity or that need attention", () => {
    expect(isActive(busy)).toBe(true);
    expect(isActive(failed)).toBe(true);
    expect(isActive(stale)).toBe(true);
    expect(isActive(quiet1)).toBe(false);
  });
});

describe("SourceGrid (AC-006)", () => {
  it("hides quiet sources behind a toggle by default", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <SourceGrid sources={[quiet1, busy, failed, quiet2, stale]} />,
    );
    expect(screen.getAllByTestId("source-card")).toHaveLength(3);
    const toggle = screen.getByTestId("toggle-inactive");
    expect(toggle).toHaveTextContent("Show 2 inactive sources");

    await user.click(toggle);
    expect(screen.getAllByTestId("source-card")).toHaveLength(5);
    expect(toggle).toHaveTextContent("Hide 2 inactive sources");
  });

  it("renders no toggle when every source is active", () => {
    renderWithProviders(<SourceGrid sources={[busy, failed]} />);
    expect(screen.queryByTestId("toggle-inactive")).not.toBeInTheDocument();
  });

  it("explains an all-quiet window", () => {
    renderWithProviders(<SourceGrid sources={[quiet1]} />);
    expect(
      screen.getByText("No source has synced in this window."),
    ).toBeInTheDocument();
    expect(screen.getByTestId("toggle-inactive")).toHaveTextContent(
      "Show 1 inactive source",
    );
  });
});
