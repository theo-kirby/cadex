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

#: How far frame 0 may put a part from the solved pose the engine published
#: its clearance at, in millimetres (ADR-584). Frame 0 is MuJoCo's pose of
#: the exported MJCF, whose writer keeps about six significant figures: the
#: excavator's bucket sits at x = 0.279177 m, 7e-5 mm from where the engine
#: put it. The export holds every body origin within
#: ``CadexDynamics.MJCF_POSE_TOLERANCE_MM`` (1e-2 mm) of the solved pose per
#: coordinate, so a part moves at most sqrt(3) times that, and a distance or
#: box gap between two parts by at most twice that. Anything farther is a
#: pose the trace got wrong, which is what this check is for (ADR-242).
MJCF_POSE_TOLERANCE_MM = 1.0e-2
INITIAL_POSE_TOLERANCE_MM = 2.0 * math.sqrt(3.0) * MJCF_POSE_TOLERANCE_MM


def _box_gap(p, q):
    """The gap between two exact boxes, as the engine culls by (ADR-423)."""
    return math.sqrt(sum(max(0.0, lo_a - hi_b, lo_b - hi_a) ** 2 for lo_a, hi_a, lo_b, hi_b in (
        (p.XMin, p.XMax, q.XMin, q.XMax), (p.YMin, p.YMax, q.YMin, q.YMax),
        (p.ZMin, p.ZMax, q.ZMin, q.ZMax))))


def _disagreement(static, distance, volume, common_area):
    """Why frame 0 disagrees with a published static row, or ``""``.

    The bound is :data:`INITIAL_POSE_TOLERANCE_MM` on a distance, and that
    shift swept over the overlap's boundary on a common volume (ADR-584). A
    culled row is a box-gap lower bound (ADR-423) and need only be reached.
    """
    if static is None or static.get("error"):
        return "no published measurement"
    shift = INITIAL_POSE_TOLERANCE_MM
    published = float(static["distance_mm"])
    if static.get("culled"):
        if not distance >= published - shift:
            return (f"measured box gap {distance!r} mm is below the published bound "
                    f"{published!r} mm by more than {shift:.3g} mm")
    elif not abs(distance - published) <= shift:
        return (f"measured {distance!r} mm, published {published!r} mm "
                f"(tolerance {shift:.3g} mm)")
    expected = float(static["common_volume_mm3"])
    allowed = max(1e-5, common_area * shift)
    if not abs(volume - expected) <= allowed:
        return (f"measured common volume {volume!r} mm3, published {expected!r} mm3 "
                f"(tolerance {allowed:.3g} mm3)")
    return ""


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
    # A bolt threaded into a printed part at the solved pose may share up to
    # its thread with it through the motion too (ADR-492, ADR-583).
    allowances = {tuple(sorted((r["first"], r["second"]))): float(r["allowance_mm3"])
                  for r in plan.get("thread_allowances", [])}
    worst = {}
    # A common volume is invariant under a rigid motion of both shapes, so a
    # pair whose relative pose is unchanged keeps the volume already measured
    # (ADR-582). Parts on one MuJoCo body differ by ~1e-18 frame to frame.
    measured = {}
    booleans = {"run": 0, "reused": 0}
    for index, frame in enumerate(trace):
        for name, (shape, local) in shapes.items():
            pose = frame["placements"][name]
            position = App.Vector(*pose["position_mm"])
            rotation = App.Rotation(*pose["rotation_xyzw"])
            shape.Placement = App.Placement(position, rotation).multiply(local)
        boxes = ({name: shape.optimalBoundingBox(False, True) for name, (shape, _) in shapes.items()}
                 if index == 0 else None)
        for a, first in enumerate(names):
            for second in names[a + 1:]:
                left, right = shapes[first][0], shapes[second][0]
                pair = (first, second)
                common_area = 0.0
                # A disjoint AABB proves zero common volume; otherwise OCCT.
                if not left.BoundBox.intersect(right.BoundBox):
                    volume = 0.0
                else:
                    relative = left.Placement.inverse().multiply(right.Placement).Matrix.A
                    seen = measured.get(pair)
                    if seen and max(abs(x - y) for x, y in zip(relative, seen[0])) <= 1e-9:
                        volume, common_area = seen[1], seen[2]
                        booleans["reused"] += 1
                    else:
                        common = left.common(right)
                        volume = float(common.Volume)
                        # A volume moves under a shift by at most its
                        # boundary's area times the shift (ADR-584).
                        common_area = float(common.Area) if volume > 0.0 else 0.0
                        booleans["run"] += 1
                        if not math.isfinite(volume) or volume < -1e-6:
                            raise ValueError("invalid common volume")
                        measured[pair] = (relative, volume, common_area)
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
                        distance = _box_gap(boxes[first], boxes[second])
                    else:
                        distance = float(Part.Compound(left.Shells).distToShape(Part.Compound(right.Shells))[0])
                    # Both within what the MJCF's pose can move them (ADR-584),
                    # not within float noise: frame 0 is the solved pose only
                    # to the file's six significant figures.
                    reason = _disagreement(static, distance, volume, common_area)
                    if reason:
                        raise ValueError(f"initial pose disagrees with published clearance: {pair}: {reason}")
                if pair not in worst or volume > worst[pair]["common_volume_mm3"]:
                    worst[pair] = {"first": first, "second": second,
                                   "common_volume_mm3": volume, "time_s": frame["time_s"],
                                   "common_area_mm2": common_area}
    threaded = 0
    for pair, row in worst.items():
        if pair in allowances:
            row["thread_allowance_mm3"] = allowances[pair]
            threaded += row["common_volume_mm3"] > plan["maximum_volume_mm3"]
    # A pair the simulator held in contact overlaps by its contact's depth
    # (ADR-599). A lens of thickness t has volume at most t times half its
    # surface, so the pair may share that much at the penetration
    # tolerance; a contact deeper than the tolerance holds none.
    depth = float(plan.get("contact_depth_mm") or 0.0)
    touching = {tuple(sorted((r["first"], r["second"]))) for r in plan.get("contacts", [])
                if 0.0 < float(r["depth_mm"]) <= depth}
    contact = 0
    for pair, row in worst.items():
        if pair in touching and row["common_volume_mm3"] > plan["maximum_volume_mm3"]:
            row["contact_allowance_mm3"] = 0.5 * row["common_area_mm2"] * depth
            contact += row["common_volume_mm3"] <= row["contact_allowance_mm3"]
    failures = [r for r in worst.values() if r["common_volume_mm3"] > max(
        plan["maximum_volume_mm3"], r.get("thread_allowance_mm3", 0.0),
        r.get("contact_allowance_mm3", 0.0))]
    return {"pass": not failures, "source": "exact BREP solids at sampled MuJoCo poses",
            "initial_pose_agrees": True, "initial_pose_tolerance_mm": INITIAL_POSE_TOLERANCE_MM,
            "samples": len(trace), "pairs_checked": len(worst), "booleans": booleans,
            "threaded": threaded, "in_contact": contact,
            "maximum_volume_mm3": plan["maximum_volume_mm3"], "failing": failures,
            "pairs": list(worst.values())}


if os.environ.get("CADEX_SMOKE_GEOMETRY_PLAN"):
    plan = json.loads(Path(os.environ["CADEX_SMOKE_GEOMETRY_PLAN"]).read_text())
    try:
        result = measure(plan)
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
    Path(plan["out"]).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
