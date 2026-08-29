import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { makeQueryClient } from "../test/render";
import {
  useMediaSummary,
  useSources,
  useSourceStats,
  useSummary,
  useSyntheticHistory,
  useSyntheticStatus,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={makeQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("API hooks against the mocked contract", () => {
  it("useSyntheticStatus resolves and derives a refetch interval from the server", async () => {
    const { result } = renderHook(() => useSyntheticStatus(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.interval_seconds).toBe(300);
  });

  it("useSyntheticHistory passes the limit through", async () => {
    const { result } = renderHook(() => useSyntheticHistory(50), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.length).toBeGreaterThan(0);
  });

  it("useSources unwraps the {sources} envelope", async () => {
    const { result } = renderHook(() => useSources(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(["movies", "nas-backup", "photos"]);
  });

  it("useSummary and useSourceStats fetch analytics", async () => {
    const summary = renderHook(
      () =>
        useSummary({ period: "daily", start: "2026-08-22", end: "2026-08-29" }),
      { wrapper },
    );
    const stats = renderHook(() => useSourceStats({ start: "2026-08-22" }), {
      wrapper,
    });
    await waitFor(() => expect(summary.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(stats.result.current.isSuccess).toBe(true));
    expect(summary.result.current.data?.data).toHaveLength(7);
    expect(stats.result.current.data?.[0].source_name).toBe("movies");
  });

  it("useMediaSummary fetches counts", async () => {
    const { result } = renderHook(() => useMediaSummary(7), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toMatchObject({
      new_movies: 1,
      new_shows: 1,
      new_episodes: 2,
    });
  });
});
