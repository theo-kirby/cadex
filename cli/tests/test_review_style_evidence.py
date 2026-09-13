# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The committed D11 comparison evidence stays consistent with its claims.

``docs/probes/review-style/compare.py`` writes a compact receipt beside the
project it compares; ``implementation.json`` (copy100), ``shin55.json``
(shin55-final) and ``wren.json`` (wren57-retry on the persistent Wren copy) are
those receipts, committed without their images. The
project lives outside this checkout, so these tests hold each receipt to
itself and to the documents that cite it: the viewport and capture page were
lossless-identical, the decoded frame was inside the codec tolerance the probe
enforces, the historical clip shares the final clip's style identity, the
persistent page selected the run being compared, real pointer orbit kept the
model drawn, the Wren repeat compared the reference renderer at the same close
and wide framings beside an actual shipped reference frame, and the lifecycle
report no longer calls the shin55 repeat missing. Nothing here needs a
browser, FFmpeg or the project.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT

STYLE = REPO_ROOT / "docs" / "probes" / "review-style"
RECEIPTS = {"implementation.json": "copy100", "shin55.json": "shin55-final", "wren.json": "wren57-retry"}
HISTORICAL = {"shin55.json": "shin55-checkpoint20", "wren.json": "wren2-final"}


@pytest.fixture(scope="module", params=sorted(RECEIPTS))
def receipt(request) -> tuple[str, dict]:
    return RECEIPTS[request.param], json.loads((STYLE / request.param).read_text())


def test_receipt_compares_the_run_the_persistent_page_selected(receipt):
    run, evidence = receipt
    assert evidence["run"] == run
    identity = evidence["persistent_identity"]
    assert identity["selected"] == run and identity["relation"] == "current"
    assert identity["revision"] == evidence["video"]["accepted_revision"] == identity["model"]["revision"]
    assert not identity["stale"] and identity["error"] is None
    assert evidence["camera"] == evidence["video"]["camera"]
    assert evidence["stats"]["style"] == evidence["video"]["style"] == "cadex-prototype-light-v1"


def test_viewport_capture_and_decoded_frame_agree(receipt):
    _run, evidence = receipt
    assert evidence["lossless_viewport_capture_equal"] is True
    shots = evidence["screenshots"]
    assert shots["persistent-same-pose"] == shots["capture-same-pose"]
    assert 0 < evidence["codec_mean_absolute_rgb_error"] < 3
    images = evidence["images"]
    for name in ("reference-light-reed", "persistent-same-pose", "video-frame0", "persistent-close",
                 "persistent-wide", "persistent-under", "checkpoint-frame0", "side-by-side"):
        assert images[name + ".png"], name
    assert images["persistent-same-pose.png"] == shots["persistent-same-pose"]


def test_historical_clip_keeps_the_final_clips_style_identity(receipt):
    _run, evidence = receipt
    checkpoint, video = evidence["checkpoint"], evidence["video"]
    assert evidence["checkpoint_playback_download_poll"] is True
    assert checkpoint["style_sha256"] == video["style_sha256"]
    assert checkpoint["renderer"] == video["renderer"]
    assert checkpoint["sha256"] != video["sha256"] and checkpoint["policy_sha256"] != video["policy_sha256"]
    assert checkpoint["frames"] >= video["frames"]


@pytest.mark.parametrize("name", sorted(HISTORICAL))
def test_repeats_orbited_by_real_pointer_input_with_the_model_drawn(name):
    evidence = json.loads((STYLE / name).read_text())
    assert evidence["historical"] == HISTORICAL[name]
    assert evidence["historical_relation"].startswith("HISTORICAL")
    orbit = evidence["orbit"]
    before, dragged, zoomed, far = (orbit[k] for k in ("before", "after_drag", "after_zoom_in", "after_zoom_out"))
    assert dragged["distance"] == before["distance"] and dragged["yaw"] != before["yaw"]
    assert dragged["pitch"] > 0, "the drag must stay above the presentation floor to show the restaged grid"
    assert zoomed["distance"] < before["distance"] < 2 * before["distance"] < far["distance"]
    assert min(orbit["model_pixels"].values()) > 1000
    assert orbit["stage_far"]["fog"]["far"] > evidence["stats"]["stage"]["fog"]["far"]
    for shot in ("persistent-orbit-drag", "persistent-orbit-zoom", "persistent-orbit-far"):
        assert evidence["images"][shot + ".png"] == evidence["screenshots"][shot]


def test_wren_repeat_compares_the_reference_at_close_and_wide_beside_a_shipped_frame():
    evidence = json.loads((STYLE / "wren.json").read_text())
    baseline = json.loads((STYLE / "evidence.json").read_text())
    assert evidence["project"] == "ot5-wren-copy54"
    assert evidence["reference_commit"] == baseline["reference_commit"]
    # The historical clip is the earlier design (105 mm feet), not a checkpoint of the same one:
    # both are complete eight-second recordings with their own accepted revisions.
    checkpoint, video = evidence["checkpoint"], evidence["video"]
    assert checkpoint["accepted_revision"] != video["accepted_revision"]
    assert checkpoint["frames"] == video["frames"] == 81
    assert checkpoint["sim_seconds"] == video["sim_seconds"] == 8.0
    # The reference renderer was restaged at the persistent close and wide cameras.
    for shot in ("reference-light-reed", "reference-light-reed-close", "reference-light-reed-wide",
                 "persistent-close", "persistent-wide"):
        assert evidence["images"][shot + ".png"], shot
    assert evidence["screenshots"]["reference-light-reed-close"] != evidence["screenshots"]["reference-light-reed"]
    assert evidence["screenshots"]["reference-light-reed-wide"] != evidence["screenshots"]["reference-light-reed"]
    # An actual shipped reference clip, the same file the baseline decoded, contributes a frame.
    shipped = evidence["reference_shipped_frame"]
    assert shipped["theme"] == "dark" and shipped["seconds"] == 4
    assert shipped["video_sha256"] == baseline["reference_frames"][shipped["video"]]["video_sha256"]
    assert evidence["images"]["reference-shipped-orbit-4s.png"] == shipped["image_sha256"]
    motion = evidence["motion_frames"]
    assert {m["run"] for m in motion.values()} == {"wren57-retry", "wren2-final"}
    assert all(len(m["sha256"]) == 64 for m in motion.values())


def test_documents_cite_the_shin55_repeat_and_drop_the_old_limit():
    style = (STYLE / "README.md").read_text()
    lifecycle = (REPO_ROOT / "docs" / "probes" / "reed-lifecycle" / "README.md").read_text()
    evidence = json.loads((STYLE / "shin55.json").read_text())
    error = f"{evidence['codec_mean_absolute_rgb_error']:.4f}"
    assert "shin55-final shin55-checkpoint20 style44" in style
    assert error in style, error
    assert "shin55.json" in lifecycle
    assert "was not repeated" not in lifecycle


def test_documents_cite_the_wren_repeat_with_its_measured_error():
    style = (STYLE / "README.md").read_text()
    wren = (REPO_ROOT / "docs" / "probes" / "wren-fresh" / "README.md").read_text()
    lifecycle = (REPO_ROOT / "docs" / "probes" / "reed-lifecycle" / "README.md").read_text()
    evidence = json.loads((STYLE / "wren.json").read_text())
    assert "wren57-retry wren2-final style64" in style
    assert f"{evidence['codec_mean_absolute_rgb_error']:.4f}" in style
    assert "wren.json" in wren and "wren.json" in lifecycle
