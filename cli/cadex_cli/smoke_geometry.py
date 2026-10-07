# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Trusted read-only BREP measurement child, like the CLI export adapter.

No project source is executed. Poses are absolute component transforms;
the source shape's own placement is composed, never replaced (ADR-242).
"""
import json
import math
import os
from pathlib import Path


def _box_gap(first, second):
    """The gap between two shapes' exact boxes, as the engine culls by (ADR-423)."""
    p, q = first.optimalBoundingBox(False, True), second.optimalBoundingBox(False, True)
    return math.sqrt(sum(max(0.0, lo_a - hi_b, lo_b - hi_a) ** 2 for lo_a, hi_a, lo_b, hi_b in (
        (p.XMin, p.XMax, q.XMin, q.XMax), (p.YMin, p.YMax, q.YMin, q.YMax),
        (p.ZMin, p.ZMax, q.ZMin, q.ZMax))))


def measure(plan):
    import FreeCAD as App
    import Part

    trace = json.loads(Path(plan["trace"]).read_text())
    shapes = {}
    for row in plan["geometry"]:
        shape = Part.Shape()
        shape.read(row["path"])
        if shape.isNull() or not shape.isValid() or not shape.Solids:
            raise ValueError("no valid exact solid for " + row["name"])
        shapes[row["name"]] = (shape, shape.Placement.copy())
    if not shapes or not trace:
        raise ValueError("empty geometry or trace is not a smoke check")
    names = sorted(shapes)
    expected = {tuple(sorted((r["first"], r["second"]))): r for r in plan["static"]}
    worst = {}
    for index, frame in enumerate(trace):
        for name, (shape, local) in shapes.items():
            pose = frame["placements"][name]
            position = App.Vector(*pose["position_mm"])
            rotation = App.Rotation(*pose["rotation_xyzw"])
            shape.Placement = App.Placement(position, rotation).multiply(local)
        for a, first in enumerate(names):
            for second in names[a + 1:]:
                left, right = shapes[first][0], shapes[second][0]
                # A disjoint AABB proves zero common volume; otherwise OCCT.
                volume = (float(left.common(right).Volume)
                          if left.BoundBox.intersect(right.BoundBox) else 0.0)
                if not math.isfinite(volume) or volume < -1e-6:
                    raise ValueError("invalid common volume")
                pair = (first, second)
                if index == 0:
                    static = expected.get(pair)
                    # Measured as the engine measured it (ADR-581): a culled
                    # row's distance is the exact boxes' gap (ADR-423), which
                    # must reach it; any other row is the shells' distance
                    # (ADR-425), which must equal it. A solid's distToShape
                    # asks OCCT's point classifier, which can call a far
                    # vertex inside and return 0.
                    if static is None or static.get("error"):
                        distance = math.nan
                    elif static.get("culled"):
                        distance = _box_gap(left, right)
                    else:
                        distance = float(Part.Compound(left.Shells).distToShape(Part.Compound(right.Shells))[0])
                    if (not math.isclose(volume, static["common_volume_mm3"] if static else math.nan,
                                         abs_tol=1e-5, rel_tol=1e-6) or
                            (distance < static["distance_mm"] - 1e-5 if static.get("culled") else
                             not math.isclose(distance, static["distance_mm"], abs_tol=1e-5, rel_tol=1e-6))):
                        raise ValueError(f"initial pose disagrees with published clearance: {pair}: "
                                         f"measured {distance:g} mm, published "
                                         f"{static.get('distance_mm') if static else None} mm")
                if pair not in worst or volume > worst[pair]["common_volume_mm3"]:
                    worst[pair] = {"first": first, "second": second,
                                   "common_volume_mm3": volume, "time_s": frame["time_s"]}
    failures = [r for r in worst.values() if r["common_volume_mm3"] > plan["maximum_volume_mm3"]]
    return {"pass": not failures, "source": "exact BREP solids at sampled MuJoCo poses",
            "initial_pose_agrees": True, "samples": len(trace), "pairs_checked": len(worst),
            "maximum_volume_mm3": plan["maximum_volume_mm3"], "failing": failures,
            "pairs": list(worst.values())}


if os.environ.get("CADEX_SMOKE_GEOMETRY_PLAN"):
    plan = json.loads(Path(os.environ["CADEX_SMOKE_GEOMETRY_PLAN"]).read_text())
    try:
        result = measure(plan)
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
    Path(plan["out"]).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
