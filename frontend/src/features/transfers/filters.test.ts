import { describe, expect, it } from "vitest";

import {
  DEFAULT_FILTERS,
  filtersFromSearch,
  filtersToParams,
  filtersToSearch,
} from "./filters";

describe("transfer filters ⇄ URL (AC-012)", () => {
  it("round-trips non-default values and omits defaults", () => {
    const filters = {
      source: "movies",
      range: "30d" as const,
      from: "",
      to: "",
      status: "failed" as const,
      dryRuns: true,
    };
    const search = filtersToSearch(filters);
    expect(search.toString()).toBe(
      "source=movies&range=30d&status=failed&dry=1",
    );
    expect(filtersFromSearch(search)).toEqual(filters);
    expect(filtersToSearch(DEFAULT_FILTERS).toString()).toBe("");
    expect(filtersFromSearch(new URLSearchParams())).toEqual(DEFAULT_FILTERS);
  });

  it("infers a custom range from explicit dates", () => {
    const parsed = filtersFromSearch(
      new URLSearchParams("from=2026-08-01&to=2026-08-15"),
    );
    expect(parsed.range).toBe("custom");
    expect(filtersToSearch(parsed).toString()).toBe(
      "range=custom&from=2026-08-01&to=2026-08-15",
    );
  });

  it("maps ranges to API params", () => {
    const now = new Date("2026-08-29T12:00:00");
    expect(filtersToParams({ ...DEFAULT_FILTERS, source: "tv" }, now)).toEqual({
      source_name: "tv",
      start_date: "2026-08-23",
      end_date: undefined,
      limit: 100,
      synthetic: "hide",
    });
    expect(
      filtersToParams({ ...DEFAULT_FILTERS, range: "90d" }, now).start_date,
    ).toBe("2026-06-01");
    expect(
      filtersToParams(
        {
          ...DEFAULT_FILTERS,
          range: "custom",
          from: "2026-08-01",
          to: "2026-08-15",
        },
        now,
      ),
    ).toMatchObject({ start_date: "2026-08-01", end_date: "2026-08-15" });
  });
});
