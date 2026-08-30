import { screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import type { MediaNewResponse } from "../../api/types";
import { renderWithProviders } from "../../test/render";
import { server } from "../../test/setup";
import { NewThisWeek } from "./NewThisWeek";

const DAY = 86_400_000;
const at = (daysAgo: number) =>
  new Date(Date.now() - daysAgo * DAY).toISOString();

function episode(season: number, ep: number, daysAgo: number) {
  return {
    season,
    episode: ep,
    first_seen_at: at(daysAgo),
    sync_log_id: null,
    source_name: "tv",
  };
}

function respond(data: Partial<MediaNewResponse>) {
  server.use(
    http.get("/api/v1/media/new", () =>
      HttpResponse.json({ days: 7, shows: [], movies: [], ...data }),
    ),
  );
}

describe("NewThisWeek diary (AC-007/008/009)", () => {
  it("groups by day newest-first, collapsing a show's episodes per day", async () => {
    respond({
      shows: [
        {
          title: "Severance",
          year: 2022,
          new_episodes: [episode(2, 5, 0), episode(2, 6, 0), episode(2, 4, 1)],
        },
      ],
      movies: [
        {
          title: "Dune: Part Two",
          year: 2024,
          first_seen_at: at(0),
          sync_log_id: null,
          source_name: "movies",
        },
      ],
    });
    renderWithProviders(<NewThisWeek />);
    const days = await screen.findAllByTestId("media-day");
    expect(days).toHaveLength(7);

    expect(days[0]).toHaveTextContent("Today");
    expect(days[0]).toHaveTextContent("Severance ×2 · S02E05–06");
    expect(days[0]).toHaveTextContent("Dune: Part Two (2024)");

    expect(days[1]).toHaveTextContent("Yesterday");
    expect(days[1]).toHaveTextContent("Severance · S02E04");

    // watch-list tone: no source names, no counts headline
    expect(screen.queryByText(/tv|movies/)).not.toBeInTheDocument();
    expect(screen.queryByText(/1 movie/)).not.toBeInTheDocument();

    // quiet days keep the rhythm, greyed
    expect(days[3]).toHaveTextContent("nothing new");
    expect(days[3]).toHaveAttribute("data-quiet", "true");
    expect(days[0]).toHaveAttribute("data-quiet", "false");
  });

  it("caps a big day at 4 titles with an overflow link to Media", async () => {
    respond({
      movies: Array.from({ length: 6 }, (_, i) => ({
        title: `Movie ${i + 1}`,
        year: 2000 + i,
        first_seen_at: at(0),
        sync_log_id: null,
        source_name: "movies",
      })),
    });
    renderWithProviders(<NewThisWeek />);
    const today = (await screen.findAllByTestId("media-day"))[0];
    expect(within(today).getAllByTestId("media-title")).toHaveLength(4);
    const more = within(today).getByRole("link", { name: /\+2 more/ });
    expect(more).toHaveAttribute("href", "/app/media");
  });

  it("keeps the single empty note for a week with no arrivals", async () => {
    respond({});
    renderWithProviders(<NewThisWeek />);
    expect(await screen.findByText("Nothing new this week.")).toBeVisible();
    expect(screen.queryByTestId("media-day")).not.toBeInTheDocument();
  });
});
