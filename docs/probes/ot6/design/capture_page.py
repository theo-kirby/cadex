# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Capture the operator dashboard at desktop and phone width and measure it.

    PYTHONPATH=cli:cli/tests pixi run python docs/probes/ot6/design/capture_page.py URL OUT_DIR LABEL

Writes ``<label>-1400.png`` (1400x900) and ``<label>-400x850.png`` (400x850,
mobile emulation) into OUT_DIR, plus ``<label>.json`` with what the page
reported: the selected project and run, horizontal overflow at each width,
the computed type sizes of the headings and body, and the palette tokens the
stylesheet declares (the spec's names, plus the pre-spec names so the same
script measured the "before"; a name the stylesheet no longer declares is
simply absent). At the phone size it also drives the page by touch — a
one-finger drag on the model, a tap on Fit — and records the camera before
and after, then clips each of the spec's regions (§2) to
``<label>-400-<region>.png``, at most one phone screen tall, recording each
region's full height. Inspects only; it never starts or stops a server, and
the URL is an argument so no private address enters a committed file.
"""
import json
from pathlib import Path
import sys
import time

from cdp_browser import HeadlessBrowser, find_browser

MEASURE = """(function () {
  var cs = getComputedStyle(document.documentElement);
  var tokens = {};
  ['--bg','--surface','--surface-2','--surface-3','--rule','--rule-strong','--ink','--ink-2','--accent',
   '--ok','--warn','--bad','--info','--panel','--line','--fg','--muted','--hist'].forEach(function (name) {
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


REGIONS = ("top", "sidebar", "identity", "model", "curves", "videos-region", "record")


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
    result = page.evaluate(MEASURE)
    if not mobile:
        return result
    # Touch: one finger orbits, a tap on Fit restores the camera. The page
    # must not scroll under the finger.
    page.scroll_into_view("#viewer")
    box = page.rect("#viewer")
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    before = page.evaluate("window.cadexReview.viewer().camera()")
    scroll = page.evaluate("scrollY")
    page.touch_drag(cx, cy, cx + 120, cy + 50)
    after = page.evaluate("window.cadexReview.viewer().camera()")
    scrolled = page.evaluate("scrollY") - scroll
    # A finger lifts and comes back: Chromium drops a tap that lands within
    # a few hundred ms of the drag's end, on a phone as under emulation.
    time.sleep(1.0)
    page.tap(*_centre(page, "#model-fit"))
    try:
        fitted = page.wait_for("(function(){var c=window.cadexReview.viewer().camera(); return c.yaw === 0.8 && c})()", timeout=5)
    except Exception:  # noqa: BLE001 — recorded as a failure, not raised
        fitted = page.evaluate("window.cadexReview.viewer().camera()")
    result["touch"] = {"camera_before": before, "camera_after_drag": after,
                       "orbited": after["yaw"] != before["yaw"] and after["pitch"] != before["pitch"]
                       and after["distance"] == before["distance"],
                       "page_scrolled_px": scrolled,
                       "camera_after_fit": fitted, "fit_restored": fitted == before}
    page.evaluate("scrollTo(0, 0)")
    result["regions"] = {}
    for region in REGIONS:
        box = page.rect("#" + region)
        clip = dict(box, height=min(box["height"], height))
        region_path = path.with_name(f"{path.stem.split('-')[0]}-400-{region}.png")
        page.screenshot(region_path, clip=clip)
        result["regions"][region] = {"width": box["width"], "height": box["height"],
                                     "captured_height": clip["height"], "png_bytes": region_path.stat().st_size}
    return result


def _centre(page, selector):
    page.scroll_into_view(selector)
    box = page.rect(selector)
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


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
