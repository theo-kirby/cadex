"""orun20 S1 lab: fillet the through-thickness corner edges of a built project's panels.

usage: pixi run python docs/probes/orun20/s1/fillet_lab.py PROJECT RADIUS [PANEL ...]

Reads the accepted build as corners.py does; for each panel takes the edges no
longer than three panel thicknesses with a vertex at a sharp outline corner,
and tries ``makeFillet`` at RADIUS, then 0.6 and 0.35 of it. Writes nothing.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "build", "release", "lib"))
sys.path.insert(0, os.path.join(HERE, ".."))
import FreeCAD  # noqa: E402
import Part  # noqa: E402

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import corners  # noqa: E402

project, radius, names = Path(sys.argv[1]), float(sys.argv[2]), sys.argv[3:]
_revision, attempt, result = corners.accepted_attempt(project)
by = {row["name"]: row for row in result["outputs"]}
names = names or [n for n in by if n.startswith("pnl_")]
for name in names:
    shape = Part.Shape()
    shape.read(str(attempt / by[name]["artifact_path"]))
    v0 = corners.panel_corners(shape)
    points = [FreeCAD.Vector(*p) for p in v0["sharp_at_mm"]]
    t = v0["thickness_mm"]
    picks = [e for e in shape.Edges if e.Length <= 3 * t and
             any(min((vx.Point - p).Length for vx in e.Vertexes) < 0.6 for p in points)]
    row = {"name": name, "sharp": v0["sharp_corners"], "edges": len(picks)}
    for r in (radius, radius * 0.6, radius * 0.35):
        try:
            filleted = shape.makeFillet(r, picks)
            if not filleted.isValid() or len(filleted.Solids) != 1:
                raise RuntimeError("invalid result")
            v = corners.panel_corners(filleted)
            row.update(radius=round(r, 2), sharp_after=v["sharp_corners"],
                       smallest_mm=v["smallest_radius_mm"])
            break
        except Exception as exc:
            row["refused_%g" % round(r, 2)] = str(exc).splitlines()[0][:60]
    print(json.dumps(row), flush=True)
