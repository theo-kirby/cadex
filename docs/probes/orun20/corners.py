"""orun20 K2: a build's sharp-edge share and its shell panels' outline-corner radii.

usage: pixi run python docs/probes/orun20/corners.py PROJECT [--json OUT] [--panel NAME ...] [--part REGEX]

Reads only the project's accepted build: ``script.json`` names the accepted
revision, digest and attempt (its pinned staging, else the attempts under
``script_artifacts/<revision>/``), and the attempt whose ``result.json``
carries that digest holds every output's facts and BREP. Nothing in the project is written, and no engine is opened.

Two measures:

* **Sharp-edge share**, the concept sheet's ``sharp_outside_edge_share``
  (``CadexStudio.edge_proxy``, ADR-415): sharp convex edge length over
  total solid edge length, summed once per placement over the printed
  components (a placed output with no ``catalog``), world geometry left
  out. The per-output figures are the engine's own ``sharp_edges`` facts.
* **Outline corners** of every ``role="panel"`` component. A panel's skin
  is grown from its largest face across edges where the surface turns by
  less than ``SKIN_TURN_DEG`` into faces at least ``SKIN_WIDTH`` panel
  thicknesses wide (a face's width is its area over half its outer
  perimeter; the thickness is ``2 * volume / area``), so the rim, edge
  fillets and screw bosses are left out and a faceted skin's creases are
  crossed. The outline is the skin's boundary: edges with one skin face,
  in loops; a loop shorter than ``HOLE_MM`` is a screw hole and is skipped.
  On the outline:

  - a *sharp corner* is a vertex where the outline turns by more than
    ``CORNER_DEG`` in the skin's tangent plane (the mean of the skin
    normals there), so the bend of the panel's surface is not a corner;
  - a *rounded corner* is an outline edge whose smallest radius of
    geodesic curvature (the outline's curvature within the skin's tangent
    plane, sampled at ``SAMPLES`` points) is under ``ROUND_MM``.

  Per panel: its sharp corners (radius 0), its rounded corners with their
  radii, its smallest corner radius, and how many corners are under
  ``SMALL_MM``. A corner measured on a curve OCCT cannot evaluate is
  counted under ``unresolved``, never as round.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                                "build", "release", "lib"))
import FreeCAD  # noqa: E402,F401  (loads the Part module's runtime)
import Part  # noqa: E402

# After FreeCAD: its import resets the names __main__ already bound.
import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

SKIN_TURN_DEG = 50.0
SKIN_WIDTH = 1.5
HOLE_MM = 40.0
CORNER_DEG = 30.0
ROUND_MM = 50.0
SMALL_MM = 4.0
SAMPLES = 24


def accepted_attempt(project: Path) -> tuple[str, Path, dict]:
    state = json.loads((project / "script.json").read_text())
    revision, digest = state["accepted_revision"], state["accepted_digest"]
    # The manifest pins the accepted attempt; on a project's first accepted script its
    # directory is named for another revision (ADR-311), so the pin is read first.
    pinned = (state.get("accepted_attempt") or {}).get("staging")
    candidates = [project / pinned / "result.json"] if pinned else []
    candidates += sorted((project / "script_artifacts" / revision).glob("attempt-*/result.json"))
    for result in candidates:
        if not result.is_file():
            continue
        value = json.loads(result.read_text())
        if value.get("ok") and value.get("digest") == digest:
            return revision, result.parent, value
    raise SystemExit(f"{project}: no attempt under script_artifacts/{revision[:8]} carries digest {digest[:8]}")


def sharp_share(outputs: list[dict], part=None) -> dict:
    by_name = {item["name"]: item for item in outputs}
    world = set()
    for item in outputs:
        if item.get("type") == "assembly":
            world |= {str(row.get("name") if isinstance(row, dict) else row)
                      for row in item.get("world_geometry") or []}
    total = sharp = 0.0
    unresolved = printed = 0
    unmeasured = []
    for link in outputs:
        if link.get("type") != "component_link" or link["name"] in world:
            continue
        if part is not None and not part.search(link["name"]):
            continue
        source = by_name.get(link.get("source_output") or "") or {}
        if "catalog" in source:
            continue
        printed += 1
        facts = (source.get("facts") or {}).get("sharp_edges")
        if not isinstance(facts, dict):
            unmeasured.append(link["name"])
            continue
        total += float(facts["edge_length_mm"])
        sharp += float(facts["sharp_convex_length_mm"])
        unresolved += int(facts.get("unresolved_edges") or 0)
    return {"value": None if unmeasured else round(sharp / total if total else 0.0, 4),
            "edge_length_mm": round(total, 1), "sharp_convex_length_mm": round(sharp, 1),
            "printed_components": printed, "unresolved_edges": unresolved, "unmeasured": unmeasured}


def _width(face) -> float:
    perimeter = sum(edge.Length for edge in face.OuterWire.Edges)
    return face.Area / (perimeter / 2.0) if perimeter > 0 else 0.0


def _normal(face, point):
    u, v = face.Surface.parameter(point)
    return face.normalAt(u, v)


def _key(shape) -> int:
    return shape.hashCode()


class Index:
    """isSame-keyed lookups over a shape's sub-shapes (hashCode ignores orientation)."""

    def __init__(self):
        self.buckets: dict[int, list] = {}
        self.items: list = []

    def get(self, shape, add=True) -> int | None:
        bucket = self.buckets.setdefault(_key(shape), [])
        for position in bucket:
            if self.items[position].isSame(shape):
                return position
        if not add:
            return None
        self.items.append(shape)
        bucket.append(len(self.items) - 1)
        return len(self.items) - 1


def panel_corners(shape) -> dict:
    faces = list(shape.Faces)
    thickness = 2.0 * shape.Volume / shape.Area
    edges = Index()
    owners: dict[int, list[int]] = {}
    for f, face in enumerate(faces):
        for edge in face.Edges:
            e = edges.get(edge)
            if f not in owners.setdefault(e, []):
                owners[e].append(f)
    face_edges = {f: [edges.get(edge) for edge in face.Edges] for f, face in enumerate(faces)}
    widths = [_width(face) for face in faces]

    # Grow the skin from the largest face.
    turn = math.cos(math.radians(SKIN_TURN_DEG))
    start = max(range(len(faces)), key=lambda f: faces[f].Area)
    skin, queue = {start}, [start]
    while queue:
        f = queue.pop()
        for e in face_edges[f]:
            for g in owners[e]:
                if g in skin or widths[g] < SKIN_WIDTH * thickness:
                    continue
                edge = edges.items[e]
                try:
                    point = edge.valueAt(0.5 * (edge.FirstParameter + edge.LastParameter))
                    if _normal(faces[f], point).dot(_normal(faces[g], point)) < turn:
                        continue
                except Exception:
                    continue
                skin.add(g)
                queue.append(g)

    outline = {e: next(f for f in fs if f in skin) for e, fs in owners.items()
               if sum(1 for f in fs if f in skin) == 1}
    # Loops by shared vertices; a short loop is a screw hole.
    vertices = Index()
    at_vertex: dict[int, list[int]] = {}
    ends: dict[int, list[int]] = {}
    for e in outline:
        for vertex in edges.items[e].Vertexes:
            v = vertices.get(vertex)
            ends.setdefault(e, []).append(v)
            at_vertex.setdefault(v, []).append(e)
    loop_of, loops = {}, []
    for e in outline:
        if e in loop_of:
            continue
        members, stack = [], [e]
        loop_of[e] = len(loops)
        while stack:
            current = stack.pop()
            members.append(current)
            for v in ends.get(current, []):
                for other in at_vertex[v]:
                    if other not in loop_of:
                        loop_of[other] = len(loops)
                        stack.append(other)
        loops.append(members)
    kept = {e for members in loops
            if sum(edges.items[m].Length for m in members) >= HOLE_MM for e in members}
    holes = sum(1 for members in loops if sum(edges.items[m].Length for m in members) < HOLE_MM)

    sharp, rounded, unresolved = [], [], 0
    cos_corner = math.cos(math.radians(CORNER_DEG))
    for v, incident in at_vertex.items():
        incident = [e for e in incident if e in kept]
        if len(incident) != 2:
            continue
        point = vertices.items[v].Point
        try:
            tangents, normals = [], []
            for e in incident:
                edge = edges.items[e]
                near_first = (edge.valueAt(edge.FirstParameter) - point).Length <= (
                    edge.valueAt(edge.LastParameter) - point).Length
                t = edge.tangentAt(edge.FirstParameter if near_first else edge.LastParameter)
                # Both tangents pointing away from the vertex.
                tangents.append(t if near_first else t * -1.0)
                normals.append(_normal(faces[outline[e]], point))
            n = normals[0] + normals[1]
            if n.Length < 1e-9:
                n = normals[0]
            n.normalize()
            a, b = (t - n * t.dot(n) for t in tangents)
            if a.Length < 1e-9 or b.Length < 1e-9:
                unresolved += 1
                continue
            # A straight continuation has the away-tangents opposite (cos = -1).
            if -a.dot(b) / (a.Length * b.Length) < cos_corner:
                sharp.append([round(c, 1) for c in (point.x, point.y, point.z)])
        except Exception:
            unresolved += 1
    for e in kept:
        edge, face = edges.items[e], faces[outline[e]]
        smallest = math.inf
        where = None
        try:
            first, last = edge.FirstParameter, edge.LastParameter
            for i in range(SAMPLES + 1):
                u = first + (last - first) * i / SAMPLES
                try:
                    kappa = edge.curvatureAt(u)
                except Exception:
                    kappa = 0.0  # a straight edge has no principal normal
                if kappa <= 1e-9:
                    continue
                point = edge.valueAt(u)
                t = edge.tangentAt(u)
                principal = edge.normalAt(u)
                geodesic = abs(kappa * principal.dot(_normal(face, point).cross(t)))
                if geodesic > 1e-9 and 1.0 / geodesic < smallest:
                    smallest, where = 1.0 / geodesic, point
        except Exception:
            unresolved += 1
            continue
        if smallest < ROUND_MM:
            rounded.append({"radius_mm": round(smallest, 2),
                            "at_mm": [round(c, 1) for c in (where.x, where.y, where.z)]})
    rounded.sort(key=lambda row: row["radius_mm"])
    radii = [0.0] * len(sharp) + [row["radius_mm"] for row in rounded]
    return {
        "thickness_mm": round(thickness, 2),
        "faces": len(faces), "skin_faces": len(skin),
        "outline_loops": len(loops) - holes, "screw_holes_skipped": holes,
        "sharp_corners": len(sharp), "rounded_corners": len(rounded),
        "smallest_radius_mm": min(radii) if radii else None,
        "under_4mm": sum(1 for r in radii if r < SMALL_MM),
        "unresolved": unresolved,
        "sharp_at_mm": sharp, "rounded": rounded,
    }


def measure(project: Path, only=(), part=None) -> dict:
    revision, attempt, result = accepted_attempt(project)
    outputs = result["outputs"]
    by_name = {item["name"]: item for item in outputs}
    panels = {}
    for link in outputs:
        properties = (link.get("definition") or {}).get("properties") or {}
        if link.get("type") != "component_link" or properties.get("role") != "panel":
            continue
        name = link["source_output"]
        if only and name not in only:
            continue
        if part is not None and not part.search(link["name"]):
            continue
        shape = Part.Shape()
        shape.read(str(attempt / by_name[name]["artifact_path"]))
        panels[name] = panel_corners(shape)
    radii = [row["smallest_radius_mm"] for row in panels.values() if row["smallest_radius_mm"] is not None]
    return {
        "project": project.name, "revision": revision, "digest": result["digest"],
        "part": part.pattern if part is not None else None,
        "sharp_edge_share": sharp_share(outputs, part),
        "panels": len(panels),
        "smallest_corner_radius_mm": min(radii) if radii else None,
        "corners_under_4mm": sum(row["under_4mm"] for row in panels.values()),
        "sharp_corners": sum(row["sharp_corners"] for row in panels.values()),
        "rounded_corners": sum(row["rounded_corners"] for row in panels.values()),
        "unresolved": sum(row["unresolved"] for row in panels.values()),
        "parameters": {"skin_turn_deg": SKIN_TURN_DEG, "skin_width_t": SKIN_WIDTH, "hole_mm": HOLE_MM,
                       "corner_deg": CORNER_DEG, "round_mm": ROUND_MM, "small_mm": SMALL_MM,
                       "samples": SAMPLES},
        "by_panel": panels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--json", type=Path, help="write the whole measurement here")
    parser.add_argument("--panel", action="append", default=[], help="measure only this panel output")
    parser.add_argument("--part", help="measure only components whose name matches this regex, both "
                        "measures (case-insensitive; `cadex hero`'s head focus for the head)")
    args = parser.parse_args()
    part = re.compile(args.part, re.IGNORECASE) if args.part else None
    value = measure(args.project.expanduser().resolve(), args.panel, part)
    if args.json:
        args.json.write_text(json.dumps(value, indent=1) + "\n")
    share = value["sharp_edge_share"]
    print(f"{value['project']} {value['revision'][:8]}: sharp-edge share {share['value']:.1%} "
          f"({share['printed_components']} printed); {value['panels']} panels, "
          f"smallest outline-corner radius {value['smallest_corner_radius_mm']} mm, "
          f"{value['corners_under_4mm']} corners under 4 mm "
          f"({value['sharp_corners']} sharp, {value['rounded_corners']} rounded, "
          f"{value['unresolved']} unresolved)")
    print("| panel | t mm | sharp | rounded | smallest r mm | < 4 mm |")
    print("|---|---|---|---|---|---|")
    for name, row in value["by_panel"].items():
        print(f"| {name} | {row['thickness_mm']} | {row['sharp_corners']} | {row['rounded_corners']} | "
              f"{row['smallest_radius_mm']} | {row['under_4mm']} |")


if __name__ == "__main__":
    main()
