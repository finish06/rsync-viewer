import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { OverviewPage } from "./OverviewPage";

describe("OverviewPage (AC-006, AC-008, AC-026)", () => {
  it("splits sources: problem cards, healthy rows, attention cards (AC-002)", async () => {
    renderWithProviders(<OverviewPage />);
    // fixtures: movies ok · nas-backup failed · photos stale
    const cards = await screen.findAllByTestId("source-card");
    expect(cards).toHaveLength(2);
    const byName = Object.fromEntries(
      cards.map((c) => [
        within(c).getByText(/^(nas-backup|photos)$/).textContent,
        c,
      ]),
    );
    expect(byName["nas-backup"]).toHaveAttribute("data-status", "failed");
    expect(byName["nas-backup"]).toHaveTextContent("2 in a row");
    expect(byName["photos"]).toHaveAttribute("data-status", "stale");

    const rows = screen.getAllByTestId("source-row");
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("movies");
    expect(rows[0]).toHaveAttribute("data-status", "ok");
    expect(rows[0]).toHaveAttribute("href", "/app/transfers?source=movies");

    // exceptions-first: the attention strip names both problems
    const attention = screen.getAllByTestId("attention-card");
    expect(attention).toHaveLength(2);
  });

  it("groups activity by day and expands a day to its transfers, then a transfer to detail", async () => {
    const user = userEvent.setup();
    renderWithProviders(<OverviewPage />);
    const days = await screen.findAllByTestId("activity-day");
    expect(days.length).toBeGreaterThanOrEqual(2);
    expect(days[0]).toHaveTextContent("Today");
    expect(days[0]).toHaveTextContent("2 syncs");
    expect(days[0]).toHaveTextContent("1 ✕");

    // Newest day is expanded by default; failed transfer is listed
    const rows = within(days[0]).getAllByTestId("sync-row");
    expect(rows).toHaveLength(2);
    const failedRow = rows.find(
      (r) => r.getAttribute("data-status") === "failed",
    )!;
    expect(failedRow).toHaveTextContent("exit 11");

    await user.click(within(failedRow).getByRole("button"));
    const detail = await within(failedRow).findByTestId("sync-detail");
    expect(detail).toHaveTextContent("No space left on device");
    expect(within(detail).getByTestId("file-list")).toHaveTextContent(
      "Videos/Movies/big_movie.mkv",
    );
  });

  it("shows the new-this-week summary with titles", async () => {
    renderWithProviders(<OverviewPage />);
    const panel = await screen.findByTestId("new-this-week");
    expect(panel).toHaveTextContent("1 movie");
    expect(panel).toHaveTextContent("1 show · 2 episodes");
    expect(panel).toHaveTextContent("Severance");
    expect(panel).toHaveTextContent("The Polar Express (2004)");
  });

  it("shows the waiting-for-first-sync state when there are no sources", async () => {
    server.use(
      http.get("/api/v1/sources/health", () => HttpResponse.json([])),
      http.get("/api/v1/sync-logs", () => HttpResponse.json({ items: [] })),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByTestId("empty-overview")).toHaveTextContent(
      "Waiting for your first sync",
    );
    expect(
      await screen.findByText("No transfers in the last 7 days."),
    ).toBeInTheDocument();
  });

  it("shows a retryable error per panel without blanking the page", async () => {
    server.use(
      http.get("/api/v1/sources/health", () =>
        HttpResponse.json({ message: "db down" }, { status: 500 }),
      ),
    );
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load source health.",
    );
    expect(await screen.findAllByTestId("activity-day")).not.toHaveLength(0);
  });
});
