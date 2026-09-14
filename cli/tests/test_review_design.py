# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The review dashboard's design spec, and the ot6 evidence caps (ADR-328).

``docs/REVIEW-DESIGN.md`` is the contract the page is held to (ADR-329).
Without a browser this suite pins the spec's required sections, its
page-background token to the environment module's dark scene background
(one palette across chrome and viewport), its "before" and "after"
measurements to the committed receipts, and every ot6 receipt to the
charter's caps — 16 KB per receipt, 200 KB per image — with no private
address or this machine's hostname in any of them. With a Chromium it
renders the page at the two charter sizes, 1400×900 and 400×850 with touch
emulation, and reads the spec back from the rendered page: the layout
viewport is the device width, nothing overflows it, the palette tokens and
type scale compute to §3–§4, the viewport fills the desk stage and the
phone's column, the run list is in the left sidebar at desk and a closed
disclosure on the phone, and at desk the frame of §12 resizes, folds and
changes what its stage shows under a real mouse (ADR-342).
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import math
import re
import shutil
import socket
import struct
import json

import pytest

from test_review_server import _model_state, _telemetry, browser, needs_browser, served  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs" / "REVIEW-DESIGN.md"
STATIC = REPO / "cli" / "cadex_cli" / "review_static"
EVIDENCE_DIRS = (REPO / "docs" / "probes" / "ot6", REPO / "docs" / "review-design")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
RECEIPT_CAP = 16 * 1024
IMAGE_CAP = 200 * 1024
PRIVATE_ADDRESS = re.compile(r"\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SECTIONS = ("## 1. Purpose", "## 2. Hierarchy", "## 3. Type scale", "## 4. Palette",
            "## 5. Spacing and shape", "## 6. Breakpoints")
TOKENS = ("--bg", "--surface", "--surface-2", "--surface-3", "--rule", "--rule-strong",
          "--ink", "--ink-2", "--accent", "--ok", "--warn", "--bad", "--info")
TYPE = {"body": "14px", "h1": "22px", "h2": "17px", ".badge": "12px", ".mono": "12px"}
# The desk frame's thin top bar and ruled sidebar sections step the two
# headings down one rung of the same scale (§12).
TYPE_DESK = {**TYPE, "h1": "17px", "h2": "14px"}
# The charter's two sizes: (width, height, mobile emulation with touch).
SIZES = {"desk": (1400, 900, False), "phone": (400, 850, True)}
PHONE_GUTTER = 12


def evidence_files():
    return sorted(path for root in EVIDENCE_DIRS if root.exists()
                  for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)


def spec_tokens() -> dict[str, str]:
    """The palette table's ``token -> hex`` pairs."""

    found = dict(re.findall(r"^\| `(--[a-z0-9-]+)` \| `(#[0-9a-f]{6})` \|", SPEC.read_text(), re.M))
    assert set(found) == set(TOKENS), sorted(set(found) ^ set(TOKENS))
    return found


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", path
    return struct.unpack(">II", head[16:24])


def test_spec_has_every_required_section_and_a_verified_date():
    text = SPEC.read_text()
    assert re.search(r"^Verified against source: \d{4}-\d{2}-\d{2}\.", text, re.M)
    for section in SECTIONS:
        assert section in text, section


def test_page_background_is_the_environment_scene_background():
    """One palette across chrome and viewport: ``--bg`` is the mat's ``scene.bg``."""

    environment = (STATIC / "environment.js").read_text()
    scene = re.search(r"export const PALETTE = \{.*?scene:\s*\{\s*bg:\s*0x([0-9a-f]{6})", environment, re.S)
    assert scene, "environment.js no longer declares its scene background"
    assert spec_tokens()["--bg"] == "#" + scene.group(1)


def test_the_environment_is_dark_only_and_the_style_says_so():
    """ADR-331: the light palette is removed, not kept behind a switch. The
    module exports one palette and no theme setter; the viewer's style name,
    which every new video records, names the dark look."""

    environment = (STATIC / "environment.js").read_text()
    assert environment.count("export const PALETTE = {") == 1
    assert "THEME_PALETTES" not in environment and "setTheme" not in environment
    assert not re.search(r"^\s*light:\s*\{", environment, re.M), "a light palette is declared"
    scene = (STATIC / "review_scene.js").read_text()
    assert re.search(r"^export const STYLE = 'cadex-prototype-dark-v1';$", scene, re.M)
    assert "cadex-prototype-light" not in scene


def test_every_palette_token_is_distinct_and_dark_chrome_is_darker_than_ink():
    tokens = spec_tokens()
    assert len(set(tokens.values())) == len(tokens)
    def luminance(value: str) -> float:
        return sum(int(value[i:i + 2], 16) for i in (1, 3, 5)) / 3
    for surface in ("--bg", "--surface", "--surface-2", "--surface-3", "--rule"):
        assert luminance(tokens[surface]) < luminance(tokens["--ink-2"]) < luminance(tokens["--ink"])


def test_before_receipt_records_the_page_the_spec_describes():
    receipt = json.loads((REPO / "docs/probes/ot6/design/before.json").read_text())
    shots = receipt["shots"]
    desk, phone, narrow = shots["1400"], shots["400x850"], shots["400-desktop"]
    # The operator URL served the active project with a run selected, live.
    for shot in (desk, phone):
        assert shot["project"].endswith(" — review") and shot["view"].startswith("RUN ")
        assert shot["freshness"] == "live" and shot["model"] == "loaded"
    assert desk["innerWidth"] == 1400 and desk["horizontal_overflow_px"] == 0
    # The sliver: the layout viewport widened past the phone, and the canvas collapsed.
    assert phone["innerWidth"] > 400 and phone["canvas"]["width"] < 50
    assert narrow["innerWidth"] == 400 and narrow["horizontal_overflow_px"] > 0
    text = SPEC.read_text()
    for number in (phone["innerWidth"], phone["canvas"]["width"], narrow["horizontal_overflow_px"],
                   desk["canvas"]["width"]):
        assert f"{number}" in text, f"spec §7 no longer cites {number}"


def test_before_screenshots_are_the_two_charter_sizes():
    assert png_size(REPO / "docs/review-design/before-1400.png") == (1400, 900)
    assert png_size(REPO / "docs/review-design/before-400x850.png") == (400, 850)


@pytest.mark.parametrize("path", evidence_files(), ids=lambda p: str(p.relative_to(REPO)))
def test_ot6_evidence_respects_the_charter_caps_and_names_no_private_address(path):
    size = path.stat().st_size
    if path.suffix.lower() in IMAGE_SUFFIXES:
        assert size <= IMAGE_CAP, f"{size} bytes > {IMAGE_CAP}"
        return
    assert size <= RECEIPT_CAP, f"{size} bytes > {RECEIPT_CAP}"
    text = path.read_text(errors="replace")
    assert not PRIVATE_ADDRESS.search(text), "a private-network address is committed"
    assert socket.gethostname() not in text, "this machine's hostname is committed"


def test_the_spec_itself_names_no_private_address():
    text = SPEC.read_text()
    assert not PRIVATE_ADDRESS.search(text)
    assert socket.gethostname() not in text


# -- the rendered page ---------------------------------------------------------

# §2's reading order: what a phone reads top to bottom, and what the desk
# frame distributes between its left sidebar, stage and right sidebar.
READING_ORDER = ("#sidebar", "#identity", "#model", "#model-settings", "#curves", "#videos-region",
                 "#record", "#params-panel", "#artifacts-panel", "#docs-panel")
HEADINGS = ["Runs", "Documents and decisions", "Model", "Curves", "Videos", "Identity", "Model settings",
            "Training and rollout", "Parameters and specs", "Artifacts"]

MEASURE = """(function () {
  var cs = getComputedStyle(document.documentElement);
  function rect(sel) { var n = document.querySelector(sel); if (!n) return null; var r = n.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height, right: r.right}; }
  function size(sel) { return getComputedStyle(document.querySelector(sel)).fontSize; }
  var smallest = Infinity;
  document.querySelectorAll('body *').forEach(function (n) {
    var v = parseFloat(getComputedStyle(n).fontSize); if (v > 0 && v < smallest) smallest = v; });
  return {
    innerWidth: innerWidth, scrollWidth: document.documentElement.scrollWidth,
    tokens: Object.fromEntries(%s.map(function (t) { return [t, cs.getPropertyValue(t).trim()]; })),
    fonts: Object.fromEntries(%s.map(function (s) { return [s, size(s)]; })),
    smallest_font: smallest,
    body_bg: getComputedStyle(document.body).backgroundColor,
    headings: Array.from(document.querySelectorAll('h2')).map(function (h) {
      return {text: h.textContent, transform: getComputedStyle(h).textTransform}; }),
    regions: %s.map(function (s) { return rect(s).y; }),
    canvas: rect('#viewer'), stage: rect('#stage'), left: rect('#left'), right: rect('#right'), top: rect('#top'),
    scrollHeight: document.documentElement.scrollHeight, innerHeight: innerHeight,
    sidebar: rect('#sidebar'), views: rect('#views'),
    summary: rect('#runs-summary'), runs: rect('#runs'), runs_open: document.getElementById('runs').open,
    views_visible: document.getElementById('views').checkVisibility(),
    histories: Array.from(document.querySelectorAll('[data-history]')).map(function (n) {
      var r = n.getBoundingClientRect(), s = n.querySelector('svg');
      return {y: r.y, width: r.width, svg: s ? s.getBoundingClientRect().width : 0}; }),
    metrics: Array.from(document.querySelectorAll('[data-metric]')).map(function (n) { return n.textContent; })
  };
})()""" % (json.dumps(list(TOKENS)), json.dumps(list(TYPE)), json.dumps(list(READING_ORDER)))


def _rendered(browser, url, size):
    width, height, mobile = SIZES[size]
    page = browser.page("about:blank")
    page.send("Emulation.setDeviceMetricsOverride",
              {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile})
    if mobile:
        page.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
    page.send("Page.navigate", {"url": url})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    return page


@needs_browser
@pytest.mark.parametrize("size", sorted(SIZES))
def test_rendered_page_follows_the_spec(served, browser, size) -> None:
    """§6's invariants, read back from the page at each charter size."""

    root, server = served
    _telemetry(root, iteration=4, run="first")
    page = _rendered(browser, server.url, size)
    page.evaluate("window.cadexReview.select('first')", await_promise=True)
    assert _model_state(page) == "loaded"
    page.wait_for("document.querySelectorAll('[data-history] svg').length === 3")
    page.wait_for("document.getElementById('freshness').dataset.state === 'live'")
    m = page.evaluate(MEASURE)
    width = SIZES[size][0]
    # 2. The layout viewport is the device width; 1. nothing overflows it.
    assert m["innerWidth"] == width
    assert m["scrollWidth"] <= m["innerWidth"], m["scrollWidth"]
    # 4. The palette is the spec's, and the page background is the dark scene background.
    assert m["tokens"] == spec_tokens()
    assert m["body_bg"] == "rgb(20, 20, 20)"
    # 5. The type scale, and nothing below 12 px.
    assert m["fonts"] == (TYPE_DESK if size == "desk" else TYPE)
    assert m["smallest_font"] >= 12
    # Headings are sentence case, never uppercase.
    assert [h["text"] for h in m["headings"]] == HEADINGS
    assert all(h["transform"] == "none" for h in m["headings"])
    # The stat row keeps the "key: value" text the other suites read.
    assert m["metrics"][:2] == ["iteration: 4", "total: 10"]
    tops = [h["y"] for h in m["histories"]]
    if size == "desk":
        # 3. The frame (§12): a thin bar over a left sidebar, the stage and a
        # right sidebar, edge to edge, and the page itself never scrolls.
        assert m["top"]["height"] <= 48, m["top"]
        assert m["scrollHeight"] <= m["innerHeight"], m["scrollHeight"]
        assert round(m["left"]["x"]) == 0 and round(m["left"]["width"]) == 264
        assert round(m["right"]["right"]) == width and round(m["right"]["width"]) == 340
        assert m["left"]["right"] <= m["stage"]["x"] and m["stage"]["right"] <= m["right"]["x"]
        assert m["stage"]["y"] >= m["top"]["y"] + m["top"]["height"]
        assert m["stage"]["width"] >= width - 264 - 340 - 2 * 6 - 2
        # The viewport fills the stage below its tabs; the runs are open in the sidebar.
        assert m["canvas"]["width"] >= 0.98 * m["stage"]["width"]
        assert m["canvas"]["height"] >= m["stage"]["height"] - 48
        assert m["sidebar"]["x"] >= m["left"]["x"] and m["sidebar"]["right"] <= m["left"]["right"]
        assert m["runs_open"] and m["summary"]["height"] == 0
        # The curves are stacked on the stage, each the width of the column.
        assert tops == sorted(tops) and len(set(round(t) for t in tops)) == 3, f"curves not stacked: {tops}"
        return
    # 3. On the phone the viewport is the full width inside the gutters; the
    # run list is a closed disclosure whose line is the only thing visible.
    assert m["regions"] == sorted(m["regions"]), "regions are out of reading order"
    assert m["canvas"]["width"] >= 0.9 * (width - 2 * PHONE_GUTTER)
    assert m["sidebar"]["width"] == width - 2 * PHONE_GUTTER and m["sidebar"]["y"] < m["regions"][1]
    assert not m["runs_open"] and m["summary"]["height"] > 0 and not m["views_visible"]
    assert round(m["runs"]["y"] + m["runs"]["height"]) == round(m["summary"]["y"] + m["summary"]["height"])
    assert page.text("#runs-summary") == "Runs · current: second · 3 recorded"
    assert tops == sorted(tops) and len(set(round(t) for t in tops)) == 3, f"curves not stacked: {tops}"
    assert all(h["svg"] >= 0.9 * h["width"] >= 200 for h in m["histories"]), m["histories"]
    # Opening the disclosure shows every run; the page still does not overflow.
    page.click("#runs-summary")
    page.wait_for("document.getElementById('runs').open")
    assert page.evaluate("document.querySelectorAll('#views li[data-run]').length") == 3
    assert page.evaluate("document.getElementById('views').checkVisibility()")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def _centre(page, selector):
    page.scroll_into_view(selector)
    box = page.rect(selector)
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


@needs_browser
def test_phone_touch_orbits_pinches_plays_and_downloads(served, browser) -> None:
    """D2's interaction half at 400×850 with touch emulation, on a run with a
    real encoded video: one finger orbits the model without scrolling the
    page, two fingers pinch-zoom, a tap on Fit resets the camera, the curves
    are legible, a tap starts the video and a tap downloads it whole."""

    from cadex_cli.video import render as render_video
    from test_video import _video_run

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg not available")
    root, server = served
    _video_run(root, "clip")
    video = render_video(root, "clip")
    _telemetry(root, iteration=4, run="clip")
    page = _rendered(browser, server.url, "phone")
    page.evaluate("window.cadexReview.select('clip')", await_promise=True)
    assert _model_state(page) == "loaded"
    page.wait_for("document.querySelectorAll('[data-history] svg').length === 3")
    assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000, "the model is not drawn"
    # One finger orbits: yaw and pitch change, the distance does not, and the
    # page stays where it was (touch-action: none on the canvas).
    cx, cy = _centre(page, "#viewer")
    before = page.evaluate("window.cadexReview.viewer().camera()")
    scroll = page.evaluate("scrollY")
    page.touch_drag(cx, cy, cx + 120, cy + 50)
    orbited = page.wait_for(
        "(function(){var c=window.cadexReview.viewer().camera();"
        f"return (c.yaw !== {before['yaw']} && c.pitch !== {before['pitch']}) && c}})()")
    assert orbited["distance"] == before["distance"]
    assert page.evaluate("scrollY") == scroll, "the drag scrolled the page"
    # Two fingers spreading zoom in; the orbit is untouched.
    page.pinch(cx, cy, 60, 180)
    zoomed = page.wait_for(
        "(function(){var c=window.cadexReview.viewer().camera();"
        f"return c.distance < {orbited['distance']} && c}})()")
    assert zoomed["yaw"] == orbited["yaw"] and zoomed["pitch"] == orbited["pitch"]
    assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
    # A tap on Fit — a 40 px control under a coarse pointer — resets the camera.
    assert page.rect("#model-fit")["height"] >= 40
    page.tap(*_centre(page, "#model-fit"))
    reset = page.wait_for("(function(){var c=window.cadexReview.viewer().camera(); return c.yaw === 0.8 && c})()")
    assert reset["distance"] == before["distance"]
    # The curves are legible: each history fills the width, its caption is
    # body-sized or larger, and nothing on the page is below 12 px.
    curves = page.evaluate("""Array.from(document.querySelectorAll('[data-history]')).map(function (n) {
      var r = n.getBoundingClientRect(), s = n.querySelector('svg').getBoundingClientRect();
      return {width: r.width, svg: s.width, height: s.height,
              caption: Math.min.apply(null, Array.from(n.querySelectorAll('*')).map(function (e) {
                return parseFloat(getComputedStyle(e).fontSize); }))}; })""")
    assert len(curves) == 3
    for curve in curves:
        assert curve["svg"] >= 0.9 * curve["width"] >= 300 and curve["height"] >= 60, curve
        assert curve["caption"] >= 12, curve
    # The video plays from a tap on the page's own Play control, which then
    # reads Pause, and a tap on the download link fetches it whole.
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    assert page.rect("#videos video")["width"] >= 0.9 * (SIZES["phone"][0] - 2 * PHONE_GUTTER - 2 * PHONE_GUTTER)
    page.evaluate("document.querySelector('#videos video').muted = true")
    assert page.text("#videos [data-video-play]") == "Play" and page.rect("#videos [data-video-play]")["height"] >= 40
    page.tap(*_centre(page, "#videos [data-video-play]"))
    page.wait_for("(function(){var v=document.querySelector('#videos video');return !v.paused && v.currentTime > 0.1})()")
    assert page.text("#videos [data-video-play]") == "Pause"
    download = page.download("#videos li[data-video] a[href$='download=1']", by_touch=True)
    assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video["sha256"]
    assert download.received_bytes == download.total_bytes == download.path.stat().st_size
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@needs_browser
def test_desk_sidebars_drag_fold_and_the_stage_changes_what_it_shows(served, browser) -> None:
    """§12 at 1400×900 with a real mouse: dragging a sidebar's inner edge
    resizes it and the viewport's backing store follows; dragging it most of
    the way shut folds it and the stage takes the width; the top bar's toggle
    brings it back at the width it had; a section folds under its heading;
    the stage's tabs change what the centre shows, and a document opened from
    the sidebar comes onto the stage and leaves it with the view."""

    root, server = served
    _telemetry(root, iteration=4, run="first")
    page = _rendered(browser, server.url, "desk")
    page.evaluate("try { localStorage.clear() } catch (_) {}")
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexReview && !!window.cadexFrame")
    page.evaluate("window.cadexReview.ready", await_promise=True)
    page.evaluate("window.cadexReview.select('first')", await_promise=True)
    assert _model_state(page) == "loaded"
    settle = "new Promise(r => setTimeout(r, 400))"

    def geometry():
        return page.evaluate("""(function () {
          function r(s) { var b = document.querySelector(s).getBoundingClientRect(); return {x: b.x, width: b.width, right: b.right, height: b.height}; }
          var c = document.getElementById('viewer');
          return {left: r('#left'), right: r('#right'), stage: r('#stage'), canvas: r('#viewer'), backing: c.width,
                  handle: r('.resizer[data-side="left"]'), frame: window.cadexFrame.layout()}; })()""")

    before = geometry()
    assert before["frame"]["left"] == {"width": 264, "open": True} and before["frame"]["stage"] == "model"
    # Drag the left edge 136 px outwards: the sidebar widens, the stage narrows
    # by the same amount, and the canvas redraws at its new width.
    hx = before["handle"]["x"] + before["handle"]["width"] / 2
    page.drag(hx, 400, hx + 136, 400)
    page.evaluate(settle, await_promise=True)
    wider = geometry()
    assert abs(wider["left"]["width"] - 400) <= 2, wider["left"]
    assert abs((before["stage"]["width"] - wider["stage"]["width"]) - 136) <= 3
    assert abs(wider["backing"] - wider["canvas"]["width"]) <= 2 and wider["backing"] < before["backing"]
    assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
    # Drag it nearly shut: it folds away entirely and the stage takes the room.
    hx = wider["handle"]["x"] + wider["handle"]["width"] / 2
    page.drag(hx, 400, 40, 400)
    page.evaluate(settle, await_promise=True)
    folded = geometry()
    assert folded["frame"]["left"]["open"] is False and folded["left"]["width"] == 0
    assert page.evaluate("getComputedStyle(document.getElementById('left')).visibility") == "hidden"
    assert folded["stage"]["width"] > wider["stage"]["width"] + 380
    assert page.attribute("#toggle-left", "aria-expanded") == "false"
    # The top bar's toggle reopens it at the width it had before it folded.
    page.click("#toggle-left")
    page.evaluate(settle, await_promise=True)
    assert abs(geometry()["left"]["width"] - 400) <= 2
    # The right sidebar folds from the bar and the page still never scrolls.
    page.click("#toggle-right")
    page.evaluate(settle, await_promise=True)
    assert geometry()["right"]["width"] == 0
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth")
    page.click("#toggle-right")
    # A section folds under its heading, and unfolds.
    page.click("#identity > h2")
    assert page.attribute("#identity", "data-folded") == "true"
    assert not page.evaluate("document.getElementById('view-revision').checkVisibility()")
    page.click("#identity > h2")
    assert page.evaluate("document.getElementById('view-revision').checkVisibility()")
    # The stage's tabs: curves replace the model in the centre.
    page.click("#stage-tabs [data-stage='curves']")
    assert page.attribute("#stage", "data-active") == "curves"
    assert page.evaluate("document.querySelector('[data-history] svg').checkVisibility({visibilityProperty: true})")
    assert not page.evaluate("document.getElementById('viewer').checkVisibility({visibilityProperty: true})")
    assert page.attribute("#curves-dot", "data-state") == page.attribute("#telemetry", "data-state")
    # A document opened from the sidebar takes the stage; the view changing closes it.
    page.click("#docs li[data-doc='DECISIONS.md'] a")
    page.wait_for("document.getElementById('doc-view').textContent.includes('ADR-')")
    assert page.attribute("#stage", "data-active") == "doc"
    assert page.evaluate("!document.getElementById('doc-tab').hidden")
    assert page.evaluate("document.getElementById('doc-view').checkVisibility({visibilityProperty: true})")
    page.evaluate("window.cadexReview.select('second')", await_promise=True)
    page.wait_for("document.getElementById('stage').dataset.active === 'model'")
    assert page.evaluate("document.getElementById('doc-tab').hidden")
    # The layout is the reader's, remembered across a reload in this browser.
    page.send("Page.reload", {})
    page.wait_for("document.readyState === 'complete' && !!window.cadexFrame")
    assert page.evaluate("window.cadexFrame.layout().left") == {"width": 400, "open": True}


def test_after_receipt_records_the_page_the_spec_describes():
    """The operator URL, captured at both sizes after the redesign (§8)."""

    receipt = json.loads((REPO / "docs/probes/ot6/design/after.json").read_text())
    shots = receipt["shots"]
    desk, phone = shots["1400"], shots["400x850"]
    tokens = spec_tokens()
    for shot, width in ((desk, 1400), (phone, 400)):
        assert shot["project"].endswith(" — review") and shot["view"].startswith("RUN ")
        assert shot["freshness"] == "live" and shot["model"] == "loaded"
        assert shot["innerWidth"] == width and shot["horizontal_overflow_px"] == 0
        assert {k: v for k, v in shot["tokens"].items() if k in tokens} == tokens
        assert (shot["fonts"]["body"], shot["fonts"]["h1"], shot["fonts"]["h2"]) == ("14px", "22px", "17px")
    assert phone["canvas"]["width"] >= 0.9 * (400 - 2 * PHONE_GUTTER)
    assert desk["canvas"]["width"] >= 0.9 * (1400 - 2 * 24 - 24 - 280 - 2 * 16)
    text = SPEC.read_text()
    for number in (phone["innerWidth"], phone["canvas"]["width"], desk["canvas"]["width"], phone["page_height"]):
        grouped = f"{number:,}".replace(",", " ")  # the spec writes 6 463, the receipt 6463
        assert f"{number}" in text or grouped in text, f"spec §8 no longer cites {number}"


def test_after_screenshots_are_the_two_charter_sizes():
    assert png_size(REPO / "docs/review-design/after-1400.png") == (1400, 900)
    assert png_size(REPO / "docs/review-design/after-400x850.png") == (400, 850)


REGIONS = ("top", "sidebar", "identity", "model", "curves", "videos-region", "record")


def test_phone_receipt_records_touch_orbit_and_every_region_on_the_operator_url():
    """The operator URL at 400×850 under touch emulation (§8): a one-finger
    drag orbited without scrolling the page, a tap on Fit restored the
    camera, and each of §2's regions was clipped to a screenshot at most one
    phone screen tall, committed beside the spec under the image cap."""

    receipt = json.loads((REPO / "docs/probes/ot6/design/phone.json").read_text())
    phone = receipt["shots"]["400x850"]
    assert phone["project"].endswith(" — review") and phone["view"].startswith("RUN ")
    assert phone["freshness"] == "live" and phone["model"] == "loaded"
    assert phone["innerWidth"] == 400 and phone["horizontal_overflow_px"] == 0
    touch = phone["touch"]
    assert touch["orbited"] and touch["page_scrolled_px"] == 0 and touch["fit_restored"]
    assert touch["camera_after_drag"]["distance"] == touch["camera_before"]["distance"]
    assert touch["camera_after_fit"] == touch["camera_before"]
    assert tuple(phone["regions"]) == REGIONS
    text = SPEC.read_text()
    for region, measured in phone["regions"].items():
        assert measured["captured_height"] == min(measured["height"], 850)
        width, height = png_size(REPO / f"docs/review-design/phone-{region}.png")
        # A clip's fractional height is truncated by the browser, not rounded.
        assert width == int(measured["width"]) and height == int(measured["captured_height"]), region
        assert f"phone-{region}.png" in text, f"spec §8 does not cite phone-{region}.png"


LOOK = REPO / "docs/probes/ot6/look"
FOLLOW_IMAGES = ("follow-side-by-side", "video-follow-0s", "video-follow-4s", "video-follow-8s", "viewport-follow-4s",
                 "viewport-follow-close", "viewport-follow-wide", "viewport-follow-orbit")
LOOK_IMAGES = ("side-by-side", "reference-shipped-orbit-4s", "reference-dark-lark", "persistent-same-pose",
               "video-frame0", "persistent-framed", "persistent-wide", "persistent-orbit-far")


def test_look_receipt_compares_the_dark_viewport_capture_video_and_reference():
    """D3's comparison on the operator URL (ADR-331): the run the persistent
    page selected, both style names dark, viewport and capture identical,
    the decoded frame inside the codec tolerance, the reference renderer's
    same-pose frame at the viewport's luminance, the floor outrunning the fog
    at every framing reached, the model drawn through the orbit, and the
    committed frames beside the assessment."""

    receipt = json.loads((LOOK / "look.json").read_text())
    identity = receipt["persistent_identity"]
    assert identity["selected"] == receipt["run"] and identity["relation"] == "current"
    assert not identity["stale"] and identity["error"] is None
    assert identity["revision"] == receipt["video"]["accepted_revision"]
    assert receipt["stats"]["style"] == receipt["capture_style"] == receipt["video"]["style"] == "cadex-prototype-dark-v1"
    assert receipt["camera"] == receipt["video"]["camera"]
    shots = receipt["screenshots"]
    assert receipt["lossless_viewport_capture_equal"] is True
    assert shots["persistent-same-pose"] == shots["capture-same-pose"]
    assert 0 < receipt["codec_mean_absolute_rgb_error"] < 3
    lum = receipt["luminance"]
    for patch in ("all", "sky", "floor"):
        assert abs(lum["reference-dark-lark"][patch] - lum["persistent-same-pose"][patch]) <= 0.2, patch
    assert receipt["page_tokens"] == {"bg": spec_tokens()["--bg"], "body": "rgb(20, 20, 20)"}
    for name, stage in receipt["stage"].items():
        assert stage["roomSize"] >= 4 * stage["fog"]["far"] - 1e-6, name
        assert stage["pitch"] == 1
    assert receipt["stage"]["persistent-close"]["minor"] < receipt["stage"]["persistent-same-pose"]["minor"]
    assert receipt["stage"]["persistent-wide"]["minor"] == 0
    assert min(receipt["model_pixels"].values()) > 1000
    assert receipt["framing"]["fraction"] == 0.22
    assert set(receipt["reference_shipped"]) == {"orbit", "swing", "flip"}
    assert len(receipt["reference_commit"]) == 40
    text = (LOOK / "README.md").read_text()
    for name in LOOK_IMAGES:
        assert (LOOK / f"{name}.png").is_file(), name
        assert receipt["images"][f"{name}.png"], name
    for name in ("side-by-side", "persistent-same-pose", "video-frame0", "persistent-framed", "persistent-wide"):
        assert f"{name}.png" in text, f"the assessment does not cite {name}.png"
    assert f"{receipt['codec_mean_absolute_rgb_error']:.2f}" in text
    assert "Verified against source: 2026-" in text


def test_follow_receipt_records_the_tracking_camera_and_timer_on_the_operator_url():
    """D3's second half on the operator URL (ADR-332): the run the persistent
    page selected, the follow rig's declared numbers and standoff formula, the
    viewport's rig agreeing with the recording's, apparent size held at the
    declared fraction in every decoded frame and at the close and wide
    framings, viewport and capture identical with the timer on, every decoded
    frame inside the codec tolerance, the floor outrunning the fog, the drag
    leaving the distance alone, the timer confined to the bottom-left, and
    the committed frames cited by the assessment."""

    receipt = json.loads((LOOK / "follow.json").read_text())
    identity = receipt["persistent_identity"]
    assert identity["selected"] == receipt["run"] and identity["relation"] == "current"
    assert not identity["stale"] and identity["error"] is None
    video, rig = receipt["video"], receipt["video"]["framing"]
    assert identity["revision"] == video["accepted_revision"]
    assert video["style"] == "cadex-prototype-dark-v1" and video["overlay"].startswith("timer")
    assert "follow camera at the declared framing" in video["sampling"]
    assert rig["fraction"] == 0.22 and rig["subject_y"] == -0.06 and rig["max_drift"] == 0.26 and rig["smooth_frames"] == 4
    assert abs(rig["standoff_mm"] - rig["subject_height_mm"] / (2 * math.tan(math.radians(27.5)) * 0.22)) < 1e-6
    assert rig["worst_drift_ndc"] < rig["max_drift"]
    assert abs(rig["size_min"] - 0.22) < 0.005 and abs(rig["size_max"] - 0.22) < 0.005
    assert receipt["rig_agrees"] is True and receipt["lossless_viewport_capture_equal"] is True
    text = (LOOK / "README.md").read_text()
    for s in ("0", "4", "8"):
        error = receipt["codec_mean_absolute_rgb_error"][s]
        assert 0 < error < 3 and f"{error:.2f}" in text
        camera = receipt["cameras"][s]
        assert camera["distance"] == rig["standoff_mm"] and camera["yaw"] == 0.8 and camera["pitch"] == 0.5
        assert abs(receipt["apparent_fraction"][f"viewport-follow-{s}s"]["analytic"] - 0.22) < 0.005
    for label, fraction in (("close", 0.5), ("wide", 0.08)):
        assert abs(receipt["apparent_fraction"][f"viewport-follow-{label}"]["analytic"] - fraction) < 0.005
        assert receipt["cameras"][label]["distance"] < rig["standoff_mm"] or label == "wide"
    for name, stage in receipt["stage"].items():
        assert stage["roomSize"] >= 4 * stage["fog"]["far"] - 1e-6, name
        assert stage["pitch"] == 1
    assert receipt["stage"]["viewport-follow-close"]["minor"] < receipt["stage"]["viewport-follow-4s"]["minor"]
    assert receipt["stage"]["viewport-follow-wide"]["minor"] == 0
    assert min(receipt["model_pixels"].values()) > 1000
    orbit = receipt["orbit"]
    assert orbit["after_drag"]["distance"] == orbit["before"]["distance"] == rig["standoff_mm"]
    assert orbit["after_drag"]["yaw"] != orbit["before"]["yaw"]
    region = receipt["timer_region"]
    assert region["count"] > 400 and region["box"][1] > 512 * 0.8 and region["box"][2] < 512 * 0.3
    assert set(receipt["reference_shipped"]) == {"orbit", "swing", "flip"}
    assert len(receipt["reference_commit"]) == 40
    for name in FOLLOW_IMAGES:
        assert (LOOK / f"{name}.png").is_file(), name
        assert receipt["images"][f"{name}.png"], name
        assert f"{name}.png" in text, f"the assessment does not cite {name}.png"


FINCH = REPO / "docs/probes/ot6/finch"


def test_finch_training_receipt_measures_the_real_biped_in_the_new_look():
    """D6 (ADR-336): one bounded real GPU run on Finch under the charter's
    limits, the task's episode, fall threshold and seed set declared, a
    checkpoint video published while the trainer was active and a final
    video afterwards — both in the dark reference look and naming what they
    show — each policy measured over the declared ten seeds for pelvis
    displacement, survival and falls, the render's impact on the trainer's
    own update intervals, and the persistent dashboard serving the project
    with the run selected at the end. A policy that did not stand is a valid
    measured result; this pins the measurement, not the outcome."""

    receipt = json.loads((FINCH / "training.json").read_text())
    assert receipt["schema"] == "finch-training-evidence-v1" and receipt["project"] == "ot6-finch"
    assert receipt["fall_below_mm"] == 84.0 and receipt["task"]["episode_steps"] == 400 and receipt["task"]["control_hz"] == 50
    requested = receipt["requested"]
    assert requested["timeout_seconds"] <= 7200 and receipt["training_wall_seconds"] < requested["timeout_seconds"]
    assert receipt["resource_bound"]["MemoryMax"] == str(20 * 1024 ** 3) and receipt["resource_bound"]["ActiveState"] == "active"
    assert receipt["memory"]["host_peak_bytes"] < 20 * 1024 ** 3
    assert receipt["trainer_exit"] == 0 and receipt["trainer_final"]["state"] == "done" and receipt["trainer_final"]["device"] == "gpu"
    assert receipt["trainer_final"]["iteration"] == requested["iterations"] - 1
    overhead = receipt["render_overhead"]
    assert overhead["concurrent_renders"] == 1 and overhead["during_window"]["count"] >= 1
    assert all(overhead[w]["median_s"] > 0 for w in ("before_window", "during_window", "after_window"))
    live = receipt["live_browser"]
    assert live["persistent_server"] and live["default_view_kind"] == "RUN " + receipt["run"]
    assert live["first_seen_count"] >= 7 and live["first_seen_max_committed_to_page_s"] < 5 and live["reload_count"] == 1
    text = (FINCH / "README.md").read_text()
    for phase in ("checkpoint20", "final"):
        entry = receipt[phase]
        assert len(entry["policy_sha256"]) == 64
        assert entry["witness"]["witness_error"] < entry["witness"]["witness_tolerance"]
        assert entry["trainer_active_after_browser"] == (phase == "checkpoint20") and entry["browser_check_exit"] == 0
        video = entry["video"]
        assert video["style"] == "cadex-prototype-dark-v1" and video["showing"].startswith("tessellated solids")
        assert video["accepted_revision"] == entry["playback_revision"] != receipt["accepted_revision"] and video["frames"] > 0
        assert entry["browser"]["download_sha256"] == video["sha256"] and entry["browser"]["components"] == 29
        assert entry["browser"]["is_default"] == (phase == "final")
        frame = FINCH / entry["video_frame"]["png"]
        assert frame.is_file() and frame.stat().st_size <= IMAGE_CAP
        assert hashlib.sha256(frame.read_bytes()).hexdigest() == entry["video_frame"]["sha256"]
        assert frame.name in text, f"the assessment does not cite {frame.name}"
        seeds = entry["seeds"]
        assert seeds["seeds"] == list(range(10)) and seeds["episode_seconds"] == 8.0 and seeds["fall_below_mm"] == 84.0
        assert len(seeds["per_seed"]) == 10 and seeds["falls"] + seeds["stood_full_episode"] == 10
        assert seeds["falls"] == sum(1 for row in seeds["per_seed"] if row["fell"])
        assert all(0 < row["survival_s"] <= 8.0 for row in seeds["per_seed"])
        assert seeds["survival_s"]["min"] <= seeds["survival_s"]["mean"] <= seeds["survival_s"]["max"] <= 8.0
        assert seeds["per_seed"][0]["survival_s"] == entry["observed_s"] and seeds["per_seed"][0]["fell"] == entry["fell"]
        for key in ("falls", "stood_full_episode"):
            assert f"{seeds[key]} / 10" in text or f"{seeds[key]}/10" in text, (phase, key)
    # Declaring each retained policy in the script accepts a new revision (the same lifecycle
    # as Lark's), so at the end the dashboard's accepted revision is the final playback's and
    # the training run is served as history at its own.
    end = receipt["dashboard_at_end"]
    assert end["project"] == "ot6-finch" and end["accepted_revision"] == receipt["final"]["playback_revision"]
    served = {r["run"]: r for r in end["runs"]}
    assert {receipt["run"], receipt["run"] + "-checkpoint20", receipt["run"] + "-final"} <= set(served)
    assert served[receipt["run"]]["accepted_revision"] == receipt["accepted_revision"] and served[receipt["run"]]["relation"] == "historical"
    assert served[receipt["run"] + "-final"]["policy_sha256"] == receipt["final"]["policy_sha256"] and served[receipt["run"] + "-final"]["videos"] == 1
    assert end["fresh_visit_selects"] == receipt["run"] + "-final"
    assert "Verified against source: 2026-" in text


ROBIN = REPO / "docs/probes/ot6/robin"


def test_robin_training_receipt_measures_the_balancer_in_the_new_look():
    """D7 (ADR-338): one bounded real GPU run on Robin, the product-agent
    balancer, under the charter's limits, the task's episode, fall threshold
    and seed set declared, a checkpoint video published while the trainer was
    active and a final video afterwards -- both in the dark reference look and
    naming what they show -- each policy measured over the declared ten seeds
    for chassis displacement, chassis pitch, survival and falls, the render's
    impact on the trainer's own update intervals, and the persistent dashboard
    serving the project with the run selected at the end. A policy that did
    not balance is a valid measured result; this pins the measurement, not the
    outcome."""

    receipt = json.loads((ROBIN / "training.json").read_text())
    assert receipt["schema"] == "robin-training-evidence-v1" and receipt["project"] == "ot6-robin"
    # 0.7 x the 66 mm upright chassis-frame height, read from the retained task bundle.
    assert abs(receipt["fall_below_mm"] - 46.2) < 1e-6 and receipt["task"]["fall_frac"] == 0.7
    assert receipt["task"]["episode_steps"] == 400 and receipt["task"]["control_hz"] == 50
    requested = receipt["requested"]
    assert requested["timeout_seconds"] <= 7200 and receipt["training_wall_seconds"] < requested["timeout_seconds"]
    assert receipt["resource_bound"]["MemoryMax"] == str(20 * 1024 ** 3) and receipt["resource_bound"]["ActiveState"] == "active"
    assert receipt["memory"]["host_peak_bytes"] < 20 * 1024 ** 3
    assert receipt["trainer_exit"] == 0 and receipt["trainer_final"]["state"] == "done" and receipt["trainer_final"]["device"] == "gpu"
    assert receipt["trainer_final"]["iteration"] == requested["iterations"] - 1
    overhead = receipt["render_overhead"]
    assert overhead["concurrent_renders"] == 1 and overhead["render_seconds"] > 0
    assert all(overhead[w]["median_s"] > 0 for w in ("before_window", "after_window"))
    if overhead["during_window"]["count"] == 0:
        # Robin's updates take under a second and its checkpoint steps half a minute: a render
        # shorter than the step it fell inside overlaps no update interval, and its impact is
        # that step's length beside the run's other checkpoint steps.
        step = overhead["enclosing_interval"]
        assert step["checkpoint_boundary"] and step["seconds"] > overhead["render_seconds"] and len(step["other_checkpoint_steps_s"]) >= 2
    live = receipt["live_browser"]
    assert live["persistent_server"] and live["default_view_kind"] == "RUN " + receipt["run"]
    # The observer's own guarantee: at least seven trainer updates seen on the page in one visit, and
    # every update it could match to its commit time reached the page within five seconds (with
    # sub-second updates the first page value can precede the file poll, so one may go unmatched).
    assert live["samples"] >= 7 and live["first_seen_count"] >= 6
    assert live["first_seen_max_committed_to_page_s"] < 5 and live["reload_count"] == 1
    text = (ROBIN / "TRAINING.md").read_text()
    for phase in ("checkpoint20", "final"):
        entry = receipt[phase]
        assert len(entry["policy_sha256"]) == 64
        assert entry["witness"]["witness_error"] < entry["witness"]["witness_tolerance"]
        assert entry["trainer_active_after_browser"] == (phase == "checkpoint20") and entry["browser_check_exit"] == 0
        video = entry["video"]
        assert video["style"] == "cadex-prototype-dark-v1" and video["showing"].startswith("tessellated solids")
        assert video["accepted_revision"] == entry["playback_revision"] != receipt["accepted_revision"] and video["frames"] > 0
        assert entry["browser"]["download_sha256"] == video["sha256"] and entry["browser"]["components"] == 24
        assert entry["browser"]["is_default"] == (phase == "final")
        frame = ROBIN / entry["video_frame"]["png"]
        assert frame.is_file() and frame.stat().st_size <= IMAGE_CAP
        assert hashlib.sha256(frame.read_bytes()).hexdigest() == entry["video_frame"]["sha256"]
        assert frame.name in text, f"the assessment does not cite {frame.name}"
        seeds = entry["seeds"]
        assert seeds["seeds"] == list(range(10)) and seeds["episode_seconds"] == 8.0 and abs(seeds["fall_below_mm"] - 46.2) < 1e-6
        per_seed = [dict(zip(seeds["per_seed_columns"], row)) for row in seeds["per_seed"]]
        assert len(per_seed) == 10 and seeds["falls"] + seeds["balanced_full_episode"] == 10
        assert seeds["falls"] == sum(1 for row in per_seed if row["fell"])
        assert all(0 < row["survival_s"] <= 8.0 and 0 <= row["max_abs_pitch_deg"] <= 180 for row in per_seed)
        assert all(abs(row["final_pitch_deg"]) <= row["max_abs_pitch_deg"] + 0.05 for row in per_seed)
        assert seeds["survival_s"]["min"] <= seeds["survival_s"]["mean"] <= seeds["survival_s"]["max"] <= 8.0
        assert seeds["max_abs_pitch_deg"]["min"] <= seeds["max_abs_pitch_deg"]["mean"] <= seeds["max_abs_pitch_deg"]["max"]
        assert per_seed[0]["survival_s"] == entry["observed_s"] and per_seed[0]["fell"] == entry["fell"]
        for key in ("falls", "balanced_full_episode"):
            assert f"{seeds[key]} / 10" in text or f"{seeds[key]}/10" in text, (phase, key)
    # The first run diverged to NaN at the trainer's default learning rate and is kept as a failed
    # run on the dashboard, with its checkpoint video; the receipt carries it beside the run that
    # completed, and the driver asserted its record unchanged.
    diverged = receipt["diverged_run"]
    assert diverged["record_status"] == "failed" and diverged["trainer_final"]["state"] == "failed" and "diverged" in diverged["error"]
    assert diverged["requested"]["learning_rate"] > requested["learning_rate"] and diverged["checkpoint20_published_while_active"]
    end = receipt["dashboard_at_end"]
    assert end["project"] == "ot6-robin" and end["accepted_revision"] == receipt["final"]["playback_revision"]
    served = {r["run"]: r for r in end["runs"]}
    assert {receipt["run"], receipt["run"] + "-checkpoint20", receipt["run"] + "-final"} <= set(served)
    assert served[receipt["run"]]["accepted_revision"] == receipt["accepted_revision"] and served[receipt["run"]]["relation"] == "historical"
    assert served[receipt["run"] + "-final"]["policy_sha256"] == receipt["final"]["policy_sha256"] and served[receipt["run"] + "-final"]["videos"] == 1
    assert end["fresh_visit_selects"] == receipt["run"] + "-final"
    assert "Verified against source: 2026-" in text


HERON = REPO / "docs/probes/ot6/heron"


def test_heron_design_receipt_is_a_buildable_arm_on_the_operator_url():
    """D8's design half, on D5's rules: Heron, the product-agent two-DoF arm,
    is two catalog MG90S servos with their catalog single-arm horns, two
    MR128 bearings and six M2 screws mounting three modelled printable parts;
    every fit rule in the retained measurements holds; nothing in the world is
    in the design; the persistent dashboard showed its tessellated solids at
    both charter widths without horizontal overflow, with the proxies only
    under the labelled toggle."""

    fit = json.loads((HERON / "fit.json").read_text())
    assert fit["schema"] == "heron-fit-evidence-v1" and fit["project"] == "ot6-heron"
    assert fit["ok"] and all(c["ok"] for c in fit["checks"]) and len(fit["checks"]) >= 50
    assert fit["catalog_counts"] == {"servo/mg90s": 2, "servo_horn/mg90s-single_arm": 2, "bearing/mr128": 2,
                                     "bolt/m2x6-socket": 4, "bolt/m2x16-socket": 2}
    rows = fit["inventory"]
    assert fit["components"] == len(rows) == 15
    modelled = sorted(r["solid"] for r in rows if not r["catalog"])
    assert modelled == ["base", "forearm", "upper_arm"]
    assert all(r["source"].startswith("modelled: printed") for r in rows if not r["catalog"])
    assert all(r["valid_single_solid"] for r in rows)
    names = {c["check"]: c for c in fit["checks"]}
    assert names["no plane, floor, bench or world geometry in the design"]["measured"] == 0
    assert names["the base is the only grounded component"]["measured"] == 1
    for joint in ("shoulder", "elbow"):
        assert names[f"{joint} servo tabs seated on the cheek outer face: distance"]["measured"] == 0
        assert names[f"{joint} servo/cheek common volume"]["measured"] == 0
        assert names[f"{joint} horn nested in the block pocket: distance"]["measured"] == 0
        assert names[f"{joint} window clearance around the case (section)"]["expected"] == fit["params"]["window_clear"]
        assert names[f"{joint} stub in the bearing bore: radial clearance"]["expected"] == fit["params"]["stub_clear"]
    assert fit["mass_g"]["total"] == pytest.approx(fit["mass_g"]["printed"] + fit["mass_g"]["purchased"], abs=0.02)

    reopen = json.loads((HERON / "reopen.json").read_text())
    assert reopen["revision"] == fit["revision"] and len(reopen["runs"]) >= 3
    assert all(r["exit"] == 0 and r["revision"] == fit["revision"] for r in reopen["runs"])
    assert reopen["every_run_matches_accepted_digest"] and reopen["distinct_digests"] == [reopen["accepted_digest"]]

    operator = json.loads((HERON / "operator.json").read_text())
    assert operator["project_revision"] == fit["revision"] and operator["components"] == 15
    assert [v["width"] for v in operator["visits"]] == [1400, 400]
    for visit in operator["visits"]:
        assert visit["selected"] == "accepted" and not visit["overflow"]
        assert visit["status"].endswith("showing: tessellated solids")
        assert "with collision proxies" in visit["proxy_status"]
        assert png_size(HERON / f"operator-{visit['width']}.png")[0] <= visit["width"]


def test_heron_training_receipt_measures_the_arm_reach_in_the_new_look():
    """D8 (ADR-340): one bounded real GPU run on Heron, the product-agent
    two-DoF arm, under the charter's limits, the task's episode, target,
    tolerance, floor and seed set declared, a checkpoint video published while
    the trainer was active and a final video afterwards -- both in the dark
    reference look and naming what they show -- each policy measured over the
    declared ten seeds for the tip's reach error at episode end and over the
    final second, its best approach, successes and terminations, the render's
    impact on the trainer's own update intervals, a viewport frame from the
    servo side, and the persistent dashboard serving the project with the run
    selected at the end. A policy that did not reach is a valid measured
    result; this pins the measurement, not the outcome."""

    receipt = json.loads((HERON / "training.json").read_text())
    assert receipt["schema"] == "heron-training-evidence-v1" and receipt["project"] == "ot6-heron"
    task = receipt["task"]
    assert task["episode_steps"] == 200 and task["control_hz"] == 50
    assert receipt["target_mm"] == [task["target_x"], 0.0, task["target_z"]] == [100.0, 0.0, 60.0]
    assert receipt["reach_tol_mm"] == task["reach_tol"] == 10.0 and receipt["tip_floor_mm"] == task["tip_floor"] == 5.0
    requested = receipt["requested"]
    assert requested["timeout_seconds"] <= 7200 and receipt["training_wall_seconds"] < requested["timeout_seconds"]
    assert receipt["resource_bound"]["MemoryMax"] == str(20 * 1024 ** 3) and receipt["resource_bound"]["ActiveState"] == "active"
    assert receipt["memory"]["host_peak_bytes"] < 20 * 1024 ** 3
    assert receipt["trainer_exit"] == 0 and receipt["trainer_final"]["state"] == "done" and receipt["trainer_final"]["device"] == "gpu"
    assert receipt["trainer_final"]["iteration"] == requested["iterations"] - 1
    overhead = receipt["render_overhead"]
    assert overhead["concurrent_renders"] == 1 and overhead["render_seconds"] > 0
    assert all(overhead[w]["median_s"] > 0 for w in ("before_window", "after_window"))
    if overhead["during_window"]["count"] == 0:
        step = overhead["enclosing_interval"]
        assert step["checkpoint_boundary"] and step["seconds"] > overhead["render_seconds"] and len(step["other_checkpoint_steps_s"]) >= 2
    live = receipt["live_browser"]
    assert live["persistent_server"] and live["default_view_kind"] == "RUN " + receipt["run"]
    assert live["samples"] >= 7 and live["first_seen_count"] >= 6
    assert live["first_seen_max_committed_to_page_s"] < 5 and live["reload_count"] == 1
    text = (HERON / "TRAINING.md").read_text()
    for phase in ("checkpoint20", "final"):
        entry = receipt[phase]
        assert len(entry["policy_sha256"]) == 64
        assert entry["witness"]["witness_error"] < entry["witness"]["witness_tolerance"]
        assert entry["trainer_active_after_browser"] == (phase == "checkpoint20") and entry["browser_check_exit"] == 0
        video = entry["video"]
        assert video["style"] == "cadex-prototype-dark-v1" and video["showing"].startswith("tessellated solids")
        assert video["accepted_revision"] == entry["playback_revision"] != receipt["accepted_revision"] and video["frames"] > 0
        assert entry["browser"]["download_sha256"] == video["sha256"] and entry["browser"]["components"] == 15
        assert entry["browser"]["is_default"] == (phase == "final")
        frame = HERON / entry["video_frame"]["png"]
        assert frame.is_file() and frame.stat().st_size <= IMAGE_CAP
        assert hashlib.sha256(frame.read_bytes()).hexdigest() == entry["video_frame"]["sha256"]
        assert frame.name in text, f"the assessment does not cite {frame.name}"
        seeds = entry["seeds"]
        assert seeds["seeds"] == list(range(10)) and seeds["episode_seconds"] == 4.0
        assert seeds["target_mm"] == receipt["target_mm"] and seeds["reach_tol_mm"] == 10.0 and seeds["tip_floor_mm"] == 5.0
        per_seed = [dict(zip(seeds["per_seed_columns"], row)) for row in seeds["per_seed"]]
        assert len(per_seed) == 10
        assert seeds["successes"] == sum(1 for row in per_seed if row["success"])
        assert seeds["terminations"] == sum(1 for row in per_seed if row["terminated"])
        assert seeds["terminations"] + seeds["full_episode"] == 10
        # Success is the script's own bar: within tolerance at the end and over the whole final second, unterminated.
        assert all(row["success"] == (not row["terminated"] and row["end_error_mm"] <= 10.0 and row["final_second_max_error_mm"] <= 10.0) for row in per_seed)
        assert all(0 <= row["min_error_mm"] <= row["end_error_mm"] <= row["final_second_max_error_mm"] + 0.05 for row in per_seed)
        assert all(0 < row["survival_s"] <= 4.0 and (row["first_within_tol_s"] is None) == (row["min_error_mm"] > 10.0) for row in per_seed)
        assert seeds["end_error_mm"]["min"] <= seeds["end_error_mm"]["mean"] <= seeds["end_error_mm"]["max"]
        assert per_seed[0]["survival_s"] == entry["observed_s"] and per_seed[0]["terminated"] == entry["terminated"]
        assert abs(per_seed[0]["end_error_mm"] - entry["end_error_mm"]) <= 0.06
        assert f"{seeds['successes']} / 10" in text or f"{seeds['successes']}/10" in text, phase
    view = json.loads((HERON / "servo-view.json").read_text())
    assert view["selected"] == "RUN " + receipt["run"] + "-final" and view["showing"] == "solids"
    assert view["camera_before"]["yaw"] == 0.8 and view["camera_after"]["yaw"] < -1.0
    assert view["camera_after"]["distance"] == view["camera_before"]["distance"]
    png = HERON / view["png"]
    assert png.is_file() and png.stat().st_size == view["png_bytes"] <= IMAGE_CAP
    assert hashlib.sha256(png.read_bytes()).hexdigest() == view["png_sha256"] and png.name in text
    end = receipt["dashboard_at_end"]
    assert end["project"] == "ot6-heron" and end["accepted_revision"] == receipt["final"]["playback_revision"]
    served = {r["run"]: r for r in end["runs"]}
    assert {receipt["run"], receipt["run"] + "-checkpoint20", receipt["run"] + "-final"} <= set(served)
    assert served[receipt["run"]]["accepted_revision"] == receipt["accepted_revision"] and served[receipt["run"]]["relation"] == "historical"
    assert served[receipt["run"] + "-final"]["policy_sha256"] == receipt["final"]["policy_sha256"] and served[receipt["run"] + "-final"]["videos"] == 1
    assert end["fresh_visit_selects"] == receipt["run"] + "-final"
    assert "Verified against source: 2026-" in text


REGRESSION = REPO / "docs/probes/ot6/regression"
# The ot5 behaviours D9 names, each pinned to the tests that exercise it in
# the CLI suite (`file::test`), so a renamed or deleted test breaks the receipt.
OT5_BEHAVIOURS = {
    "review server and record suites": [
        "test_review_server.py::test_the_project_api_reads_the_project_live",
        "test_review_record.py::test_the_record_carries_identities_and_only_relative_paths"],
    "live polling within five seconds": [
        "test_review_server.py::test_browser_polls_training_histories_checkpoints_and_stale_states",
        "test_review_history_scale.py::test_browser_long_history_keeps_selection_and_playback_with_bounded_poll_work"],
    "playback and download": [
        "test_review_server.py::test_recorded_videos_are_served_whole_or_by_range",
        "test_review_server.py::test_browser_playing_video_survives_new_current_attempt",
        "test_review_server.py::test_browser_interrupted_download_leaves_polling_and_a_fresh_download_working"],
    "restart during training": [
        "test_review_lifecycle.py::test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone"],
    "copy isolation": [
        "test_review_lifecycle.py::test_copied_project_reopens_without_source_and_keeps_edits_isolated",
        "test_review_record.py::test_the_reader_reads_a_copied_project_the_same"],
    "failed-run states": [
        "test_review_server.py::test_browser_explains_a_failed_observation_whose_training_finished",
        "test_review_server.py::test_browser_lists_a_completed_run_whose_policy_was_never_stored_as_a_problem",
        "test_review_server.py::test_browser_observes_final_policy_publication_failure"],
    "headless operation": [
        "test_review_server.py::test_the_review_command_serves_until_interrupted_and_writes_nothing",
        "test_review_server.py::test_browser_reaches_the_dashboard_over_the_private_network_address"],
}


def test_final_regression_receipt_shows_everything_ot5_proved_still_holds():
    """D9: after the redesign, the look change and the three model changes,
    the engine and CLI suites are green on the recorded commit, every ot5
    behaviour the criterion names is exercised by tests that still exist and
    whose files passed with no failure, and a fresh visit to the persistent
    operator URL at 1400×900 and at 400×850 under touch selects the arm's
    final run by itself, draws its real solids, has no horizontal overflow,
    polls with no gap over five seconds, plays the retained video and
    downloads it with the recorded digest — the phone visit orbiting by one
    finger without scrolling the page. Skips are not claimed as exercised."""

    receipt = json.loads((REGRESSION / "final.json").read_text())
    assert receipt["schema"] == "ot6-d9-final-regression-v1" and len(receipt["source_commit"]) == 40
    suites = {s["command"]: s for s in receipt["suites"]}
    assert set(suites) == {"pixi run test-engine", "pixi run python -m pytest cli/tests"}
    for s in suites.values():
        assert s["exit_code"] == 0 and s["failed"] == 0 and s["error"] == 0 and s["passed"] > 0
        assert s["started"] < s["finished"] and s["seconds"] > 0 and len(s["log_sha256"]) == 64
    files = suites["pixi run python -m pytest cli/tests"]["files"]  # path -> [passed, skipped, failed]
    assert sum(row[0] for row in files.values()) == suites["pixi run python -m pytest cli/tests"]["passed"]
    assert sum(row[1] for row in files.values()) == suites["pixi run python -m pytest cli/tests"]["skipped"]
    assert suites["pixi run test-engine"]["passed"] >= 2114
    assert suites["pixi run python -m pytest cli/tests"]["passed"] >= 609
    for behaviour, tests in OT5_BEHAVIOURS.items():
        for test in tests:
            path, name = test.split("::")
            assert f"def {name}(" in (REPO / "cli/tests" / path).read_text(), f"{behaviour}: {test} is gone"
            assert files[f"cli/tests/{path}"][2] == 0, behaviour
    assert receipt["operator_url"] == "http://<private-address>:8765/"
    assert receipt["project"] == "ot6-heron" and receipt["run"] == "heron1-final"
    served = {r["run"]: r for r in receipt["runs"]}
    assert served["heron1-final"]["relation"] == "current" and served["heron1-final"]["videos"] == 1
    assert served["heron1"]["relation"] == "historical" and served["heron1-checkpoint20"]["videos"] == 1
    video = receipt["retained_video"]
    assert video["style"] == "cadex-prototype-dark-v1" and video["showing"].startswith("tessellated solids")
    visits = {(v["width"], v["height"]): v for v in receipt["visits"]}
    assert set(visits) == {(1400, 900), (400, 850)}
    text = (REGRESSION / "README.md").read_text()
    for size, visit in visits.items():
        assert visit["touch"] == (size == (400, 850))
        assert visit["selected"] == "heron1-final" and visit["relation"] == "current" and not visit["stale"]
        assert visit["overflow_px"] == 0 and visit["drawn_pixels"] > 1000
        assert visit["status"].endswith("showing: tessellated solids")
        polling = visit["polling"]
        assert polling["project_fetches"] >= 3 and polling["max_gap_s"] < 5 and polling["last_poll_ms"] > 0
        assert visit["playback_seconds"] > 0.1
        assert visit["download"]["sha256"] == video["sha256"] and visit["download"]["by_touch"] == visit["touch"]
        png = REGRESSION / visit["png"]
        assert png.is_file() and png.stat().st_size == visit["png_bytes"] <= IMAGE_CAP
        assert hashlib.sha256(png.read_bytes()).hexdigest() == visit["png_sha256"]
        assert png_size(png)[0] <= size[0] and png.name in text
    orbit = visits[(400, 850)]["touch_orbit"]
    assert orbit["camera_after"]["yaw"] != orbit["camera_before"]["yaw"]
    assert orbit["camera_after"]["distance"] == orbit["camera_before"]["distance"]
    assert orbit["page_scrolled_px"] == 0
    assert "ActiveState=active" in receipt["service"]
    for behaviour in OT5_BEHAVIOURS:
        assert behaviour in text, f"the assessment does not name {behaviour!r}"
    assert "Verified against source: 2026-" in text


REPORT = REPO / "docs/probes/ot6/REPORT.md"
RECORDS = REPO / ".hypergraph/graph/record"


def test_closing_report_links_every_criterion_to_committed_evidence():
    """D10: the closing report has a section per criterion and an open-items
    section, every relative link resolves to a committed file, every record it
    cites exists in the record graph, every ADR it names exists in the log, and
    it names no private address (the caps test above holds it under 16 KB)."""

    text = REPORT.read_text()
    assert re.search(r"^Verified against source: \d{4}-\d{2}-\d{2}\.", text, re.M)
    for n in range(1, 11):
        assert re.search(rf"^## D{n}\. ", text, re.M), f"D{n} has no section"
    assert "## What remains open" in text
    for link in re.findall(r"\]\(([^)]+)\)", text):
        assert (REPORT.parent / link).is_file(), link
    slugs = set(re.findall(r"\[rec: ([a-z]+-[a-z]+-\d{4})\]", text))
    assert len(slugs) >= 15
    for slug in slugs:
        assert (RECORDS / f"{slug}.md").is_file(), slug
    decisions = (REPO / "docs/DECISIONS.md").read_text()
    adrs = set(re.findall(r"ADR-(\d{3})", text))
    assert {"328", "329", "330", "331", "332", "333", "334", "335", "336", "337", "338", "339", "340"} <= adrs
    for adr in adrs:
        assert f"## ADR-{adr} " in decisions, adr
    assert not PRIVATE_ADDRESS.search(text) and socket.gethostname() not in text


@needs_browser
def test_floor_grid_is_anchored_to_the_world_whatever_the_floor_size(served, browser) -> None:
    """ADR-343: the floor grows with the fog as the camera pulls back, and its
    grid must not slide — world x = y = 0 is a block corner and every pitch
    line a whole multiple of the pitch, at any footprint, and resizing never
    repaints the texture."""

    _root, server = served
    page = _open_plain(browser, server.url)
    rows = page.evaluate("""(async () => {
      const THREE = await import('/three.module.js'), floor = await import('/floor.js');
      const world = new THREE.Group(), out = [];
      const group = floor.buildStageFloor(world, {size: 24, pitch: 1, minor: 0.1});
      const map = group.children[0].material.map;
      for (const size of [24, 25.025, 50.05, 84, 671.3]) {
        floor.resizeStageFloor(group, {size, floorZ: -0.04});
        const mesh = group.children[0];
        // tile coordinate of world x at uv = (x + size/2) / size, in blocks of 2·pitch
        const at = x => ((x + size / 2) / size) * map.repeat.x + map.offset.x;
        out.push({size, scale: mesh.scale.x, z: mesh.position.z, same: mesh.material.map === map,
                  origin: at(0), metre: at(1), three: at(3), offset: map.offset.x});
      }
      return out; })()""", await_promise=True)
    for row in rows:
        assert row["same"] and row["scale"] == row["size"] and row["z"] == -0.04
        assert 0 <= row["offset"] < 1
        for key, blocks in (("origin", 0), ("metre", 0.5), ("three", 1.5)):
            assert abs((row[key] - blocks) - round(row[key] - blocks)) < 1e-9, row


def _open_plain(browser, url):
    page = browser.page(url)
    page.wait_for("document.readyState === 'complete'")
    return page
