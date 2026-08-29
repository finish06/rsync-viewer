import { format, parseISO, subDays } from "date-fns";

export type RangeKey = "7d" | "30d" | "90d" | "custom";
export type StatusKey = "all" | "failed";

export interface TransferFilters {
  source: string;
  range: RangeKey;
  from: string;
  to: string;
  status: StatusKey;
  dryRuns: boolean;
}

export const DEFAULT_FILTERS: TransferFilters = {
  source: "",
  range: "7d",
  from: "",
  to: "",
  status: "all",
  dryRuns: false,
};

const RANGE_DAYS: Record<Exclude<RangeKey, "custom">, number> = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
};

/** URL ⇄ filter state (AC-012). Only non-default values are written. */
export function filtersFromSearch(search: URLSearchParams): TransferFilters {
  const range = search.get("range");
  const status = search.get("status");
  const from = search.get("from") ?? "";
  const to = search.get("to") ?? "";
  return {
    source: search.get("source") ?? "",
    range:
      range === "30d" || range === "90d" || range === "custom"
        ? range
        : from || to
          ? "custom"
          : "7d",
    from,
    to,
    status: status === "failed" ? "failed" : "all",
    dryRuns: search.get("dry") === "1",
  };
}

export function filtersToSearch(filters: TransferFilters): URLSearchParams {
  const search = new URLSearchParams();
  if (filters.source) search.set("source", filters.source);
  if (filters.range !== "7d") search.set("range", filters.range);
  if (filters.range === "custom") {
    if (filters.from) search.set("from", filters.from);
    if (filters.to) search.set("to", filters.to);
  }
  if (filters.status !== "all") search.set("status", filters.status);
  if (filters.dryRuns) search.set("dry", "1");
  return search;
}

/** Resolve the filter state into API query params. */
export function filtersToParams(
  filters: TransferFilters,
  now: Date = new Date(),
) {
  let start_date: string | undefined;
  let end_date: string | undefined;
  if (filters.range === "custom") {
    start_date = filters.from || undefined;
    end_date = filters.to
      ? format(parseISO(filters.to), "yyyy-MM-dd")
      : undefined;
  } else {
    start_date = format(
      subDays(now, RANGE_DAYS[filters.range] - 1),
      "yyyy-MM-dd",
    );
  }
  return {
    source_name: filters.source || undefined,
    start_date,
    end_date,
    limit: 100,
    synthetic: "hide" as const,
  };
}
