# SPDX-License-Identifier: LGPL-2.1-or-later

"""Display tessellation + face/edge ID maps for one worker run (Phase 5.1).

Per BREP output the worker produces one ``cadex-tessellation-v1`` artifact:
a binary buffer (f32 vertices, u32 triangles, f32 edge vertices) plus a JSON
sidecar whose ``face_ranges``/``edge_polylines`` map triangle and polyline
spans back to the exact 1-based Face/Edge enumeration that ``face_details``
and ``edge_details`` report (cadex_part_worker.part_shape_facts). Mesh
outputs emit their own triangle buffer with a trivial one-range map.

Display artifacts are opt-in per request and digest-neutral: the content
digest is computed before any display artifact exists and never reads the
``display/`` directory.

This module never imports FreeCAD at module scope: the tessellation
functions operate on already-built shape objects, so the pure logic
(deflection resolution, request validation, buffer packing) is testable
under the stubbed pytest suite.
"""

from __future__ import annotations

import array
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

TESSELLATION_SCHEMA = "cadex-tessellation-v1"
DISPLAY_DIR_NAME = "display"

#: Relative deflection per quality preset (fraction of the bounding-box
#: diagonal). "standard" keeps interactive drags light on mid-size parts;
#: absolute deflection 0.3 on the 98-face filleted probe plate produced 409k
#: triangles, which the adaptive default must not reproduce. "draft" is the
#: progressive-display preset: shells request it while a slider drag is in
#: flight and re-request "standard" once the drag settles (Phase 6).
QUALITY_PRESETS: dict[str, float] = {
    "draft": 0.05,
    "coarse": 0.02,
    "standard": 0.005,
    "fine": 0.001,
}
DEFAULT_QUALITY = "standard"

#: Absolute clamp so degenerate bounding boxes cannot request absurd meshes.
MIN_DEFLECTION = 0.05
MAX_DEFLECTION = 5.0

_DISPLAY_REQUEST_KEYS = frozenset({"quality", "deflection", "edges"})


def validate_display_request(value: Any) -> dict[str, Any] | None:
    """Normalize one opt-in display request; None means display is off."""

    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("display must be an object with quality/deflection/edges.")
    unknown = set(map(str, value)) - _DISPLAY_REQUEST_KEYS
    if unknown:
        raise ValueError(
            f"display contains unknown fields: {sorted(unknown)}; "
            "allowed: quality, deflection, edges."
        )
    quality = str(value.get("quality") or DEFAULT_QUALITY)
    if quality not in QUALITY_PRESETS:
        raise ValueError(
            f"display.quality must be one of {sorted(QUALITY_PRESETS)}."
        )
    deflection = value.get("deflection")
    if deflection is not None:
        if isinstance(deflection, bool) or not isinstance(deflection, (int, float)):
            raise ValueError("display.deflection must be a positive number.")
        deflection = float(deflection)
        if not deflection > 0.0 or deflection != deflection or deflection == float("inf"):
            raise ValueError("display.deflection must be a finite positive number.")
    edges = value.get("edges", True)
    if not isinstance(edges, bool):
        raise ValueError("display.edges must be a boolean.")
    return {
        "quality": quality,
        "deflection": float(deflection) if deflection is not None else None,
        "edges": edges,
    }


def resolve_deflection(display: Mapping[str, Any], bbox_diagonal: float) -> float:
    """Adaptive deflection: clamp(rel × diagonal); explicit override wins."""

    override = display.get("deflection")
    if override is not None:
        return float(override)
    relative = QUALITY_PRESETS[str(display.get("quality") or DEFAULT_QUALITY)]
    diagonal = float(bbox_diagonal or 0.0)
    return max(MIN_DEFLECTION, min(MAX_DEFLECTION, relative * diagonal))


def _discretize_edge(edge: Any, deflection: float) -> list[Any]:
    try:
        points = edge.discretize(Deflection=float(deflection))
        if len(points) >= 2:
            return list(points)
    except Exception:
        pass
    try:
        points = edge.discretize(Number=2)
        if len(points) >= 2:
            return list(points)
    except Exception:
        pass
    # Seam/pole edges can be valid topology that OCC refuses to discretize;
    # fall back to the endpoint vertices so every edge keeps a polyline.
    vertices = list(getattr(edge, "Vertexes", []) or [])
    points = [vertex.Point for vertex in vertices[:2]]
    if len(points) == 1:
        points = points * 2
    if not points:
        raise ValueError("The edge has no vertices and could not be discretized.")
    return points


def tessellate_shape(
    shape: Any,
    deflection: float,
    *,
    include_edges: bool = True,
) -> dict[str, Any]:
    """Tessellate every face and discretize every edge of one BREP shape.

    ``face_ranges[i]`` is the ``[first_triangle, triangle_count]`` span of
    Face ``i+1``; ``edge_polylines[j]`` is the ``[first_point, point_count]``
    span of Edge ``j+1`` inside ``edge_vertices``. Reversed faces have their
    triangle winding flipped so triangle normals consistently face outward.
    """

    vertices: list[float] = []
    triangles: list[int] = []
    face_ranges: list[list[int]] = []
    for face in list(getattr(shape, "Faces", []) or []):
        face_vertices, face_triangles = face.tessellate(float(deflection))
        base = len(vertices) // 3
        start = len(triangles) // 3
        for point in face_vertices:
            vertices.extend((float(point.x), float(point.y), float(point.z)))
        flip = str(getattr(face, "Orientation", "") or "") == "Reversed"
        for tri in face_triangles:
            a, b, c = (int(tri[0]) + base, int(tri[1]) + base, int(tri[2]) + base)
            triangles.extend((a, c, b) if flip else (a, b, c))
        face_ranges.append([start, len(face_triangles)])
    edge_vertices: list[float] = []
    edge_polylines: list[list[int]] = []
    if include_edges:
        for edge in list(getattr(shape, "Edges", []) or []):
            points = _discretize_edge(edge, float(deflection))
            start = len(edge_vertices) // 3
            for point in points:
                edge_vertices.extend(
                    (float(point.x), float(point.y), float(point.z))
                )
            edge_polylines.append([start, len(points)])
    return {
        "vertices": vertices,
        "triangles": triangles,
        "face_ranges": face_ranges,
        "edge_vertices": edge_vertices,
        "edge_polylines": edge_polylines,
    }


def trivial_mesh_tessellation(points: Any, facets: Any) -> dict[str, Any]:
    """Mesh outputs already are triangles: one range covering the buffer."""

    vertices: list[float] = []
    for point in points:
        vertices.extend((float(point.x), float(point.y), float(point.z)))
    triangles: list[int] = []
    for facet in facets:
        triangles.extend((int(facet[0]), int(facet[1]), int(facet[2])))
    return {
        "vertices": vertices,
        "triangles": triangles,
        "face_ranges": [[0, len(triangles) // 3]],
        "edge_vertices": [],
        "edge_polylines": [],
    }


def _pack(values: list[float] | list[int], typecode: str) -> bytes:
    packed = array.array(typecode, values)
    if sys.byteorder != "little":
        packed.byteswap()
    return packed.tobytes()


def write_display_artifact(
    root: Path,
    stem: str,
    tessellation: Mapping[str, Any],
    *,
    deflection: float,
    quality: str,
    source_sha256: str,
) -> dict[str, Any]:
    """Write ``display/<stem>.tess.bin`` + sidecar; return the display record.

    Binary layout (little-endian, in order): f32 vertices, u32 triangles,
    f32 edge vertices. The sidecar carries the byte layout, counts, and the
    face/edge ID maps.
    """

    display_dir = Path(root) / DISPLAY_DIR_NAME
    display_dir.mkdir(parents=True, exist_ok=True)
    vertices = list(tessellation["vertices"])
    triangles = list(tessellation["triangles"])
    edge_vertices = list(tessellation["edge_vertices"])
    vertex_bytes = _pack(vertices, "f")
    triangle_bytes = _pack(triangles, "I")
    edge_bytes = _pack(edge_vertices, "f")
    binary_relative = Path(DISPLAY_DIR_NAME) / f"{stem}.tess.bin"
    sidecar_relative = Path(DISPLAY_DIR_NAME) / f"{stem}.tess.json"
    (Path(root) / binary_relative).write_bytes(
        vertex_bytes + triangle_bytes + edge_bytes
    )
    sidecar = {
        "schema": TESSELLATION_SCHEMA,
        "artifact_path": str(binary_relative),
        "byte_order": "little",
        "deflection": float(deflection),
        "quality": str(quality),
        "source_sha256": str(source_sha256),
        "counts": {
            "vertices": len(vertices) // 3,
            "triangles": len(triangles) // 3,
            "edge_vertices": len(edge_vertices) // 3,
            "faces": len(tessellation["face_ranges"]),
            "edges": len(tessellation["edge_polylines"]),
        },
        "layout": {
            "vertices": {"offset": 0, "bytes": len(vertex_bytes), "dtype": "f32"},
            "triangles": {
                "offset": len(vertex_bytes),
                "bytes": len(triangle_bytes),
                "dtype": "u32",
            },
            "edge_vertices": {
                "offset": len(vertex_bytes) + len(triangle_bytes),
                "bytes": len(edge_bytes),
                "dtype": "f32",
            },
        },
        "face_ranges": [list(item) for item in tessellation["face_ranges"]],
        "edge_polylines": [list(item) for item in tessellation["edge_polylines"]],
    }
    (Path(root) / sidecar_relative).write_text(
        json.dumps(sidecar, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return {
        "artifact_kind": "tessellation",
        "artifact_path": str(binary_relative),
        "sidecar_path": str(sidecar_relative),
        "deflection": float(deflection),
        "quality": str(quality),
        "counts": dict(sidecar["counts"]),
    }


def read_sidecar(path: Path) -> dict[str, Any]:
    """Read and structurally validate one tessellation sidecar."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != TESSELLATION_SCHEMA:
        raise ValueError(f"{path} is not a {TESSELLATION_SCHEMA} sidecar.")
    for key in ("counts", "layout", "face_ranges", "edge_polylines"):
        if key not in data:
            raise ValueError(f"{path} sidecar is missing {key!r}.")
    return data


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_display_artifacts(
    root: Path,
    outputs: list[dict[str, Any]],
    display: Mapping[str, Any],
) -> None:
    """Attach one display record per artifact-backed output (worker-side).

    Called after the content digest is computed, so display can never feed
    the digest. BREP outputs re-import their exported artifact (the exact
    bytes the digest covered); mesh outputs read their PLY artifact and emit
    a trivial one-range map. Outputs without a geometric artifact (solver
    diagnostics) carry ``display: None``.
    """

    root = Path(root)
    for index, item in enumerate(outputs):
        kind = str(item.get("artifact_kind") or "")
        artifact = str(item.get("artifact_path") or "")
        stem = f"display-{index:03d}"
        if kind == "brep" and artifact:
            import Part

            shape = Part.Shape()
            shape.importBrep(str(root / artifact))
            deflection = resolve_deflection(
                display, float(shape.BoundBox.DiagonalLength)
            )
            tessellation = tessellate_shape(
                shape,
                deflection,
                include_edges=bool(display.get("edges", True)),
            )
            item["display"] = write_display_artifact(
                root,
                stem,
                tessellation,
                deflection=deflection,
                quality=str(display.get("quality") or DEFAULT_QUALITY),
                source_sha256=_file_sha256(root / artifact),
            )
        elif kind == "mesh" and artifact:
            import Mesh

            mesh = Mesh.Mesh()
            mesh.read(Filename=str(root / artifact))
            points, facets = mesh.Topology
            tessellation = trivial_mesh_tessellation(points, facets)
            bounds = mesh.BoundBox
            deflection = resolve_deflection(
                display, float(getattr(bounds, "DiagonalLength", 0.0) or 0.0)
            )
            item["display"] = write_display_artifact(
                root,
                stem,
                tessellation,
                deflection=deflection,
                quality=str(display.get("quality") or DEFAULT_QUALITY),
                source_sha256=_file_sha256(root / artifact),
            )
        else:
            item["display"] = None
