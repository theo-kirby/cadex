"""orun20 S1 lab: outline corners of every solid output of a project's newest attempt.

usage: pixi run python docs/probes/orun20/s1/measure_lab.py PROJECT

For lab projects that publish bare pieces (no role="panel" components), which
corners.py does not see. Uses corners.panel_corners on each output's BREP.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "build", "release", "lib"))
sys.path.insert(0, os.path.join(HERE, ".."))
import FreeCAD  # noqa: E402,F401
import Part  # noqa: E402

import glob  # noqa: E402
import json  # noqa: E402

import corners  # noqa: E402

attempt = sorted(glob.glob(os.path.join(sys.argv[1], "script_artifacts", "*", "attempt-*", "")))[-1]
result = json.load(open(os.path.join(attempt, "result.json")))
for output in result["outputs"]:
    if not output.get("artifact_path"):
        continue
    shape = Part.Shape()
    shape.read(os.path.join(attempt, output["artifact_path"]))
    if not shape.Solids:
        continue
    v = corners.panel_corners(shape)
    print(output["name"], {k: v[k] for k in ("thickness_mm", "sharp_corners", "rounded_corners",
                                             "smallest_radius_mm", "under_4mm", "unresolved")},
          [row["radius_mm"] for row in v["rounded"]])
