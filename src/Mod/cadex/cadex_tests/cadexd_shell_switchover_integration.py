# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shell-switchover integration + latency parity (Phase 5.4).

Runs under FreeCADCmd:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex_tests>'); \\
        import cadexd_shell_switchover_integration as m; raise SystemExit(m.main())"

Drives the *session* entry (``run_project_xscript_operation``) — the same
seam the parameters panel and provider dispatch use — against a real
cadexd child: write_script hydrates tagged display objects into the live
document; 10 ``set_params`` drags on the 24-hole/fillet/mesh-skin baseline
part measure the client→cadexd→worker→hydrate cycle (parity bar:
median ≤ 0.65 s, baseline 0.57 s in-process); contract-driven GC removes
display objects when outputs leave the contract.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

BASELINE_SCRIPT = """
p = params(hole=num(2.5, unit="mm", min=1.0, max=4.0, step=0.1))
base = part.box(120, 80, 8)
holes = [
    part.cylinder(p.hole, 16, origin=[10 + 18 * (i % 6), 12 + 18 * (i // 6), -4])
    for i in range(24)
]
plate = part.fillet(part.cut(base, holes), 1.0)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "skin": skin}
"""

REDUCED_SCRIPT = """
p = params(hole=num(2.5, unit="mm", min=1.0, max=4.0, step=0.1))
plate = part.box(60, 40, 8)
result = {"plate": plate}
"""


class _ShellService:
    """The session-facing service surface the switched-over path touches."""

    def __init__(self, project_root: Path, document) -> None:
        self._root = project_root
        self._document = document

    def _active_document(self):
        return self._document

    def project_scope_snapshot(self):
        return {"root": str(self._root), "project_id": "switchover-test"}


def _tagged(document, output: str | None = None) -> list:
    import CadexScriptedDomains as contracts

    result = []
    for obj in document.Objects:
        props = list(getattr(obj, "PropertiesList", []) or [])
        if contracts.PROP_PROGRAM_ID not in props:
            continue
        if str(getattr(obj, contracts.PROP_PROGRAM_ID)) != "project":
            continue
        if output is not None and (
            str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "")) != output
        ):
            continue
        result.append(obj)
    return result


def main() -> int:
    import FreeCAD as App

    import CadexdClient
    from CadexSession import run_project_xscript_operation

    root = Path(tempfile.mkdtemp(prefix="cadexd-switchover-"))
    document = App.newDocument("ShellSwitchover")
    report: dict = {}
    try:
        service = _ShellService(root, document)

        events: list[dict] = []
        written = run_project_xscript_operation(
            service,
            "xscript.project.write_script",
            {"source": BASELINE_SCRIPT, "expected_revision": ""},
            progress_callback=events.append,
        )
        assert written.get("ok") is True, written
        assert "display" not in written, "display block must stay shell-side"
        assert any(
            event.get("event") == "cadex_domain_worker_started" for event in events
        ), events

        plates = _tagged(document, "plate")
        skins = _tagged(document, "skin")
        assert len(plates) == 1 and plates[0].TypeId == "Part::Feature", plates
        assert len(skins) == 1 and skins[0].TypeId == "Mesh::Feature", skins
        assert plates[0].Shape.Volume > 0
        hole_faces_before = len(plates[0].Shape.Faces)

        # 10 slider drags through client → cadexd → worker → hydrate.
        durations = []
        revision = str(written["model_state"]["next_write_expected_revision"])
        for index in range(10):
            value = 1.5 + 0.2 * index
            started = time.perf_counter()
            patched = run_project_xscript_operation(
                service,
                "xscript.project.set_params",
                {"values": {"hole": value}, "expected_revision": revision},
            )
            durations.append(time.perf_counter() - started)
            assert patched.get("ok") is True, patched
            revision = str(patched["model_state"]["next_write_expected_revision"])
        median = statistics.median(durations)

        # The live document tracked the last drag (same object, new shape).
        assert len(_tagged(document, "plate")) == 1
        assert len(plates[0].Shape.Faces) == hole_faces_before

        # Contract-driven GC: dropping the mesh output removes its object.
        reduced = run_project_xscript_operation(
            service,
            "xscript.project.write_script",
            {"source": REDUCED_SCRIPT, "expected_revision": revision},
        )
        assert reduced.get("ok") is True, reduced
        assert _tagged(document, "skin") == [], "skin display object must be GCed"
        assert len(_tagged(document, "plate")) == 1

        # Engine-truth inspection flows through the same client.
        client = CadexdClient.client_for_project(str(root))
        inspected = client.request("inspect", {"scope": "script", "path": "/revisions"})
        assert inspected.get("ok") is True, inspected
        assert inspected["value"]["accepted_revision"] == reduced["revision"]

        report = {
            "ok": True,
            "set_params_seconds": [round(value, 3) for value in durations],
            "median_seconds": round(median, 3),
            "parity_bar_seconds": 0.65,
            "median_within_bar": median <= 0.65,
        }
    finally:
        CadexdClient.close_all()
        App.closeDocument(document.Name)
        shutil.rmtree(root, ignore_errors=True)

    print("SWITCHOVER-INTEGRATION " + json.dumps(report, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
