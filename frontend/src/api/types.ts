// Hand-mirrored from app/schemas/*.py — keep in sync with the backend contract
// (specs/insight-ui.md §5). Dates are ISO-8601 strings in UTC.

export type SyntheticStatusValue =
  "passing" | "failing" | "unknown" | "disabled";

export interface SyntheticStatus {
  enabled: boolean;
  status: SyntheticStatusValue;
  last_check_at: string | null;
  last_latency_ms: number | null;
  interval_seconds: number;
  uptime_24h_pct: number | null;
  uptime_7d_pct: number | null;
  checks_24h: number;
}

export interface SyntheticCheck {
  checked_at: string;
  status: "passing" | "failing";
  latency_ms: number;
  error: string | null;
}

export interface DailyPoint {
  date: string;
  syncs: number;
  failures: number;
  bytes: number;
}

export type SourceStatus = "ok" | "failed" | "never";

export interface SourceHealth {
  source_name: string;
  last_sync_at: string | null;
  last_status: SourceStatus;
  last_exit_code: number | null;
  consecutive_failures: number;
  expected_interval_hours: number | null;
  is_stale: boolean;
  daily: DailyPoint[];
}

export interface SyncLogListItem {
  id: string;
  source_name: string;
  start_time: string;
  end_time: string;
  total_size_bytes: number | null;
  bytes_received: number | null;
  transfer_speed: number | null;
  file_count: number;
  status: string;
  is_dry_run: boolean;
  exit_code?: number | null;
}

export interface SyncLogDetail extends SyncLogListItem {
  bytes_sent: number | null;
  speedup_ratio: number | null;
  raw_content: string;
  file_list: string[] | null;
  exit_code: number | null;
  created_at: string;
}

export interface CursorPagination {
  next_cursor: string | null;
  prev_cursor: string | null;
  has_next: boolean;
  has_prev: boolean;
  limit: number;
}

export interface PaginatedSyncLogs {
  items: SyncLogListItem[];
  pagination?: CursorPagination;
  total?: number;
}

export type SummaryPeriod = "daily" | "weekly" | "monthly";

export interface SummaryDataPoint {
  date: string;
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  avg_duration_seconds: number | null;
  total_bytes_transferred: number;
  total_files_transferred: number;
}

export interface SummaryResponse {
  period: SummaryPeriod;
  start: string;
  end: string;
  data: SummaryDataPoint[];
}

export interface SourceStats {
  source_name: string;
  total_syncs: number;
  success_rate: number;
  avg_duration_seconds: number | null;
  avg_files_transferred: number | null;
  avg_bytes_transferred: number | null;
  last_sync_at: string | null;
}

export interface EpisodeRead {
  season: number | null;
  episode: number | null;
  first_seen_at: string;
  sync_log_id: string | null;
  source_name: string;
}

export interface ShowGroup {
  title: string;
  year: number | null;
  new_episodes: EpisodeRead[];
}

export interface MovieRead {
  title: string;
  year: number | null;
  first_seen_at: string;
  sync_log_id: string | null;
  source_name: string;
}

export interface MediaNewResponse {
  days: number;
  shows: ShowGroup[];
  movies: MovieRead[];
}

export interface MediaSummary {
  days: number;
  new_movies: number;
  new_shows: number;
  new_episodes: number;
}

export interface UserPreferences {
  theme?: "light" | "dark";
}

export interface ApiError {
  error_code: string;
  message: string;
  detail?: string;
  path?: string;
}

// --- Settings (specs/settings-ui.md) ---

export type SmtpEncryption = "none" | "starttls" | "ssl_tls";

export interface SmtpSettings {
  configured: boolean;
  host: string | null;
  port: number | null;
  username: string | null;
  encryption: SmtpEncryption;
  from_address: string | null;
  from_name: string | null;
  enabled: boolean;
  has_password: boolean;
  encryption_key_configured: boolean;
  updated_at: string | null;
}

export interface SmtpSettingsWrite {
  host: string;
  port: number;
  username?: string | null;
  password?: string | null;
  encryption: SmtpEncryption;
  from_address: string;
  from_name: string;
  enabled: boolean;
}

export interface OidcSettings {
  configured: boolean;
  issuer_url: string | null;
  client_id: string | null;
  provider_name: string | null;
  scopes: string;
  enabled: boolean;
  hide_local_login: boolean;
  has_client_secret: boolean;
  callback_url: string;
  encryption_key_configured: boolean;
  updated_at: string | null;
}

export interface OidcSettingsWrite {
  issuer_url: string;
  client_id: string;
  client_secret?: string | null;
  provider_name: string;
  scopes: string;
  enabled: boolean;
  hide_local_login: boolean;
}

export interface OidcDiscovery {
  issuer_url: string;
  endpoints: Record<string, string>;
}

export interface SyntheticSettings {
  enabled: boolean;
  interval_seconds: number;
  last_status: string;
  last_check_at: string | null;
  last_latency_ms: number | null;
  last_error: string | null;
}

export interface MonitoringSetupRequest {
  source_name: string;
  rsync_source: string;
  cron_schedule?: string;
  ssh_key_path?: string;
  rsync_args?: string;
  sync_mode?: "pull" | "push";
}

export interface MonitoringSetupResult {
  source_name: string;
  key_name: string;
  api_key: string;
  snippet: string;
}

export interface ChangelogItem {
  text: string;
  children: string[];
}

export interface ChangelogVersion {
  version: string;
  date: string | null;
  sections: Record<string, ChangelogItem[]>;
}

export interface ChangelogResponse {
  app_version: string;
  versions: ChangelogVersion[];
  has_more: boolean;
}

export interface ApiKeyRead {
  id: string;
  name: string;
  key_prefix: string;
  user_id?: string | null;
  role_override: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at?: string | null;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  key: string;
  key_prefix: string;
  role: string;
  created_at: string;
}

export interface UserRead {
  id: string;
  username: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface WebhookRead {
  id: string;
  name: string;
  url: string;
  headers: Record<string, string> | null;
  webhook_type: "generic" | "discord";
  source_filters: string[] | null;
  options: Record<string, unknown> | null;
  enabled: boolean;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
}

export interface WebhookWrite {
  name: string;
  url: string;
  headers?: Record<string, string> | null;
  webhook_type: "generic" | "discord";
  source_filters?: string[] | null;
  options?: Record<string, unknown> | null;
  enabled: boolean;
}
