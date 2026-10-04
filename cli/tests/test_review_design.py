# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The app's design spec, and the ot6 evidence caps (ADR-328, ADR-534).

``docs/DASHBOARD.md`` is the contract the page is held to (ADR-329).
Without a browser this suite pins the spec's required sections, its
page-background token to the environment module's dark scene background
(one palette across chrome and viewport), its "before" and "after"
measurements to the committed receipts, and every ot6 receipt to the
charter's caps — 16 KB per receipt, 200 KB per image — with no private
address or this machine's hostname in any of them. With a Chromium it
renders the page at the two charter sizes, 1400×900 and 400×850 with touch
emulation, and reads the spec back from the rendered page: the layout
viewport is the device width, nothing overflows it, the palette tokens and
type scale compute to §3–§4, the default layout's three areas tile the
screen at desk (§12), and on the phone one area, the 3D viewport, fills it
above a tab bar (ADR-534).
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

from test_review_server import _model_state, browser, needs_browser, served  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs" / "DASHBOARD.md"
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
TYPE = {"body": "14px", "h1": "17px", "h2": "14px", "#accepted-line": "12px"}
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

# §2: the three editors, in the default layout's reading order, and the
# settings editor's panels.
EDITORS = ["settings", "view3d", "view2d"]
HEADINGS = ["File", "Revisions", "View"]

MEASURE = """(function () {
  var cs = getComputedStyle(document.documentElement);
  function box(n) { if (!n) return null; var r = n.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height, right: r.right, bottom: r.bottom}; }
  function rect(sel) { return box(document.querySelector(sel)); }
  function size(sel) { return getComputedStyle(document.querySelector(sel)).fontSize; }
  var smallest = Infinity;
  document.querySelectorAll('body *').forEach(function (n) {
    if (!n.checkVisibility()) return;
    var v = parseFloat(getComputedStyle(n).fontSize); if (v > 0 && v < smallest) smallest = v; });
  return {
    innerWidth: innerWidth, scrollWidth: document.documentElement.scrollWidth,
    tokens: Object.fromEntries(%s.map(function (t) { return [t, cs.getPropertyValue(t).trim()]; })),
    fonts: Object.fromEntries(%s.map(function (s) { return [s, size(s)]; })),
    smallest_font: smallest,
    body_bg: getComputedStyle(document.body).backgroundColor,
    headings: Array.from(document.querySelectorAll('#screen h2')).map(function (h) {
      return {text: h.textContent, transform: getComputedStyle(h).textTransform}; }),
    mode: document.getElementById('screen').dataset.mode,
    areas: Array.from(document.querySelectorAll('#screen .area')).map(function (a) {
      return Object.assign({editor: a.dataset.editor}, box(a)); }),
    tabs: Array.from(document.querySelectorAll('#screen nav.tabs .tab')).map(function (t) { return t.dataset.editor; }),
    canvas: rect('#viewer'), model: rect('#model'), screen: rect('#screen'), top: rect('#top'),
    scrollHeight: document.documentElement.scrollHeight, innerHeight: innerHeight
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
def test_rendered_page_follows_the_spec(tmp_path, browser, size) -> None:
    """§6's invariants, read back from the page at each charter size."""

    from test_review_server import REVISION_B, _review_project, _stage_accepted, serve
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        _assert_follows_the_spec(browser, server, size)
    finally:
        server.shutdown()
        server.server_close()


def _assert_follows_the_spec(browser, server, size) -> None:
    page = _rendered(browser, server.url, size)
    assert _model_state(page) == "loaded"
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
    # Headings are sentence case, never uppercase.
    assert all(h["transform"] == "none" for h in m["headings"])
    # 3. §12: a thin bar over the screen; the page never scrolls; the screen fills the rest.
    assert m["top"]["height"] <= 48, m["top"]
    assert m["scrollHeight"] <= m["innerHeight"], m["scrollHeight"]
    assert m["screen"]["y"] >= m["top"]["bottom"] - 1 and round(m["screen"]["bottom"]) == m["innerHeight"]
    # The 3D viewport's canvas fills its area's body.
    assert m["canvas"]["width"] >= 0.98 * m["model"]["width"] and m["canvas"]["height"] >= 0.98 * m["model"]["height"]
    if size == "desk":
        # §12: the default layout tiles the screen with the three editors, none overlapping.
        assert m["mode"] == "areas"
        assert [a["editor"] for a in m["areas"]] == EDITORS
        assert [h["text"] for h in m["headings"]] == HEADINGS
        covered = sum(a["width"] * a["height"] for a in m["areas"])
        assert 0.95 * m["screen"]["width"] * m["screen"]["height"] <= covered <= m["screen"]["width"] * m["screen"]["height"]
        for i, a in enumerate(m["areas"]):
            for b in m["areas"][i + 1:]:
                overlap = (min(a["right"], b["right"]) - max(a["x"], b["x"]), min(a["bottom"], b["bottom"]) - max(a["y"], b["y"]))
                assert overlap[0] <= 0.5 or overlap[1] <= 0.5, (a, b)
        return
    # §6: on the phone one editor fills the screen, the 3D viewport first, and a tab bar picks it.
    assert m["mode"] == "tabs"
    assert [a["editor"] for a in m["areas"]] == ["view3d"]
    assert m["tabs"] == ["view3d", "view2d", "settings"]
    assert m["canvas"]["width"] >= width - 1


@needs_browser
def test_light_theme_is_chosen_kept_and_drawn(tmp_path, browser) -> None:
    """§4: the light theme overrides the same tokens, survives a reload, and
    the hairline style draws the theme's paper."""

    from test_review_server import REVISION_B, _review_project, _stage_accepted, serve
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _rendered(browser, server.url, "desk")
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        page.click("#theme-choice button[data-choice=light]")
        assert page.evaluate("document.documentElement.dataset.theme") == "light"
        light = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert light != "rgb(20, 20, 20)"
        page.click("#view3d-style button[data-style=hairline]")
        assert page.evaluate("window.cadexReview.viewer().stats().render_style") == "hairline"
        page.send("Page.reload", {})
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate("window.cadexReview.ready", await_promise=True)
        assert page.evaluate("document.documentElement.dataset.theme") == "light"
        assert page.evaluate("getComputedStyle(document.body).backgroundColor") == light
        assert page.evaluate("window.cadexReview.renderStyle()") == "hairline"
        # The hairline's paper fills the canvas where the model is not.
        assert _model_state(page) == "loaded"
        pixel = page.evaluate("""(function () {
          var v = window.cadexReview.viewer(); v.draw();
          var c = document.getElementById('viewer'), g = document.createElement('canvas');
          g.width = c.width; g.height = c.height; var x = g.getContext('2d'); x.drawImage(c, 0, 0);
          return Array.from(x.getImageData(2, 2, 1, 1).data.slice(0, 3)); })()""")
        assert pixel == [0xfb, 0xfb, 0xf9], pixel
        page.evaluate("localStorage.clear()")
    finally:
        server.shutdown()
        server.server_close()


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


#: Browser tests ADR-533 removed with the page panels they drove. A receipt
#: that cites one keeps its history; the behaviour is no longer on the page.
REMOVED_BY_ADR_533 = frozenset({
    "test_browser_long_history_keeps_selection_and_playback_with_bounded_poll_work",
    "test_browser_explains_a_failed_observation_whose_training_finished",
    "test_browser_interrupted_download_leaves_polling_and_a_fresh_download_working",
    "test_browser_cancelled_download_is_logged_once_and_the_next_download_completes",
    "test_browser_lists_a_completed_run_whose_policy_was_never_stored_as_a_problem",
    "test_browser_observes_final_policy_publication_failure",
    "test_browser_playing_video_survives_new_current_attempt",
    "test_browser_polls_training_histories_checkpoints_and_stale_states",
})

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
            assert files[f"cli/tests/{path}"][2] == 0, behaviour
            if name in REMOVED_BY_ADR_533:
                continue
            assert f"def {name}(" in (REPO / "cli/tests" / path).read_text(), f"{behaviour}: {test} is gone"
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
