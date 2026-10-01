# Web first-load performance audit

_2026-10-02 · production build served by the Docker nginx image, measured with Chromium at 390×844 mobile emulation on a throttled "slow 4G" profile (150 ms RTT, 1.6 Mbps down, 750 kbps up, 4× CPU slowdown), cache disabled, median of 3 runs._

## What was actually wrong

1. **Nothing was compressed.** nginx served the 469 KB entry script and the API JSON uncompressed. This was by far the largest cost.
2. **The landing page carried code it never uses.**
   - zod, react-hook-form and @hookform/resolvers (≈37 KB gzipped) are used only by the sign-in and registration forms.
   - The signed-in layouts (app shell and role navigation) were imported eagerly.
   - Both translation files were bundled, so every visitor downloaded English *and* Kiswahili.
3. Not a problem:
   - react-dom, react-router, i18next and TanStack Query are genuinely needed to render `/`.
   - lucide icons were already imported per icon (tree-shaken).
   - There are no chart, date, map, editor or animation libraries in the bundle.
   - Fonts already load only the Latin subsets (unicode-range) with `font-display: swap`.
   - The hero photo was already responsive WebP with `fetchpriority="high"` and not lazy-loaded; the Dar es Salaam photo is lazy below the fold.

## Changes

| Change | Why |
|---|---|
| nginx `gzip_static` + build-time precompression (`web/scripts/precompress.mjs`, level 9) and on-the-fly gzip for proxied API JSON | Cuts transferred JS by ~78% with no per-request CPU |
| Lazy-load the sign-in/register pages (zod, react-hook-form), the provider join page and the signed-in layouts | Form and signed-in code leave the landing critical path |
| Idle-time prefetch of the sign-in chunk (skipped when `Save-Data` is on) | "Book a cleaning" leads to sign-in; it is ready without delaying the first render |
| Kiswahili translations loaded on demand; English stays in the entry as default and fallback. Kiswahili users get their language before first render (no English flash); everyone else fetches it on hover, focus or touch of the language switch | Nobody downloads both languages up front, and switching stays instant |
| `Suspense` boundaries inside the public layout and app shell, with a full-height route loader | The header and sidebar stay mounted while a route loads, and no layout shift occurs (this fixed a CLS of 0.22 on `/login` introduced by lazy-loading) |
| `experimentalMinChunkSize` | Merges tiny shared chunks to avoid extra round trips on high-latency networks |
| Cache headers: `/assets/*` (hashed) `max-age=31536000, immutable`; `index.html` `no-cache`; `/brand/*` one day | Repeat visits reuse assets; deploys show up immediately |

**Deliberately not done:**

- **Manual vendor chunks.** Splitting react/router/query into separate files doesn't reduce first-visit bytes and adds requests on HTTP/1.1. It would only help repeat visits after a deploy; revisit with HTTP/2 and frequent releases.
- **Replacing react-dom, i18next or TanStack Query.** These are mature dependencies doing real work.
- **Dropping the Fraunces display font (36 KB).** It carries the brand typography.
- **Splitting translation files by app area.** That would save ~5 KB for added complexity.
- **Signed-in icon micro-chunks.** About 12 icons shared between signed-in routes still form ~300-byte chunks. App code imports them through the lucide barrel, so Rollup's module graph cannot assign them cleanly. They never load on public pages, they preload in parallel with their route, and they are then cached immutably.

## Before / after

| Landing page `/` | Before | After |
|---|---|---|
| Entry JS (minified) | 480 KB | 340 KB |
| Entry JS on the wire | 469 KB (uncompressed) | **105 KB** (gzip) |
| JS needed to render `/` | 469 KB | **105 KB** |
| Total transferred to render `/` | 622 KB | **≈215 KB** (+27 KB sign-in chunk prefetched after load) |
| API JSON on the wire | 16 KB | 6.6 KB |
| Largest chunk | 480 KB (entry) | 340 KB (entry) |
| Chunks required for `/` | entry JS + CSS | entry JS + CSS (unchanged count) |
| First Contentful Paint | 3.6 s | **1.4 s** |
| Largest Contentful Paint (hero image) | 3.7 s | **1.6 s** |
| Cumulative Layout Shift | 0.000 | 0.000 |

Other journeys after the change:

| Journey | FCP | LCP | CLS | Notes |
|---|---|---|---|---|
| Kiswahili first visit | 2.1 s | 2.2 s | 0.000 | Renders directly in Kiswahili; the 10.7 KB language chunk costs one extra round trip |
| Direct `/login` | 1.4 s | 1.8 s | 0.001 | |

The improvement comes from **fewer bytes on the critical path** (compression, plus form, signed-in and second-language code moved off the landing path), not from dividing the same code into more files: the landing page still needs exactly two first-party code files.

## Reproducing

```bash
docker compose up -d --build web
# Hashed asset: expect Content-Encoding: gzip and Cache-Control: immutable.
curl -sI -H 'Accept-Encoding: gzip' http://localhost:8080/assets/<entry>.js
```

## Possible next steps

- Serve over HTTP/2 or HTTP/3 behind TLS in production (fewer connection limits, header compression).
- Brotli: the stock nginx image has no brotli module. A CDN or `ngx_brotli` build would save a further ~15% on JS.
- Kiswahili first visits: emit a `<link rel="modulepreload">` for the language chunk when the stored locale is `sw`, removing the extra round trip.
