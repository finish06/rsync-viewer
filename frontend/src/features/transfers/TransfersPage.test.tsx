import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { Route, Routes, useLocation } from "react-router";

import { syncLogs } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { groupDaySource, TransfersPage } from "./TransfersPage";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderPage(route = "/app/transfers") {
  return renderWithProviders(
    <Routes>
      <Route
        path="/app/transfers"
        element={
          <>
            <TransfersPage />
            <LocationProbe />
          </>
        }
      />
    </Routes>,
    { route },
  );
}

describe("groupDaySource (AC-009)", () => {
  it("nests day → source → sync with rollups", () => {
    const groups = groupDaySource(syncLogs.items);
    expect(groups[0].sources.map((s) => s.source)).toEqual([
      "nas-backup",
      "movies",
    ]);
    expect(groups[0]).toMatchObject({ syncs: 2, failed: 1, files: 3 });
    expect(groups[0].sources[0]).toMatchObject({ failed: 1, bytes: 0 });
    expect(groups.length).toBe(2);
  });
});

describe("TransfersPage (AC-009–AC-012)", () => {
  it("renders grouped days and sources with rollups and expands a sync inline", async () => {
    const user = userEvent.setup();
    renderPage();
    const days = await screen.findAllByTestId("transfer-day");
    expect(days[0]).toHaveTextContent("Today");
    expect(days[0]).toHaveTextContent("2 syncs · 1 failed");
    const sources = within(days[0]).getAllByTestId("transfer-source");
    expect(sources.map((s) => s.textContent)).toEqual([
      expect.stringContaining("nas-backup"),
      expect.stringContaining("movies"),
    ]);
    const row = within(sources[0]).getByTestId("sync-row");
    await user.click(within(row).getByRole("button"));
    expect(await within(row).findByTestId("sync-detail")).toHaveTextContent(
      "No space left",
    );
  });

  it("restores filters from the URL and applies them to the request", async () => {
    let requested = "";
    server.use(
      http.get("/api/v1/sync-logs", ({ request }) => {
        requested = new URL(request.url).search;
        return HttpResponse.json(syncLogs);
      }),
    );
    renderPage("/app/transfers?source=movies&range=30d&status=failed");
    await screen.findAllByTestId("transfer-day");
    expect(requested).toContain("source_name=movies");
    expect(screen.getByRole("button", { name: "30d" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Failed" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    // status=failed is a client-side filter: only the failed transfer remains
    expect(screen.getAllByTestId("sync-row")).toHaveLength(1);
  });

  it("writes filter changes to the URL", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findAllByTestId("transfer-day");
    await user.click(screen.getByRole("button", { name: "90d" }));
    await user.click(screen.getByRole("button", { name: "Failed" }));
    expect(screen.getByTestId("location")).toHaveTextContent(
      "?range=90d&status=failed",
    );
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByTestId("location")).toHaveTextContent("");
  });

  it("offers Load more while the cursor has a next page", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get("/api/v1/sync-logs", ({ request }) => {
        calls += 1;
        const cursor = new URL(request.url).searchParams.get("cursor");
        return HttpResponse.json({
          items: cursor
            ? [
                {
                  ...syncLogs.items[2],
                  id: "44444444-4444-4444-8444-444444444444",
                },
              ]
            : syncLogs.items,
          pagination: {
            next_cursor: cursor ? null : "c2",
            prev_cursor: null,
            has_next: !cursor,
            has_prev: false,
            limit: 100,
          },
        });
      }),
    );
    renderPage();
    const more = await screen.findByRole("button", { name: "Load more" });
    await user.click(more);
    expect(await screen.findAllByTestId("sync-row")).toHaveLength(4);
    expect(calls).toBe(2);
    expect(
      screen.queryByRole("button", { name: "Load more" }),
    ).not.toBeInTheDocument();
  });

  it("shows an empty state with a clear action", async () => {
    server.use(
      http.get("/api/v1/sync-logs", () => HttpResponse.json({ items: [] })),
    );
    renderPage("/app/transfers?source=nothing");
    expect(await screen.findByText(/No transfers match/)).toBeInTheDocument();
  });
});
