# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A pose-only preview pays for no fit measurement (ADR-527).

Static and swept fit were 0.72 s of a 0.77 s warm preview on the latency
bar's part (``cadexd_latency_integration.py``), and a preview returns only
solved placements. The driver below makes every fit stage raise, then runs a
real preview through ``cadex_project_worker._run_preview`` under FreeCADCmd:
if any of them is still reached, the preview fails instead of answering.
"""

import json
import os
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
)
FREECADCMD = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)

_DRIVER = r'''
import json
import sys
import tempfile
from pathlib import Path

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))
import cadex_assembly_worker
import cadex_project_worker
from CadexScriptedRuntime import _project_api_contracts


def refuse(*_args, **_kwargs):
    raise AssertionError("a preview reached a fit stage")


for name in ("_measure_clearance", "_check_fit", "_check_attachments",
             "_measure_joint_sweeps"):
    setattr(cadex_assembly_worker, name, refuse)

SOURCE = """
p = params(reach=num(12, unit="mm", min=0, max=30, step=1))
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[p.reach, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""

request = {
    "schema": cadex_project_worker.SCHEMA,
    "source": SOURCE,
    "inputs": {},
    "param_values": {"reach": 12},
    "api_contracts": _project_api_contracts(),
    "mode": "preview",
}
root = Path(tempfile.mkdtemp(prefix="cadex-preview-fit-"))
loaded = cadex_project_worker._run_preview(dict(request), root)
posed = cadex_project_worker._run_preview(
    {**request, "param_values": {"reach": 25},
     "baseline": {"definitions_fingerprint": loaded["definitions_fingerprint"]}},
    root,
)
print("PREVIEW-FIT " + json.dumps(posed, sort_keys=True, default=str))
'''


@pytest.mark.skipif(FREECADCMD is None, reason="No FreeCADCmd binary to run a preview.")
def test_a_preview_answers_placements_without_measuring_fit(tmp_path) -> None:
    driver = tmp_path / "preview_fit_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            str(FREECADCMD),
            "-c",
            (
                f"import sys; sys.argv = ['driver', {str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    marker = next(
        (line for line in completed.stdout.splitlines() if line.startswith("PREVIEW-FIT ")),
        None,
    )
    assert marker, (
        f"preview driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    posed = json.loads(marker.removeprefix("PREVIEW-FIT "))
    assert posed["previewable"] is True, posed
    # The solve still ran: the revolute joint puts `swing` where `reach` says.
    swing = [round(value, 6) for value in posed["placements"]["swing"][3::4]]
    assert swing == [25.0, 0.0, 4.0, 1.0], posed
