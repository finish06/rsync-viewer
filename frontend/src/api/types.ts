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
