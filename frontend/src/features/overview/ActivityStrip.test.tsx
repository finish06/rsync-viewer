import { describe, expect, it } from "vitest";

import type { SyncLogListItem } from "../../api/types";
import { groupByDay } from "./ActivityStrip";

function item(overrides: Partial<SyncLogListItem>): SyncLogListItem {
  return {
    id: crypto.randomUUID(),
    source_name: "movies",
    start_time: "2026-08-29T10:00:00",
    end_time: "2026-08-29T10:05:00",
    total_size_bytes: 0,
    bytes_received: 1000,
    transfer_speed: 0,
    file_count: 1,
    status: "completed",
    is_dry_run: false,
    exit_code: 0,
    ...overrides,
  };
}

describe("groupByDay (AC-008)", () => {
  it("groups by local day, newest first, with counts, bytes, and top sources", () => {
    const groups = groupByDay([
      item({ start_time: "2026-08-28T23:30:00", source_name: "tv" }),
      item({
        start_time: "2026-08-29T01:00:00",
        exit_code: 11,
        bytes_received: 0,
      }),
      item({ start_time: "2026-08-29T02:00:00", source_name: "movies" }),
      item({ start_time: "2026-08-29T03:00:00", source_name: "photos" }),
    ]);
    expect(groups.map((g) => g.key)).toEqual(["2026-08-29", "2026-08-28"]);
    expect(groups[0]).toMatchObject({ syncs: 3, failed: 1, bytes: 2000 });
    expect(groups[0].topSources[0]).toBe("movies");
    expect(groups[1]).toMatchObject({
      syncs: 1,
      failed: 0,
      bytes: 1000,
      topSources: ["tv"],
    });
  });

  it("handles an empty list", () => {
    expect(groupByDay([])).toEqual([]);
  });
});
