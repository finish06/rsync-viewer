import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { buildQuery, fetchJson, mutateJson } from "./client";
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
  UserPreferences,
  ApiKeyCreated,
  ApiKeyRead,
  ChangelogResponse,
  MonitoringSetupRequest,
  MonitoringSetupResult,
  OidcDiscovery,
  OidcSettings,
  OidcSettingsWrite,
  SmtpSettings,
  SmtpSettingsWrite,
  SyntheticSettings,
  UserRead,
  WebhookRead,
  WebhookWrite,
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

/** Stored user preferences (theme) — applied on load so a new browser matches the server. */
export function usePreferences() {
  return useQuery({
    queryKey: ["users", "me", "preferences"] as const,
    queryFn: () => fetchJson<UserPreferences>("/users/me/preferences"),
    staleTime: Infinity,
  });
}

export function useMediaSummary(days = 7) {
  return useQuery({
    queryKey: queryKeys.mediaSummary(days),
    queryFn: () =>
      fetchJson<MediaSummary>(`/media/summary${buildQuery({ days })}`),
  });
}

// ---------------------------------------------------------------------------
// Settings (specs/settings-ui.md)
// ---------------------------------------------------------------------------

export const settingsKeys = {
  smtp: ["settings", "smtp"] as const,
  oidc: ["settings", "oidc"] as const,
  synthetic: ["settings", "synthetic"] as const,
  changelog: (all: boolean) => ["changelog", all] as const,
  apiKeys: (all: boolean) => ["api-keys", all] as const,
  users: ["users"] as const,
  webhooks: ["webhooks"] as const,
};

export function useSmtpSettings() {
  return useQuery({
    queryKey: settingsKeys.smtp,
    queryFn: () => fetchJson<SmtpSettings>("/settings/smtp"),
  });
}

export function useSaveSmtpSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SmtpSettingsWrite) =>
      mutateJson<SmtpSettings>("/settings/smtp", "PUT", body),
    onSuccess: (data) => qc.setQueryData(settingsKeys.smtp, data),
  });
}

export function useTestSmtp() {
  return useMutation({
    mutationFn: (to_address: string) =>
      mutateJson<{ sent: boolean; to_address: string }>(
        "/settings/smtp/test",
        "POST",
        { to_address },
      ),
  });
}

export function useOidcSettings() {
  return useQuery({
    queryKey: settingsKeys.oidc,
    queryFn: () => fetchJson<OidcSettings>("/settings/oidc"),
  });
}

export function useSaveOidcSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OidcSettingsWrite) =>
      mutateJson<OidcSettings>("/settings/oidc", "PUT", body),
    onSuccess: (data) => qc.setQueryData(settingsKeys.oidc, data),
  });
}

export function useTestOidcDiscovery() {
  return useMutation({
    mutationFn: (issuer_url: string) =>
      mutateJson<OidcDiscovery>("/settings/oidc/test-discovery", "POST", {
        issuer_url,
      }),
  });
}

export function useSyntheticSettings() {
  return useQuery({
    queryKey: settingsKeys.synthetic,
    queryFn: () => fetchJson<SyntheticSettings>("/settings/synthetic"),
  });
}

export function useSaveSyntheticSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { enabled: boolean; interval_seconds: number }) =>
      mutateJson<SyntheticSettings>("/settings/synthetic", "PUT", body),
    onSuccess: (data) => {
      qc.setQueryData(settingsKeys.synthetic, data);
      void qc.invalidateQueries({ queryKey: queryKeys.syntheticStatus });
    },
  });
}

export function useMonitoringSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MonitoringSetupRequest) =>
      mutateJson<MonitoringSetupResult>(
        "/settings/monitoring-setup",
        "POST",
        body,
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useChangelog(all = false) {
  return useQuery({
    queryKey: settingsKeys.changelog(all),
    queryFn: () =>
      fetchJson<ChangelogResponse>(
        `/changelog${buildQuery({ all: all || undefined })}`,
      ),
    staleTime: Infinity,
  });
}

export function useApiKeys(all = false) {
  return useQuery({
    queryKey: settingsKeys.apiKeys(all),
    queryFn: () =>
      fetchJson<ApiKeyRead[]>(
        `/api-keys${buildQuery({ all: all || undefined })}`,
      ),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; role_override?: string | null }) =>
      mutateJson<ApiKeyCreated>("/api-keys", "POST", body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => mutateJson<void>(`/api-keys/${id}`, "DELETE"),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: settingsKeys.users,
    queryFn: () => fetchJson<UserRead[]>("/users"),
  });
}

export function useUserMutations() {
  const qc = useQueryClient();
  const invalidate = () =>
    void qc.invalidateQueries({ queryKey: settingsKeys.users });
  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRead["role"] }) =>
      mutateJson<UserRead>(`/users/${id}/role`, "PUT", { role }),
    onSuccess: invalidate,
  });
  const changeStatus = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      mutateJson<UserRead>(`/users/${id}/status`, "PUT", { is_active }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => mutateJson<void>(`/users/${id}`, "DELETE"),
    onSuccess: invalidate,
  });
  const resetPassword = useMutation({
    mutationFn: (id: string) =>
      mutateJson<{ message?: string; reset_token?: string }>(
        `/users/${id}/reset-password`,
        "POST",
      ),
  });
  return { changeRole, changeStatus, remove, resetPassword };
}

export function useWebhooks() {
  return useQuery({
    queryKey: settingsKeys.webhooks,
    queryFn: () => fetchJson<WebhookRead[]>("/webhooks"),
  });
}

export function useWebhookMutations() {
  const qc = useQueryClient();
  const invalidate = () =>
    void qc.invalidateQueries({ queryKey: settingsKeys.webhooks });
  const create = useMutation({
    mutationFn: (body: WebhookWrite) =>
      mutateJson<WebhookRead>("/webhooks", "POST", body),
    onSuccess: invalidate,
  });
  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<WebhookWrite> }) =>
      mutateJson<WebhookRead>(`/webhooks/${id}`, "PUT", body),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => mutateJson<void>(`/webhooks/${id}`, "DELETE"),
    onSuccess: invalidate,
  });
  const test = useMutation({
    mutationFn: (id: string) =>
      mutateJson<{ status: string; http_status: number }>(
        `/webhooks/${id}/test`,
        "POST",
      ),
  });
  return { create, update, remove, test };
}
