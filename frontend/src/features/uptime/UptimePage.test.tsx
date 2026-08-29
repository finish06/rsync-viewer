import { screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { syntheticStatusDisabled } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { UptimePage } from "./UptimePage";

describe("UptimePage (AC-004, AC-007)", () => {
  it("renders status header, uptime stats, timeline cells, and recent failures", async () => {
    renderWithProviders(<UptimePage />, { route: "/app/uptime" });
    const header = await screen.findByTestId("uptime-header");
    expect(header).toHaveTextContent("PASSING");
    expect(header).toHaveTextContent("every 5 min");
    const stats = screen.getByTestId("uptime-stats");
    expect(stats).toHaveTextContent("99.8%");
    expect(stats).toHaveTextContent("288");

    const cells = await screen.findAllByTestId("timeline-cell");
    expect(cells).toHaveLength(12);
    const failing = cells.filter(
      (c) => c.getAttribute("data-status") === "failing",
    );
    expect(failing).toHaveLength(1);
    expect(failing[0]).toHaveAttribute(
      "title",
      expect.stringContaining("502 Bad Gateway"),
    );
    // newest is on the right: the failing check (index 4 from newest) sits near the end
    expect(cells.indexOf(failing[0])).toBe(cells.length - 5);

    const failures = screen.getByTestId("uptime-failures");
    expect(
      within(failures).getByText("POST /sync-logs -> 502 Bad Gateway"),
    ).toBeInTheDocument();
  });

  it("explains the disabled state with a settings link", async () => {
    server.use(
      http.get("/api/v1/synthetic/status", () =>
        HttpResponse.json(syntheticStatusDisabled),
      ),
    );
    renderWithProviders(<UptimePage />, { route: "/app/uptime" });
    expect(
      await screen.findByText("Synthetic monitoring is off."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Settings → Monitoring" }),
    ).toHaveAttribute("href", "/settings#monitoring");
  });

  it("handles an empty history", async () => {
    server.use(
      http.get("/api/v1/synthetic/history", () => HttpResponse.json([])),
    );
    renderWithProviders(<UptimePage />, { route: "/app/uptime" });
    expect(
      await screen.findByText("No checks recorded yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Not enough checks for a chart yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No failing checks in the recent history."),
    ).toBeInTheDocument();
  });

  it("shows a retryable error when status fails", async () => {
    server.use(
      http.get("/api/v1/synthetic/status", () =>
        HttpResponse.json({ message: "x" }, { status: 500 }),
      ),
    );
    renderWithProviders(<UptimePage />, { route: "/app/uptime" });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load synthetic status.",
    );
  });
});
