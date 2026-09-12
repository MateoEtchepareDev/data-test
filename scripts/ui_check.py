#!/usr/bin/env python
"""UI verification for the dashboard frontend (Fase 4 hito).

Spawns the local Flask API + a static server for `frontend/`, then drives the
page with Playwright across desktop/tablet/mobile viewports and asserts:

  * no console errors / failed network requests
  * KPIs are populated and both Chart.js charts render
  * the map initializes, tiles render (no gray tiles), 23 provinces are drawn
  * exactly one province is highlighted, fully visible, matching the API's top province
  * the legend badge shows that province
  * only Excel provinces carry data: shaded by value and permanently labeled
    with the amount; provinces without data stay as faint non-interactive outlines
  * clicking a province with sales shows its figure in the legend (one highlight)
  * "Actualizar datos" re-renders without breaking the map
  * failure mode: with the API down, the map still renders provinces and the
    UI surfaces an error instead of going blank

Use:
    .venv\\Scripts\\python.exe scripts\\ui_check.py                      # starts servers itself
    .venv\\Scripts\\python.exe scripts\\ui_check.py --site http://127.0.0.1:8000
    .venv\\Scripts\\python.exe scripts\\ui_check.py --shots C:\\temp\\ui-shots --viewports desktop-1366x768,mobile-390x844
"""

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

VIEWPORTS = {
    "desktop-1440x900": (1440, 900),
    "desktop-1366x768": (1366, 768),
    "small-1024x768": (1024, 768),
    "tablet-768x1024": (768, 1024),
    "mobile-390x844": (390, 844),
}

MAP_ACCENT = "rgb(194, 65, 12)"


def _port_free(port):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def wait_port(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.4)
    return False


def spawn_servers(api_port, site_port):
    procs = []
    if _port_free(api_port):
        runner = ROOT / "scripts" / "_api_dev.py"
        procs.append(subprocess.Popen(
            [sys.executable, str(runner), str(api_port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=ROOT,
        ))
    if _port_free(site_port):
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "http.server", str(site_port),
             "--directory", str(FRONTEND)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=ROOT,
        ))
    wait_port(api_port)
    wait_port(site_port)
    return procs


def wait_for(fn, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if fn():
            return True
        time.sleep(0.2)
    return False


def map_state(page):
    return page.evaluate(
        "() => {"
        "  const m = document.getElementById('mapa');"
        "  const containerRect = m.getBoundingClientRect();"
        "  const accent = " + json.dumps(MAP_ACCENT) + ";"
        "  const highlighted = Array.from(document.querySelectorAll('#mapa path')).filter(p => {"
        "    const s = getComputedStyle(p);"
        "    return s.fill === accent && s.fillOpacity === '0.9';"
        "  });"
        "  let highlightVisible = false;"
        "  if (highlighted.length === 1) {"
        "    const b = highlighted[0].getBoundingClientRect();"
        "    highlightVisible = b.width > 20 && b.height > 20 &&"
        "      b.left >= containerRect.left - 1 && b.right <= containerRect.right + 1 &&"
        "      b.top >= containerRect.top - 1 && b.bottom <= containerRect.bottom + 1;"
        "  }"
        "  return {"
        "    clientW: m.clientWidth, clientH: m.clientHeight,"
        "    inited: !!document.querySelector('#mapa .leaflet-pane'),"
        "    tiles: document.querySelectorAll('#mapa .leaflet-tile-loaded').length,"
        "    grayTiles: document.querySelectorAll('#mapa img.leaflet-tile:not(.leaflet-tile-loaded)').length,"
        "    provincePaths: document.querySelectorAll('#mapa path.leaflet-interactive').length,"
        "    highlightPaths: highlighted.length,"
        "    highlightVisible,"
        "    legendError: document.getElementById('map-destacada').classList.contains('is-error'),"
        "    alertVisible: (() => { const a = document.getElementById('api-alert');"
        "                    return a ? !a.hidden : false; })(),"
        "  };"
        "}"
    )


def normalize(text):
    byte = str(text or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        byte = byte.replace(a, b)
    return byte


def legend_name(page):
    text = page.evaluate("document.getElementById('map-destacada').textContent")
    return text.split("—")[0].strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="http://127.0.0.1:8000")
    parser.add_argument("--no-spawn", action="store_true",
                        help="expect servers already running on the ports below")
    parser.add_argument("--api-port", type=int, default=5000)
    parser.add_argument("--site-port", type=int, default=8000)
    parser.add_argument("--viewports", default=",".join(VIEWPORTS))
    parser.add_argument("--shots", default="",
                        help="save a screenshot per viewport to this directory")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    procs = [] if args.no_spawn else spawn_servers(args.api_port, args.site_port)
    site = args.site if args.no_spawn else f"http://127.0.0.1:{args.site_port}"
    api = (args.site if args.no_spawn else f"http://127.0.0.1:{args.api_port}")

    failures = []

    def check(cond, message):
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {message}")
        if not cond:
            failures.append(message)

    shots_dir = Path(args.shots) if args.shots else None
    if shots_dir:
        shots_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            viewports = [v for v in args.viewports.split(",") if v]
            w, h = VIEWPORTS[viewports[0]]
            page = browser.new_page(viewport={"width": w, "height": h})

            console_errors = []
            requests_failed = []
            page.on("pageerror", lambda e: console_errors.append(str(e)))
            page.on("console", lambda m: console_errors.append(m.text)
                    if m.type == "error" else None)
            page.on("requestfailed", lambda r: requests_failed.append(
                f"{r.method} {r.url} -> {r.failure}"))

            page.goto(site, wait_until="load", timeout=30000)
            page.wait_for_timeout(4000)

            print("== Desktop load ==")
            kpis = page.evaluate(
                "() => Array.from(document.querySelectorAll('.kpi__value')).map(e => e.textContent)"
            )
            check(len(kpis) == 3 and all(v != "—" for v in kpis),
                  "KPIs populated (first run)")

            canvases = page.evaluate(
                "() => ({line: [document.getElementById('chart-lineas').width,"
                " document.getElementById('chart-lineas').height],"
                " bar: [document.getElementById('chart-barras').width,"
                " document.getElementById('chart-barras').height]})"
            )
            check(canvases["line"][0] > 100 and canvases["line"][1] > 100,
                  "line chart rendered")
            check(canvases["bar"][0] > 100 and canvases["bar"][1] > 100,
                  "bar chart rendered")

            check(wait_for(lambda: map_state(page)["inited"], 15),
                  "map initialized (within 15s)")
            check(wait_for(lambda: map_state(page)["tiles"] > 0, 15),
                  "base tiles rendered (within 15s)")
            page.wait_for_timeout(400)
            st = map_state(page)
            check(st["clientW"] > 100 and st["clientH"] > 100,
                  f"map container has real size ({st['clientW']}x{st['clientH']})")
            check(st["tiles"] > 0, f"base tiles rendered ({st['tiles']})")
            check(wait_for(lambda: map_state(page)["grayTiles"] == 0, 10),
                  "no unloaded (gray) tiles")
            st = map_state(page)
            check(st["provincePaths"] >= 23, f"all provinces drawn ({st['provincePaths']})")
            check(st["highlightPaths"] == 1,
                  f"exactly one province highlighted ({st['highlightPaths']})")
            check(st["highlightVisible"], "highlighted province fully visible (not clipped)")
            check(not st["legendError"], "map legend has no error state")
            check(not st["alertVisible"], "no global API alert with API up")

            api_top = page.evaluate(
                "async () => { const r = await fetch('" + api
                + "/analytics/provincia-mayor-volumen');"
                " return (await r.json()).provincia; }"
            )
            check(api_top and normalize(legend_name(page)) == normalize(api_top),
                  f"legend highlights API top province ('{legend_name(page)}' vs '{api_top}')")

            print("== All viewports ==")
            for vp in viewports:
                w, h = VIEWPORTS[vp]
                page.set_viewport_size({"width": w, "height": h})
                page.wait_for_timeout(1500)
                if not map_state(page)["inited"]:
                    wait_for(lambda: map_state(page)["inited"], 10)
                if map_state(page)["tiles"] == 0:
                    wait_for(lambda: map_state(page)["tiles"] > 0, 10)
                page.wait_for_timeout(400)
                st = map_state(page)
                check(st["inited"], f"[{vp}] map initialized")
                check(st["clientW"] > 100 and st["clientH"] > 100,
                      f"[{vp}] map container real size ({st['clientW']}x{st['clientH']})")
                check(st["grayTiles"] == 0, f"[{vp}] no gray tiles")
                check(st["highlightPaths"] == 1, f"[{vp}] one province highlighted")
                check(st["highlightVisible"], f"[{vp}] highlighted province visible")
                if shots_dir:
                    page.screenshot(path=str(shots_dir / f"{vp}.png"))

            print("== Refresh lifecycle ==")
            page.set_viewport_size({"width": 1366, "height": 768})
            page.wait_for_timeout(800)
            page.click("#btn-refresh")
            page.wait_for_timeout(2000)
            if not map_state(page)["inited"]:
                wait_for(lambda: map_state(page)["inited"], 10)
            st = map_state(page)
            check(st["inited"], "map re-rendered after refresh")
            check(st["highlightPaths"] == 1, "province still highlighted after refresh")
            check(st["highlightVisible"], "highlight visible after refresh")

            print("== Province click ==")

            def province_box(page, prov):
                return page.evaluate(
                    "() => {"
                    "  const el = Array.from(document.querySelectorAll('#mapa path'))"
                    "    .find(p => p.dataset.ventasProvincia === " + json.dumps(prov) + ");"
                    "  if (!el) return null;"
                    "  el.scrollIntoView({ block: 'center' });"
                    "  const b = el.getBoundingClientRect();"
                    "  const c = document.getElementById('mapa').getBoundingClientRect();"
                    "  return {"
                    "    x: b.left + b.width / 2,"
                    "    y: b.top + b.height / 2,"
                    "    inside: b.left >= c.left - 1 && b.right <= c.right + 1 &&"
                    "      b.top >= c.top - 1 && b.bottom <= c.bottom + 1,"
                    "    pointerEvents: getComputedStyle(el).pointerEvents,"
                    "  };"
                    "}"
                )

            data_provinces = page.evaluate(
                "async () => { const r = await fetch('" + api
                + "/analytics/ventas-por-provincia'); return (await r.json()).length; }"
            )
            check(data_provinces >= 1, f"API reports data provinces ({data_provinces})")

            tooltip_count = page.evaluate(
                "() => document.querySelectorAll('#mapa .leaflet-tooltip').length"
            )
            check(tooltip_count == data_provinces,
                  f"one permanent label per Excel province ({tooltip_count}/{data_provinces})")

            money_labels = page.evaluate(
                "() => Array.from(document.querySelectorAll('#mapa .leaflet-tooltip'))"
                ".some(t => (t.textContent || '').includes('$'))"
            )
            check(money_labels, "permanent labels include the amount ($)")

            data_fill = page.evaluate(
                "() => { const el = Array.from(document.querySelectorAll('#mapa path'))"
                "  .find(p => p.dataset.ventasProvincia === 'santa fe');"
                "  return el ? getComputedStyle(el).fill : ''; }"
            )
            check(data_fill.startswith("rgba(194, 65, 12"),
                  f"Excel province shaded by value, not opaque accent ({data_fill})")

            no_data_label = page.evaluate(
                "() => Array.from(document.querySelectorAll('#mapa .leaflet-tooltip'))"
                ".some(t => (t.textContent || '').includes('Pampa'))"
            )
            check(not no_data_label, "no-data province has no permanent label")

            mendoza = province_box(page, "mendoza")
            check(mendoza is not None and mendoza["inside"],
                  "data province (Mendoza) visible inside the map")
            check(mendoza is not None and mendoza["pointerEvents"] != "none",
                  "data province receives pointer events (clickable)")
            if mendoza and mendoza["inside"] and mendoza["pointerEvents"] != "none":
                page.mouse.click(mendoza["x"], mendoza["y"])
                page.wait_for_timeout(500)
                st = map_state(page)
                check(normalize(legend_name(page)) == "mendoza",
                      f"legend shows clicked province ('{legend_name(page)}')")
                check(st["highlightPaths"] == 1,
                      "exactly one province highlighted after click")

            la_pampa = province_box(page, "la pampa")
            check(la_pampa is not None and la_pampa["inside"],
                  "no-data province (La Pampa) visible inside the map")
            check(la_pampa is not None and la_pampa["pointerEvents"] == "none",
                  "no-data province is not clickable (pointer-events none)")
            if la_pampa and la_pampa["inside"]:
                antes = legend_name(page)
                page.mouse.click(la_pampa["x"], la_pampa["y"])
                page.wait_for_timeout(400)
                st = map_state(page)
                check(legend_name(page) == antes,
                      "clicking a province without data leaves the legend unchanged")
                check(st["highlightPaths"] == 1,
                      "highlight unchanged after clicking a province without data")

            print("== Failure mode: API down ==")
            down = browser.new_page(viewport={"width": 1366, "height": 768})
            down_errors = []
            down.on("pageerror", lambda e: down_errors.append(str(e)))
            down.on("console", lambda m: down_errors.append(m.text)
                    if m.type == "error" and "Failed to load resource" not in m.text else None)
            down.route("**/analytics/**", lambda route: route.abort())
            down.route("**/kpis/**", lambda route: route.abort())
            down.goto(site, wait_until="load", timeout=30000)
            down.wait_for_timeout(3000)
            if not map_state(down)["inited"]:
                wait_for(lambda: map_state(down)["inited"], 15)
            if map_state(down)["tiles"] == 0:
                wait_for(lambda: map_state(down)["tiles"] > 0, 10)
            down.wait_for_timeout(400)
            st = map_state(down)
            check(st["inited"], "[api-down] map still initializes (GeoJSON independent of API)")
            check(st["provincePaths"] >= 23, f"[api-down] all provinces drawn ({st['provincePaths']})")
            check(st["grayTiles"] == 0, "[api-down] no gray tiles")
            check(st["highlightPaths"] == 0, "[api-down] no highlight (top province unknown)")
            check(st["legendError"], "[api-down] legend shows error state")
            check(st["alertVisible"], "[api-down] global API alert visible")
            down_labels = down.evaluate(
                "() => document.querySelectorAll('#mapa .leaflet-tooltip').length"
            )
            check(down_labels == 0, "[api-down] no permanent labels (no province data)")
            check(len(down_errors) == 0, f"[api-down] no console errors ({down_errors})")
            if shots_dir:
                down.screenshot(path=str(shots_dir / "api-down.png"))

            check(len(console_errors) == 0,
                  f"no console/page errors ({console_errors})")
            check(len(requests_failed) == 0,
                  f"no failed requests ({requests_failed})")

            browser.close()

        if failures:
            print(f"\n{len(failures)} check(s) FAILED")
            for f in failures:
                print("  -", f)
            return 1
        print("\nAll UI checks passed.")
        return 0
    finally:
        for proc in procs:
            try:
                proc.kill()
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())