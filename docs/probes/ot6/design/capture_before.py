# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Capture the operator dashboard at desktop and phone width and measure it.

    PYTHONPATH=cli:cli/tests pixi run python docs/probes/ot6/design/capture_before.py URL OUT_DIR LABEL

Writes ``<label>-1400.png`` (1400x900) and ``<label>-400x850.png`` (400x850,
mobile emulation) into OUT_DIR, plus ``<label>.json`` with what the page
reported: the selected project and run, horizontal overflow at each width,
the computed type sizes of the headings and body, and the palette tokens the
stylesheet declares. Inspects only; it never starts or stops a server, and
the URL is an argument so no private address enters a committed file.
"""
import json
from pathlib import Path
import sys

from cdp_browser import HeadlessBrowser, find_browser

MEASURE = """(function () {
  var cs = getComputedStyle(document.documentElement);
  var tokens = {};
  ['--bg','--panel','--line','--fg','--muted','--ok','--warn','--bad','--info','--hist',
   '--surface','--surface-2','--rule','--ink','--ink-2','--accent'].forEach(function (name) {
    var v = cs.getPropertyValue(name).trim(); if (v) tokens[name] = v; });
  function size(sel) { var n = document.querySelector(sel); return n ? getComputedStyle(n).fontSize : null; }
  var canvas = document.getElementById('viewer').getBoundingClientRect();
  var sidebar = document.getElementById('sidebar').getBoundingClientRect();
  return {
    innerWidth: innerWidth, innerHeight: innerHeight,
    visual_viewport: { width: visualViewport.width, scale: visualViewport.scale },
    scrollWidth: document.documentElement.scrollWidth,
    horizontal_overflow_px: Math.max(0, document.documentElement.scrollWidth - innerWidth),
    page_height: document.documentElement.scrollHeight,
    fonts: { body: size('body'), h1: size('h1'), h2: size('h2'), badge: size('.badge'),
             mono: size('.mono'), small: size('.small'), button: size('button') },
    canvas: { width: canvas.width, height: canvas.height, left: canvas.left },
    sidebar: { width: sidebar.width, top: sidebar.top },
    tokens: tokens,
    project: document.getElementById('project-name').textContent,
    view: document.getElementById('view-kind').textContent,
    freshness: document.getElementById('freshness').dataset.state,
    model: document.getElementById('model-status').dataset.state
  };
})()"""


def capture(browser, url, width, height, mobile, path):
    page = browser.page("about:blank")
    page.send("Emulation.setDeviceMetricsOverride", {
        "width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile})
    if mobile:
        page.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
    page.send("Page.navigate", {"url": url})
    page.wait_for("document.readyState === 'complete'")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state !== 'empty'", timeout=30)
    page.wait_for("document.getElementById('freshness').dataset.state !== 'loading'", timeout=30)
    page.screenshot(path)
    return page.evaluate(MEASURE)


def main(url, out, label):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    result = {"url_host": url.split("//", 1)[-1].rstrip("/").split(":")[-1], "shots": {}}
    with HeadlessBrowser(find_browser()) as browser:
        for name, width, height, mobile in (("1400", 1400, 900, False), ("400x850", 400, 850, True),
                                            ("400-desktop", 400, 850, False)):
            path = out / f"{label}-{name}.png"
            result["shots"][name] = capture(browser, url, width, height, mobile, path)
            result["shots"][name]["png_bytes"] = path.stat().st_size
    (out / f"{label}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:4])
