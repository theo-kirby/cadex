# SPDX-License-Identifier: LGPL-2.1-or-later

"""Isolated OCC executor for the production Part XScript API."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from CadexSubshapeQuery import (
    SUBSHAPE_COLLECTIONS,
    SubshapeSelectionError,
    resolve_selected_subshapes,
)


class PartOperationError(ValueError):
    """Model-facing Part operation failure with precise operation context."""

    def __init__(
        self,
        message: str,
        *,
        stage: str = "part_operation",
        operation: str = "",
        parameter: str = "",
        correction: str = "",
        observed: Mapping[str, Any] | None = None,
    ) -> None:
        self.details = {
            "stage": str(stage or "part_operation"),
            **({"operation": str(operation)} if operation else {}),
            **({"parameter": str(parameter)} if parameter else {}),
            **({"observed": dict(observed)} if observed else {}),
            "correction": str(correction or "Inspect the rejected Part operation and change the exact stated cause before retrying."),
        }
        super().__init__(str(message))


MAX_SUBELEMENT_FACTS = 256
_REFERENCE_SHAPES: Mapping[tuple[str, str], Any] = MappingProxyType({})

#: Staging root whose ``assets`` directory ``shape_from_mesh`` imports from.
_ASSET_ROOT: Path | None = None
#: ``(payload, root) -> Mesh`` in canonical order, injected per request.
_MESH_INGEST: Any = None


def configure_part_assets(root: Path | None, mesh_ingest: Any = None) -> None:
    """Bind what ``shape_from_mesh`` needs, for one worker request.

    Two bindings, for two reasons.

    The **root** because ``build_mesh(payload, root)`` resolves
    ``mesh.import_file`` names against ``<root>/assets`` while
    ``build_part_shape(payload, *, diagnostics)`` has no root, and threading
    one in would touch every ``_shape`` call site in this module and the
    recursive payload chain in ``cadex_domain_worker``.

    The **mesh ingest callable** because this module is in cadexd's import
    closure and ``cadex_mesh_worker`` deliberately is not — domain workers
    are staged into the sandbox by filename, not imported (see
    ``cadex_tests/test_engine_purity_guardrails``). A static
    ``from cadex_mesh_worker import build_mesh`` here would pull the whole
    domain-worker stack into the service to serve a call the service never
    makes. The staged callers own that edge and hand the entry point in.

    Both mirror the module's existing idiom for host-staged material,
    :func:`configure_part_references` (ADR-043).
    """

    global _ASSET_ROOT, _MESH_INGEST
    _ASSET_ROOT = None if root is None else Path(root)
    _MESH_INGEST = mesh_ingest


def configure_part_references(root: Path, entries: list[dict[str, Any]]) -> None:
    """Load and authenticate host-staged BREP snapshots for one worker request."""

    import Part

    resolved_root = Path(root).resolve()
    shapes: dict[tuple[str, str], Any] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"document_references[{index}] must be an object.")
        document_uid = str(entry.get("document_uid") or "")
        object_name = str(entry.get("object_name") or "")
        key = (document_uid, object_name)
        if not all(key) or key in shapes:
            raise ValueError(
                f"document_references[{index}] has missing or duplicate identity."
            )
        path = (resolved_root / str(entry.get("artifact_path") or "")).resolve()
        if resolved_root not in path.parents or not path.is_file():
            raise ValueError(
                f"document_references[{index}] BREP is missing or outside worker staging."
            )
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        expected_digest = str(entry.get("brep_sha256") or "")
        if digest.hexdigest() != expected_digest:
            raise ValueError(
                f"document_references[{index}] BREP SHA-256 does not match the host snapshot."
            )
        shape = Part.Shape()
        shape.importBrep(str(path))
        if shape.isNull() or not shape.isValid():
            raise ValueError(f"document_references[{index}] is not a valid BREP shape.")
        expected_shape_type = str(entry.get("shape_type") or "")
        if expected_shape_type and str(shape.ShapeType) != expected_shape_type:
            raise ValueError(
                f"document_references[{index}] changed shape type during transfer: "
                f"expected {expected_shape_type}, received {shape.ShapeType}."
            )
        shapes[key] = shape
    global _REFERENCE_SHAPES
    _REFERENCE_SHAPES = MappingProxyType(shapes)


def configure_part_references_from_shapes(entries: list[dict[str, Any]]) -> None:
    """Bind component reference shapes that never left this process.

    The preview counterpart of :func:`configure_part_references`, and the
    difference is the whole point: that one authenticates a BREP by
    re-reading the file and matching its SHA-256 against what the host
    recorded, because the artifact *crossed a process boundary* and the shape
    the assembly solves must provably be the shape the part domain built. In
    a preview nothing crossed anything — the shape came out of
    ``build_part_shape`` a few microseconds earlier, in this interpreter — so
    the round trip would authenticate a byte stream against a hash of itself
    and charge an export plus an import for the privilege (ADR-055).

    Validity is still checked: a null or invalid shape must not reach the
    solver by either route.
    """

    shapes: dict[tuple[str, str], Any] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"preview_references[{index}] must be an object.")
        key = (
            str(entry.get("document_uid") or ""),
            str(entry.get("object_name") or ""),
        )
        if not all(key) or key in shapes:
            raise ValueError(
                f"preview_references[{index}] has missing or duplicate identity."
            )
        shape = entry.get("shape")
        if shape is None or shape.isNull() or not shape.isValid():
            raise ValueError(f"preview_references[{index}] is not a valid shape.")
        shapes[key] = shape
    global _REFERENCE_SHAPES
    _REFERENCE_SHAPES = MappingProxyType(shapes)


def detached_reference_shape(reference: Mapping[str, Any]) -> Any:
    """Return a copy of one authenticated host-staged reference shape.

    Shared domain workers use this narrow accessor instead of reading BREP
    artifacts again or reaching into the Part worker's private registry.
    """

    if not isinstance(reference, Mapping) or set(reference) != {
        "document_uid",
        "object_name",
    }:
        raise ValueError(
            "A staged shape reference must contain exactly document_uid and object_name."
        )
    key = (
        str(reference.get("document_uid") or ""),
        str(reference.get("object_name") or ""),
    )
    shape = _REFERENCE_SHAPES.get(key)
    if shape is None:
        raise ValueError(
            f"Reference {key[1]!r} was not authenticated from this worker request."
        )
    return shape.copy()


def _point_fact(value: Any) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def _bounds_fact(shape: Any) -> dict[str, list[float]]:
    bounds = shape.BoundBox
    return {
        "min": [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)],
        "max": [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)],
        "size": [float(bounds.XLength), float(bounds.YLength), float(bounds.ZLength)],
    }


def _geometry_type(value: Any) -> str:
    name = type(value).__name__
    return name.removeprefix("Part.") or "Unknown"


def _topology_geometry_type(value: Any, attribute: str) -> str:
    """Return an explicit type for valid degenerate OCC topology.

    Seam and pole edges can be topologically valid while FreeCAD raises
    ``TypeError: undefined curve type`` when their Curve property is read.
    Domain context and validation must preserve that fact instead of rejecting
    the entire BREP.
    """

    try:
        geometry = getattr(value, attribute)
    except (AttributeError, RuntimeError, TypeError):
        return "Undefined"
    return _geometry_type(geometry)


def _face_fact(index: int, face: Any) -> dict[str, Any]:
    center = getattr(face, "CenterOfMass", None)
    item: dict[str, Any] = {
        "index": index,
        "surface_type": _topology_geometry_type(face, "Surface"),
        "orientation": str(getattr(face, "Orientation", "") or ""),
        "area_mm2": float(face.Area),
        "center_mm": _point_fact(center) if center is not None else None,
        "bounds_mm": _bounds_fact(face),
        "edge_count": len(list(face.Edges)),
        "wire_count": len(list(face.Wires)),
    }
    try:
        u_min, u_max, v_min, v_max = (float(value) for value in face.ParameterRange)
        normal = face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
        item["normal_at_center"] = _point_fact(normal)
    except Exception:
        item["normal_at_center"] = None
    return item


def _edge_fact(index: int, edge: Any) -> dict[str, Any]:
    center = getattr(edge, "CenterOfMass", None)
    vertices = list(edge.Vertexes)
    return {
        "index": index,
        "curve_type": _topology_geometry_type(edge, "Curve"),
        "orientation": str(getattr(edge, "Orientation", "") or ""),
        "length_mm": float(edge.Length),
        "center_mm": _point_fact(center) if center is not None else None,
        "bounds_mm": _bounds_fact(edge),
        "endpoints_mm": [_point_fact(vertex.Point) for vertex in vertices[:2]],
        "closed": bool(edge.isClosed()),
    }


def part_shape_facts(
    shape: Any,
    *,
    max_subelements: int = MAX_SUBELEMENT_FACTS,
) -> dict[str, Any]:
    """Return bounded, JSON-safe topology facts for model inspection and selectors."""

    detail_limit = max(0, min(int(max_subelements), MAX_SUBELEMENT_FACTS))
    bounds = shape.BoundBox
    center = getattr(shape, "CenterOfMass", None)
    faces = list(getattr(shape, "Faces", []) or [])
    edges = list(getattr(shape, "Edges", []) or [])
    return {
        "shape_type": str(getattr(shape, "ShapeType", "") or ""),
        "valid": bool(shape.isValid()),
        "null": bool(shape.isNull()),
        "solids": len(list(getattr(shape, "Solids", []) or [])),
        "shells": len(list(getattr(shape, "Shells", []) or [])),
        "faces": len(faces),
        "wires": len(list(getattr(shape, "Wires", []) or [])),
        "edges": len(edges),
        "vertices": len(list(getattr(shape, "Vertexes", []) or [])),
        "length_mm": float(getattr(shape, "Length", 0.0) or 0.0),
        "area_mm2": float(getattr(shape, "Area", 0.0) or 0.0),
        "volume_mm3": float(getattr(shape, "Volume", 0.0) or 0.0),
        "center_of_mass_mm": _point_fact(center) if center is not None else None,
        "bounds_center_mm": [
            float((bounds.XMin + bounds.XMax) / 2.0),
            float((bounds.YMin + bounds.YMax) / 2.0),
            float((bounds.ZMin + bounds.ZMax) / 2.0),
        ],
        "bounds_mm": _bounds_fact(shape),
        "face_details": [
            _face_fact(index, face)
            for index, face in enumerate(faces[:detail_limit], start=1)
        ],
        "edge_details": [
            _edge_fact(index, edge)
            for index, edge in enumerate(edges[:detail_limit], start=1)
        ],
        "subelement_detail_limit": detail_limit,
        "subelement_details_truncated": bool(
            len(faces) > detail_limit or len(edges) > detail_limit
        ),
    }


def _error(operation: str, parameter: str, message: str) -> PartOperationError:
    selection_failure = parameter in {"edges", "faces", "where"}
    correction = (
        "Build the selector from the latest accepted face_details or edge_details "
        "for this exact shape — match on geometry_type, normal/direction, radius "
        "or near_point, and declare expected_count."
        if selection_failure
        else (
            f"Correct api.{operation} parameter {parameter!r} using the exact "
            "describe_api signature and current accepted shape facts, then retry "
            "against the failed working revision."
        )
    )
    return PartOperationError(
        f"api.{operation}: {parameter}: {message}",
        stage=("part_topology_selection" if selection_failure else "part_argument"),
        operation=operation,
        parameter=parameter,
        correction=correction,
    )


def _properties(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("properties")
    if not isinstance(value, dict):
        raise _error(
            str(payload.get("operation") or "<unknown>"), "properties", "must be an object"
        )
    return dict(value)


def _argument(
    payload: dict[str, Any],
    index: int,
    name: str,
    default: Any = None,
) -> Any:
    arguments = payload.get("arguments")
    if not isinstance(arguments, list):
        raise _error(str(payload.get("operation") or "<unknown>"), "arguments", "must be an array")
    if index < len(arguments):
        return arguments[index]
    return _properties(payload).get(name, default)


def _vector(operation: str, parameter: str, value: Any, *, nonzero: bool = False):
    import FreeCAD as App

    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise _error(operation, parameter, "expected [x, y, z]")
    try:
        result = App.Vector(*(float(item) for item in value))
    except (TypeError, ValueError) as exc:
        raise _error(operation, parameter, "coordinates must be finite numbers") from exc
    if not all(math.isfinite(item) for item in (result.x, result.y, result.z)):
        raise _error(operation, parameter, "coordinates must be finite numbers")
    if nonzero and result.Length <= 1.0e-12:
        raise _error(operation, parameter, "vector magnitude must be non-zero")
    return result


def _serialized(operation: str, parameter: str, value: Any) -> dict[str, Any]:
    required = {"domain", "operation", "output_type", "arguments", "properties"}
    if not isinstance(value, dict) or not required <= set(value):
        raise _error(operation, parameter, "expected a serialized Part api value")
    if value.get("domain") != "part":
        raise _error(operation, parameter, "value belongs to another XScript domain")
    return dict(value)


def _serialized_mesh(operation: str, parameter: str, value: Any) -> dict[str, Any]:
    """A serialized *mesh* value. Deliberately a sibling of :func:`_serialized`.

    ``_serialized``'s ``domain != "part"`` rejection is load-bearing at three
    dozen call sites; ``shape_from_mesh`` is the one operation that ingests
    another domain, so it gets its own guard rather than a relaxed shared one.
    """

    required = {"domain", "operation", "output_type", "arguments", "properties"}
    if not isinstance(value, dict) or not required <= set(value):
        raise _error(operation, parameter, "expected a serialized Mesh api value")
    if value.get("domain") != "mesh":
        raise _error(operation, parameter, "value did not come from the Mesh api")
    return dict(value)


def _shape(operation: str, parameter: str, value: Any):
    return build_part_shape(_serialized(operation, parameter, value))


def _shape_list(
    operation: str,
    parameter: str,
    value: Any,
    *,
    minimum: int = 1,
) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise _error(operation, parameter, f"expected at least {minimum} Part value(s)")
    return [_shape(operation, f"{parameter}[{index}]", item) for index, item in enumerate(value)]


def _selected_subshapes(
    operation: str,
    parameter: str,
    shape: Any,
    requested: Any,
    kind: str,
) -> list[Any]:
    """Resolve a geometric selector (or ``"all"``) to concrete subshapes.

    Phase 10b: the index form is gone. A failed selector reports the declared
    and actual counts plus the subshapes that *were* available, so the agent
    can re-query rather than guess an ordinal.
    """

    try:
        selected, _details = resolve_selected_subshapes(shape, kind, requested)
    except SubshapeSelectionError as exc:
        raise PartOperationError(
            f"api.{operation}: {parameter}: {exc}",
            stage="part_topology_selection",
            operation=operation,
            parameter=parameter,
            observed=exc.details,
            correction=(
                "Re-read the available subshapes in observed.available and write a "
                "selector that matches exactly expected_count of them; widen or "
                "narrow the fingerprint rather than guessing an ordinal."
            ),
        ) from exc
    except ValueError as exc:
        raise _error(operation, parameter, str(exc)) from exc
    return selected


def _refine(shape: Any, enabled: bool, *, operation: str) -> Any:
    if not enabled:
        return shape
    refined = shape.removeSplitter()
    if refined.isNull():
        raise PartOperationError(
            f"api.{operation}: refinement produced a null shape",
            stage="part_result_validation",
            operation=operation,
            correction=(
                "Set refine=False to inspect the unrefined boolean result, or repair "
                "the upstream overlap/tolerance that caused refinement to collapse it."
            ),
        )
    return refined


def _wire_from_shape(operation: str, parameter: str, shape: Any):
    import Part

    if str(getattr(shape, "ShapeType", "")) == "Wire":
        return shape
    edges = list(getattr(shape, "Edges", []) or [])
    if not edges:
        raise _error(operation, parameter, "value contains no edges")
    try:
        return Part.Wire(edges)
    except Exception as exc:
        raise _error(operation, parameter, f"edges do not form one ordered wire: {exc}") from exc


#: Sample count for the discrete bend-radius check on a fitted cable spline.
#: Fixed rather than length-derived so the verdict is the same every run.
_CABLE_BEND_SAMPLES = 97
#: Distinct lattice cells one route may probe before it refuses.
_CABLE_MAX_CELLS = 200000
#: Triangulation memo for cable obstacles, keyed by content and deflection.
_CABLE_TESSELLATION: dict[tuple[str, float], Any] = {}
_CABLE_TESSELLATION_LIMIT = 32
#: Bounding boxes of mesh obstacles, keyed by content. Materializing a mesh
#: value re-imports and canonicalizes its asset, which is the same work
#: whether the caller wants the triangles or six numbers -- and a harness
#: names the same handful of components on every one of its cables.
_CABLE_MESH_BOXES: dict[str, tuple[float, float, float, float, float, float]] = {}
_CABLE_MESH_BOX_LIMIT = 64


def _cable_bounding_box(value: Any) -> tuple[float, float, float, float, float, float]:
    box = value.BoundBox
    return (
        float(box.XMin),
        float(box.YMin),
        float(box.ZMin),
        float(box.XMax),
        float(box.YMax),
        float(box.ZMax),
    )


def _cable_obstacles(operation: str, entries: Any):
    """Resolve the ``avoid`` list into triangulated solids and mesh boxes.

    Part obstacles are returned as their triangulation.  ``Shape.isInside``
    was the obvious way to answer occupancy and it is the wrong one: measured
    against the drone frame — 219 faces, fused and filleted — it costs 3.3 ms
    a point, because OCC builds a fresh solid classifier per call, and the
    seven cables on that model spent 40 s in it.  One tessellation costs
    0.10 s and answers every cell in the corridor (ADR-056).

    Mesh obstacles collapse to their axis-aligned bounding box: the modules a
    harness runs between are box-shaped, and the obstacle where that would be
    badly wrong — a frame enclosing the whole model — is a ``part`` solid.
    """

    if not isinstance(entries, list):
        raise _error(operation, "avoid", "must be an array of Part or Mesh values")
    solids: list[tuple[str, str, Any]] = []
    boxes: list[tuple[float, float, float, float, float, float]] = []
    for index, entry in enumerate(entries):
        name = f"avoid[{index}]"
        if isinstance(entry, dict) and entry.get("domain") == "mesh":
            if _ASSET_ROOT is None or _MESH_INGEST is None:
                raise PartOperationError(
                    f"api.{operation}: this worker request has no staged mesh kernel "
                    "to materialize a mesh obstacle with",
                    stage="part_contract",
                    operation=operation,
                    parameter=name,
                    correction=(
                        f"Build {operation} from the project script surface; that "
                        "is the surface that stages the project's mesh assets."
                    ),
                )
            mesh_key = _memo_key(entry)
            box = _CABLE_MESH_BOXES.get(mesh_key)
            if box is None:
                box = _cable_bounding_box(
                    _MESH_INGEST(_serialized_mesh(operation, name, entry), _ASSET_ROOT)
                )
                if len(_CABLE_MESH_BOXES) < _CABLE_MESH_BOX_LIMIT:
                    _CABLE_MESH_BOXES[mesh_key] = box
            boxes.append(box)
            continue
        # Deliberately not resolved here: on a tessellation memo hit the
        # shape is never needed, and building it is a copy of a fused,
        # filleted solid per cable.
        solids.append((_memo_key(entry), name, entry))
    return solids, boxes


def _cable_solid_cells(
    solids: list[tuple[str, str, Any]],
    *,
    operation: str,
    origin: list[float],
    far: list[float],
    cell: float,
    counts: tuple[int, int, int],
) -> set[tuple[int, int, int]]:
    """Rasterise the obstacle surfaces into the routing lattice.

    The **surface**, not the volume, and that is sufficient: a closed shell
    rasterised at half a cell leaves no gap a 26-connected step can cross, so
    an obstacle's interior is unreachable without passing through cells this
    marks.  It also makes the clearance dilation mean the right thing, since
    clearance is measured from a surface.

    Triangles are sampled on a barycentric grid at half a cell rather than
    having their bounding box filled: one triangle can cover a whole planar
    face, and filling its box would wall off the room in front of it.
    """

    marked: set[tuple[int, int, int]] = set()
    step = cell * 0.5
    for key, name, entry in solids:
        deflection = max(cell / 4.0, 0.01)
        memo_key = (key, deflection)
        triangulation = _CABLE_TESSELLATION.get(memo_key)
        if triangulation is None:
            triangulation = _shape(operation, name, entry).tessellate(deflection)
            if len(_CABLE_TESSELLATION) < _CABLE_TESSELLATION_LIMIT:
                _CABLE_TESSELLATION[memo_key] = triangulation
        points, facets = triangulation
        for facet in facets:
            first, second, third = points[facet[0]], points[facet[1]], points[facet[2]]
            corners = (first, second, third)
            if any(
                max(corner[axis] for corner in corners) < origin[axis]
                or min(corner[axis] for corner in corners) > far[axis]
                for axis in range(3)
            ):
                continue
            longest = max(
                (second - first).Length, (third - second).Length, (first - third).Length
            )
            steps = max(1, int(math.ceil(longest / step)))
            for along in range(steps + 1):
                for across in range(steps + 1 - along):
                    u, v = along / steps, across / steps
                    cell_index = tuple(
                        int(
                            (
                                first[axis]
                                + (second[axis] - first[axis]) * u
                                + (third[axis] - first[axis]) * v
                                - origin[axis]
                            )
                            / cell
                        )
                        for axis in range(3)
                    )
                    if all(0 <= cell_index[axis] < counts[axis] for axis in range(3)):
                        marked.add(cell_index)  # type: ignore[arg-type]
    return marked


def _cable_min_bend_radius(points: list[Any]) -> float:
    """Tightest three-point circumradius along a sampled polyline.

    Discrete on purpose: it depends only on the sampled points, so it says
    the same thing on every kernel build, where a curvature query need not.
    """

    tightest = math.inf
    for index in range(len(points) - 2):
        first, middle, last = points[index], points[index + 1], points[index + 2]
        legs = (
            (middle - first).Length,
            (last - middle).Length,
            (first - last).Length,
        )
        twice_area = (middle - first).cross(last - first).Length
        if twice_area <= 1.0e-12 or min(legs) <= 1.0e-12:
            # Collinear samples bend not at all: infinite radius, no verdict.
            continue
        tightest = min(tightest, legs[0] * legs[1] * legs[2] / (2.0 * twice_area))
    return tightest


def _route_corridor(
    *,
    operation: str,
    anchor_start: Any,
    anchor_end: Any,
    gauge: float,
    clearance: float,
    cell_mm: float,
    solids: list[Any],
    boxes: list[Any],
):
    """The lattice one route is searched on: resolution, corridor, occupancy.

    Shared by ``part.cable`` and ``part.bundle`` (ADR-057).  A bundle passes
    its *outer* diameter as ``gauge``, so the corridor and the clearance
    dilation account for the whole lay rather than one conductor.

    Returns ``(cell, low, high, counts, occupied)`` — everything
    ``CadexRouting.route_path`` needs but the two ports themselves.
    """

    span = (anchor_end - anchor_start).Length
    # The resolution the route is searched at.  One cell per gauge (or per
    # clearance, whichever is coarser) resolves the gaps a wire of this size
    # can actually use, and the cost is cubic in the reciprocal: halving it
    # was measured at 6x the routing time on the drone's motor leads.
    cell = cell_mm or max(gauge, clearance, span / 400.0)
    # The corridor: the two anchors, opened out far enough that a detour has
    # somewhere to go, and no further -- this box is what bounds the search.
    margin = clearance + gauge + max(4.0 * cell, span / 3.0)
    low = [
        min(anchor_start[axis], anchor_end[axis]) - margin for axis in range(3)
    ]
    high = [
        max(anchor_start[axis], anchor_end[axis]) + margin for axis in range(3)
    ]

    counts = tuple(
        max(1, int(math.ceil((high[axis] - low[axis]) / cell))) for axis in range(3)
    )
    solid_cells = _cable_solid_cells(
        solids,
        operation=operation,
        origin=low,
        far=high,
        cell=cell,
        counts=counts,  # type: ignore[arg-type]
    )

    def occupied(i: int, j: int, k: int) -> bool:
        if (i, j, k) in solid_cells:
            return True
        x = low[0] + (i + 0.5) * cell
        y = low[1] + (j + 0.5) * cell
        z = low[2] + (k + 0.5) * cell
        for box in boxes:
            if box[0] <= x <= box[3] and box[1] <= y <= box[4] and box[2] <= z <= box[5]:
                return True
        return False

    return cell, low, high, counts, occupied


#: The correction ``part.cable`` offers when a route bends tighter than the
#: conductor tolerates.  A bundle names its own cause instead (ADR-057).
_BEND_CORRECTION = (
    "The corridor forces a kink this conductor cannot take. "
    "Raise cell_mm so the route is smoother, add slack, or move "
    "a port so the run does not have to turn so sharply."
)
#: ...and when the sweep itself fails.
_SWEEP_CORRECTION = (
    "The route turns tighter than the gauge can be swept through. "
    "Reduce gauge_mm, raise cell_mm for a smoother route, or declare "
    "min_bend_radius_mm so the route is rejected before the sweep."
)


def _sweep_conductor(
    waypoints: list[Any],
    *,
    operation: str,
    gauge: float,
    centre: Any,
    min_bend_radius_mm: Any = None,
    bend_samples: int | None = None,
    bend_correction: str = _BEND_CORRECTION,
    sweep_correction: str = _SWEEP_CORRECTION,
    context: str = "",
):
    """Fit a spline through ``waypoints`` and sweep a round conductor along it.

    Shared by ``part.cable`` and ``part.bundle`` (ADR-057).  ``centre`` is
    where the profile circle sits — the run's first point.

    The sweep runs in OCC's **true** Frenet mode.  The section is a circle
    centred on the spine, so in principle the mode cannot matter; in practice
    corrected Frenet collapses helical spines, measured at up to 51% of the
    volume missing on a six-way lay while still returning one closed, valid
    solid.  True Frenet held every measured case to within 0.62%.
    """

    import FreeCAD as App
    import Part

    curve = Part.BSplineCurve()
    curve.interpolate(
        Points=[App.Vector(*point) for point in waypoints],
        PeriodicFlag=False,
        Tolerance=1.0e-7,
    )
    path_edge = curve.toShape()

    if min_bend_radius_mm is not None:
        samples = path_edge.discretize(
            Number=bend_samples if bend_samples is not None else _CABLE_BEND_SAMPLES
        )
        tightest = _cable_min_bend_radius(list(samples))
        if tightest < float(min_bend_radius_mm):
            raise PartOperationError(
                f"api.{operation}: the route bends to {tightest:.3f} mm radius, "
                f"tighter than the declared minimum of "
                f"{float(min_bend_radius_mm):.3f} mm{context}",
                stage="part_routing",
                operation=operation,
                parameter="min_bend_radius_mm",
                observed={
                    "min_bend_radius_mm": float(min_bend_radius_mm),
                    "route_bend_radius_mm": tightest,
                },
                correction=bend_correction,
            )

    try:
        tangent = curve.tangent(curve.FirstParameter)[0]
    except Exception:
        tangent = App.Vector(*waypoints[1]) - App.Vector(*waypoints[0])
    profile = Part.Wire([Part.makeCircle(gauge / 2.0, centre, tangent)])
    result = Part.Wire([path_edge]).makePipeShell([profile], True, True)
    if result is None or result.isNull() or not result.Solids:
        raise PartOperationError(
            f"api.{operation}: the conductor could not be swept along the "
            f"routed path{context}",
            stage="part_kernel",
            operation=operation,
            correction=sweep_correction,
        )
    return result


def _build_cable(payload: dict[str, Any], properties: dict[str, Any]):
    """Search a route between two ports and sweep the conductor along it.

    The search lives in ``CadexRouting`` and the budget is why it lives in
    this process at all: the script sandbox meters every traced line against
    a 400k operation budget and explicitly declines to trace frames outside
    the script, so an A* written in the script would spend budget per node
    while the same search here costs one operation (ADR-056).
    """

    import CadexRouting

    operation = "cable"
    start = _argument(payload, 0, "start")
    end = _argument(payload, 1, "end")
    if not isinstance(start, list) or len(start) != 2:
        raise _error(operation, "start", "expected a (point, direction) pair")
    if not isinstance(end, list) or len(end) != 2:
        raise _error(operation, "end", "expected a (point, direction) pair")
    start_point = _vector(operation, "start[0]", start[0])
    start_dir = _vector(operation, "start[1]", start[1], nonzero=True)
    end_point = _vector(operation, "end[0]", end[0])
    end_dir = _vector(operation, "end[1]", end[1], nonzero=True)

    gauge = float(properties.get("gauge_mm", 0.0))
    clearance = float(properties.get("clearance_mm", 1.0))
    slack = float(properties.get("slack", 1.05))
    if gauge <= 0.0:
        raise _error(operation, "gauge_mm", "must be greater than zero")
    standoff = clearance + gauge / 2.0
    solids, boxes = _cable_obstacles(operation, properties.get("avoid", []))

    # Not Vector.normalize(), which normalizes in place: start_dir is handed
    # to the router afterwards and must still be the direction it was given.
    anchor_start = start_point + start_dir * (standoff / start_dir.Length)
    anchor_end = end_point + end_dir * (standoff / end_dir.Length)
    cell, low, high, counts, occupied = _route_corridor(
        operation=operation,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
        gauge=gauge,
        clearance=clearance,
        cell_mm=float(properties.get("cell_mm", 0.0)),
        solids=solids,
        boxes=boxes,
    )

    try:
        waypoints = CadexRouting.route_path(
            (start_point.x, start_point.y, start_point.z),
            (start_dir.x, start_dir.y, start_dir.z),
            (end_point.x, end_point.y, end_point.z),
            (end_dir.x, end_dir.y, end_dir.z),
            occupied=occupied,
            cell_mm=cell,
            clearance_mm=clearance,
            standoff_mm=standoff,
            slack=slack,
            bounds=(low, high),
            max_cells=_CABLE_MAX_CELLS,
        )
    except CadexRouting.RoutingError as exc:
        corrections = {
            "blocked": (
                "Nothing connects the two ports at this clearance: lower "
                "clearance_mm, remove an obstacle from avoid that does not "
                "really block the run, or move a port to a face the wire can "
                "actually leave from."
            ),
            "budget": (
                "The search ran out of cells before it found a way through. "
                "Raise cell_mm to search coarsely, or shorten the run by "
                "routing through an intermediate port."
            ),
            "bounds": (
                "The two ports do not describe a routable run. Check that each "
                "port's direction points away from its component and that the "
                "two points are not the same point."
            ),
        }
        raise PartOperationError(
            f"api.cable: {exc}",
            stage="part_routing",
            operation=operation,
            observed={"reason": exc.reason, **exc.observed},
            correction=corrections.get(exc.reason, corrections["bounds"]),
        ) from exc

    return _sweep_conductor(
        waypoints,
        operation=operation,
        gauge=gauge,
        centre=start_point,
        min_bend_radius_mm=properties.get("min_bend_radius_mm"),
    )


#: Shared centrelines, keyed on a bundle payload with the per-conductor
#: fields stripped -- see ``_bundle_route_key``. Cleared per request with
#: ``_SHAPE_MEMO``: this holds a *route*, and a route that leaked into another
#: request would place a wire using the previous request's obstacles under a
#: self-consistent digest, which is the worst failure this codebase can have.
_BUNDLE_ROUTES: dict[str, tuple[tuple[float, float, float], ...]] = {}
_BUNDLE_ROUTE_LIMIT = 32

#: Bundle payload fields that pick a conductor out of a lay rather than
#: describe the lay. Everything else feeds the shared search, so this is a
#: deny-list on purpose: forgetting a future cosmetic field costs one wasted
#: search, forgetting a future route-affecting one would return the wrong wire.
_BUNDLE_PER_CONDUCTOR_FIELDS = ("conductor", "label")


def _bundle_route_key(payload: dict[str, Any]) -> str:
    """Content identity for the *route* a bundle's conductors share."""

    properties = {
        name: value
        for name, value in _properties(payload).items()
        if name not in _BUNDLE_PER_CONDUCTOR_FIELDS
    }
    return _memo_key({**payload, "properties": properties})


def _bundle_ports(operation: str, connections: Any) -> list[list[list[Any]]]:
    """Validate the ``(start_port, end_port)`` pairs into vectors."""

    if not isinstance(connections, list) or len(connections) < 2:
        raise _error(
            operation,
            "connections",
            "expected at least two (start_port, end_port) pairs",
        )
    result: list[list[list[Any]]] = []
    for index, pair in enumerate(connections):
        name = f"connections[{index}]"
        if not isinstance(pair, list) or len(pair) != 2:
            raise _error(operation, name, "expected a (start_port, end_port) pair")
        ends: list[list[Any]] = []
        for side, port in (("0", pair[0]), ("1", pair[1])):
            if not isinstance(port, list) or len(port) != 2:
                raise _error(
                    operation, f"{name}[{side}]", "expected a (point, direction) pair"
                )
            ends.append(
                [
                    _vector(operation, f"{name}[{side}][0]", port[0]),
                    _vector(operation, f"{name}[{side}][1]", port[1], nonzero=True),
                ]
            )
        result.append(ends)
    return result


def _bundle_gather(operation: str, ports: list[list[Any]], side: str):
    """Where the bundle leaves one end, and which way.

    The point is the centroid of that end's ports; the direction is the sum of
    their *unit* directions, so a port whose direction vector happens to be
    long does not steer the whole bundle.  Ports that disagree by more than
    about sixty degrees on average have no common way out, and that is refused
    here rather than left to produce a meaningless average.
    """

    import FreeCAD as App

    count = len(ports)
    point = App.Vector(0.0, 0.0, 0.0)
    direction = App.Vector(0.0, 0.0, 0.0)
    for port in ports:
        point = point + port[0]
        direction = direction + port[1] * (1.0 / port[1].Length)
    point = point * (1.0 / count)
    agreement = direction.Length / count
    if agreement < 0.5:
        raise PartOperationError(
            f"api.{operation}: the {side} ports do not agree on a direction to "
            f"leave along (mean agreement {agreement:.3f})",
            stage="part_routing",
            operation=operation,
            parameter="connections",
            observed={"end": side, "direction_agreement": agreement},
            correction=(
                "A bundle leaves each end as one run, so its ports have to face "
                "roughly the same way. Give them a common outward direction, or "
                "route these wires as separate part.cable calls."
            ),
        )
    return point, direction * (1.0 / direction.Length)


def _build_bundle(payload: dict[str, Any], properties: dict[str, Any]):
    """Route one path for several conductors and sweep the requested one.

    One search serves the whole bundle: the route is memoised on the payload
    with the per-conductor fields stripped, so N conductors cost one A* and N
    sweeps rather than N of each (ADR-057).  The corridor is searched at the
    bundle's *outer* diameter, because what has to fit through a gap is the
    lay, not one wire.
    """

    import FreeCAD as App
    import Part

    import CadexBundle
    import CadexRouting

    operation = "bundle"
    connections = _bundle_ports(operation, _argument(payload, 0, "connections"))
    count = len(connections)
    conductor = int(properties.get("conductor", 0))
    if not 0 <= conductor < count:
        raise _error(
            operation,
            "conductor",
            f"must index one of the {count} declared connections",
        )

    gauge = float(properties.get("gauge_mm", 0.0))
    if gauge <= 0.0:
        raise _error(operation, "gauge_mm", "must be greater than zero")
    style = str(properties.get("style") or "twisted")
    if style not in CadexBundle.STYLES:
        raise _error(operation, "style", "expected 'twisted' or 'flat'")
    clearance = float(properties.get("clearance_mm", 1.0))
    slack = float(properties.get("slack", 1.05))
    left_handed = bool(properties.get("left_handed", False))
    twist_pitch = properties.get("twist_pitch_mm")
    twist_pitch = None if twist_pitch is None else float(twist_pitch)
    spacing = properties.get("spacing_mm")
    spacing = None if spacing is None else float(spacing)
    up = properties.get("up")
    up = (0.0, 0.0, 1.0) if up is None else (float(up[0]), float(up[1]), float(up[2]))

    def _refuse(exc: "CadexBundle.BundleError"):
        corrections = {
            "pitch": (
                "The conductors cannot be laid this tightly: a lay only exists "
                "when twist_pitch_mm exceeds the conductor count times gauge_mm. "
                "Raise twist_pitch_mm, reduce gauge_mm, or use style='flat'."
            ),
            "count": (
                "A bundle lays two or more conductors around a shared route; a "
                "single wire is part.cable."
            ),
            "radius": (
                "No lay radius keeps these conductors apart. Raise "
                "twist_pitch_mm or reduce gauge_mm."
            ),
            "path": (
                "The shared route is too short or too coarse to lay conductors "
                "along. Raise cell_mm, or move the ports further apart."
            ),
        }
        return PartOperationError(
            f"api.{operation}: {exc}",
            stage="part_routing",
            operation=operation,
            observed={"reason": exc.reason, **exc.observed},
            correction=corrections.get(exc.reason, corrections["path"]),
        )

    try:
        diameter = CadexBundle.outer_diameter(
            gauge,
            count=count,
            style=style,
            twist_pitch_mm=twist_pitch,
            spacing_mm=spacing,
        )
    except CadexBundle.BundleError as exc:
        raise _refuse(exc) from exc

    start_point, start_dir = _bundle_gather(
        operation, [pair[0] for pair in connections], "start"
    )
    end_point, end_dir = _bundle_gather(
        operation, [pair[1] for pair in connections], "end"
    )
    reach = (end_point - start_point).Length
    if reach <= 1.0e-9:
        raise _error(
            operation,
            "connections",
            "the two ends gather to the same point, so there is no run to route",
        )

    # Two different lengths, deliberately not the same number.
    #
    # The *stand-off* is how far off the surface the search starts, and it is
    # what ``part.cable`` computes as clearance + half the wire: far enough to
    # be clear of the component, no further. Push it out and the route has to
    # come back in, which on a short run is a hairpin the sweep cannot turn.
    #
    # The *breakout* is the arc over which the conductors fan out from their
    # own pads into the lay. It wants to be generous -- a half-cosine that
    # travels the bundle's width in less than about that width is a corner --
    # but never more than the run can spare, since two breakouts meeting in
    # the middle would leave nothing actually laid up as a bundle.
    standoff = clearance + diameter / 2.0
    breakout = properties.get("breakout_mm")
    if breakout is None:
        breakout = min(1.5 * diameter + clearance, reach / 3.0)
    else:
        breakout = float(breakout)

    route_key = _bundle_route_key(payload)
    shared = _BUNDLE_ROUTES.get(route_key)
    if shared is None:
        solids, boxes = _cable_obstacles(operation, properties.get("avoid", []))
        anchor_start = start_point + start_dir * standoff
        anchor_end = end_point + end_dir * standoff
        cell, low, high, _counts, occupied = _route_corridor(
            operation=operation,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
            gauge=diameter,
            clearance=clearance,
            cell_mm=float(properties.get("cell_mm", 0.0)),
            solids=solids,
            boxes=boxes,
        )
        try:
            waypoints = CadexRouting.route_path(
                (start_point.x, start_point.y, start_point.z),
                (start_dir.x, start_dir.y, start_dir.z),
                (end_point.x, end_point.y, end_point.z),
                (end_dir.x, end_dir.y, end_dir.z),
                occupied=occupied,
                cell_mm=cell,
                # The lattice keeps the *centreline* this far from material, so
                # it has to hold the whole lay, not just the clearance -- the
                # same figure the stand-off uses, for the same reason.
                clearance_mm=standoff,
                standoff_mm=standoff,
                slack=slack,
                bounds=(low, high),
                max_cells=_CABLE_MAX_CELLS,
            )
        except CadexRouting.RoutingError as exc:
            corrections = {
                "blocked": (
                    "Nothing connects the two ends at this clearance with room "
                    f"for a {diameter:.2f} mm bundle: lower clearance_mm, reduce "
                    "the conductor count or gauge_mm, remove an obstacle from "
                    "avoid that does not really block the run, or move a port."
                ),
                "budget": (
                    "The search ran out of cells before it found a way through. "
                    "Raise cell_mm to search coarsely, or shorten the run by "
                    "routing through an intermediate port."
                ),
                "bounds": (
                    "The two ends do not describe a routable run. Check that "
                    "each port's direction points away from its component and "
                    "that the two ends are not at the same point."
                ),
            }
            # The label is in the message, not only in observed: a harness
            # declares many bundles, and a refusal that does not say which
            # one sends you reading every port literal in the script.
            named = str(properties.get("label") or "")
            raise PartOperationError(
                f"api.{operation}: {exc}"
                + (f" (bundle {named!r})" if named else ""),
                stage="part_routing",
                operation=operation,
                observed={
                    "reason": exc.reason,
                    "bundle_diameter_mm": diameter,
                    "breakout_mm": breakout,
                    "label": named,
                    **exc.observed,
                },
                correction=corrections.get(exc.reason, corrections["bounds"]),
            ) from exc

        # The shared span runs gather point to gather point -- the whole run,
        # ports included. Each conductor fans out from its own port into the
        # lay over the breakout, so the ends are a blend rather than a stub,
        # and there is no corner anywhere for the sweep to turn.
        span_points: list[tuple[float, float, float]] = []
        for candidate in [
            tuple(float(axis) for axis in point) for point in waypoints
        ]:
            if span_points and (
                (candidate[0] - span_points[-1][0]) ** 2
                + (candidate[1] - span_points[-1][1]) ** 2
                + (candidate[2] - span_points[-1][2]) ** 2
            ) <= 1.0e-12:
                continue
            span_points.append(candidate)  # type: ignore[arg-type]
        while len(span_points) < 3:
            if len(span_points) < 2:
                raise _error(
                    operation,
                    "connections",
                    "the routed span collapsed to a point; raise breakout_mm or "
                    "move the two ends apart",
                )
            span_points.insert(
                1,
                tuple(  # type: ignore[arg-type]
                    (span_points[0][axis] + span_points[1][axis]) / 2.0
                    for axis in range(3)
                ),
            )

        spine = Part.BSplineCurve()
        spine.interpolate(
            Points=[App.Vector(*point) for point in span_points],
            PeriodicFlag=False,
            Tolerance=1.0e-7,
        )
        samples = CadexBundle.sample_count(
            spine.length(),
            style=style,
            twist_pitch_mm=twist_pitch,
            cell_mm=cell,
        )
        shared = tuple(
            (float(point.x), float(point.y), float(point.z))
            for point in spine.toShape().discretize(Number=samples)
        )
        if len(_BUNDLE_ROUTES) < _BUNDLE_ROUTE_LIMIT:
            _BUNDLE_ROUTES[route_key] = shared

    try:
        lay = CadexBundle.conductor_paths(
            shared,
            count=count,
            style=style,
            gauge_mm=gauge,
            spacing_mm=spacing,
            twist_pitch_mm=twist_pitch,
            left_handed=left_handed,
            up=up,
            start_points=[
                (pair[0][0].x, pair[0][0].y, pair[0][0].z) for pair in connections
            ],
            end_points=[
                (pair[1][0].x, pair[1][0].y, pair[1][0].z) for pair in connections
            ],
            breakout_mm=breakout,
        )
    except CadexBundle.BundleError as exc:
        raise _refuse(exc) from exc

    waypath: list[tuple[float, float, float]] = []
    for candidate in lay[conductor]:
        if waypath and (
            (candidate[0] - waypath[-1][0]) ** 2
            + (candidate[1] - waypath[-1][1]) ** 2
            + (candidate[2] - waypath[-1][2]) ** 2
        ) <= 1.0e-12:
            continue
        waypath.append(candidate)

    # A hard floor under any declared minimum: a conductor that doubles back
    # tighter than its own radius sweeps into a solid that is closed, valid
    # and self-intersecting -- so it is refused here rather than published.
    declared = properties.get("min_bend_radius_mm")
    floor = gauge / 2.0
    if declared is None or float(declared) < floor:
        declared = floor

    return _sweep_conductor(
        waypath,
        operation=operation,
        gauge=gauge,
        centre=App.Vector(*waypath[0]),
        min_bend_radius_mm=declared,
        # The check has to see the lay, not a fixed 97 samples spread over a
        # run that may hold fifty turns -- too coarse and it over-reports the
        # radius, which makes it pass conductors it should refuse.
        bend_samples=max(_CABLE_BEND_SAMPLES, len(waypath)),
        context=(
            " (bundle %r conductor %d)" % (str(properties.get("label") or ""), conductor)
            if properties.get("label")
            else " (conductor %d)" % conductor
        ),
        bend_correction=(
            "The lay and the route bend the same way here. Raise "
            "twist_pitch_mm so the conductor turns less, raise cell_mm so the "
            "route is smoother, lower slack towards 1.0 so the run hangs less "
            "(a run that is close to vertical sags along its own axis), or "
            "move a port so the run turns less sharply."
        ),
        sweep_correction=(
            "The conductor turns tighter than its gauge can be swept through. "
            "Raise twist_pitch_mm, reduce gauge_mm, raise cell_mm for a "
            "smoother route, or declare min_bend_radius_mm so the route is "
            "rejected before the sweep."
        ),
    )


def _build(
    operation: str,
    payload: dict[str, Any],
    diagnostics: dict[str, Any] | None = None,
):
    import FreeCAD as App
    import Part

    properties = _properties(payload)
    if operation == "from_object":
        reference = _argument(payload, 0, "reference")
        if not isinstance(reference, dict) or set(reference) != {
            "document_uid",
            "object_name",
        }:
            raise _error(
                operation,
                "reference",
                "expected document_uid and object_name from a validated program input",
            )
        key = (
            str(reference.get("document_uid") or ""),
            str(reference.get("object_name") or ""),
        )
        shape = _REFERENCE_SHAPES.get(key)
        if shape is None:
            raise _error(
                operation,
                "reference",
                "was not staged from this program's validated inputs; add the exact "
                "stable reference to inputs and its x-cadex-reference schema",
            )
        return shape.copy()
    if operation == "box":
        return Part.makeBox(
            float(_argument(payload, 0, "length")),
            float(_argument(payload, 1, "width")),
            float(_argument(payload, 2, "height")),
            _vector(operation, "origin", properties.get("origin", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
        )
    if operation == "wedge":
        length = float(_argument(payload, 0, "length"))
        width = float(_argument(payload, 1, "width"))
        height = float(_argument(payload, 2, "height"))
        ridge = float(properties.get("ridge_x", 0.0))
        return Part.makeWedge(
            0.0,
            0.0,
            0.0,
            0.0,
            ridge,
            length,
            width,
            height,
            height,
            ridge,
            _vector(operation, "origin", properties.get("origin", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
        )
    if operation == "plane":
        return Part.makePlane(
            float(_argument(payload, 0, "length")),
            float(_argument(payload, 1, "width")),
            _vector(operation, "origin", properties.get("origin", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "normal",
                properties.get("normal", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            _vector(
                operation,
                "x_direction",
                properties.get("x_direction", [1.0, 0.0, 0.0]),
                nonzero=True,
            ),
        )
    if operation == "prism":
        sides = int(_argument(payload, 0, "sides"))
        radius = float(_argument(payload, 1, "circumradius"))
        height = float(_argument(payload, 2, "height"))
        rotation_degrees = float(properties.get("rotation_degrees", 0.0))
        points = [
            App.Vector(
                radius * math.cos(math.radians(rotation_degrees + 360.0 * index / sides)),
                radius * math.sin(math.radians(rotation_degrees + 360.0 * index / sides)),
                0.0,
            )
            for index in range(sides)
        ]
        points.append(points[0])
        result = Part.Face(Part.makePolygon(points)).extrude(App.Vector(0.0, 0.0, height))
        direction = _vector(
            operation,
            "direction",
            properties.get("direction", [0.0, 0.0, 1.0]),
            nonzero=True,
        )
        rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), direction)
        result.Placement = App.Placement(
            _vector(operation, "center", properties.get("center", [0.0, 0.0, 0.0])),
            rotation,
        )
        return result
    if operation == "cylinder":
        return Part.makeCylinder(
            float(_argument(payload, 0, "radius")),
            float(_argument(payload, 1, "height")),
            _vector(operation, "origin", properties.get("origin", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            float(properties.get("angle", 360.0)),
        )
    if operation == "cone":
        return Part.makeCone(
            float(_argument(payload, 0, "radius1")),
            float(_argument(payload, 1, "radius2")),
            float(_argument(payload, 2, "height")),
            _vector(operation, "origin", properties.get("origin", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            float(properties.get("angle", 360.0)),
        )
    if operation == "sphere":
        return Part.makeSphere(
            float(_argument(payload, 0, "radius")),
            _vector(operation, "center", properties.get("center", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            float(properties.get("latitude1", -90.0)),
            float(properties.get("latitude2", 90.0)),
            float(properties.get("longitude", 360.0)),
        )
    if operation == "torus":
        return Part.makeTorus(
            float(_argument(payload, 0, "major_radius")),
            float(_argument(payload, 1, "minor_radius")),
            _vector(operation, "center", properties.get("center", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "direction",
                properties.get("direction", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            float(properties.get("angle1", -180.0)),
            float(properties.get("angle2", 180.0)),
            float(properties.get("sweep", 360.0)),
        )
    if operation == "line":
        return Part.makeLine(
            _vector(operation, "start", _argument(payload, 0, "start")),
            _vector(operation, "end", _argument(payload, 1, "end")),
        )
    if operation == "arc":
        return Part.Arc(
            _vector(operation, "start", _argument(payload, 0, "start")),
            _vector(operation, "point", _argument(payload, 1, "point")),
            _vector(operation, "end", _argument(payload, 2, "end")),
        ).toShape()
    if operation == "circle":
        return Part.makeCircle(
            float(_argument(payload, 0, "radius")),
            _vector(operation, "center", properties.get("center", [0.0, 0.0, 0.0])),
            _vector(
                operation,
                "normal",
                properties.get("normal", [0.0, 0.0, 1.0]),
                nonzero=True,
            ),
            float(properties.get("start_angle", 0.0)),
            float(properties.get("end_angle", 360.0)),
        )
    if operation == "ellipse":
        center = _vector(operation, "center", properties.get("center", [0.0, 0.0, 0.0]))
        normal = _vector(
            operation,
            "normal",
            properties.get("normal", [0.0, 0.0, 1.0]),
            nonzero=True,
        )
        result = Part.Ellipse(
            center,
            float(_argument(payload, 0, "major_radius")),
            float(_argument(payload, 1, "minor_radius")),
        ).toShape()
        rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), normal)
        if abs(float(rotation.Angle)) > 1.0e-12:
            result.rotate(center, rotation.Axis, math.degrees(float(rotation.Angle)))
        return result
    if operation == "bezier":
        poles = _argument(payload, 0, "poles")
        if not isinstance(poles, list):
            raise _error(operation, "poles", "must be an array")
        curve = Part.BezierCurve()
        curve.setPoles(
            [_vector(operation, f"poles[{index}]", point) for index, point in enumerate(poles)]
        )
        weights = properties.get("weights", [])
        if not isinstance(weights, list):
            raise _error(operation, "weights", "must be an array")
        for index, weight in enumerate(weights, start=1):
            curve.setWeight(index, float(weight))
        return curve.toShape()
    if operation == "bspline":
        points = _argument(payload, 0, "points")
        if not isinstance(points, list):
            raise _error(operation, "points", "must be an array")
        curve = Part.BSplineCurve()
        curve.interpolate(
            Points=[
                _vector(operation, f"points[{index}]", point) for index, point in enumerate(points)
            ],
            PeriodicFlag=bool(properties.get("periodic")),
            Tolerance=float(properties.get("tolerance", 1.0e-7)),
        )
        return curve.toShape()
    if operation == "nurbs_curve":
        poles = _argument(payload, 0, "poles")
        degree = int(_argument(payload, 1, "degree"))
        knots = _argument(payload, 2, "knots")
        multiplicities = _argument(payload, 3, "multiplicities")
        weights = properties.get("weights", [])
        if not all(
            isinstance(value, list)
            for value in (poles, knots, multiplicities, weights)
        ):
            raise _error(
                operation,
                "poles/knots/multiplicities/weights",
                "must be arrays",
            )
        curve = Part.BSplineCurve()
        curve.buildFromPolesMultsKnots(
            [
                _vector(operation, f"poles[{index}]", point)
                for index, point in enumerate(poles)
            ],
            [int(value) for value in multiplicities],
            [float(value) for value in knots],
            bool(properties.get("periodic")),
            degree,
            [float(value) for value in weights] if weights else None,
            bool(weights),
        )
        return curve.toShape()
    if operation == "helix":
        representation = str(properties.get("representation") or "standard")
        arguments = (
            float(_argument(payload, 0, "pitch")),
            float(_argument(payload, 1, "height")),
            float(_argument(payload, 2, "radius")),
            float(properties.get("angle", 0.0)),
            bool(properties.get("left_handed")),
        )
        if representation == "segmented":
            return Part.makeLongHelix(*arguments)
        if representation != "standard":
            raise _error(
                operation,
                "representation",
                "must be standard or segmented",
            )
        standard_arguments = (*arguments, bool(properties.get("vertical_height")))
        return Part.makeHelix(*standard_arguments)
    if operation == "wire":
        items = _argument(payload, 0, "items")
        if not isinstance(items, list) or not items:
            raise _error(operation, "items", "must be a non-empty array")
        if all(isinstance(item, dict) for item in items):
            edges = []
            for index, item in enumerate(items):
                nested = _shape(operation, f"items[{index}]", item)
                edges.extend(list(getattr(nested, "Edges", []) or []))
            if not edges:
                raise _error(operation, "items", "Part values contain no edges")
            result = Part.Wire(edges)
        else:
            points = [
                _vector(operation, f"items[{index}]", point) for index, point in enumerate(items)
            ]
            if bool(properties.get("closed")) and not points[0].isEqual(points[-1], 1.0e-9):
                points.append(points[0])
            result = Part.makePolygon(points)
        if bool(properties.get("closed")) and not result.isClosed():
            raise _error(operation, "items", "edges do not form a closed wire")
        return result
    if operation == "face":
        outer = _wire_from_shape(
            operation,
            "outer",
            _shape(operation, "outer", _argument(payload, 0, "outer")),
        )
        holes = properties.get("holes", [])
        if not isinstance(holes, list):
            raise _error(operation, "holes", "must be an array")
        wires = [outer]
        for index, item in enumerate(holes):
            wires.append(
                _wire_from_shape(
                    operation,
                    f"holes[{index}]",
                    _shape(operation, f"holes[{index}]", item),
                )
            )
        # Part.Face([outer, holes...]) accepts same-oriented inner wires on some
        # OCC versions but can silently return an invalid face.  Subtracting
        # independently validated planar faces lets OCC orient each loop and
        # gives the worker a topology it can validate consistently.
        face = Part.Face(outer)
        for index, hole in enumerate(wires[1:]):
            hole_face = Part.Face(hole)
            if not hole_face.isValid():
                raise _error(operation, f"holes[{index}]", "does not define a valid planar face")
            face = face.cut(hole_face)
            if face.isNull() or not face.isValid():
                raise _error(
                    operation,
                    f"holes[{index}]",
                    "could not be subtracted from the outer face; ensure it is coplanar, "
                    "strictly inside, and does not cross another hole",
                )
        return face
    if operation == "shell":
        faces = _shape_list(operation, "faces", _argument(payload, 0, "faces"))
        flattened = [face for shape in faces for face in list(getattr(shape, "Faces", []) or [])]
        if not flattened:
            raise _error(operation, "faces", "values contain no faces")
        return Part.makeShell(flattened)
    if operation == "solid":
        shell = _shape(operation, "shell", _argument(payload, 0, "shell"))
        shells = list(getattr(shell, "Shells", []) or [])
        source = shell if str(getattr(shell, "ShapeType", "")) == "Shell" else None
        if source is None and len(shells) == 1:
            source = shells[0]
        if source is None:
            raise _error(operation, "shell", "must contain exactly one shell")
        return Part.makeSolid(source)
    if operation == "compound":
        return Part.makeCompound(_shape_list(operation, "shapes", _argument(payload, 0, "shapes")))
    if operation == "subshape":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        kind = str(_argument(payload, 1, "kind") or "").lower()
        if kind not in SUBSHAPE_COLLECTIONS:
            raise _error(operation, "kind", f"unsupported subshape kind {kind!r}")
        return _selected_subshapes(
            operation,
            "where",
            shape,
            _argument(payload, 2, "where"),
            kind,
        )[0]
    if operation == "extrude":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        vector = _vector(operation, "vector", _argument(payload, 1, "vector"), nonzero=True)
        return shape.extrude(vector)
    if operation == "revolve":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        return shape.revolve(
            _vector(operation, "axis_origin", _argument(payload, 1, "axis_origin")),
            _vector(
                operation,
                "axis_direction",
                _argument(payload, 2, "axis_direction"),
                nonzero=True,
            ),
            float(properties.get("angle", 360.0)),
        )
    if operation == "loft":
        sections = [
            _wire_from_shape(operation, f"sections[{index}]", shape)
            for index, shape in enumerate(
                _shape_list(operation, "sections", _argument(payload, 0, "sections"), minimum=2)
            )
        ]
        return Part.makeLoft(
            sections,
            solid=bool(properties.get("solid")),
            ruled=bool(properties.get("ruled")),
            closed=bool(properties.get("closed")),
            max_degree=int(properties.get("max_degree", 5)),
        )
    if operation == "sweep":
        raw_profile = _argument(payload, 0, "profile")
        if isinstance(raw_profile, list):
            profile_shapes = _shape_list(
                operation,
                "profile",
                raw_profile,
            )
        else:
            profile_shapes = [_shape(operation, "profile", raw_profile)]
        profiles = [
            _wire_from_shape(operation, f"profile[{index}]", profile)
            for index, profile in enumerate(profile_shapes)
        ]
        path = _wire_from_shape(
            operation,
            "path",
            _shape(operation, "path", _argument(payload, 1, "path")),
        )
        transitions = {"transformed": 0, "right_corner": 1, "round_corner": 2}
        return path.makePipeShell(
            profiles,
            bool(properties.get("solid")),
            bool(properties.get("frenet")),
            transitions[str(properties.get("transition") or "transformed")],
        )
    if operation == "cable":
        return _build_cable(payload, properties)
    if operation == "bundle":
        return _build_bundle(payload, properties)
    if operation == "ruled_surface":
        first = _shape(operation, "first", _argument(payload, 0, "first"))
        second = _shape(operation, "second", _argument(payload, 1, "second"))
        return Part.makeRuledSurface(first, second)
    if operation == "filled_surface":
        boundaries = _shape_list(
            operation,
            "boundaries",
            _argument(payload, 0, "boundaries"),
            minimum=1,
        )
        edges = [edge for boundary in boundaries for edge in list(boundary.Edges)]
        if len(edges) < 2:
            raise _error(operation, "boundaries", "must contain at least two edges")
        return Part.makeFilledFace(edges)
    if operation == "fuse":
        shapes = _shape_list(operation, "shapes", _argument(payload, 0, "shapes"), minimum=2)
        result = shapes[0].fuse(
            tuple(shapes[1:]),
            float(properties.get("tolerance", 0.0)),
        )
        return _refine(
            result,
            bool(properties.get("refine", True)),
            operation=operation,
        )
    if operation == "cut":
        base = _shape(operation, "base", _argument(payload, 0, "base"))
        tools = _shape_list(operation, "tools", _argument(payload, 1, "tools"))
        result = base.cut(tuple(tools), float(properties.get("tolerance", 0.0)))
        return _refine(
            result,
            bool(properties.get("refine", True)),
            operation=operation,
        )
    if operation == "common":
        shapes = _shape_list(operation, "shapes", _argument(payload, 0, "shapes"), minimum=2)
        result = shapes[0].common(
            tuple(shapes[1:]),
            float(properties.get("tolerance", 0.0)),
        )
        return _refine(
            result,
            bool(properties.get("refine", True)),
            operation=operation,
        )
    if operation == "section":
        left = _shape(operation, "left", _argument(payload, 0, "left"))
        right = _shape(operation, "right", _argument(payload, 1, "right"))
        return left.section(right, float(properties.get("tolerance", 0.0)))
    if operation == "general_fuse":
        shapes = _shape_list(operation, "shapes", _argument(payload, 0, "shapes"), minimum=2)
        result, provenance = shapes[0].generalFuse(
            tuple(shapes[1:]),
            float(properties.get("tolerance", 0.0)),
        )
        if diagnostics is not None:
            diagnostics["general_fuse"] = {
                "input_count": len(shapes),
                "source_fragment_counts": [
                    len(list(fragments or [])) for fragments in list(provenance or [])
                ],
                "result_solid_count": len(list(getattr(result, "Solids", []) or [])),
                "result_face_count": len(list(getattr(result, "Faces", []) or [])),
            }
        return result
    if operation == "slice":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        normal = _vector(operation, "normal", _argument(payload, 1, "normal"), nonzero=True)
        offsets = _argument(payload, 2, "offsets")
        if not isinstance(offsets, list) or not offsets:
            raise _error(operation, "offsets", "must be a non-empty array")
        raw_slices = shape.slices(normal, [float(value) for value in offsets])
        if hasattr(raw_slices, "ShapeType"):
            slices = list(getattr(raw_slices, "Wires", []) or [])
        else:
            slices = list(raw_slices or [])
        if not slices:
            raise _error(
                operation,
                "offsets",
                "none of the requested planes intersect the shape",
            )
        return Part.makeCompound(slices)
    if operation == "defeature":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        faces = _selected_subshapes(
            operation,
            "faces",
            shape,
            _argument(payload, 1, "faces"),
            "face",
        )
        return shape.defeaturing(faces)
    if operation == "to_nurbs":
        return _shape(operation, "shape", _argument(payload, 0, "shape")).toNurbs()
    if operation == "reverse":
        return _shape(operation, "shape", _argument(payload, 0, "shape")).reversed()
    if operation == "shape_from_mesh":
        # The ingest counterpart of sew: triangles in, BREP topology out.
        if _ASSET_ROOT is None or _MESH_INGEST is None:
            raise PartOperationError(
                "api.shape_from_mesh: this worker request has no staged mesh "
                "kernel to materialize the mesh value with",
                stage="part_contract",
                operation=operation,
                correction=(
                    "Build shape_from_mesh from the project script surface; that "
                    "is the surface that stages the project's mesh assets."
                ),
            )
        nested = _serialized_mesh(operation, "mesh", _argument(payload, 0, "mesh"))
        try:
            # The ingest canonicalizes, which is load-bearing rather than
            # cosmetic: it is the only thing making the point/facet arrays —
            # and therefore the exported BREP bytes the project digest hashes —
            # order-stable across runs.
            mesh = _MESH_INGEST(nested, _ASSET_ROOT)
        except Exception as exc:
            # Rewrapped here, with the mesh kernel's own stage and correction
            # preserved: build_part_shape's generic handler would relabel this
            # `part_kernel` and drop the text that says how to fix the mesh.
            details = getattr(exc, "details", None)
            details = details if isinstance(details, Mapping) else {}
            raise PartOperationError(
                str(exc)
                if details
                else (
                    f"api.{operation}: the mesh value could not be materialized: "
                    f"{exc.__class__.__name__}: {exc}"
                ),
                stage=str(details.get("stage") or "mesh_kernel"),
                operation=operation,
                parameter="mesh",
                correction=str(details.get("correction") or "")
                or (
                    "Inspect the mesh value this operation consumes: fix the "
                    "mesh operation, or the asset name it imports."
                ),
            ) from exc
        result = Part.Shape()
        # Mutates in place and returns None on the pinned build; assigning the
        # call's value would silently produce a null shape.
        result.makeShapeFromMesh(
            mesh.Topology,
            float(properties.get("tolerance", 0.1)),
            bool(properties.get("sew", True)),
        )
        if str(payload.get("output_type") or "") != "solid":
            return result
        # makeShapeFromMesh returns a Shell or a Compound of shells, never a
        # Solid; build_part_shape's declared-vs-actual check rejects a raw
        # Shell declared solid, so promote it here.
        if str(result.ShapeType) == "Solid":
            return result
        if str(result.ShapeType) == "Shell":
            return Part.makeSolid(result)
        shells = list(getattr(result, "Shells", []) or [])
        if len(shells) == 1:
            return Part.makeSolid(shells[0])
        raise _error(
            operation,
            "solid",
            f"the mesh sewed into {len(shells)} shells, so it cannot form one "
            "solid; pass solid=False for a shell, or repair the mesh so it is "
            "one closed surface",
        )
    if operation == "sew":
        shapes = _shape_list(operation, "shapes", _argument(payload, 0, "shapes"))
        result = Part.makeCompound(shapes)
        result.sewShape()
        output_type = str(payload.get("output_type") or "")
        if output_type == "solid" and str(result.ShapeType) != "Solid":
            shells = list(getattr(result, "Shells", []) or [])
            if str(result.ShapeType) == "Shell":
                result = Part.makeSolid(result)
            elif len(shells) == 1:
                result = Part.makeSolid(shells[0])
            else:
                raise _error(
                    operation,
                    "output_type",
                    f"sewing produced {len(shells)} shells, so it cannot form one solid",
                )
        elif output_type == "compound" and str(result.ShapeType) != "Compound":
            result = Part.makeCompound([result])
        return result
    if operation == "repair":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        if not shape.fix(
            float(properties.get("working_tolerance", 1.0e-7)),
            float(properties.get("minimum_tolerance", 1.0e-7)),
            float(properties.get("maximum_tolerance", 1.0e-3)),
        ):
            raise _error(
                operation,
                "shape",
                "ShapeFix could not repair the topology within the requested tolerances",
            )
        return shape
    if operation in {"fillet", "chamfer"}:
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        selected = _selected_subshapes(
            operation,
            "edges",
            shape,
            properties.get("edges", "all"),
            "edge",
        )
        distance = float(_argument(payload, 1, "radius" if operation == "fillet" else "distance"))
        method = shape.makeFillet if operation == "fillet" else shape.makeChamfer
        return method(distance, selected)
    if operation == "offset":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        joins = {"arc": 0, "tangent": 1, "intersection": 2}
        return shape.makeOffsetShape(
            float(_argument(payload, 1, "distance")),
            float(properties.get("tolerance", 1.0e-7)),
            inter=False,
            self_inter=False,
            offsetMode=0,
            join=joins[str(properties.get("join") or "arc")],
            fill=bool(properties.get("fill")),
        )
    if operation == "offset2d":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        joins = {"arc": 0, "tangent": 1, "intersection": 2}
        return shape.makeOffset2D(
            float(_argument(payload, 1, "distance")),
            join=joins[str(properties.get("join") or "arc")],
            fill=bool(properties.get("fill")),
            openResult=bool(properties.get("open_result")),
            intersection=bool(properties.get("intersection")),
        )
    if operation == "thicken":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        faces = _selected_subshapes(
            operation,
            "faces",
            shape,
            _argument(payload, 1, "faces"),
            "face",
        )
        joins = {"arc": 0, "tangent": 1, "intersection": 2}
        return shape.makeThickness(
            faces,
            float(_argument(payload, 2, "thickness")),
            float(properties.get("tolerance", 1.0e-7)),
            False,
            False,
            0,
            joins[str(properties.get("join") or "arc")],
        )
    if operation == "transform":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape")).copy()
        pivot = _vector(operation, "pivot", properties.get("pivot", [0.0, 0.0, 0.0]))
        scale = properties.get("scale", [1.0, 1.0, 1.0])
        if not isinstance(scale, list) or len(scale) != 3:
            raise _error(operation, "scale", "must contain three factors")
        if any(abs(float(value) - 1.0) > 1.0e-12 for value in scale):
            factors = [float(value) for value in scale]
            if max(factors) - min(factors) <= 1.0e-12:
                shape.scale(factors[0], pivot)
            else:
                matrix = App.Matrix()
                matrix.A11 = factors[0]
                matrix.A22 = factors[1]
                matrix.A33 = factors[2]
                matrix.A14 = pivot.x * (1.0 - factors[0])
                matrix.A24 = pivot.y * (1.0 - factors[1])
                matrix.A34 = pivot.z * (1.0 - factors[2])
                shape = shape.transformGeometry(matrix)
        rotation = float(properties.get("rotation_degrees", 0.0))
        if abs(rotation) > 1.0e-12:
            shape.rotate(
                pivot,
                _vector(
                    operation,
                    "rotation_axis",
                    properties.get("rotation_axis"),
                    nonzero=True,
                ),
                rotation,
            )
        shape.translate(_vector(operation, "translation", properties.get("translation")))
        return shape
    if operation == "mirror":
        shape = _shape(operation, "shape", _argument(payload, 0, "shape"))
        return shape.mirror(
            _vector(operation, "plane_origin", _argument(payload, 1, "plane_origin")),
            _vector(
                operation,
                "plane_normal",
                _argument(payload, 2, "plane_normal"),
                nonzero=True,
            ),
        )
    if operation == "project":
        target = _shape(operation, "target", _argument(payload, 0, "target"))
        profile = _shape(operation, "profile", _argument(payload, 1, "profile"))
        mode = str(properties.get("mode") or "parallel")
        vector = _vector(
            operation,
            "vector",
            _argument(payload, 2, "vector"),
            nonzero=mode == "parallel",
        )
        if mode == "parallel":
            result = target.makeParallelProjection(
                profile,
                vector,
            )
        elif mode == "perspective":
            result = target.makePerspectiveProjection(
                profile,
                vector,
            )
        else:
            raise _error(operation, "mode", "must be parallel or perspective")
        if str(payload.get("output_type") or "") == "wire":
            edges = list(getattr(result, "Edges", []) or [])
            if not edges:
                raise _error(operation, "profile", "projection produced no edges")
            try:
                result = Part.Wire(edges)
            except Exception as exc:
                raise _error(
                    operation,
                    "output_type",
                    "projection produced disconnected edges; request 'compound' instead",
                ) from exc
        elif str(result.ShapeType) != "Compound":
            result = Part.makeCompound([result])
        return result
    if operation == "refine":
        return _refine(
            _shape(operation, "shape", _argument(payload, 0, "shape")),
            True,
            operation=operation,
        )
    raise _error(operation, "operation", "is not implemented by the Part worker")


#: Content-keyed shapes built during ONE worker request.
#:
#: A value used twice -- a `plate` fed to two `mesh.from_shape` calls, a
#: sub-assembly cut against several things -- was built once per consumer,
#: because nothing memoised anything: +0.164 s per extra consumer, measured.
#: Assembly components already dedupe; nothing else did.
#:
#: Reset in `reset_part_shape_memo`, called from the request's `try/finally`
#: rather than at entry. A warm worker that leaked this across requests
#: would return geometry for the *previous* parameter values under a
#: self-consistent digest, which is the worst failure this codebase can
#: have. The finally is the guard that makes that impossible.
_SHAPE_MEMO: dict[str, tuple[Any, dict[str, Any]]] = {}

#: Entries, not bytes: shapes are opaque here. Small because sharing is
#: shallow in practice -- a handful of expensive nodes, not hundreds.
_SHAPE_MEMO_LIMIT = 64


def reset_part_shape_memo() -> None:
    """Drop every memoised shape. One request must never see another's."""

    _SHAPE_MEMO.clear()
    _BUNDLE_ROUTES.clear()


def _memo_key(payload: Mapping[str, Any]) -> str:
    """Content identity for one part definition.

    Same construction as ``cadex_project_api.inline_source_token`` so the
    tree has one content-key idiom rather than two that drift.
    """

    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "src-" + hashlib.sha256(canonical).hexdigest()[:24]


def build_part_shape(
    payload: dict[str, Any],
    *,
    diagnostics: dict[str, Any] | None = None,
):
    """Execute one validated Part definition and wrap OCC errors usefully.

    Memoised by content. **Copies on the way in and on the way out**, for
    three independent reasons, any one of which would be enough:

    - ``part.repair`` calls ``shape.fix(...)`` *in place* on what it is
      given. Harmless while nothing was shared; silent cache corruption
      under a memo.
    - ``part.transform`` already copies, precisely because it mutates.
    - **The digest hazard.** ``MeshPart.meshFromShape`` runs ``BRepMesh``,
      which skips faces that already carry a triangulation. Handing
      ``mesh.from_shape`` a shape that ``part_shape_facts`` had already
      tessellated would change the PLY, its ``geometry_sha256`` and the
      project digest -- while ``test_project_rebuild`` stayed green, because
      rebuild would use the memo too. ``Shape.copy()`` defaults to
      ``copyMesh=False``, which is exactly what makes a hit
      indistinguishable from a fresh build.

    Measured: ``copy()`` is 0.62 ms against the 42.7 ms of ``cut`` +
    ``makeFillet`` it replaces on the baseline part -- 68x cheaper, so the
    copy is not what this costs.
    """

    key = _memo_key(payload)
    memoised = _SHAPE_MEMO.get(key)
    if memoised is not None:
        shape, fragment = memoised
        if diagnostics is not None and fragment:
            # Replay the fragment: `general_fuse` publishes a declared
            # live_outputs.* key, so a hit must report what a build did.
            diagnostics.update(fragment)
        return shape.copy()

    fragment: dict[str, Any] = {}
    shape = _build_part_shape_uncached(
        payload, diagnostics=fragment if diagnostics is not None else None
    )
    if diagnostics is not None and fragment:
        diagnostics.update(fragment)
    if len(_SHAPE_MEMO) < _SHAPE_MEMO_LIMIT:
        _SHAPE_MEMO[key] = (shape.copy(), dict(fragment))
    return shape


def _build_part_shape_uncached(
    payload: dict[str, Any],
    *,
    diagnostics: dict[str, Any] | None = None,
):
    operation = str(payload.get("operation") or "")
    if not operation:
        raise PartOperationError(
            "Part output has no operation name",
            stage="part_contract",
            correction="Return only values created by one declared Part runtime export.",
        )
    try:
        shape = _build(operation, payload, diagnostics)
    except PartOperationError:
        raise
    except Exception as exc:
        raise PartOperationError(
            f"api.{operation}: OpenCascade rejected the requested operation: "
            f"{exc.__class__.__name__}: {exc}",
            stage="part_kernel",
            operation=operation,
            observed={
                "exception_type": exc.__class__.__name__,
                "message": str(exc),
            },
            correction=(
                f"Inspect api.{operation} inputs and the upstream accepted shape facts. "
                "Change the smallest invalid geometry or tolerance; do not repeat the "
                "unchanged call."
            ),
        ) from exc
    if shape is None or shape.isNull():
        raise PartOperationError(
            f"api.{operation}: OpenCascade produced a null shape",
            stage="part_result_validation",
            operation=operation,
            observed={"shape_type": "Null"},
            correction=(
                f"Inspect api.{operation} inputs for non-intersecting, degenerate, or "
                "self-intersecting geometry and change that exact cause."
            ),
        )
    if not shape.isValid():
        raise PartOperationError(
            f"api.{operation}: OpenCascade produced an invalid shape",
            stage="part_result_validation",
            operation=operation,
            observed={"shape_type": str(getattr(shape, "ShapeType", "") or "")},
            correction=(
                f"Repair the upstream geometry used by api.{operation}; use api.repair "
                "only with the smallest bounded tolerances justified by the defect."
            ),
        )
    output_type = str(payload.get("output_type") or "")
    exact_types = {
        "edge": ("Edge", "Edges"),
        "wire": ("Wire", "Wires"),
        "face": ("Face", "Faces"),
        "shell": ("Shell", "Shells"),
        "solid": ("Solid", "Solids"),
    }
    if output_type in exact_types:
        expected_shape_type, collection_name = exact_types[output_type]
        if str(getattr(shape, "ShapeType", "")) != expected_shape_type:
            children = list(getattr(shape, collection_name, []) or [])
            if len(children) != 1:
                raise PartOperationError(
                    f"api.{operation}: declared {output_type} but OpenCascade produced "
                    f"{getattr(shape, 'ShapeType', '<unknown>')} containing "
                    f"{len(children)} {collection_name.lower()}",
                    stage="part_output_type",
                    operation=operation,
                    parameter="output_type",
                    observed={
                        "declared_output_type": output_type,
                        "shape_type": str(getattr(shape, "ShapeType", "") or ""),
                        "matching_child_count": len(children),
                    },
                    correction=(
                        "Declare the topology class actually produced by this operation, "
                        "or change the source geometry so it produces exactly one requested "
                        f"{output_type}."
                    ),
                )
            shape = children[0]
        if shape.isNull() or not shape.isValid():
            raise PartOperationError(
                f"api.{operation}: normalized {output_type} topology is invalid",
                stage="part_result_validation",
                operation=operation,
                parameter="output_type",
                observed={"declared_output_type": output_type},
                correction=(
                    "Change the upstream operation so its normalized topology is valid; "
                    "do not weaken the declared output type."
                ),
            )
    elif output_type == "compound" and str(getattr(shape, "ShapeType", "")) != "Compound":
        raise PartOperationError(
            f"api.{operation}: declared compound but OpenCascade produced "
            f"{getattr(shape, 'ShapeType', '<unknown>')}",
            stage="part_output_type",
            operation=operation,
            parameter="output_type",
            observed={
                "declared_output_type": "compound",
                "shape_type": str(getattr(shape, "ShapeType", "") or ""),
            },
            correction=(
                "Use api.compound for an unfused multi-shape publication, or declare "
                "the exact topology produced by this operation."
            ),
        )
    return shape
