import { describe, expect, it } from "vitest";

import {
  dayLabel,
  durationBetween,
  episodeLabel,
  formatBytes,
  formatDuration,
  formatPercent,
  formatRelative,
  localDayKey,
} from "./format";

describe("formatBytes", () => {
  it("scales units", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1023)).toBe("1023 B");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(6.2 * 1024 ** 3)).toBe("6.2 GB");
    expect(formatBytes(150 * 1024 ** 3)).toBe("150 GB");
  });
  it("handles missing", () => {
    expect(formatBytes(null)).toBe("—");
  });
});

describe("formatDuration", () => {
  it("renders compact units", () => {
    expect(formatDuration(12)).toBe("12s");
    expect(formatDuration(192)).toBe("3m 12s");
    expect(formatDuration(3720)).toBe("1h 2m");
    expect(formatDuration(null)).toBe("—");
  });
  it("computes between timestamps", () => {
    expect(
      durationBetween("2026-08-29T10:00:00Z", "2026-08-29T10:03:12Z"),
    ).toBe(192);
    expect(durationBetween("bad", "2026-08-29T10:03:12Z")).toBeNull();
  });
});

describe("formatRelative (AC-009)", () => {
  const now = new Date("2026-08-29T12:00:00Z");
  it("is relative within 24h and absolute after", () => {
    expect(formatRelative("2026-08-29T11:59:50Z", now)).toBe("just now");
    expect(formatRelative("2026-08-29T11:48:00Z", now)).toBe("12 minutes ago");
    expect(formatRelative("2026-08-27T09:30:00Z", now)).toMatch(
      /Aug 27, \d\d:\d\d/,
    );
    expect(formatRelative(null, now)).toBe("never");
  });
});

describe("labels", () => {
  it("formats percent and episodes", () => {
    expect(formatPercent(99.83)).toBe("99.8%");
    expect(formatPercent(null)).toBe("—");
    expect(episodeLabel(2, 3)).toBe("S02E03");
    expect(episodeLabel(null, 7)).toBe("S??E07");
  });
  it("groups by local day", () => {
    const now = new Date("2026-08-29T12:00:00");
    expect(dayLabel(localDayKey("2026-08-29T01:00:00"), now)).toBe("Today");
    expect(dayLabel(localDayKey("2026-08-28T23:00:00"), now)).toBe("Yesterday");
    expect(dayLabel("2026-08-20", now)).toBe("Thu, Aug 20");
  });
});
