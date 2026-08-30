# UX: Overview v2 — exceptions first (DRAFT, pending human sign-off)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ✓ All 3 sources healthy        ● UP 99.6% · checked 2m ago           │  attention strip (calm)
│                                         [ ▂▃▂▅▃▇▂ 14-day volume ]    │  volume mini-chart, right
└──────────────────────────────────────────────────────────────────────┘
   — or, when something is wrong —
┌──────────────────────────────────────────────────────────────────────┐
│ ✕ nas-backup FAILED 3h ago · 3 in a row · overdue by ~6h   [view →]  │  loud card(s), one per problem
└──────────────────────────────────────────────────────────────────────┘

SOURCES                                                    last 14 days
● movies       synced 2h ago    · due in ~22h   ▂▃▂▅▃▇▂   41 syncs · 12.3 GB
● tv           synced 40m ago   · due in ~5h    ▃▃▅▂▃▅▃   88 syncs · 30.1 GB
○ photos       never synced                                —
[Show 1 inactive source]

┌ New this week ┐ ┌ Activity (last 7 days) ────────────────────────────┐
│ (unchanged)   │ │ (unchanged)                                        │
└───────────────┘ └────────────────────────────────────────────────────┘
```

Principles
- One emotional register per state: green calm line vs red cards — never both
  competing.
- Healthy rows are one line, muted; the only coloured pixel is the status dot
  and the due chip when it flips to overdue.
- Volume chart is ambient (no axes, tooltip on hover), sharing the strip so
  it costs no vertical space.
- Declutter: "1 sync", failures shown only when > 0, "—" for < 1 KB.
