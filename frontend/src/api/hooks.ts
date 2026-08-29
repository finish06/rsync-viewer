import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { buildQuery, fetchJson } from "./client";
import type {
  MediaNewResponse,
  MediaSummary,
  PaginatedSyncLogs,
  SourceHealth,
  SourceStats,
  SummaryPeriod,
  SummaryResponse,
  SyncLogDetail,
  SyntheticCheck,
  SyntheticStatus,
} from "./types";

export const queryKeys = {
  syntheticStatus: ["synthetic", "status"] as const,
  syntheticHistory: (limit: number) => ["synthetic", "history", limit] as const,
  sourcesHealth: (days: number) => ["sources", "health", days] as const,
  syncLogs: (params: object) => ["sync-logs", params] as const,
  syncLog: (id: string) => ["sync-logs", id] as const,
  sources: ["sync-logs", "sources"] as const,
  summary: (params: object) => ["analytics", "summary", params] as const,
  sourceStats: (params: object) => ["analytics", "sources", params] as const,
  mediaNew: (days: number, kind?: string) =>
    ["media", "new", days, kind ?? "all"] as const,
  mediaSummary: (days: number) => ["media", "summary", days] as const,
};

/** Liveness pill: refetch at the server-configured check interval (AC-001). */
export function useSyntheticStatus() {
  return useQuery({
    queryKey: queryKeys.syntheticStatus,
    queryFn: () => fetchJson<SyntheticStatus>("/synthetic/status"),
    refetchInterval: (query) => {
      const seconds = query.state.data?.interval_seconds ?? 300;
      return Math.max(seconds, 30) * 1000;
    },
  });
}

export function useSyntheticHistory(limit = 100) {
  return useQuery({
    queryKey: queryKeys.syntheticHistory(limit),
    queryFn: () =>
      fetchJson<SyntheticCheck[]>(`/synthetic/history${buildQuery({ limit })}`),
  });
}

export function useSourcesHealth(days = 14) {
  return useQuery({
    queryKey: queryKeys.sourcesHealth(days),
    queryFn: () =>
      fetchJson<SourceHealth[]>(`/sources/health${buildQuery({ days })}`),
    refetchInterval: 60_000,
  });
}

export interface SyncLogParams {
  source_name?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  cursor?: string;
  direction?: "forward" | "backward";
  synthetic?: "hide" | "only" | "show";
}

export function useSyncLogs(params: SyncLogParams) {
  return useQuery({
    queryKey: queryKeys.syncLogs(params),
    queryFn: () =>
      fetchJson<PaginatedSyncLogs>(`/sync-logs${buildQuery(params)}`),
    refetchInterval: 60_000,
  });
}

/** Cursor-paginated list for infinite scroll (AC-011). */
export function useInfiniteSyncLogs(
  params: Omit<SyncLogParams, "cursor" | "direction">,
) {
  return useInfiniteQuery({
    queryKey: ["sync-logs", "infinite", params] as const,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      fetchJson<PaginatedSyncLogs>(
        `/sync-logs${buildQuery({ ...params, cursor: pageParam ?? undefined })}`,
      ),
    getNextPageParam: (last) =>
      last.pagination?.has_next ? last.pagination.next_cursor : null,
  });
}

export function useSyncLog(id: string | null) {
  return useQuery({
    queryKey: queryKeys.syncLog(id ?? ""),
    queryFn: () => fetchJson<SyncLogDetail>(`/sync-logs/${id}`),
    enabled: Boolean(id),
  });
}

export function useSources() {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: async () => {
      const body = await fetchJson<{ sources: string[] } | string[]>(
        "/sync-logs/sources",
      );
      return Array.isArray(body) ? body : body.sources;
    },
  });
}

export interface SummaryParams {
  period: SummaryPeriod;
  start: string;
  end: string;
  source?: string;
}

export function useSummary(params: SummaryParams) {
  return useQuery({
    queryKey: queryKeys.summary(params),
    queryFn: () =>
      fetchJson<SummaryResponse>(`/analytics/summary${buildQuery(params)}`),
  });
}

export function useSourceStats(params: { start?: string; end?: string }) {
  return useQuery({
    queryKey: queryKeys.sourceStats(params),
    queryFn: () =>
      fetchJson<SourceStats[]>(`/analytics/sources${buildQuery(params)}`),
  });
}

export function useMediaNew(days = 7, kind?: "show" | "movie") {
  return useQuery({
    queryKey: queryKeys.mediaNew(days, kind),
    queryFn: () =>
      fetchJson<MediaNewResponse>(`/media/new${buildQuery({ days, kind })}`),
  });
}

export function useMediaSummary(days = 7) {
  return useQuery({
    queryKey: queryKeys.mediaSummary(days),
    queryFn: () =>
      fetchJson<MediaSummary>(`/media/summary${buildQuery({ days })}`),
  });
}
