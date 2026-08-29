# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Headless pin resolution integration (Phase 5.2).

Runs under FreeCADCmd:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex_tests>'); \\
        import pin_resolution_integration as m; raise SystemExit(m.main())"

Accepts a parametric drilled plate, then verifies: fingerprint and direct
index resolution agree with each other and with the accepted revision's
``face_details``; re-resolution after ``set_params`` moves the hole to the
new location.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from CadexPinResolution import resolve_pin  # noqa: E402
from CadexScriptedDomainPublication import publish_project_candidate  # noqa: E402
from CadexScriptedRuntime import (  # noqa: E402
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    record_project_candidate_failure,
    validate_project_result,
)
import cadex_rebuild  # noqa: E402


SCRIPT = """
p = params(hole_x=num(15, unit="mm", min=6, max=48))
plate = part.cut(
    part.box(60, 40, 6),
    part.cylinder(3, 12, origin=[p.hole_x, 20, -3]),
)
result = {"plate": plate}
"""


def _accept(service, tool: str, arguments: dict) -> dict:
    captured = capture_project_state(service, tool, arguments)
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    if execution.get("ok") is not True:
        record_project_candidate_failure(prepared, execution)
        raise AssertionError(f"{tool} execution failed: {execution}")
    validated = validate_project_result(prepared, execution)
    publication = publish_project_candidate(service, prepared, validated)
    accept_project_candidate(prepared, publication, validated)
    return validated


def _cylindrical_face(validated: dict) -> dict:
    plate = next(item for item in validated["outputs"] if item["name"] == "plate")
    matches = [
        fact
        for fact in plate["facts"]["face_details"]
        if fact["surface_type"] == "Cylinder"
    ]
    assert len(matches) == 1, matches
    return matches[0]


def main() -> int:
    import FreeCAD as App

    from CadexProject import CadexProjectScriptStore

    root = Path(tempfile.mkdtemp(prefix="cadex-pin-integration-"))
    document = App.newDocument("PinIntegration")
    report: dict = {}
    try:
        service = cadex_rebuild._RebuildService(root, document)
        store = CadexProjectScriptStore(root)

        validated = _accept(
            service,
            "xscript.project.write_script",
            {"source": SCRIPT, "expected_revision": ""},
        )
        accepted_face = _cylindrical_face(validated)
        state = store.read_state()
        assert state["accepted_attempt"], state

        fingerprint = {
            "element_type": "face",
            "geometry_type": "Cylinder",
            "expected_count": 1,
        }
        by_fingerprint = resolve_pin(root, "plate", fingerprint)
        assert by_fingerprint["ok"] is True, by_fingerprint
        assert by_fingerprint["revision"] == state["accepted_revision"]
        assert by_fingerprint["subelements"] == [
            f"Face{accepted_face['index']}"
        ], (by_fingerprint, accepted_face)

        by_index = resolve_pin(
            root,
            "plate",
            {"element_type": "face", "index": int(accepted_face["index"])},
        )
        assert by_index["ok"] is True, by_index
        assert by_index["subelements"] == by_fingerprint["subelements"]
        # Same face, same geometry: centers agree with face_details.
        for resolved in (by_fingerprint, by_index):
            center = resolved["details"][0]["center_mm"]
            for actual, expected in zip(center, accepted_face["center_mm"]):
                assert abs(actual - expected) < 1.0e-6, (resolved, accepted_face)
        assert abs(by_index["details"][0]["center_mm"][0] - 15.0) < 1.0e-6

        # Unresolvable fingerprint returns the structured envelope.
        missed = resolve_pin(
            root,
            "plate",
            {"element_type": "face", "geometry_type": "Sphere", "expected_count": 1},
        )
        assert missed["ok"] is False
        assert missed["failure_code"] == "PIN_SELECTION_UNRESOLVED", missed

        # Move the hole via set_params; re-resolution follows the geometry.
        working = str(store.read_state()["working_revision"])
        _accept(
            service,
            "xscript.project.set_params",
            {"values": {"hole_x": 33.0}, "expected_revision": working},
        )
        moved = resolve_pin(root, "plate", fingerprint)
        assert moved["ok"] is True, moved
        assert moved["revision"] != by_fingerprint["revision"]
        assert abs(moved["details"][0]["center_mm"][0] - 33.0) < 1.0e-6, moved

        report = {
            "ok": True,
            "face": by_fingerprint["subelements"][0],
            "moved_center_x": moved["details"][0]["center_mm"][0],
        }
    finally:
        App.closeDocument(document.Name)
        shutil.rmtree(root, ignore_errors=True)

    print("PIN-INTEGRATION " + json.dumps(report, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
