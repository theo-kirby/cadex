# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A simulation output can be published (ADR-048).

``_configure_assembly_simulation`` reads ``item["simulation_trace_preview"]``
and refuses the whole candidate when it is absent. Nothing wrote that key --
the read was its only occurrence in the repository -- so every script
containing ``assembly.simulation(...)`` died at publication with
``DOMAIN_PUBLICATION_FAILED: An Assembly simulation has no authenticated
trace summary``.

This drives the publisher with the item dict the worker actually builds,
under the suite's stubbed FreeCAD, and pins the preview's shape against
``cadex_assembly_worker._simulation_trace_preview`` so the two halves cannot
drift apart again.
"""

from __future__ import annotations

from typing import Any

import pytest

import cadex_assembly_worker
from CadexScriptedDomainPublication import _configure_assembly_simulation


class _StubObject:
    """The narrow slice of an App::FeaturePython the publisher touches."""

    def __init__(self, type_id: str = "App::FeaturePython") -> None:
        self.TypeId = type_id
        self.PropertiesList: list[str] = []
        self.Proxy: Any = None
        self.Group: list[Any] = []

    def addProperty(self, _type, name, _group="", _doc="", **_kwargs):
        self.PropertiesList.append(name)
        setattr(self, name, 0)
        return self

    def addExtension(self, _name):
        if "Group" not in self.PropertiesList:
            self.PropertiesList.append("Group")
        return None


def _frames(count: int) -> list[dict[str, Any]]:
    """Frames shaped exactly as ``_execute_native_simulation`` records them.

    ``component_placements`` is ``_compact_placement``'s output -- a
    position in mm plus an **xyzw** quaternion -- not a 4x4 matrix. Verified
    against a live trace; the shell's bake has to reorder it to wxyz.
    """

    return [
        {
            "frame_index": index,
            "frame_kind": "input" if index == 0 else "solver_output",
            "nominal_time_s": None if index == 0 else 0.05 * (index - 1),
            "component_placements": {
                "base": {
                    "position_mm": [0.0, 0.0, 0.0],
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                "swing": {
                    "position_mm": [float(index), 0.0, 0.0],
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
            },
        }
        for index in range(count)
    ]


def _item(frames: list[dict[str, Any]], *, with_preview: bool = True) -> dict[str, Any]:
    """The publisher-facing item ``_execute_native_simulation`` builds."""

    parameters = {
        "start_time_s": 0.0,
        "end_time_s": 1.0,
        "time_step_s": 0.05,
        "error_tolerance": 1.0e-06,
        "frames_per_second": 30,
    }
    item: dict[str, Any] = {
        "name": "sim",
        "artifact_kind": "assembly_simulation_json",
        "assembly_data": {
            "assembly_output": "asm",
            "simulation_output": "sim",
            "motion_outputs": ["spin"],
            "parameters": dict(parameters),
            "native_code": 0,
            "frame_count": len(frames),
            "pose_count": len(frames) * 2,
            "artifact_sha256": "0" * 64,
        },
    }
    if with_preview:
        item["simulation_trace_preview"] = (
            cadex_assembly_worker._simulation_trace_preview(frames)
        )
    return item


def test_a_simulation_publishes() -> None:
    """The whole point: this raised for every simulation script before."""

    frames = _frames(21)
    obj = _StubObject()
    _configure_assembly_simulation(obj, _item(frames), {"spin": _StubObject()})

    assert obj.CadexFrameCount == 21
    assert obj.CadexPoseCount == 42
    assert obj.aTimeStart == 0.0 and obj.bTimeEnd == 1.0
    assert obj.jFramesPerSecond == 30
    assert obj.CadexSimulationTracePreview


def test_a_policy_rollout_publishes_through_the_same_branch_unchanged() -> None:
    """M8's phase 4, which is empty, asserted rather than assumed (ADR-085).

    A rollout is an ``assembly_simulation_json`` like any other simulation,
    so ``_configure_assembly_simulation`` already handles it and M8 changed
    nothing here. What is worth pinning is that the *policy* block survives:
    the publisher serialises the whole ``assembly_data`` into
    ``CadexAssemblySimulationValidation``, so the three digests that make a
    policy, a task and a model mean anything together are on the published
    proxy without a property of their own.
    """

    import json

    frames = _frames(27)
    item = _item(frames)
    item["assembly_data"]["motion_outputs"] = []
    item["assembly_data"]["policy"] = {
        "policy_output": "gait",
        "policy_sha256": "a" * 64,
        "task_sha256": "b" * 64,
        "model_sha256": "c" * 64,
        "total_reward": 243.4,
        "step_count": 100,
        "truncated": True,
    }

    obj = _StubObject()
    _configure_assembly_simulation(obj, item, {})

    assert obj.CadexFrameCount == 27
    assert obj.Group == []
    published = json.loads(obj.CadexAssemblySimulationValidation)
    assert published["policy"]["policy_sha256"] == "a" * 64
    assert published["policy"]["task_sha256"] == "b" * 64
    assert published["policy"]["model_sha256"] == "c" * 64
    assert published["policy"]["total_reward"] == 243.4


def test_a_simulation_without_a_preview_is_still_refused() -> None:
    """The guard stays. It was right; nothing was answering it."""

    obj = _StubObject()
    with pytest.raises(RuntimeError, match="no authenticated trace summary"):
        _configure_assembly_simulation(
            obj, _item(_frames(21), with_preview=False), {"spin": _StubObject()}
        )


def test_the_preview_is_the_input_middle_and_final_frames() -> None:
    """Exactly what CadexSimulationTracePreview's description promises."""

    frames = _frames(21)
    preview = cadex_assembly_worker._simulation_trace_preview(frames)

    assert [frame["frame_index"] for frame in preview] == [0, 10, 20]
    # A verbatim subset of the frames hashed into artifact_sha256, so the
    # published preview is checkable against the retained artifact.
    assert preview == [frames[0], frames[10], frames[20]]
    # Frame 0 is the input frame and carries no time.
    assert preview[0]["frame_kind"] == "input"
    assert preview[0]["nominal_time_s"] is None


@pytest.mark.parametrize(
    "count, expected",
    [(2, [0, 1]), (3, [0, 1, 2]), (4, [0, 2, 3]), (10_000, [0, 5000, 9999])],
)
def test_the_preview_is_bounded_and_never_repeats_a_frame(count, expected) -> None:
    """Three frames however long the run, and deduplicated at the short end.

    A two-frame trace is the interesting case: 0, count // 2 and count - 1
    all collide, and repeating the last frame twice would publish a preview
    that misrepresents the trace.
    """

    preview = cadex_assembly_worker._simulation_trace_preview(_frames(count))
    assert [frame["frame_index"] for frame in preview] == expected
    assert len(preview) <= 3
