import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { mediaNew } from "../../test/handlers";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { MediaPage, transferLink } from "./MediaPage";

describe("MediaPage (AC-019)", () => {
  it("shows counts, show groups with episode chips, and movies", async () => {
    renderWithProviders(<MediaPage />, { route: "/app/media" });
    const counts = await screen.findByTestId("media-counts");
    expect(counts).toHaveTextContent("1 movie");
    expect(counts).toHaveTextContent("1 show");
    expect(counts).toHaveTextContent("2 episodes");
    const show = screen.getByTestId("show-item");
    expect(show).toHaveTextContent("Severance (2022)");
    expect(show).toHaveTextContent("2 new");
    expect(within(show).getByRole("link", { name: "S02E03" })).toHaveAttribute(
      "href",
      expect.stringContaining("/app/transfers?range=custom"),
    );
    const movie = screen.getByTestId("movie-item");
    expect(movie).toHaveTextContent("The Polar Express (2004)");
    expect(within(movie).getByRole("link")).toHaveAttribute(
      "href",
      expect.stringContaining("source=movies"),
    );
  });

  it("changes the window via the URL", async () => {
    const user = userEvent.setup();
    let requested = "";
    server.use(
      http.get("/api/v1/media/new", ({ request }) => {
        requested = new URL(request.url).search;
        return HttpResponse.json({ ...mediaNew, days: 30 });
      }),
    );
    renderWithProviders(<MediaPage />, { route: "/app/media" });
    await screen.findByTestId("media-counts");
    await user.selectOptions(screen.getByLabelText("Window"), "30");
    await screen.findByTestId("media-counts");
    expect(requested).toContain("days=30");
  });

  it("shows empty states", async () => {
    server.use(
      http.get("/api/v1/media/new", () =>
        HttpResponse.json({ days: 7, shows: [], movies: [] }),
      ),
    );
    renderWithProviders(<MediaPage />, { route: "/app/media" });
    expect(
      await screen.findByText("No new episodes in this window."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No new movies in this window."),
    ).toBeInTheDocument();
  });

  it("builds a day+source transfer link", () => {
    expect(
      transferLink({ first_seen_at: "2026-08-29T10:00:00", source_name: "tv" }),
    ).toBe(
      "/app/transfers?range=custom&from=2026-08-29&to=2026-08-29&source=tv",
    );
  });
});
