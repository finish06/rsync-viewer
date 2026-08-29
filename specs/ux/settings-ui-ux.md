# UX Design: Settings in the Insight UI

**Spec:** specs/settings-ui.md
**Status:** DRAFT — pending human sign-off (generated 2026-08-29)
**Iterations:** 1

Principles: settings are reached from the ⚙ menu (never primary nav); one sub-nav on the left (bottom tabs on mobile); every form saves in place with inline validation and a toast; secrets are write-only ("unchanged" placeholders); destructive actions confirm inline, not in browser dialogs.

## Screens

### Settings shell (`/app/settings/*`)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ◉ Rsync Viewer   Overview  Transfers  Trends  Media  Uptime   ● UP 99.8%  ⚙ │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ SETTINGS      │  API KEYS                                   [+ New key]      │
│ ▸ API keys    │  ┌──────────────────────────────────────────────────────┐   │
│   Webhooks    │  │ name            prefix     role      created   last  │   │
│   Email     ⓐ │  │ laptop-backup   rsv_ab12…  operator  Aug 12    2h    ⋯│   │
│   Sign-in   ⓐ │  │ rsync-client-nas rsv_9f…   operator  Aug 27    1m    ⋯│   │
│   Monitoring ⓐ│  └──────────────────────────────────────────────────────┘   │
│   Users     ⓐ │  ☐ show all users' keys (admin)                              │
│   Changelog   │                                                              │
└───────────────┴──────────────────────────────────────────────────────────────┘
ⓐ = admin only (hidden for operators/viewers)
```

### New API key (inline panel, not modal)
```
┌ New API key ───────────────────────────────────────────────┐
│ Name [laptop-backup        ]  Role [operator ▾ (≤ yours)]  │
│                                   [Cancel] [Create key]    │
├────────────────────────────────────────────────────────────┤
│ ✓ Key created — copy it now, it will not be shown again    │
│ rsv_ab12cd34…xyz                                  [Copy]   │
└────────────────────────────────────────────────────────────┘
```

### Webhooks
```
│ WEBHOOKS                                          [+ Add webhook]           │
│ ● Discord ops    discord  ⟳ 0 fails   [Test] [Edit] [⏻ on]  [Delete]         │
│ ○ Home Assistant generic  ⟳ 3 fails   [Test] [Edit] [⏻ off] [Delete]         │
│ ┌ Edit: Discord ops ───────────────────────────────────────────────────────┐ │
│ │ Name [..] URL [..] Type (● generic ○ discord)  Sources [movies, tv]       │ │
│ │ Headers (JSON) [{"Authorization": "Bearer …"}]                           │ │
│ │ Discord: colour [#ff0045] username [..] avatar [..] footer [..]          │ │
│ │ ⚠ URL must match https://discord.com/api/webhooks/…      [Cancel] [Save] │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
```

### Email (SMTP) / Sign-in (OIDC)
```
│ EMAIL                                                                       │
│ ⚠ ENCRYPTION_KEY is not set — saving is disabled until it is.  (when absent) │
│ Host [smtp.example.com]  Port [587]  Encryption [STARTTLS ▾]                 │
│ Username [..]  Password [•••••• unchanged]  From [alerts@…]  Name [..]       │
│ [Save]      Send test to [me@example.com] [Send]  ✓ sent / ✕ could not…      │
```
Sign-in mirrors it: issuer, client ID, secret (required first time), provider name, scopes, ☐ enabled, ☐ hide local login (⚠ lock-out warning), callback URL [Copy], [Test discovery] → list of endpoints.

### Monitoring
```
│ SYNTHETIC CHECK   ● PASSING · every 5 min · last 2m ago      ☑ enabled       │
│ Interval (s) [300]  [Save]  → "Changes take effect immediately"              │
│ ── Add an rsync client ────────────────────────────────────────────────────  │
│ Source name [nas-backup]  Rsync source [user@host:/path]  Schedule [0 */6…]  │
│ SSH key [~/.ssh/id_rsa]  Args [-avz --stats]  Mode (● pull ○ push)  [Generate]│
│ ┌ docker-compose snippet ─────────────────────────────── [Copy] ───────────┐ │
│ │ services: rsync-client-nas-backup: …  RSYNC_VIEWER_API_KEY=rsv_… (once)  │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
```

### Users (admin)
```
│ USERS                                                                       │
│ username   email            role        status   last login                 │
│ finish06   …@…              admin (you) active   2m ago                     │
│ ops        ops@…            [operator▾] active   Aug 20   [Disable] [Reset pw] [Delete] │
│ ✕ Cannot demote the last admin   (inline, red, next to the row)             │
```

### Changelog
Accordion: `v2.12.0 · 2026-08-29 [current]` ▸ sections; "Show older versions".

## State Matrix
| State | Behaviour |
|---|---|
| Loading | skeleton rows/forms |
| Empty | "No API keys yet — create one", "No webhooks configured", "Not configured" for SMTP/OIDC |
| Validation error | inline under the field (422 from API mapped to field when possible, else form-level) |
| Server error | form-level red note with retry; page never blanks |
| Forbidden (403 / wrong role) | section shows "You need the admin role for this" |
| Success | green toast, form re-rendered from the server response |
| Mobile | sub-nav becomes a horizontal scrollable tab strip |

## Flow
⚙ menu → `/app/settings` (defaults to API keys) → section links. Legacy `/settings`, `/admin/users` redirect. Wizard-created key also appears under API keys.

## Key decisions
1. Inline panels instead of modals (consistent with the dashboard's expand-in-place).
2. Secrets are write-only; the UI never displays them, only "set/unset".
3. Webhook/API-key/user features reuse the existing JSON APIs; only SMTP/OIDC/synthetic/wizard/changelog get new endpoints.
4. CSRF header on every cookie-authenticated API mutation (closes the Phase 1 gap while we are here).
