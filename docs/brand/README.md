# Rsync Viewer brand

**Mark:** two arrows chasing each other in a sync loop around a green status dot — "the eye that watches your syncs".
**Tagline:** *See every sync.*

| Asset | Use |
|-------|-----|
| `frontend/public/favicon.svg` | Vector mark (source of truth for UI: header logo, SVG favicon) |
| `frontend/public/favicon.ico` | Multi-size ICO (16–256 px) for browsers without SVG favicon support |
| `frontend/public/apple-touch-icon.png`, `icon-192.png`, `icon-512.png` | iOS home screen / PWA manifest |
| `docs/brand/hero.jpg`, `hero-1600.jpg` | README header, GitHub social preview (1280×640 crop works) |
| `docs/brand/icon-512.png`, `icon-source.png` | Raster mark for stores, Discord, Grafana, … |
| `docs/brand/source-icon.jpg` | Original generated icon render (Gemini image model, 2026-08-29); the hero's original render was 1.8 MB and is kept only as `hero.jpg` (q82) |

## Colours

| Token | Hex | Where |
|-------|-----|-------|
| Navy (background) | `#0f172a` | icon background, hero, `theme-color` |
| Blue (primary) | `#2563eb` → `#38bdf8` gradient | arrows, links, charts |
| Green (status OK) | `#22c55e` | centre dot, liveness pill |
| Text on navy | `#ffffff` / `#94a3b8` | wordmark / tagline |

Wordmark: system sans-serif (`system-ui`), weight 700, tight tracking — matches the SPA header.

## Rules
- Keep the green dot; it is the "watching" element that distinguishes the mark from a generic refresh icon.
- Minimum clear space around the mark: 15 % of its width. Do not recolour the arrows outside the blue gradient.
- Prefer the SVG everywhere the platform supports it; the raster files exist only for favicon/ICO/PWA compatibility.
