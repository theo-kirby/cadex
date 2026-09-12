# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The committed D11 comparison evidence stays consistent with its claims.

``docs/probes/review-style/compare.py`` writes a compact receipt beside the
project it compares; ``implementation.json`` (copy100) and ``shin55.json``
(shin55-final) are those receipts, committed without their images. The
project lives outside this checkout, so these tests hold each receipt to
itself and to the documents that cite it: the viewport and capture page were
lossless-identical, the decoded frame was inside the codec tolerance the probe
enforces, the historical clip shares the final clip's style identity, the
persistent page selected the run being compared, real pointer orbit kept the
model drawn, and the lifecycle report no longer calls the shin55 repeat
missing. Nothing here needs a browser, FFmpeg or the project.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT

STYLE = REPO_ROOT / "docs" / "probes" / "review-style"
RECEIPTS = {"implementation.json": "copy100", "shin55.json": "shin55-final"}


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
    assert checkpoint["frames"] > video["frames"]


def test_shin55_repeat_orbited_by_real_pointer_input_with_the_model_drawn():
    evidence = json.loads((STYLE / "shin55.json").read_text())
    assert evidence["historical"] == "shin55-checkpoint20"
    assert evidence["historical_relation"].startswith("HISTORICAL")
    orbit = evidence["orbit"]
    before, dragged, zoomed, far = (orbit[k] for k in ("before", "after_drag", "after_zoom_in", "after_zoom_out"))
    assert dragged["distance"] == before["distance"] and dragged["yaw"] != before["yaw"]
    assert dragged["pitch"] > 0, "the drag must stay above the presentation floor to show the restaged grid"
    assert zoomed["distance"] < before["distance"] < 2 * before["distance"] < far["distance"]
    assert min(orbit["model_pixels"].values()) > 1000
    assert orbit["stage_far"]["fog"]["far"] > evidence["stats"]["stage"]["fog"]["far"]
    for name in ("persistent-orbit-drag", "persistent-orbit-zoom", "persistent-orbit-far"):
        assert evidence["images"][name + ".png"] == evidence["screenshots"][name]


def test_documents_cite_the_shin55_repeat_and_drop_the_old_limit():
    style = (STYLE / "README.md").read_text()
    lifecycle = (REPO_ROOT / "docs" / "probes" / "reed-lifecycle" / "README.md").read_text()
    evidence = json.loads((STYLE / "shin55.json").read_text())
    error = f"{evidence['codec_mean_absolute_rgb_error']:.4f}"
    assert "shin55-final shin55-checkpoint20 style44" in style
    assert error in style, error
    assert "shin55.json" in lifecycle
    assert "was not repeated" not in lifecycle
