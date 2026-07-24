# SPDX-License-Identifier: LGPL-2.1-or-later

"""Qt heartbeat integration for the project-script worker (Phase 2.4).

Run this file inside ``FreeCADCmd``. The project candidate's subprocess wait
happens on a background thread while the main thread owns a real Qt event
loop; the loop must keep ticking (session-level worker heartbeats) for the
whole isolated execution. The script deliberately spans every capability
domain (busy loop + part, partdesign, sketcher, and an assembly of
same-script solids) so the wait is long enough to observe heartbeats.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from PySide import QtCore  # noqa: E402

from CadexScriptedRuntime import (  # noqa: E402
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    validate_project_result,
)


PROJECT_SCRIPT = """
total = 0
for value in range(30000):
    total += value % 7
p = params(
    width=num(40, unit="mm", min=10, max=120),
    thickness=num(6, unit="mm", min=2, max=20),
)
plate = part.box(p.width, 24, p.thickness)
profile = sketcher.sketch(
    [
        sketcher.line([0, 0], [20, 0]),
        sketcher.line([20, 0], [20, 12]),
        sketcher.line([20, 12], [0, 12]),
        sketcher.line([0, 12], [0, 0]),
    ],
    [],
)
block_profile = partdesign.sketch(
    [
        partdesign.line([0, 0], [16, 0]),
        partdesign.line([16, 0], [16, 10]),
        partdesign.line([16, 10], [0, 10]),
        partdesign.line([0, 10], [0, 0]),
    ],
    [],
)
block = partdesign.body(partdesign.pad(block_profile, p.thickness))
base = assembly.component(plate, grounded=True)
lid = assembly.component(plate, placement=[0, 0, p.thickness])
asm = assembly.assembly([base, lid])
diag = assembly.solve(asm)
result = {
    "plate": plate,
    "profile": profile,
    "block": block,
    "base": base,
    "lid": lid,
    "main_assembly": asm,
    "diagnostics": diag,
}
"""


class _Service:
    """Minimal document-affine service protocol for the project lifecycle."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def _active_document(self):
        import FreeCAD as App

        return App.ActiveDocument

    def project_scope_snapshot(self):
        return {"root": str(self._root), "project_id": "qt-heartbeat"}

    @staticmethod
    def provider_document_revision() -> str:
        return "qt-heartbeat-revision"

    @staticmethod
    def active_workbench_name() -> str:
        return "CadexProject"

    @staticmethod
    def modeling_engine() -> str:
        return "xscript"


class _Bridge(QtCore.QObject):
    finished = QtCore.Signal()


def main() -> int:
    import FreeCAD as App

    application = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    del application
    root = Path(tempfile.mkdtemp(prefix="cadex-qt-heartbeat-"))
    document = App.newDocument("QtHeartbeatProject")
    try:
        service = _Service(root)
        captured = capture_project_state(
            service,
            "xscript.project.write_script",
            {"source": PROJECT_SCRIPT, "expected_revision": ""},
        )
        prepared = prepare_project_candidate(captured)

        outcomes: list[dict] = []
        failures: list[str] = []
        bridge = _Bridge()
        event_loop = QtCore.QEventLoop()
        bridge.finished.connect(event_loop.quit)
        heartbeats = [0]
        timer = QtCore.QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: heartbeats.__setitem__(0, heartbeats[0] + 1))

        def work() -> None:
            try:
                outcome = execute_candidate(prepared, cancellation_check=None)
                outcomes.append(outcome)
                if outcome.get("ok") is not True:
                    failures.append(str(outcome))
            except BaseException as exc:
                failures.append(f"{exc.__class__.__name__}: {exc}")
            finally:
                bridge.finished.emit()

        started = time.monotonic()
        worker = threading.Thread(
            target=work, name="CadexQtHeartbeatWorker", daemon=True
        )
        timer.start()
        worker.start()
        event_loop.exec()
        timer.stop()
        worker.join(timeout=5.0)
        elapsed = time.monotonic() - started
        assert not worker.is_alive(), "The background project worker did not finish."
        assert not failures, failures
        assert len(outcomes) == 1
        assert heartbeats[0] >= 10, (
            "The Qt event loop did not remain responsive during the project "
            f"subprocess wait: heartbeats={heartbeats[0]}, elapsed={elapsed:.3f}s"
        )
        validated = validate_project_result(prepared, outcomes[0])
        assert validated["ok"] is True
        assert sorted(item["name"] for item in validated["contract"]) == [
            "base",
            "block",
            "diagnostics",
            "lid",
            "main_assembly",
            "plate",
            "profile",
        ]
        print(
            json.dumps(
                {
                    "ok": True,
                    "integration": "qt_domain_worker_heartbeat",
                    "domains": sorted(
                        {item["domain"] for item in validated["contract"]}
                    ),
                    "heartbeats": heartbeats[0],
                    "elapsed_seconds": round(elapsed, 3),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    finally:
        App.closeDocument(document.Name)
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
