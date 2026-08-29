import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { Route, Routes, useLocation } from "react-router";

import { summary } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { TrendsPage, trendsFromSearch, trendsToSearch } from "./TrendsPage";

function LocationProbe() {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname + location.search}
    </output>
  );
}

function renderPage(route = "/app/trends") {
  return renderWithProviders(
    <Routes>
      <Route
        path="/app/trends"
        element={
          <>
            <TrendsPage />
            <LocationProbe />
          </>
        }
      />
      <Route path="/app/transfers" element={<LocationProbe />} />
    </Routes>,
    { route },
  );
}

describe("trends state ⇄ URL", () => {
  it("round-trips and defaults", () => {
    expect(trendsFromSearch(new URLSearchParams())).toEqual({
      period: "daily",
      range: "30d",
      source: "",
    });
    const s = { period: "weekly" as const, range: "90d", source: "tv" };
    expect(trendsToSearch(s).toString()).toBe(
      "period=weekly&range=90d&source=tv",
    );
    expect(trendsFromSearch(trendsToSearch(s))).toEqual(s);
    expect(
      trendsFromSearch(new URLSearchParams("period=bogus&range=1y")).period,
    ).toBe("daily");
  });
});

describe("TrendsPage (AC-013–AC-015)", () => {
  it("renders four linked charts and the source table", async () => {
    renderPage();
    expect(await screen.findAllByTestId("source-row")).toHaveLength(2);
    expect(screen.getAllByTestId("trend-chart")).toHaveLength(4);
    const table = screen.getByTestId("source-table");
    expect(table).toHaveTextContent("movies");
    expect(table).toHaveTextContent("86%");
  });

  it("clicking a source row filters the charts by source and updates the URL", async () => {
    const user = userEvent.setup();
    let lastSummaryQuery = "";
    server.use(
      http.get("/api/v1/analytics/summary", ({ request }) => {
        lastSummaryQuery = new URL(request.url).search;
        return HttpResponse.json(summary);
      }),
    );
    renderPage();
    const rows = await screen.findAllByTestId("source-row");
    await user.click(within(rows[1]).getByText("nas-backup"));
    expect(screen.getByTestId("location")).toHaveTextContent(
      "?source=nas-backup",
    );
    expect(rows[1]).toHaveAttribute("aria-selected", "true");
    await screen.findByRole("button", { name: "× clear source" });
    expect(lastSummaryQuery).toContain("source=nas-backup");
  });

  it("range and period controls write to the URL", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findAllByTestId("source-row");
    await user.click(screen.getByRole("button", { name: "90d" }));
    await user.selectOptions(screen.getByLabelText("Period"), "weekly");
    expect(screen.getByTestId("location")).toHaveTextContent(
      "?period=weekly&range=90d",
    );
  });

  it("shows a retryable error when the summary fails", async () => {
    server.use(
      http.get("/api/v1/analytics/summary", () =>
        HttpResponse.json({ message: "x" }, { status: 500 }),
      ),
    );
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load trends.",
    );
  });
});
