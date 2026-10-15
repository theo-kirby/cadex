# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A task's gait reference plays on the dashboard before anything trains (ADR-703).

The engine writes an ``api.gait`` stride into the task bundle's
``reference`` section, every body's pose at each sample beside the joint
angles. ``/api/project`` lists each accepted task that carries one, and
``/api/playback/reference/<task>`` serves it as playback: the one stride
repeated, each repeat a stride further on, closing on the next stride's
first pose so a loop lands where it began. The page offers it as a source
and loops it as soon as it is in.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from cadex_cli.review_server import REFERENCE_PLAY_S, serve
from test_review_server import (REVISION_B, _get, _json, _open, _review_project,
                                _stage_accepted, browser, needs_browser)  # noqa: F401  (fixture)

#: Four samples of a 0.4 s stride 200 mm long: the body walks 50 mm a sample.
DT, SAMPLES, STRIDE_MM = 0.1, 4, 200.0


def reference_bundle(staging: Path, task: str = "walk", *, reference: bool = True) -> Path:
    """A task bundle in the accepted attempt, with (or without) a gait reference."""

    bundle = {"schema": "cadex-training-task-v1", "label": task}
    if reference:
        bundle["reference"] = {
            "schema": "cadex-gait-clip-v1", "gait": "trot", "label": "cruise",
            "samples": SAMPLES, "sample_dt_s": DT,
            "parameters": {"speed_m_s": 0.5, "stride_length_m": STRIDE_MM / 1000.0,
                           "stride_frequency_hz": 2.5, "period_s": DT * SAMPLES, "duty_factor": 0.45,
                           "phase_offsets": {"LH": 0.0, "RF": 0.0, "RH": 0.5, "LF": 0.5},
                           "froude": 0.06, "hip_height_m": 0.4, "swing_height_m": 0.03},
            "contact": {"LF": [0, 0, 1, 1], "RF": [1, 1, 0, 0], "LH": [1, 1, 0, 0], "RH": [0, 0, 1, 1]},
            # the second sample's quaternion is the first's with its sign flipped
            "placements": [{"body": {"position_mm": [50.0 * k, 0.0, 10.0],
                                     "rotation_xyzw": [0.0, 0.0, 0.0, -1.0 if k == 1 else 1.0]}}
                           for k in range(SAMPLES)],
        }
    path = staging / "outputs" / f"{task}-task.json"
    path.write_text(json.dumps(bundle))
    return path


def test_the_project_lists_each_reference_and_serves_it_as_a_looping_stride(tmp_path) -> None:
    root = _review_project(tmp_path)
    staging = _stage_accepted(root, REVISION_B)
    reference_bundle(staging, "walk")
    reference_bundle(staging, "stand", reference=False)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        listed = _json(server.url + "api/project")["references"]
        assert [row["task"] for row in listed] == ["walk"]
        row = listed[0]
        assert row["gait"] == "trot" and row["label"] == "cruise"
        assert row["stride_length_m"] == 0.2 and row["period_s"] == 0.4 and row["duty_factor"] == 0.45
        assert row["url"] == "api/playback/reference/walk"

        played = _json(server.url + row["url"])
        assert played["available"] and played["task"] == "walk"
        assert played["source"].endswith("outputs/walk-task.json")
        strides = math.ceil(REFERENCE_PLAY_S / (DT * SAMPLES))
        assert played["strides"] == strides
        assert len(played["frames"]) == strides * SAMPLES + 1
        assert played["times_s"][:3] == [0.0, 0.1, 0.2]
        assert played["duration_s"] == played["times_s"][-1] == round(strides * SAMPLES * DT, 9)
        assert played["frames_per_second"] == 10.0
        # each repeat is a stride on, so the body walks on at 50 mm a sample
        xs = [frame["body"]["position_mm"][0] for frame in played["frames"]]
        assert xs == [50.0 * k for k in range(len(xs))]
        # the flipped sign is unflipped, so the page never blends the long way round
        assert all(frame["body"]["rotation_xyzw"][3] > 0 for frame in played["frames"])
        assert played["reference"]["contact"]["LF"] == [0, 0, 1, 1]

        unplayed = _json(server.url + "api/playback/reference/stand")
        assert unplayed == {"task": "stand", "source": unplayed["source"], "available": False,
                            "reason": "this task declares no gait reference"}
        assert _get(server.url + "api/playback/reference/nope")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


def test_a_project_with_no_accepted_attempt_lists_no_references(tmp_path) -> None:
    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        assert _json(server.url + "api/project")["references"] == []
        assert _get(server.url + "api/playback/reference/walk")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_the_page_offers_a_reference_and_loops_it(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    reference_bundle(_stage_accepted(root, REVISION_B), "walk")
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.wait_for("Array.prototype.some.call(document.querySelectorAll('#view3d-source option'),"
                      " function (o) { return o.value === 'reference:walk'; })")
        label = page.evaluate("document.querySelector('#view3d-source option[value=\"reference:walk\"]')"
                              ".parentNode.label")
        assert label == "Gait references"
        page.evaluate("window.cadexReview.setSource('reference:walk')", await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("(function(){var p=window.cadexReview.playback();return p&&p.playing})()")
        shown = page.evaluate("window.cadexReview.playback()")
        assert shown["reference"] == "walk" and shown["looping"] is True
        assert len(shown["times_s"]) == len(_json(server.url + "api/playback/reference/walk")["times_s"])
        assert not page.evaluate("document.getElementById('playback').hidden")
        # the clock runs to the end, and starts again rather than stopping
        end = shown["times_s"][-1]
        page.wait_for(f"window.cadexReview.playback().t > {end - 0.6}", timeout=15)
        page.wait_for(f"window.cadexReview.playback().t < {end / 2}", timeout=5)
        assert page.evaluate("window.cadexReview.playback().playing") is True
        # it walks out of a still view; followed, it stays drawn
        page.evaluate("window.cadexReview.setFollow(true)")
        assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 100
    finally:
        server.shutdown()
        server.server_close()
