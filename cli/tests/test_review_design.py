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
type scale compute to §3–§4, the viewport fills its column, the run list is
a sidebar at desk and a closed disclosure on the phone, and the curves sit
abreast at desk and stacked on the phone.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
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


def test_page_background_is_the_environment_dark_scene_background():
    """One palette across chrome and viewport: ``--bg`` is the dark mat's ``scene.bg``."""

    environment = (STATIC / "environment.js").read_text()
    dark = re.search(r"dark:\s*\{.*?scene:\s*\{\s*bg:\s*0x([0-9a-f]{6})", environment, re.S)
    assert dark, "environment.js no longer declares a dark scene background"
    assert spec_tokens()["--bg"] == "#" + dark.group(1)


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
    regions: ['#identity', '#model', '#curves', '#videos-region', '#record'].map(function (s) { return rect(s).y; }),
    canvas: rect('#viewer'), detail: rect('#detail'), sidebar: rect('#sidebar'), views: rect('#views'),
    summary: rect('#runs-summary'), runs: rect('#runs'), runs_open: document.getElementById('runs').open,
    views_visible: document.getElementById('views').checkVisibility(),
    histories: Array.from(document.querySelectorAll('[data-history]')).map(function (n) {
      var r = n.getBoundingClientRect(), s = n.querySelector('svg');
      return {y: r.y, width: r.width, svg: s ? s.getBoundingClientRect().width : 0}; }),
    metrics: Array.from(document.querySelectorAll('[data-metric]')).map(function (n) { return n.textContent; })
  };
})()""" % (json.dumps(list(TOKENS)), json.dumps(list(TYPE)))


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
    assert m["fonts"] == TYPE
    assert m["smallest_font"] >= 12
    # Headings read as a paper's: numbered, sentence case, never uppercase.
    assert [h["text"] for h in m["headings"]] == ["1 Runs", "2 Identity", "3 Model", "4 Curves", "5 Videos", "6 Record"]
    assert all(h["transform"] == "none" for h in m["headings"])
    assert m["regions"] == sorted(m["regions"]), "regions are out of reading order"
    # The stat row keeps the "key: value" text the other suites read.
    assert m["metrics"][:2] == ["iteration: 4", "total: 10"]
    tops = [h["y"] for h in m["histories"]]
    if size == "desk":
        # 3. The viewport fills the detail column; the run list is a sidebar beside it.
        assert m["canvas"]["width"] >= 0.9 * m["detail"]["width"]
        assert m["sidebar"]["width"] == 280 and m["sidebar"]["right"] <= m["detail"]["x"]
        assert m["runs_open"] and m["summary"]["height"] == 0
        assert len(set(round(t) for t in tops)) == 1, f"curves not abreast: {tops}"
        return
    # 3. On the phone the viewport is the full width inside the gutters; the
    # run list is a closed disclosure whose line is the only thing visible.
    assert m["canvas"]["width"] >= 0.9 * (width - 2 * PHONE_GUTTER)
    assert m["sidebar"]["width"] == width - 2 * PHONE_GUTTER and m["sidebar"]["y"] < m["detail"]["y"]
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
