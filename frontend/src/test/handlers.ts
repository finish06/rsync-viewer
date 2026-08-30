// MSW handlers mirroring the backend contract (specs/insight-ui.md §5).
// Tests override individual handlers with server.use(...) as needed.

import { HttpResponse, http } from "msw";

import type {
  ApiKeyRead,
  ChangelogResponse,
  MediaNewResponse,
  MediaSummary,
  PaginatedSyncLogs,
  SourceHealth,
  SourceStats,
  SummaryResponse,
  SyncLogDetail,
  SyntheticCheck,
  SyntheticStatus,
  OidcSettings,
  SmtpSettings,
  SyntheticSettings,
  UserRead,
  WebhookRead,
} from "../api/types";

export const syntheticStatusPassing: SyntheticStatus = {
  enabled: true,
  status: "passing",
  last_check_at: new Date(Date.now() - 2 * 60_000).toISOString(),
  last_latency_ms: 143,
  interval_seconds: 300,
  uptime_24h_pct: 99.8,
  uptime_7d_pct: 99.6,
  checks_24h: 288,
};

export const syntheticStatusDisabled: SyntheticStatus = {
  enabled: false,
  status: "disabled",
  last_check_at: null,
  last_latency_ms: null,
  interval_seconds: 300,
  uptime_24h_pct: null,
  uptime_7d_pct: null,
  checks_24h: 0,
};

export const syntheticHistory: SyntheticCheck[] = Array.from(
  { length: 12 },
  (_, i) => ({
    checked_at: new Date(Date.now() - i * 300_000).toISOString(),
    status: i === 4 ? "failing" : "passing",
    latency_ms: i === 4 ? 2100 : 120 + i,
    error: i === 4 ? "POST /sync-logs -> 502 Bad Gateway" : null,
  }),
);

function daily(
  days: number,
  syncs: number,
  failures = 0,
): SourceHealth["daily"] {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(Date.now() - (days - 1 - i) * 86_400_000);
    return {
      date: date.toISOString().slice(0, 10),
      syncs,
      failures,
      bytes: syncs * 1024 ** 3,
    };
  });
}

export const sourcesHealth: SourceHealth[] = [
  {
    source_name: "movies",
    last_sync_at: new Date(Date.now() - 12 * 60_000).toISOString(),
    last_status: "ok",
    last_exit_code: 0,
    consecutive_failures: 0,
    expected_interval_hours: null,
    is_stale: false,
    daily: daily(14, 1),
  },
  {
    source_name: "nas-backup",
    last_sync_at: new Date(Date.now() - 40 * 60_000).toISOString(),
    last_status: "failed",
    last_exit_code: 11,
    consecutive_failures: 2,
    expected_interval_hours: 24,
    is_stale: false,
    daily: daily(14, 1, 1),
  },
  {
    source_name: "photos",
    last_sync_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
    last_status: "ok",
    last_exit_code: 0,
    consecutive_failures: 0,
    expected_interval_hours: 24,
    is_stale: true,
    daily: daily(14, 0),
  },
];

export const syncLogs: PaginatedSyncLogs = {
  items: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      source_name: "nas-backup",
      start_time: new Date(Date.now() - 40 * 60_000).toISOString(),
      end_time: new Date(Date.now() - 37 * 60_000).toISOString(),
      total_size_bytes: 0,
      bytes_received: 0,
      transfer_speed: 0,
      file_count: 0,
      status: "completed",
      is_dry_run: false,
      exit_code: 11,
    },
    {
      id: "22222222-2222-4222-8222-222222222222",
      source_name: "movies",
      start_time: new Date(Date.now() - 12 * 60_000).toISOString(),
      end_time: new Date(Date.now() - 8 * 60_000).toISOString(),
      total_size_bytes: 8_000_000_000,
      bytes_received: 6_200_000_000,
      transfer_speed: 25_000_000,
      file_count: 3,
      status: "completed",
      is_dry_run: false,
      exit_code: 0,
    },
    {
      id: "33333333-3333-4333-8333-333333333333",
      source_name: "movies",
      start_time: new Date(Date.now() - 26 * 3_600_000).toISOString(),
      end_time: new Date(Date.now() - 26 * 3_600_000 + 60_000).toISOString(),
      total_size_bytes: 1_000_000,
      bytes_received: 1_000_000,
      transfer_speed: 1_000_000,
      file_count: 1,
      status: "completed",
      is_dry_run: false,
      exit_code: 0,
    },
  ],
  pagination: {
    next_cursor: null,
    prev_cursor: null,
    has_next: false,
    has_prev: false,
    limit: 100,
  },
};

export const syncLogDetail: SyncLogDetail = {
  ...syncLogs.items[0],
  bytes_sent: 0,
  speedup_ratio: null,
  raw_content:
    'rsync: write failed on "/backup/Videos/Movies/big_movie.mkv": No space left on device (28)\nrsync error: error in file IO (code 11) at receiver.c(393)',
  file_list: ["Videos/Movies/big_movie.mkv"],
  exit_code: 11,
  created_at: syncLogs.items[0].end_time,
};

export const summary: SummaryResponse = {
  period: "daily",
  start: "2026-08-22",
  end: "2026-08-29",
  data: Array.from({ length: 7 }, (_, i) => ({
    date: new Date(Date.now() - (6 - i) * 86_400_000)
      .toISOString()
      .slice(0, 10),
    total_syncs: 5 + i,
    successful_syncs: 5 + i - (i === 3 ? 1 : 0),
    failed_syncs: i === 3 ? 1 : 0,
    avg_duration_seconds: 120 + i * 10,
    total_bytes_transferred: (10 + i) * 1024 ** 3,
    total_files_transferred: 100 + i * 7,
  })),
};

export const sourceStats: SourceStats[] = [
  {
    source_name: "movies",
    total_syncs: 42,
    success_rate: 1,
    avg_duration_seconds: 190,
    avg_files_transferred: 12,
    avg_bytes_transferred: 5.9 * 1024 ** 3,
    last_sync_at: new Date(Date.now() - 12 * 60_000).toISOString(),
  },
  {
    source_name: "nas-backup",
    total_syncs: 14,
    success_rate: 0.857,
    avg_duration_seconds: 175,
    avg_files_transferred: 300,
    avg_bytes_transferred: 3.8 * 1024 ** 3,
    last_sync_at: new Date(Date.now() - 40 * 60_000).toISOString(),
  },
];

export const mediaNew: MediaNewResponse = {
  days: 7,
  shows: [
    {
      title: "Severance",
      year: 2022,
      new_episodes: [
        {
          season: 2,
          episode: 3,
          first_seen_at: new Date().toISOString(),
          sync_log_id: syncLogs.items[1].id,
          source_name: "tv",
        },
        {
          season: 2,
          episode: 2,
          first_seen_at: new Date(Date.now() - 86_400_000).toISOString(),
          sync_log_id: null,
          source_name: "tv",
        },
      ],
    },
  ],
  movies: [
    {
      title: "The Polar Express",
      year: 2004,
      first_seen_at: new Date().toISOString(),
      sync_log_id: syncLogs.items[1].id,
      source_name: "movies",
    },
  ],
};

export const mediaSummary: MediaSummary = {
  days: 7,
  new_movies: 1,
  new_shows: 1,
  new_episodes: 2,
};

export const smtpSettings: SmtpSettings = {
  configured: true,
  host: "smtp.example.com",
  port: 587,
  username: "alerts",
  encryption: "starttls",
  from_address: "alerts@example.com",
  from_name: "Rsync Viewer",
  enabled: true,
  has_password: true,
  encryption_key_configured: true,
  updated_at: new Date().toISOString(),
};

export const oidcSettings: OidcSettings = {
  configured: false,
  issuer_url: null,
  client_id: null,
  provider_name: null,
  scopes: "openid email profile",
  enabled: false,
  hide_local_login: false,
  has_client_secret: false,
  callback_url: "http://localhost/auth/oidc/callback",
  encryption_key_configured: true,
  updated_at: null,
};

export const syntheticSettings: SyntheticSettings = {
  enabled: true,
  interval_seconds: 300,
  last_status: "passing",
  last_check_at: new Date().toISOString(),
  last_latency_ms: 42,
  last_error: null,
};

export const updateStatusCurrent = {
  current: "2.12.0",
  latest: "2.12.0",
  update_available: false,
  release_url: null,
  published_at: null,
  checked_at: "2026-08-30T18:00:00Z",
};

export const updateStatusNewer = {
  current: "2.12.0",
  latest: "2.18.0",
  update_available: true,
  release_url: "https://github.com/finish06/rsync-viewer/releases/tag/v2.18.0",
  published_at: "2026-08-30T12:00:00Z",
  checked_at: "2026-08-30T18:00:00Z",
};

export const apiKeys: ApiKeyRead[] = [
  {
    id: "aaaaaaaa-0000-4000-8000-000000000001",
    name: "laptop-backup",
    key_prefix: "rsv_ab12",
    role_override: null,
    created_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
    last_used_at: new Date(Date.now() - 3_600_000).toISOString(),
  },
];

export const users: UserRead[] = [
  {
    id: "bbbbbbbb-0000-4000-8000-000000000001",
    username: "cal",
    email: "cal@example.com",
    role: "admin",
    is_active: true,
    last_login_at: new Date().toISOString(),
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "bbbbbbbb-0000-4000-8000-000000000002",
    username: "ops",
    email: "ops@example.com",
    role: "operator",
    is_active: true,
    last_login_at: null,
    created_at: "2026-02-01T00:00:00Z",
  },
];

export const webhooks: WebhookRead[] = [
  {
    id: "cccccccc-0000-4000-8000-000000000001",
    name: "Discord ops",
    url: "https://discord.com/api/webhooks/123/abc",
    headers: null,
    webhook_type: "discord",
    source_filters: ["movies"],
    options: { color: 16711749, username: "Rsync Viewer" },
    enabled: true,
    consecutive_failures: 0,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "cccccccc-0000-4000-8000-000000000002",
    name: "Home Assistant",
    url: "https://ha.local/api/webhook/xyz",
    headers: { Authorization: "Bearer secret" },
    webhook_type: "generic",
    source_filters: null,
    options: null,
    enabled: false,
    consecutive_failures: 3,
    created_at: "2026-03-02T00:00:00Z",
    updated_at: "2026-03-02T00:00:00Z",
  },
];

export const changelog: ChangelogResponse = {
  app_version: "2.13.0",
  versions: [
    {
      version: "2.13.0",
      date: "2026-08-29",
      sections: { Added: [{ text: "Settings API", children: [] }] },
    },
    {
      version: "2.12.0",
      date: "2026-08-29",
      sections: {
        Changed: [
          { text: "SPA is the dashboard", children: ["legacy removed"] },
        ],
      },
    },
  ],
  has_more: true,
};

export const handlers = [
  http.get("/api/v1/settings/smtp", () => HttpResponse.json(smtpSettings)),
  http.put("/api/v1/settings/smtp", async ({ request }) => {
    const body = (await request.json()) as Partial<SmtpSettings>;
    return HttpResponse.json({
      ...smtpSettings,
      ...body,
      has_password: true,
      configured: true,
    });
  }),
  http.post("/api/v1/settings/smtp/test", async ({ request }) => {
    const body = (await request.json()) as { to_address: string };
    return HttpResponse.json({ sent: true, to_address: body.to_address });
  }),
  http.get("/api/v1/settings/oidc", () => HttpResponse.json(oidcSettings)),
  http.put("/api/v1/settings/oidc", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      ...oidcSettings,
      ...body,
      configured: true,
      has_client_secret: true,
    });
  }),
  http.post("/api/v1/settings/oidc/test-discovery", async ({ request }) => {
    const body = (await request.json()) as { issuer_url: string };
    return HttpResponse.json({
      issuer_url: body.issuer_url,
      endpoints: {
        authorization_endpoint: `${body.issuer_url}/authorize`,
        jwks_uri: `${body.issuer_url}/jwks`,
      },
    });
  }),
  http.get("/api/v1/settings/synthetic", () =>
    HttpResponse.json(syntheticSettings),
  ),
  http.put("/api/v1/settings/synthetic", async ({ request }) => {
    const body = (await request.json()) as {
      enabled: boolean;
      interval_seconds: number;
    };
    return HttpResponse.json({
      ...syntheticSettings,
      ...body,
      interval_seconds: Math.max(30, body.interval_seconds),
    });
  }),
  http.post("/api/v1/settings/monitoring-setup", async ({ request }) => {
    const body = (await request.json()) as { source_name: string };
    const source = body.source_name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    return HttpResponse.json(
      {
        source_name: source,
        key_name: `rsync-client-${source}`,
        api_key: "rsv_newkey123",
        snippet: `services:\n  rsync-client-${source}:\n    environment:\n      - RSYNC_VIEWER_API_KEY=rsv_newkey123`,
      },
      { status: 201 },
    );
  }),
  http.get("/api/v1/changelog", ({ request }) => {
    const all = new URL(request.url).searchParams.get("all") === "true";
    return HttpResponse.json(
      all ? { ...changelog, has_more: false } : changelog,
    );
  }),
  http.get("/api/v1/api-keys", () => HttpResponse.json(apiKeys)),
  http.post("/api/v1/api-keys", async ({ request }) => {
    const body = (await request.json()) as {
      name: string;
      role_override?: string | null;
    };
    return HttpResponse.json(
      {
        id: "aaaaaaaa-0000-4000-8000-000000000009",
        name: body.name,
        key: "rsv_brandnewkey_0123456789",
        key_prefix: "rsv_bran",
        role: body.role_override ?? "operator",
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),
  http.delete(
    "/api/v1/api-keys/:id",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.get("/api/v1/users", () => HttpResponse.json(users)),
  http.put("/api/v1/users/:id/role", async ({ params, request }) => {
    const body = (await request.json()) as { role: UserRead["role"] };
    const user = users.find((u) => u.id === params.id)!;
    return HttpResponse.json({ ...user, role: body.role });
  }),
  http.put("/api/v1/users/:id/status", async ({ params, request }) => {
    const body = (await request.json()) as { is_active: boolean };
    const user = users.find((u) => u.id === params.id)!;
    return HttpResponse.json({ ...user, is_active: body.is_active });
  }),
  http.delete(
    "/api/v1/users/:id",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.post("/api/v1/users/:id/reset-password", () =>
    HttpResponse.json({ message: "Password reset email sent" }),
  ),
  http.get("/api/v1/webhooks", () => HttpResponse.json(webhooks)),
  http.post("/api/v1/webhooks", async ({ request }) => {
    const body = (await request.json()) as Partial<WebhookRead>;
    return HttpResponse.json(
      { ...webhooks[0], ...body, id: "cccccccc-0000-4000-8000-000000000009" },
      { status: 201 },
    );
  }),
  http.put("/api/v1/webhooks/:id", async ({ params, request }) => {
    const body = (await request.json()) as Partial<WebhookRead>;
    const wh = webhooks.find((w) => w.id === params.id)!;
    return HttpResponse.json({ ...wh, ...body });
  }),
  http.delete(
    "/api/v1/webhooks/:id",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.post("/api/v1/webhooks/:id/test", () =>
    HttpResponse.json({ status: "sent", http_status: 204 }),
  ),
  http.get("/api/v1/synthetic/status", () =>
    HttpResponse.json(syntheticStatusPassing),
  ),
  http.get("/api/v1/synthetic/history", () =>
    HttpResponse.json(syntheticHistory),
  ),
  http.get("/api/v1/sources/health", () => HttpResponse.json(sourcesHealth)),
  http.get("/api/v1/sync-logs", () => HttpResponse.json(syncLogs)),
  http.get("/api/v1/sync-logs/sources", () =>
    HttpResponse.json({ sources: ["movies", "nas-backup", "photos"] }),
  ),
  http.get("/api/v1/sync-logs/:id", () => HttpResponse.json(syncLogDetail)),
  http.get("/api/v1/analytics/summary", () => HttpResponse.json(summary)),
  http.get("/api/v1/analytics/sources", () => HttpResponse.json(sourceStats)),
  http.get("/api/v1/media/new", () => HttpResponse.json(mediaNew)),
  http.get("/api/v1/media/summary", () => HttpResponse.json(mediaSummary)),
  http.get("/api/v1/users/me/preferences", () =>
    HttpResponse.json({ theme: "dark" }),
  ),
  http.get("/api/v1/version/updates", () =>
    HttpResponse.json(updateStatusCurrent),
  ),
];
