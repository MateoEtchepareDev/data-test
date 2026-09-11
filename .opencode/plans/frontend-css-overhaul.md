# Plan: CSS + Frontend Overhaul (dashboard, Fase 4)

## Goal
Fix the "broken map" and overhaul the dashboard UI: responsive layout (replace the fixed 1366×768 `transform: scale()` stage), keep the existing warm amber design language, and make the UI behave like a real product when the API is slow/down.

## Findings (via Playwright, acting as a final user)
- The app was verified in a real headless Chromium at 5 viewports; no console/network errors when the API is up.
- **Real bug 1 — map dies with the API:** `mapa.js` awaited `Promise.all([API, GeoJSON])`; if `/analytics/provincia-mayor-volumen` rejects, the whole map render throws → permanently blank map with no error message, no retry. GeoJSON fetch was needlessly blocked by the API call.
- **Real bug 2 — fixed stage:** `.stage` is hardcoded 1366×768 and scaled with `transform: scale()` (fit.js). On a laptop/mobile this letterboxes and shrinks the map content; Leaflet sizing + tooltip interactions degrade. Measured: mobile renders the dashboard at `scale(0.28)` — unusable.
- **Not a bug (avoid "fixing" it):** Leaflet's SVG `width/height` ≈1.2× the container is its padded pan-zoom bounds, normal behavior (confirmed in leaflet-src.js). The map was never visually cropped; the "wrong highlighting" impression comes from the shrink/letterbox shift of the fixed stage. Province name matching (API `Córdoba` vs GeoJSON `Córdoba`) is correct, but is now normalized defensively.
- **Polish gaps found as a final user:** charts and map failed silently with no message; refresh button gave no feedback; no global "API no disponible" signal.

## Changes already applied (on disk, unstaged)
- `frontend/js/mapa.js` — decoupled fetches; map always renders provinces even if API fails; error badge on legend; accent-insensitive name matching; `ResizeObserver` + resize `invalidateSize()`; global resize hook.
- `frontend/js/api.js` — `Dash.onRefresh` hooks, `setRefreshing` (button spinner/disabled), `showApiAlert` banner, `mostrarErrorPanel` (canvas-safe).
- `frontend/js/chart-lineas.js` / `chart-barras.js` — per-panel error message instead of silent blank.
- `frontend/index.html` — removed `fit.js`, added `#map-destacada` legend and `#api-alert`; `DOMContentLoaded → Dash.refresh()`.
- `frontend/css/styles.css` — responsive rewrite: 3-col → 2-col → 1-col grid; panel min-heights so charts/map keep real size on mobile; alert/legend/error/loading styles; keeps warm amber palette.
- Deleted `frontend/js/fit.js`.
- `scripts/ui_check.py` + `scripts/_api_dev.py` — Playwright verification harness.

## Remaining steps (blocked by plan-mode; execute after approval)
1. `scripts/ui_check.py`:
   - Remove the `paneAligned` assertion (false positive — map pane is intentionally larger; Leaflet clips it).
   - Keep real assertions: map init within timeout, container >100px, tiles>0, no gray tiles, 23 province paths, exactly 1 highlight, highlight fully inside container, legend == API top province, no console/page errors, no failed requests.
   - Add failure-mode scenario: `page.route()` abort on API endpoints → map still renders 23 provinces, no highlight, legend shows error, `#api-alert` visible, no console errors.
   - Add `--shots DIR` to save a screenshot per viewport for human review.
2. Update `docs/roadmap.md` — record `scripts/ui_check.py` as the reproducible Fase 4 UI verification harness.
3. Run `scripts/ui_check.py` → expect all green across 5 viewports + refresh + failure mode.
4. Run `pytest` (services/api, packages/shared) to confirm no regression.
5. Save viewport screenshots to a temp folder and report the path for the user to eyeball.

## Files touched
- `frontend/index.html`, `frontend/css/styles.css`, `frontend/js/{maps,api,kpis? no—mapa,api,chart-lineas,chart-barras}.js`, deleted `frontend/js/fit.js`
- `scripts/ui_check.py`, `scripts/_api_dev.py` (new)
- `docs/roadmap.md` (to append verification note)

## Verification definition of done
`python scripts/ui_check.py` exits 0 with all `[PASS]`, `pytest` green, screenshots confirm responsive layout at desktop/tablet/mobile.