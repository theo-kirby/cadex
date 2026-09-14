# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Read-only Robin offset reproducer; run with the pixi Python interpreter.

Arguments: PROJECT OUT_DIR FREECADCMD CADEX_MODULE_DIR.
Uses the retained accepted result, never accepts or edits the project. Four
fresh processes replay both wheel definitions and fingerprint every operation.
Then four processes offset the *same saved input BREP* directly in OCCT.
Full results stay in OUT_DIR, outside the product checkout.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


DRIVER = r'''
import hashlib, json, os, sys
from pathlib import Path
import Part
sys.path.insert(0, os.environ["CADEX_SOURCE"])
import cadex_part_worker as worker
destination = Path(os.environ["PROBE_RESULT"])
rows = []
def facts(shape, **identity):
    data = shape.exportBrepToString().encode()
    return dict(identity, sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data), volume=shape.Volume,
                faces=len(shape.Faces), edges=len(shape.Edges))
if os.environ["PROBE_MODE"] == "frozen":
    for side in ("l", "r"):
        shape = Part.Shape()
        shape.importBrep(str(destination.parent / (side + "-input.brep")))
        rows.append(facts(shape, side=side, operation="input"))
        offset = shape.makeOffsetShape(0.05, 1e-7, inter=False,
            self_inter=False, offsetMode=0, join=0, fill=False)
        rows.append(facts(offset, side=side, operation="offset"))
else:
    original = worker.build_part_shape
    def traced(payload, **kw):
        shape = original(payload, **kw)
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        rows.append(facts(shape, key=key, operation=payload.get("operation")))
        return shape
    worker.build_part_shape = traced
    result = json.loads(Path(os.environ["ACCEPTED_RESULT"]).read_text())
    for output in result["outputs"]:
        if output["name"] not in ("wheel_l", "wheel_r"):
            continue
        worker.reset_part_shape_memo()
        traced(output["definition"])
        if os.environ["PROBE_MODE"] == "save":
            # Robin's final cut has two arguments: wheel blank and offset cutter.
            offset = output["definition"]["arguments"][1]
            if isinstance(offset, list):
                offset = offset[0]
            assert offset["operation"] == "offset"
            assert offset["arguments"][1] == 0.05
            assert offset["properties"].get("join", "arc") == "arc"
            assert not offset["properties"].get("fill", False)
            shape = original(offset["arguments"][0])
            shape.exportBrep(str(destination.parent / (output["name"][-1] + "-input.brep")))
destination.write_text(json.dumps(rows, indent=2) + "\n")
'''


def main():
    project, out, binary, module = map(lambda p: Path(p).resolve(), sys.argv[1:])
    out.mkdir(parents=True, exist_ok=True)
    state_bytes = (project / "script.json").read_bytes()
    state = json.loads(state_bytes)
    accepted = project / state["accepted_attempt"]["staging"] / "result.json"
    driver = out / "driver.py"
    driver.write_text(DRIVER)
    for mode, count in (("replay", 4), ("save", 1), ("frozen", 4)):
        for index in range(count):
            env = dict(os.environ, PYTHONHASHSEED="0", CADEX_SOURCE=str(module),
                       ACCEPTED_RESULT=str(accepted), PROBE_MODE=mode,
                       PROBE_RESULT=str(out / f"{mode}-{index}.json"))
            process = subprocess.run(
                [str(binary), "-c", f"exec(open({str(driver)!r}).read())"],
                env=env, capture_output=True, text=True, timeout=120)
            (out / f"{mode}-{index}.log").write_text(process.stdout + process.stderr)
            process.check_returncode()
            if not (out / f"{mode}-{index}.json").is_file():
                raise RuntimeError("FreeCAD did not write the probe result; inspect log")
    assert (project / "script.json").read_bytes() == state_bytes
    receipt = {"accepted_revision": state["accepted_revision"],
               "accepted_digest": state["accepted_digest"],
               "project_state_unchanged": True, "files": {}}
    for path in sorted(out.iterdir()):
        if path.is_file():
            receipt["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
