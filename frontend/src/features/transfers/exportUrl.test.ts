import { describe, expect, it } from "vitest";

import { buildExportUrl, exportFilename } from "./exportUrl";

describe("buildExportUrl (AC-006)", () => {
  it("defaults to CSV, all sources, synthetic hidden", () => {
    expect(buildExportUrl({ sources: [], format: "csv" })).toBe(
      "/api/v1/analytics/export?format=csv&synthetic=hide",
    );
  });

  it("repeats the source parameter once per selection", () => {
    const url = buildExportUrl({ sources: ["movies", "tv"], format: "csv" });
    const params = new URL(url, "http://x").searchParams;
    expect(params.getAll("source")).toEqual(["movies", "tv"]);
  });

  it("carries synthetic, dates and format", () => {
    const url = buildExportUrl({
      sources: ["photos"],
      format: "json",
      includeSynthetic: true,
      from: "2026-08-01",
      to: "2026-08-31",
    });
    const params = new URL(url, "http://x").searchParams;
    expect(params.get("format")).toBe("json");
    expect(params.get("synthetic")).toBe("show");
    expect(params.get("start")).toBe("2026-08-01");
    expect(params.get("end")).toBe("2026-08-31");
  });

  it("omits empty dates and encodes hostile source names", () => {
    const url = buildExportUrl({
      sources: ["weird name&x=1"],
      format: "csv",
      from: "",
      to: "",
    });
    expect(url).not.toContain("start=");
    const params = new URL(url, "http://x").searchParams;
    expect(params.getAll("source")).toEqual(["weird name&x=1"]);
  });
});

describe("exportFilename", () => {
  it("is dated and matches the format", () => {
    expect(exportFilename("csv", new Date("2026-08-31T10:00:00Z"))).toBe(
      "rsync-export-20260831.csv",
    );
    expect(exportFilename("json", new Date("2026-01-05T10:00:00Z"))).toBe(
      "rsync-export-20260105.json",
    );
  });
});
