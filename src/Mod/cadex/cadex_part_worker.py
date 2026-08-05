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
#: ``payload -> 4x4 row-major tuple``: where a mesh value's asset frame sits.
_MESH_PLACEMENT: Any = None


def configure_part_assets(
    root: Path | None,
    mesh_ingest: Any = None,
    mesh_placement: Any = None,
) -> None:
    """Bind what ``shape_from_mesh`` and ``terminals`` need, for one request.

    Three bindings, for two reasons.

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

    The **mesh placement callable** for the same import-boundary reason as
    the second, and it is a separate binding rather than a flag on the first
    because it does different work: resolving a terminal on an imported
    component needs where that component *is*, not its triangles (ADR-062).
    Materializing the mesh to read a matrix off it would import and
    canonicalize the whole asset to compose four numbers.

    All three mirror the module's existing idiom for host-staged material,
    :func:`configure_part_references` (ADR-043).
    """

    global _ASSET_ROOT, _MESH_INGEST, _MESH_PLACEMENT
    _ASSET_ROOT = None if root is None else Path(root)
    _MESH_INGEST = mesh_ingest
    _MESH_PLACEMENT = mesh_placement


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


def _selected_subshape_details(
    operation: str,
    parameter: str,
    shape: Any,
    requested: Any,
    kind: str,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Resolve a geometric selector (or ``"all"``) to subshapes *and* details.

    Phase 10b: the index form is gone. A failed selector reports the declared
    and actual counts plus the subshapes that *were* available, so the agent
    can re-query rather than guess an ordinal.

    The details are what ``terminals`` needs alongside the kernel objects
    (ADR-062) — a pad's normal is fingerprinted there already, and computing
    it twice would be two different ``normalAt`` calls that could disagree.
    """

    try:
        return resolve_selected_subshapes(shape, kind, requested)
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


def _selected_subshapes(
    operation: str,
    parameter: str,
    shape: Any,
    requested: Any,
    kind: str,
) -> list[Any]:
    """The kernel objects one selector names — the ops' entry point."""

    selected, _details = _selected_subshape_details(
        operation, parameter, shape, requested, kind
    )
    return selected


# -- blending: what to do when the kernel refuses some of the edges --------
#
# ``TopoShapePy::makeFillet`` builds a ``BRepFilletAPI_MakeFillet`` and calls
# ``.Shape()`` without checking ``IsDone``, so one impossible edge in three
# hundred throws away the other 299 and the model is told
# ``15StdFail_NotDone`` and nothing else (ADR-125). None of what follows is a
# C++ change: it is this module calling the existing binding more than once.

#: Kernel calls one blend may spend looking for a workable radius and the
#: failing edges. A bisection needs O(k log n) of them for k bad edges out of
#: n -- but on a fused organic body one call is most of a second, so the cap
#: is what stops a refusal costing half a minute. When it binds the result
#: says so rather than quietly reporting less.
_BLEND_PROBE_CALLS = 48

#: ...and the same cap in wall-clock, which is the one that actually binds on
#: a real body: the robot wolf's 91-edge seam set costs 0.4-0.5 s per attempt,
#: so 48 calls of it is half a minute and nobody would wait for the answer.
#: "How many kernel calls" is not what a person watching a rebuild counts.
_BLEND_PROBE_SECONDS = 10.0

#: How far down a reduced radius may go, as a fraction of what was asked.
#: Below this the answer is "not at this radius" rather than a blend nobody
#: would recognise as the one they asked for.
_BLEND_RADIUS_FLOOR = 0.05

#: Failing edges named in a refusal. The rest are counted, not listed: a
#: refusal a model cannot read is as useless as one that says nothing.
_BLEND_REPORTED_EDGES = 12


class _BlendProbe:
    """One shape, one operation, a counted budget of kernel attempts.

    Every attempt is made against the **original** shape with a subset of its
    own edges, which is not a stylistic choice: ``BRepFilletAPI_MakeFillet``
    looks its edges up in the shape it was constructed with, so an edge taken
    from a previous result cannot be passed to the next call.
    """

    def __init__(
        self,
        shape: Any,
        operation: str,
        *,
        radius_end: float | None = None,
        requested: float = 0.0,
        cap: int = _BLEND_PROBE_CALLS,
        seconds: float = _BLEND_PROBE_SECONDS,
    ) -> None:
        import time

        self.shape = shape
        self.operation = operation
        self.radius_end = radius_end
        #: The radius originally asked for, so a reduced attempt can scale
        #: ``radius_end`` in proportion and keep the taper.
        self.requested = float(requested)
        self.cap = int(cap)
        self.seconds = float(seconds)
        self.calls = 0
        self.spent = 0.0
        self._clock = time.monotonic
        self.result: Any = None

    @property
    def exhausted(self) -> bool:
        return self.calls >= self.cap or self.spent >= self.seconds

    def attempt(self, edges: list[Any], distance: float) -> bool:
        """Try one blend. Records the shape on success; never raises.

        A result that is null **or invalid** counts as a failure, and that is
        not defensive coding: partially filleting a fused body is exactly how
        OCCT produces a compound that passes ``IsDone`` and fails
        ``BRepCheck_Analyzer``. Measured on the wolf, where every partial
        blend came back invalid — a search that called those successes would
        have handed the model a shape the output validator then refused,
        with the blend context gone (ADR-125).
        """

        if not edges:
            return False
        self.calls += 1
        began = self._clock()
        try:
            if self.operation == "chamfer":
                built = self.shape.makeChamfer(distance, edges)
            elif self.radius_end is None:
                built = self.shape.makeFillet(distance, edges)
            else:
                # The two-radius overload evolves the radius along each edge;
                # the end radius scales with the start so a reduced probe
                # keeps the taper the model asked for.
                scale = distance / self.requested if self.requested else 1.0
                built = self.shape.makeFillet(
                    distance, self.radius_end * scale, edges
                )
        except Exception:
            self.spent += self._clock() - began
            return False
        try:
            usable = built is not None and not built.isNull() and built.isValid()
        except Exception:
            usable = False
        self.spent += self._clock() - began
        if not usable:
            return False
        self.result = built
        return True


def _blend_partition(
    probe: _BlendProbe, edges: list[Any], distance: float
) -> tuple[list[Any], list[Any], list[Any]]:
    """Split a failing edge set into (accepted, rejected, unprobed).

    Greedy accumulation with bisection. An edge is rejected only when it
    fails *in the presence of the set already accepted*, which is the honest
    reading: fillets interact, and two edges that each work alone can be
    impossible together. What comes back is a working subset and the edges
    that stopped it growing, not a proof about any edge in isolation.
    """

    accepted: list[Any] = []
    rejected: list[Any] = []
    queue: list[list[Any]] = []
    middle = max(1, len(edges) // 2)
    queue.append(edges[:middle])
    if edges[middle:]:
        queue.append(edges[middle:])

    while queue:
        if probe.exhausted:
            return accepted, rejected, [edge for chunk in queue for edge in chunk]
        chunk = queue.pop(0)
        if probe.attempt(accepted + chunk, distance):
            accepted.extend(chunk)
            continue
        if len(chunk) == 1:
            rejected.extend(chunk)
            continue
        half = len(chunk) // 2
        queue.insert(0, chunk[half:])
        queue.insert(0, chunk[:half])
    return accepted, rejected, []


def _blend_largest_radius(
    probe: _BlendProbe, edges: list[Any], distance: float, *, steps: int = 5
) -> float | None:
    """The largest radius at or below ``distance`` the whole set accepts."""

    floor = distance * _BLEND_RADIUS_FLOOR
    if probe.exhausted or not probe.attempt(edges, floor):
        return None
    best, low, high = floor, floor, distance
    for _ in range(steps):
        if probe.exhausted:
            break
        middle = (low + high) / 2.0
        if probe.attempt(edges, middle):
            best = low = middle
        else:
            high = middle
    return best


#: Stations a lawed sweep builds between consecutive control points. Enough
#: that a taper reads as smooth; few enough that a 64-point law stays inside
#: the operation budget.
_SWEEP_STATIONS = 6


def _law_factor(law: list[list[float]], position: float) -> float:
    """Linear interpolation between the law's control points."""

    if position <= law[0][0]:
        return float(law[0][1])
    for (left, low), (right, high) in zip(law, law[1:]):
        if position <= right:
            span = right - left
            if span <= 0.0:
                return float(high)
            share = (position - left) / span
            return float(low) + (float(high) - float(low)) * share
    return float(law[-1][1])


def _path_stations(
    operation: str, path: Any, positions: list[float]
) -> list[tuple[Any, Any]]:
    """(point, tangent) at fractions of a wire's ARC LENGTH.

    By length rather than by parameter, and across the wire's ordered edges
    rather than one curve, because a spine is usually several edges and a
    curve's parameter is not proportional to distance along it — stations
    picked by parameter bunch up where the curve is slow, and the taper
    bunches with them.
    """

    edges = list(getattr(path, "OrderedEdges", None) or getattr(path, "Edges", []) or [])
    lengths = [float(edge.Length) for edge in edges]
    total = sum(lengths)
    if not edges or total <= 1.0e-12:
        raise _error(operation, "path", "has no length to sweep along")

    stations: list[tuple[Any, Any]] = []
    for position in positions:
        target = max(0.0, min(1.0, float(position))) * total
        walked = 0.0
        chosen, local = edges[-1], lengths[-1]
        for edge, length in zip(edges, lengths):
            if target <= walked + length or edge is edges[-1]:
                chosen, local = edge, target - walked
                break
            walked += length
        local = max(0.0, min(float(chosen.Length), local))
        try:
            parameter = chosen.getParameterByLength(local)
        except Exception:
            first, last = float(chosen.FirstParameter), float(chosen.LastParameter)
            share = local / float(chosen.Length) if chosen.Length else 0.0
            parameter = first + (last - first) * share
        try:
            tangent = chosen.tangentAt(parameter)
        except Exception:
            tangent = None
        stations.append((chosen.valueAt(parameter), tangent))
    return stations


def _swept_law(
    operation: str, profile: Any, path: Any, law: list[list[float]], solid: bool
) -> Any:
    """Sweep a profile along a path while a law scales it.

    Built as a loft through computed stations rather than through
    ``BRepOffsetAPI_MakePipeShell``, and the reason is the binding:
    ``TopoShapeWirePy::makePipeShell`` takes ``(sections, solid, frenet,
    transition)`` and exposes neither ``SetLaw`` nor the guide-curve mode.
    Reaching those means a new binding in ``src/Mod/Part``, which is a
    decision about the fork's delta rather than a fix (ADR-125). The loft is
    what the model was doing by hand anyway — the wolf's tail is five tilted
    circles — and it produces the same class of NURBS solid.
    """

    import FreeCAD as App
    import Part
    from FreeCAD import Vector

    positions: list[float] = []
    for (left, _low), (right, _high) in zip(law, law[1:]):
        for step in range(_SWEEP_STATIONS):
            positions.append(left + (right - left) * step / _SWEEP_STATIONS)
    positions.append(1.0)

    origin = profile.CenterOfMass
    stations = _path_stations(operation, path, positions)

    sections = []
    previous_tangent = None
    for position, (point, tangent) in zip(positions, stations):
        if tangent is None or tangent.Length <= 1.0e-12:
            tangent = previous_tangent or Vector(0.0, 0.0, 1.0)
        previous_tangent = tangent
        factor = _law_factor(law, position)
        section = profile.copy()
        if abs(factor - 1.0) > 1.0e-12:
            section.scale(factor, origin)
        # The profile is authored in its own plane; each station rotates it
        # onto the path's tangent there and drops it on the path.
        rotation = App.Rotation(App.Vector(0.0, 0.0, 1.0), tangent)
        if abs(float(rotation.Angle)) > 1.0e-12:
            section.rotate(origin, rotation.Axis,
                           math.degrees(float(rotation.Angle)))
        section.translate(point.sub(origin))
        sections.append(_wire_from_shape(operation, "profile", section))

    return Part.makeLoft(sections, bool(solid), False, False)


def _edge_midpoint(edge: Any) -> Any:
    """A point that is actually ON the edge.

    Not ``CenterOfMass``: for a circle that is the centre, which is the one
    place on the plane the curve never passes through.
    """

    first = float(edge.FirstParameter)
    last = float(edge.LastParameter)
    return edge.valueAt((first + last) / 2.0)


def _box_contains(box: Any, point: Any, margin: float) -> bool:
    return (
        box.XMin - margin <= point.x <= box.XMax + margin
        and box.YMin - margin <= point.y <= box.YMax + margin
        and box.ZMin - margin <= point.z <= box.ZMax + margin
    )


def _seam_edges(
    result: Any, inputs: list[Any], *, tolerance: float = 1.0e-5
) -> tuple[list[Any], list[dict[str, Any]]]:
    """The edges a boolean made: those lying on two or more of its inputs.

    Every edge of a union's boundary lies on at least one input. An edge
    that lies on *two* was created where they intersect, and that is the
    seam — the thing a person means by "weld this join". No provenance is
    consulted and none is needed, which is why this stays out of
    ``CadexSubshapeQuery``'s selector vocabulary: that vocabulary is closed
    and purely geometric, and "which operation created this edge" is
    history. The seam set is computed by the operation that has the inputs
    in its hands, and by nothing else.
    """

    import Part
    from CadexSubshapeQuery import subshape_geometry

    boxes = [shape.BoundBox for shape in inputs]
    edges: list[Any] = []
    details: list[dict[str, Any]] = []
    for index, edge in enumerate(list(getattr(result, "Edges", []) or []), start=1):
        point = _edge_midpoint(edge)
        vertex = None
        hits = 0
        for shape, box in zip(inputs, boxes):
            # The bounding box is a cheap rejection: on a fused body most
            # edges are nowhere near most inputs, and distToShape is not
            # cheap enough to run n_edges x n_inputs times.
            if not _box_contains(box, point, 1.0e-3):
                continue
            if vertex is None:
                vertex = Part.Vertex(point)
            if float(vertex.distToShape(shape)[0]) <= tolerance:
                hits += 1
                if hits >= 2:
                    break
        if hits >= 2:
            edges.append(edge)
            details.append(subshape_geometry(result, "edge", index, edge))
    return edges, details


def _blend_edge_names(edges: list[Any], details: list[Mapping[str, Any]],
                      selected: list[Any]) -> list[str]:
    """Fingerprint keys for the given edges, in selection order."""

    from CadexSubshapeQuery import fingerprint_key

    names = []
    for edge in edges:
        for index, candidate in enumerate(selected):
            if candidate is edge:
                if index < len(details):
                    names.append(fingerprint_key(details[index]))
                break
    return names


def _blend(
    shape: Any,
    operation: str,
    selected: list[Any],
    details: list[Mapping[str, Any]],
    distance: float,
    *,
    radius_end: float | None = None,
    on_failure: str = "refuse",
    parameter: str = "edges",
    diagnostics: dict[str, Any] | None = None,
) -> Any:
    """Blend the selected edges, and survive the ones the kernel refuses.

    The fast path is unchanged and costs exactly one kernel call: the whole
    set at the radius asked for. Everything below it only runs when that
    call has already failed, which is when the old code raised
    ``StdFail_NotDone`` and told the model nothing it could act on.
    """

    probe = _BlendProbe(shape, operation, radius_end=radius_end, requested=distance)
    if probe.attempt(selected, distance):
        return probe.result

    # The radius search runs FIRST, and the order is a measurement rather
    # than a preference: on the wolf the partition ate the whole budget and
    # the refusal came back with no workable radius at all -- which is the
    # one number a model can act on without re-selecting anything.
    workable = _blend_largest_radius(probe, selected, distance)
    accepted, rejected, unprobed = _blend_partition(probe, selected, distance)
    refused_names = _blend_edge_names(rejected, details, selected)
    report: dict[str, Any] = {
        "requested_distance_mm" if operation == "chamfer" else "requested_radius_mm":
            float(distance),
        "edges_selected": len(selected),
        "edges_blended": len(accepted),
        "edges_refused": len(rejected),
        "edges_unprobed": len(unprobed),
        "refused_edges": refused_names[:_BLEND_REPORTED_EDGES],
        "largest_workable_radius_mm": (
            None if workable is None else round(float(workable), 4)
        ),
        "probe_calls": probe.calls,
        "probe_seconds": round(probe.spent, 3),
        "probe_capped": bool(unprobed) or probe.exhausted,
        "probe_cap": (
            "seconds" if probe.spent >= probe.seconds
            else ("calls" if probe.calls >= probe.cap else None)
        ),
    }
    if len(refused_names) > _BLEND_REPORTED_EDGES:
        report["refused_edges_omitted"] = len(refused_names) - _BLEND_REPORTED_EDGES

    if on_failure == "reduce" and workable is not None:
        # Uniform, not per-edge, and the reason is the binding: makeFillet
        # applies one radius spec per call, and a second call would have to
        # find its edges in the FIRST call's result, where they have been
        # renumbered and possibly consumed. What the model gets instead is a
        # radius the whole body accepts, and the number is in the result.
        probe.attempt(selected, workable)
        result = probe.result
        if result is not None:
            _record_blend(diagnostics, operation, {
                **report, "applied": "reduce",
                "applied_radius_mm": round(float(workable), 4)})
            return result

    if on_failure in {"skip", "reduce"} and accepted:
        probe.attempt(accepted, distance)
        result = probe.result
        if result is not None:
            _record_blend(diagnostics, operation, {
                **report, "applied": "skip",
                "applied_radius_mm": float(distance)})
            return result

    if on_failure == "skip":
        detail = "no edge in the selection could be blended at that radius"
    elif on_failure == "reduce":
        detail = (
            "no radius down to "
            f"{distance * _BLEND_RADIUS_FLOOR:.4g} mm blends this selection"
        )
    else:
        detail = (
            f"{len(rejected)} of {len(selected)} edge(s) refused the requested "
            f"{'distance' if operation == 'chamfer' else 'radius'}"
        )
        if unprobed:
            bound = (
                f"{_BLEND_PROBE_SECONDS:g} s"
                if probe.spent >= probe.seconds
                else f"{_BLEND_PROBE_CALLS}-call"
            )
            detail += (
                f"; {len(unprobed)} more went unprobed at the {bound} probe cap"
            )
    raise PartOperationError(
        f"api.{operation}: {detail}.",
        stage="part_kernel",
        operation=operation,
        parameter=parameter,
        observed=report,
        correction=_blend_correction(operation, report, on_failure),
    )


def _blend_correction(
    operation: str, report: Mapping[str, Any], on_failure: str
) -> str:
    """What to do about it, in the caller's own vocabulary."""

    workable = report.get("largest_workable_radius_mm")
    parts = []
    if int(report.get("edges_blended") or 0) and on_failure == "refuse":
        parts.append(
            f"pass on_failure='skip' to blend the {report['edges_blended']} edge(s) "
            "that do work and leave the listed ones sharp"
        )
    if workable:
        parts.append(
            f"use radius={workable} (the largest this selection accepts) or "
            "on_failure='reduce' to have it applied for you"
        )
    parts.append(
        "or narrow the selector so it no longer names the edges in "
        "observed.refused_edges"
    )
    return (
        f"api.{operation} refused rather than silently doing less work. "
        + "; ".join(parts)
        + "."
    )


def _record_blend(
    diagnostics: dict[str, Any] | None, operation: str, report: Mapping[str, Any]
) -> None:
    """Report partial work where a caller is collecting diagnostics.

    Best-effort by construction: only the operation that produces a declared
    output is given a diagnostics dict, so a blend nested inside a later
    boolean records nothing. That is why the refusal is the default and
    carries the whole report — a model reaches ``skip`` or ``reduce`` having
    already been told exactly what it is accepting, in the call before.
    """

    if diagnostics is None:
        return
    diagnostics.setdefault(f"{operation}_partial", []).append(dict(report))


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
    contain: list[Any] | None = None,
):
    """The lattice one route is searched on: resolution, corridor, occupancy.

    Shared by ``part.cable`` and ``part.bundle`` (ADR-057).  A bundle passes
    its *outer* diameter as ``gauge``, so the corridor and the clearance
    dilation account for the whole lay rather than one conductor.

    ``contain`` is extra points the corridor must hold: an authored path
    (ADR-118) may leave by any distance it likes, and a corridor sized from
    the two anchors alone would put most of it out of bounds — where the
    occupancy test cannot answer, so a wire dragged straight through a board
    would pass unchecked.

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
    corners = [
        [anchor_start[axis] for axis in range(3)],
        [anchor_end[axis] for axis in range(3)],
    ] + [[float(point[axis]) for axis in range(3)] for point in (contain or [])]
    low = [min(corner[axis] for corner in corners) - margin for axis in range(3)]
    high = [max(corner[axis] for corner in corners) + margin for axis in range(3)]

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


def _tangent_constraints(start_tangent: Any, end_tangent: Any) -> dict[str, Any]:
    """The end-tangent keywords for ``BSplineCurve.interpolate``, or none.

    Both or neither: ``BSplineCurvePy::interpolate`` loads the pair together
    (``if (t1 && t2)``), so one alone is silently ignored — which would be a
    fix that looks applied and is not.  The vectors are copied before they are
    normalised because ``Vector.normalize`` normalises **in place**, and the
    directions handed here are the caller's ports, still owed to the router.

    ``Scale=False`` and a **unit** magnitude, which is the part that had to be
    measured.  OCC's own scaling (the default, ``Scale=True``) keeps the
    direction and picks the speed itself, and on a five-waypoint route it
    picks one that makes the whole fit wavy: the 40 mm probe run measured
    45.5 mm of spline against 37.6 mm free, swinging 5.5 mm below a board it
    started 0.4 mm under, and the true-Frenet pipe shell folded on it.
    ``GeomAPI_Interpolate`` parameterises by chord length, so the natural
    speed is ~1 whatever the model's size — a unit tangent asks for the
    direction and leaves the shape alone (38.2 mm of spline, against 37.6 mm
    free, and the same excursions).
    """

    import FreeCAD as App

    if start_tangent is None or end_tangent is None:
        return {}
    pair = []
    for vector in (start_tangent, end_tangent):
        copy = App.Vector(vector)
        if copy.Length <= 1.0e-12:
            return {}
        copy.normalize()
        pair.append(copy)
    return {"InitialTangent": pair[0], "FinalTangent": pair[1], "Scale": False}


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
    start_tangent: Any = None,
    end_tangent: Any = None,
    frenet: bool = True,
    context: str = "",
):
    """Fit a spline through ``waypoints`` and sweep a round conductor along it.

    Shared by ``part.cable`` and ``part.bundle`` (ADR-057).  ``centre`` is
    where the profile circle sits — the run's first point.

    ``start_tangent`` and ``end_tangent`` are the directions the run must
    leave and arrive on, and they are the difference between a wire that meets
    its terminal square and one that clips through the joint on it (ADR-074).
    Without them the interpolation is free at both ends: a global C2 fit picks
    whatever tangent minimises its own energy, so the "straight stub" the
    router puts in front of every port is straight only as a polyline, and the
    spline through it bows from parameter zero.  The profile circle is
    oriented off that same first tangent below, so the error shows up twice —
    as a bowed lead *and* as a start face tilted against the terminal's axis.

    ``frenet`` picks the sweep frame, and the two callers want opposite
    answers — which ADR-057 half-found and ADR-074 finishes.  The section is a
    circle centred on the spine, so in principle the mode cannot matter; in
    practice each mode has a shape it cannot carry.  **Corrected** Frenet
    collapses helical spines — up to 51% of the volume missing on a six-way
    lay, and still one closed, valid solid — which is why a bundle's
    conductors sweep in true Frenet.  **True** Frenet needs a curvature to
    take its normal from, and a routed cable is mostly straight: measured
    against ``pi r^2 L``, ordinary two-port runs came out at 0.78 and 0.58 of
    the volume they should have, folding through themselves wherever the
    normal swung.  Corrected held all three probe runs to within 0.06%, so
    that is what a cable sweeps in.

    A wrong frame is invisible in every cheap check — the solid is closed, it
    is valid, it has one shell — so the assertion that catches it is volume
    against the spine's own length, and both callers have one.
    """

    import FreeCAD as App
    import Part

    curve = Part.BSplineCurve()
    curve.interpolate(
        Points=[App.Vector(*point) for point in waypoints],
        PeriodicFlag=False,
        Tolerance=1.0e-7,
        **_tangent_constraints(start_tangent, end_tangent),
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
    result = Part.Wire([path_edge]).makePipeShell([profile], True, bool(frenet))
    if result is None or result.isNull() or not result.Solids:
        raise PartOperationError(
            f"api.{operation}: the conductor could not be swept along the "
            f"routed path{context}",
            stage="part_kernel",
            operation=operation,
            correction=sweep_correction,
        )
    return result


#: Resolved terminal sets for ONE worker request, keyed on the terminal
#: payload with the terminal *name* stripped. A four-way ribbon names the
#: same board four times and must resolve — and, for a selector, *build* —
#: it once. Bounded and request-scoped like ``_CABLE_MESH_BOXES`` above, and
#: cleared in ``reset_part_shape_memo`` for the reason recorded there: a
#: terminal that leaked across requests would place a wire on the previous
#: request's geometry under a self-consistent digest.
_TERMINAL_SETS: dict[str, dict[str, dict[str, Any]]] = {}
_TERMINAL_SET_LIMIT = 64

#: The ``{component, layout}`` payload behind each key in ``_TERMINAL_SETS``,
#: in first-resolution order. The memo alone is keyed by a hash and so cannot
#: say *which board* it resolved; publishing the wiring needs that (ADR-065),
#: and re-deriving it host-side would cover declared layouts only. Cleared
#: with the memo, for the reason recorded there.
_TERMINAL_SET_SOURCES: dict[str, dict[str, Any]] = {}

#: What the model does about a terminal that would not resolve.
_TERMINAL_CORRECTION = (
    "A terminal names geometry, so fix the naming rather than the number: "
    "check the selector matches exactly as many faces as there are names, "
    "that exit= points out of the component, and that a declared layout's "
    "origin/along/axis are stated in that component's own coordinates."
)


def _terminal_candidates(
    operation: str,
    parameter: str,
    kind: str,
    faces: list[Any],
    details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The handful of numbers ``CadexTerminals`` needs off each matched face.

    Everything kernel-shaped stops here: an axis, a centre, a radius and the
    face's axial parameter range for a hole; a centre of mass, a normal and
    an area for a pad. The layout, the ordering and the landing point are
    arithmetic on those, and live in the pure module.
    """

    candidates: list[dict[str, Any]] = []
    for index, face in enumerate(faces):
        detail = dict(details[index]) if index < len(details) else {}
        ordinal = index + 1
        if kind == "holes":
            surface = getattr(face, "Surface", None)
            axis = getattr(surface, "Axis", None)
            center = getattr(surface, "Center", None)
            radius = getattr(surface, "Radius", None)
            if axis is None or center is None or radius is None:
                raise PartOperationError(
                    f"api.{operation}: {parameter}: holes= matched a "
                    f"{detail.get('geometry_type') or 'non-cylindrical'} face, "
                    "which has no barrel to thread a wire through",
                    stage="part_terminals",
                    operation=operation,
                    parameter=parameter,
                    observed={"matched": detail},
                    correction=(
                        "Add geometry_type='Cylinder' to the selector so it "
                        "names the drilled faces and nothing else, or use "
                        "pads= if the attachment is a flat contact."
                    ),
                )
            low, high = (float(value) for value in face.ParameterRange[2:4])
            axis_values = [float(axis.x), float(axis.y), float(axis.z)]
            center_values = [float(center.x), float(center.y), float(center.z)]
            candidates.append(
                {
                    "ordinal": ordinal,
                    "axis": axis_values,
                    "center": center_values,
                    "radius": float(radius),
                    "extent": [low, high],
                    # The barrel's midpoint, which is on the axis whatever the
                    # face's own centre of mass does on a partial cylinder.
                    "sort_point": [
                        center_values[a] + axis_values[a] * (low + high) / 2.0
                        for a in range(3)
                    ],
                    "detail": detail,
                }
            )
            continue
        center = getattr(face, "CenterOfMass", None)
        normal = detail.get("normal")
        if normal is None:
            try:
                u_min, u_max, v_min, v_max = (
                    float(value) for value in face.ParameterRange
                )
                sampled = face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
                normal = [float(sampled.x), float(sampled.y), float(sampled.z)]
            except Exception:
                normal = None
        if center is None or normal is None:
            raise PartOperationError(
                f"api.{operation}: {parameter}: pads= matched a face with no "
                "usable centre and normal to attach to",
                stage="part_terminals",
                operation=operation,
                parameter=parameter,
                observed={"matched": detail},
                correction=_TERMINAL_CORRECTION,
            )
        center_values = [float(center.x), float(center.y), float(center.z)]
        candidates.append(
            {
                "ordinal": ordinal,
                "center": center_values,
                "normal": [float(item) for item in normal],
                "area": float(getattr(face, "Area", 0.0) or 0.0),
                "sort_point": center_values,
                "detail": detail,
            }
        )
    return candidates


def _resolve_terminal_set(
    operation: str, parameter: str, payload: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """One component's terminals, resolved once per request and memoised."""

    import CadexTerminals

    key = terminal_set_key(payload)
    cached = _TERMINAL_SETS.get(key)
    if cached is not None:
        return cached

    component = payload.get("component")
    layout = payload.get("layout")
    if not isinstance(component, dict) or not isinstance(layout, dict):
        raise _error(
            operation,
            parameter,
            "expected a terminal from part.terminals or mesh.terminals",
        )
    kind = str(layout.get("kind") or "")
    try:
        if component.get("domain") == "mesh":
            if kind != "declared":
                raise _error(
                    operation,
                    parameter,
                    "a selector names BREP faces, and an imported mesh has "
                    "none; state a declared layout with mesh.terminals",
                )
            if _MESH_PLACEMENT is None:
                raise PartOperationError(
                    f"api.{operation}: this worker request has no staged mesh "
                    "kernel to place a mesh component's terminals with",
                    stage="part_contract",
                    operation=operation,
                    parameter=parameter,
                    correction=(
                        f"Build {operation} from the project script surface; "
                        "that is the surface that stages the project's mesh "
                        "assets."
                    ),
                )
            resolved = CadexTerminals.apply_placement(
                CadexTerminals.resolve_terminals(layout),
                _MESH_PLACEMENT(_serialized_mesh(operation, parameter, component)),
            )
        elif kind == "declared":
            # A part value is built in final coordinates, so a declared layout
            # on one is already where it says it is; there is no chain to walk.
            resolved = CadexTerminals.resolve_terminals(layout)
        else:
            shape = _shape(operation, parameter, component)
            faces, details = _selected_subshape_details(
                operation, parameter, shape, layout.get("selector"), "face"
            )
            resolved = CadexTerminals.resolve_terminals(
                layout,
                candidates=_terminal_candidates(
                    operation, parameter, kind, faces, details
                ),
            )
    except CadexTerminals.TerminalError as exc:
        raise PartOperationError(
            f"api.{operation}: {parameter}: {exc}",
            stage="part_terminals",
            operation=operation,
            parameter=parameter,
            observed=exc.details,
            correction=_TERMINAL_CORRECTION,
        ) from exc

    result = {str(entry["name"]): entry for entry in resolved}
    if len(_TERMINAL_SETS) < _TERMINAL_SET_LIMIT:
        _TERMINAL_SETS[key] = result
        _TERMINAL_SET_SOURCES[key] = {
            "component": component,
            "layout": layout,
        }
    return result


def mesh_component_placement(component: Mapping[str, Any]) -> tuple[float, ...]:
    """The composed placement chain one mesh component's terminals ride.

    The same call ``_resolve_terminal_set`` makes before it places a declared
    layout, exposed because a terminal *measured in the viewport* has to go
    the other way: it arrives in world coordinates and is written down in the
    component's own frame, through the inverse of exactly this matrix
    (ADR-120). Two constructions of one chain would drift, so there is one.
    """

    if _MESH_PLACEMENT is None:
        raise PartOperationError(
            "api.terminals: this worker request has no staged mesh kernel to "
            "resolve a mesh component's placement with",
            stage="part_contract",
            operation="terminals",
            parameter="component",
        )
    return tuple(
        float(value)
        for value in _MESH_PLACEMENT(
            _serialized_mesh("terminals", "component", dict(component))
        )
    )


def terminal_set_key(payload: Mapping[str, Any]) -> str:
    """The memo identity of one terminal set: its payload minus the name.

    Public because the project worker joins the published registry to the
    ``nets(ports=...)`` declaration by this key (ADR-065), and two
    constructions of one identity would drift.
    """

    return _memo_key(
        {name: value for name, value in payload.items() if name != "terminal"}
    )


def resolve_terminal_set_for_publication(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one terminal set for the wiring publication; never raises.

    A port the script declares but never wires has not been resolved by the
    run, and resolving it here is what puts an unconnected board on the
    editor's canvas. It must not be able to *fail* the run: publishing an
    id'd set the script never used would otherwise turn a harmless unused
    selector into a build failure, which is a worse trade than an empty node.
    """

    try:
        resolved = _resolve_terminal_set("terminals", "component", dict(payload))
    except Exception as exc:  # deliberately broad: this is derived data
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "terminals": list(resolved.values())}


def published_terminal_sets() -> list[dict[str, Any]]:
    """Every terminal set this request resolved, in first-resolution order."""

    return [
        {
            "key": key,
            "component": source.get("component"),
            "layout": source.get("layout"),
            "terminals": list(_TERMINAL_SETS.get(key, {}).values()),
        }
        for key, source in _TERMINAL_SET_SOURCES.items()
    ]


def _resolve_port(operation: str, parameter: str, value: Any):
    """One end of a run, as ``(point, direction, standoff_floor, metrics)``.

    A literal ``(point, direction)`` pair takes exactly the ADR-056 path and
    floors its stand-off at zero, so every existing script routes and digests
    identically. A terminal resolves against the geometry it names (ADR-062)
    and reports how far the search anchor has to stand off before it is out
    of the component at all — a board thickness, for a through-hole.

    ``metrics`` (the axis, radius, depth and faces behind the terminal) is
    carried and unused here. ``part.solder`` is its consumer; a joint cannot
    be built from a point and a direction.
    """

    import FreeCAD as App

    if isinstance(value, dict):
        name = str(value.get("terminal") or "")
        resolved = _resolve_terminal_set(operation, parameter, value)
        entry = resolved.get(name)
        if entry is None:
            raise _error(
                operation,
                parameter,
                f"names terminal {name!r}, which this component does not "
                f"have; it has {sorted(resolved)}",
            )
        return (
            App.Vector(*(float(item) for item in entry["point"])),
            App.Vector(*(float(item) for item in entry["direction"])),
            float(entry["standoff_floor"]),
            dict(entry["metrics"]),
        )
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (
            _vector(operation, f"{parameter}[0]", value[0]),
            _vector(operation, f"{parameter}[1]", value[1], nonzero=True),
            0.0,
            {},
        )
    raise _error(
        operation,
        parameter,
        "expected a (point, direction) pair or one terminal from "
        "part.terminals / mesh.terminals",
    )


def _end_standoff(base: float, floor: float, clearance: float) -> float:
    """How far off one end the search may start.

    ``base`` is what ADR-056 computed for both ends — clear of the surface by
    the clearance plus half the wire. A terminal may add a floor on top of
    that; since ADR-117 every terminal lands on the surface the wire arrives
    at, so that floor is zero and this is the one term left. It stays because
    ``standoff_floor`` is still what a terminal states, and a future terminal
    form that lands inside material would state a non-zero one.
    """

    return max(base, float(floor) + clearance)


#: Every route this request built, keyed by the operation's content identity.
#: Same shape and lifetime as ``_BUNDLE_ROUTES``: cleared with ``_SHAPE_MEMO``
#: per request, because a route that leaked into another request would let the
#: canvas draw one project's wire on another's geometry.
_PUBLISHED_ROUTES: dict[str, dict[str, list[list[float]]]] = {}
_PUBLISHED_ROUTE_LIMIT = 512


def _publish_route(payload: dict[str, Any], spine: Any, interior: Any) -> None:
    """Record what a wire actually followed, for ``inspect scope="wiring"``.

    Derived data, on exactly the footing the wiring registry is: computed
    after the geometry, never fed into the digest, and dropped with the shape
    memo at the end of the request.

    Two lists rather than one. ``path`` is the whole centreline the sweep was
    built from and is what a reader wants in order to *see* the route;
    ``waypoints`` is the interior alone, which is the part a user may author
    and exactly what would go back into ``waypoints=``. Publishing the split
    rather than an index into the path is what keeps the shell from having to
    know how many knots a stub is written as (ADR-118).
    """

    if len(_PUBLISHED_ROUTES) >= _PUBLISHED_ROUTE_LIMIT:
        return
    _PUBLISHED_ROUTES[_memo_key(payload)] = {
        "path": [[float(value) for value in point] for point in spine],
        "waypoints": [[float(value) for value in point] for point in interior],
    }


def published_routes() -> dict[str, dict[str, list[list[float]]]]:
    """The routes this request built, keyed by operation content identity."""

    return {key: dict(value) for key, value in _PUBLISHED_ROUTES.items()}


def _blocked_authored_segment(points, *, cell, low, counts, occupied):
    """The index of the first segment of an authored path inside material.

    Sampled at half a cell — the step ``CadexRouting`` uses for its own
    line-of-sight and sag checks, and fine enough that a segment cannot pass
    through a cell without landing in it. The occupancy is the *same*
    callback the search would have used, so "blocked" means the same thing
    whether a route was searched or authored.

    A sample outside the corridor is treated as clear rather than blocked: the
    corridor is built to contain the whole authored path, so the only points
    that can fall outside it are within a rounding of its wall, and there is
    nothing out there to collide with anyway.
    """

    import math as _math

    step = max(cell * 0.5, 1.0e-9)
    for index in range(len(points) - 1):
        start, end = points[index], points[index + 1]
        span = (end - start).Length
        divisions = max(1, int(_math.ceil(span / step)))
        for sample in range(divisions + 1):
            fraction = sample / divisions
            x = start.x + (end.x - start.x) * fraction
            y = start.y + (end.y - start.y) * fraction
            z = start.z + (end.z - start.z) * fraction
            cells = (
                int(_math.floor((x - low[0]) / cell)),
                int(_math.floor((y - low[1]) / cell)),
                int(_math.floor((z - low[2]) / cell)),
            )
            if any(cells[axis] < 0 or cells[axis] >= counts[axis] for axis in range(3)):
                continue
            if occupied(*cells):
                return index
    return None


def _build_cable(payload: dict[str, Any], properties: dict[str, Any]):
    """Search a route between two ports and sweep the conductor along it.

    The search lives in ``CadexRouting`` and the budget is why it lives in
    this process at all: the script sandbox meters every traced line against
    a 400k operation budget and explicitly declines to trace frames outside
    the script, so an A* written in the script would spend budget per node
    while the same search here costs one operation (ADR-056).
    """

    import CadexRouting
    import CadexSolder
    import FreeCAD as App

    operation = "cable"
    start_point, start_dir, start_floor, start_metrics = _resolve_port(
        operation, "start", _argument(payload, 0, "start")
    )
    end_point, end_dir, end_floor, end_metrics = _resolve_port(
        operation, "end", _argument(payload, 1, "end")
    )

    gauge = float(properties.get("gauge_mm", 0.0))
    clearance = float(properties.get("clearance_mm", 1.0))
    slack = float(properties.get("slack", 1.05))
    if gauge <= 0.0:
        raise _error(operation, "gauge_mm", "must be greater than zero")
    standoff = clearance + gauge / 2.0
    # A joint on either end holds the lead straight for the meniscus and the
    # collar together, and the anchor is where the route stops being straight
    # — so a stand-off shorter than that run puts the wire's first bend inside
    # the joint that is meant to grip it (ADR-074). The floor is applied here
    # rather than inside `_end_standoff` because it is not the router's idea:
    # `part.cable` never learns whether a joint exists, it just leaves enough
    # straight lead that one *could* be there. Both floors are measured from
    # the same place as `standoff_floor` — the terminal's landing — so they
    # add.
    start_standoff = max(
        _end_standoff(standoff, start_floor, clearance),
        start_floor + CadexSolder.lead_run_mm(start_metrics, gauge),
    )
    end_standoff = max(
        _end_standoff(standoff, end_floor, clearance),
        end_floor + CadexSolder.lead_run_mm(end_metrics, gauge),
    )
    solids, boxes = _cable_obstacles(operation, properties.get("avoid", []))
    authored = [list(point) for point in (properties.get("waypoints") or [])]

    # Not Vector.normalize(), which normalizes in place: start_dir is handed
    # to the router afterwards and must still be the direction it was given.
    anchor_start = start_point + start_dir * (start_standoff / start_dir.Length)
    anchor_end = end_point + end_dir * (end_standoff / end_dir.Length)
    cell, low, high, counts, occupied = _route_corridor(
        operation=operation,
        anchor_start=anchor_start,
        anchor_end=anchor_end,
        gauge=gauge,
        clearance=clearance,
        cell_mm=float(properties.get("cell_mm", 0.0)),
        solids=solids,
        boxes=boxes,
        contain=authored,
    )

    if authored:
        # The search is skipped entirely (ADR-118) -- no `route_interior`, no
        # lattice A*. What is *not* skipped is the collision test: a wire
        # through a board is never what was meant, and loud beats clever.
        blocked = _blocked_authored_segment(
            [anchor_start] + [App.Vector(*point) for point in authored] + [anchor_end],
            cell=cell,
            low=low,
            counts=counts,
            occupied=occupied,
        )
        if blocked is not None:
            raise PartOperationError(
                f"api.{operation}: the authored path runs through something in "
                f"avoid= on segment {blocked}",
                stage="part_routing",
                operation=operation,
                observed={
                    "reason": "waypoints_blocked",
                    "segment": blocked,
                    "waypoints": authored,
                },
                correction=(
                    "Move the waypoint at either end of that segment clear of "
                    "the obstacle, drop clearance_mm, or remove waypoints= "
                    "entirely to let the search find a way round by itself. "
                    "Segment 0 is the run from the start port's stand-off to "
                    "the first waypoint."
                ),
            )
        spine = CadexRouting.assemble_spine(
            (start_point.x, start_point.y, start_point.z),
            (anchor_start.x, anchor_start.y, anchor_start.z),
            authored,
            (anchor_end.x, anchor_end.y, anchor_end.z),
            (end_point.x, end_point.y, end_point.z),
        )
        _publish_route(payload, spine, authored)
        return _sweep_conductor(
            spine,
            operation=operation,
            gauge=gauge,
            centre=start_point,
            min_bend_radius_mm=properties.get("min_bend_radius_mm"),
            start_tangent=start_dir,
            end_tangent=end_dir * -1.0,
            frenet=False,
        )

    try:
        interior, routed_start, routed_end = CadexRouting.route_interior(
            (start_point.x, start_point.y, start_point.z),
            (start_dir.x, start_dir.y, start_dir.z),
            (end_point.x, end_point.y, end_point.z),
            (end_dir.x, end_dir.y, end_dir.z),
            occupied=occupied,
            cell_mm=cell,
            clearance_mm=clearance,
            start_standoff_mm=start_standoff,
            end_standoff_mm=end_standoff,
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

    spine = CadexRouting.assemble_spine(
        (start_point.x, start_point.y, start_point.z),
        routed_start,
        interior,
        routed_end,
        (end_point.x, end_point.y, end_point.z),
    )
    _publish_route(payload, spine, interior)
    return _sweep_conductor(
        spine,
        operation=operation,
        gauge=gauge,
        centre=start_point,
        min_bend_radius_mm=properties.get("min_bend_radius_mm"),
        # Both ports point *out* of their component, and the run arrives at
        # the far one against its direction — so the final tangent is its
        # negative, not the direction itself.
        start_tangent=start_dir,
        end_tangent=end_dir * -1.0,
        # A routed cable is mostly straight, and a straight stretch has no
        # curvature for a true Frenet normal to follow. See _sweep_conductor.
        frenet=False,
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
    """Resolve the ``(start_port, end_port)`` pairs into vectors and floors.

    Each end becomes ``[point, direction, standoff_floor]``; literals and
    terminals resolve through the same :func:`_resolve_port`, so one bundle
    may mix them (ADR-062).
    """

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
            point, direction, floor, _metrics = _resolve_port(
                operation, f"{name}[{side}]", port
            )
            ends.append([point, direction, floor])
        result.append(ends)
    return result


def _bundle_gather(operation: str, ports: list[list[Any]], side: str):
    """Where the bundle leaves one end, which way, and how far off.

    The point is the centroid of that end's ports; the direction is the sum of
    their *unit* directions, so a port whose direction vector happens to be
    long does not steer the whole bundle.  Ports that disagree by more than
    about sixty degrees on average have no common way out, and that is refused
    here rather than left to produce a meaningless average.

    The stand-off floor is the **maximum** across the end's ports, not their
    mean: the bundle leaves as one run, and a run that clears three pads but
    starts inside the fourth's board has not cleared anything (ADR-062).
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
    return (
        point,
        direction * (1.0 / direction.Length),
        max(float(port[2]) for port in ports),
    )


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

    start_point, start_dir, start_floor = _bundle_gather(
        operation, [pair[0] for pair in connections], "start"
    )
    end_point, end_dir, end_floor = _bundle_gather(
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
    start_standoff = _end_standoff(standoff, start_floor, clearance)
    end_standoff = _end_standoff(standoff, end_floor, clearance)
    breakout = properties.get("breakout_mm")
    if breakout is None:
        breakout = min(1.5 * diameter + clearance, reach / 3.0)
    else:
        breakout = float(breakout)

    route_key = _bundle_route_key(payload)
    shared = _BUNDLE_ROUTES.get(route_key)
    if shared is None:
        solids, boxes = _cable_obstacles(operation, properties.get("avoid", []))
        anchor_start = start_point + start_dir * start_standoff
        anchor_end = end_point + end_dir * end_standoff
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
                start_standoff_mm=start_standoff,
                end_standoff_mm=end_standoff,
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

        # No end-tangent constraint here, unlike the cable's spline, and the
        # reason is measured rather than assumed (ADR-074). A conductor is
        # swept along a *lay* resampled off this spine at 97 points, so the
        # spine's end tangent reaches the wire only through that resample --
        # and the pipe shell's true-Frenet frame is already a coin flip across
        # neighbouring parameters: at fixed geometry the baseline sweep
        # measures between 0.75x and 1.47x of `pi r^2 L` as twist_pitch_mm and
        # slack move by a few percent. Constraining the spine re-rolls that
        # dice for a tangent the resample mostly absorbs. The cable, whose
        # spline *is* the wire, gets the constraint; this waits for the frame.
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

    # Every conductor publishes the *shared* spine, and publishes no editable
    # interior at all (ADR-118). A bundle's route belongs to the bundle, so
    # authoring one conductor's path would silently be authoring all of them —
    # which is the same reason a bundle's membership is a script decision and
    # not a table one (ADR-065), and why the canvas draws its conductors
    # read-only (ADR-115).
    _publish_route(payload, shared, [])

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
        # A lay *is* curvature, everywhere, and corrected Frenet collapses it
        # (ADR-057). The opposite of the cable's answer, for the same reason.
        frenet=True,
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


#: What the model does about a joint whose numbers do not describe one.
#: Keyed on ``CadexSolder.SolderError.reason``, the same contract
#: ``_build_cable`` and ``_build_bundle`` have with their own pure modules.
_SOLDER_CORRECTIONS = {
    "metrics": (
        "part.solder builds a joint from a terminal's measured geometry — its "
        "axis, its bore and the face the lead lands on. Name the attachment "
        "with part.terminals or mesh.terminals; a literal (point, direction) "
        "port carries none of that."
    ),
    "gauge": (
        "gauge_mm is the diameter of the lead the joint forms around, and it "
        "is the same number the part.cable or part.bundle landing here was "
        "given. State it as a positive diameter in millimetres."
    ),
    "bore": (
        "Either the hole is too narrow for the lead or its width was never "
        "measured. Declare hole_dia on the layout so every joint on that "
        "component takes it, or reduce gauge_mm to a lead that fits."
    ),
    "pad": (
        "The joint has to be wider than the lead it wets and wider than the "
        "hole it rings. Pass pad_dia_mm to state the footprint, or name the "
        "pad with a pads= selector so its area comes off the face."
    ),
    "fillet": (
        "fillet_mm is how far the meniscus climbs the lead. It must be greater "
        "than zero, and it cannot be shorter than the pad the meniscus sweeps "
        "across — an arc that spreads further than it climbs undercuts the "
        "board instead of sitting on it. Leave it out to take the quarter-round "
        "default the pad and the gauge imply, which is exactly that floor."
    ),
}

#: What the model does about an outline the kernel would not revolve. Nothing
#: in the operation's own arguments causes this — ``CadexSolder`` proves the
#: loop simple before it emits it — so the correction points at the report
#: rather than at a number to change.
_SOLDER_PROFILE_CORRECTION = (
    "The joint's outline is derived, not stated, so no argument of part.solder "
    "produces this on its own. Set refine=False to inspect the unrefined "
    "result, and report the terminal's measured bore, depth and pad together "
    "with gauge_mm."
)


def _solder_face(specs: Mapping[str, Any]):
    """The joint's half-section, as one closed planar face (ADR-064).

    ``CadexSolder`` works in the ``(r, z)`` half-plane and never builds a
    3-D vector; this is where that half-plane acquires a position. Every point
    is the same linear combination of two orthonormal vectors, so the wire is
    planar by construction rather than by luck, and consecutive segments share
    bit-identical endpoints, so ``Part.Wire`` orders the edges instead of
    sewing them.

    This is a *single* loop, so the distrust of ``Part.Face`` over an
    outer-plus-holes wire list — recorded at the ``face`` operation, where
    inner wires get subtracted as independently validated faces instead —
    does not apply here.
    """

    import FreeCAD as App
    import Part

    origin = App.Vector(*(float(item) for item in specs["origin"]))
    axis = App.Vector(*(float(item) for item in specs["direction"]))
    radial = App.Vector(*(float(item) for item in specs["radial"]))

    def point(pair):
        return origin + radial * float(pair[0]) + axis * float(pair[1])

    edges = []
    for segment in specs["profile"]:
        start, end = point(segment["start"]), point(segment["end"])
        if segment["kind"] == "arc":
            edges.append(Part.Arc(start, point(segment["through"]), end).toShape())
        else:
            edges.append(Part.makeLine(start, end))
    wire = Part.Wire(edges)
    if not wire.isClosed():
        raise PartOperationError(
            "api.solder: the joint's outline did not close",
            stage="part_kernel",
            operation="solder",
            observed={"segments": len(edges)},
            correction=_SOLDER_PROFILE_CORRECTION,
        )
    face = Part.Face(wire)
    if face.isNull() or not face.isValid():
        raise PartOperationError(
            "api.solder: the joint's outline did not bound a valid face",
            stage="part_kernel",
            operation="solder",
            observed={"segments": len(edges)},
            correction=_SOLDER_PROFILE_CORRECTION,
        )
    return face, origin, axis


def _build_solder(payload: dict[str, Any], properties: dict[str, Any]):
    """The joint one terminal implies, as one solid of revolution (ADR-064).

    The derivation and every refusal live in ``CadexSolder``, which knows no
    kernel; what is here is a wire, a face, one ``revolve`` and the wrapping of
    a refusal into the model-facing envelope. There is no fuse and no cut —
    ADR-064 replaced the three fused primitives with a single closed outline,
    which is what retires every boolean hazard ADR-063 documented. The terminal
    resolves through the *unchanged* :func:`_resolve_port`, so N joints on one
    board cost one terminal resolution and one board build — the ADR-062
    ``_TERMINAL_SETS`` memo plus ``build_part_shape``'s content memo, shared
    with the cables landing on the same component in the same request.
    """

    import CadexSolder

    operation = "solder"
    _point, _direction, _floor, metrics = _resolve_port(
        operation, "terminal", _argument(payload, 0, "terminal")
    )

    try:
        specs = CadexSolder.solder_specs(
            metrics,
            gauge_mm=properties.get("gauge_mm"),
            pad_dia_mm=properties.get("pad_dia_mm"),
            fillet_mm=properties.get("fillet_mm"),
        )
    except CadexSolder.SolderError as exc:
        raise PartOperationError(
            f"api.{operation}: {exc}",
            stage="part_solder",
            operation=operation,
            observed={"reason": exc.reason, **exc.observed},
            correction=_SOLDER_CORRECTIONS.get(
                exc.reason, _SOLDER_CORRECTIONS["metrics"]
            ),
        ) from exc

    face, origin, axis = _solder_face(specs)
    joint = face.revolve(origin, axis, 360.0)
    # Asserted rather than assumed: `_build_part_shape_uncached` lets a single
    # self-intersecting solid through — the gap `_sweep_conductor` and
    # `_build_bundle` already close by hand — so a revolve that produced a
    # shell, two solids or a self-intersection has to be caught here.
    null = bool(joint.isNull())
    solids = 0 if null else len(joint.Solids)
    valid = False if null else bool(joint.isValid())
    if null or not valid or solids != 1:
        raise PartOperationError(
            f"api.{operation}: revolving the joint's outline did not produce "
            "one solid",
            stage="part_kernel",
            operation=operation,
            observed={"solids": solids, "valid": valid, "null": null},
            correction=_SOLDER_PROFILE_CORRECTION,
        )
    return _refine(joint, bool(properties.get("refine", True)), operation=operation)


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
        aim = properties.get("x_direction")
        if aim is not None:
            # Where +X — the major axis — landed after that rotation, versus
            # where the caller wants it. Spinning about the normal is the
            # only degree of freedom left, and it is exactly the one a
            # section table cares about.
            target = _vector(operation, "x_direction", aim, nonzero=True)
            axis = [float(value) for value in normal]
            length = math.sqrt(sum(value * value for value in axis))
            axis = [value / length for value in axis]
            along = sum(t * a for t, a in zip(target, axis))
            wanted = [t - along * a for t, a in zip(target, axis)]
            span = math.sqrt(sum(value * value for value in wanted))
            if span > 1.0e-12:
                wanted = [value / span for value in wanted]
                placed = rotation.multVec(App.Vector(1.0, 0.0, 0.0))
                current = [float(placed.x), float(placed.y), float(placed.z)]
                cross = [
                    current[1] * wanted[2] - current[2] * wanted[1],
                    current[2] * wanted[0] - current[0] * wanted[2],
                    current[0] * wanted[1] - current[1] * wanted[0],
                ]
                angle = math.degrees(math.atan2(
                    sum(c * a for c, a in zip(cross, axis)),
                    sum(c * w for c, w in zip(current, wanted)),
                ))
                if abs(angle) > 1.0e-9:
                    result.rotate(center, App.Vector(*axis), angle)
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
        law = properties.get("scale_law")
        if law:
            return _swept_law(
                operation, profiles[0], path, law, bool(properties.get("solid"))
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
    if operation == "solder":
        return _build_solder(payload, properties)
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
        result = _refine(
            shapes[0].fuse(
                tuple(shapes[1:]),
                float(properties.get("tolerance", 0.0)),
            ),
            bool(properties.get("refine", True)),
            operation=operation,
        )
        blend = properties.get("blend")
        if blend is None:
            return result
        # After refinement, deliberately: removeSplitter merges coplanar
        # faces, and a seam it has just dissolved is not a seam any more.
        seams, details = _seam_edges(result, shapes)
        if not seams:
            raise PartOperationError(
                f"api.{operation}: blend found no seam to round — the inputs "
                "do not intersect, so the union has no shared edges.",
                stage="part_topology_selection",
                operation=operation,
                parameter="blend",
                observed={"input_count": len(shapes),
                          "result_edges": len(list(getattr(result, "Edges", []) or []))},
                correction=(
                    "Overlap the shapes before fusing them, or drop blend= and "
                    "round chosen edges with api.fillet afterwards."
                ),
            )
        return _blend(
            result,
            operation,
            seams,
            details,
            float(blend),
            on_failure=str(properties.get("blend_on_failure") or "refuse"),
            parameter="blend",
            diagnostics=diagnostics,
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
        selected, details = _selected_subshape_details(
            operation,
            "edges",
            shape,
            properties.get("edges", "all"),
            "edge",
        )
        distance = float(_argument(payload, 1, "radius" if operation == "fillet" else "distance"))
        radius_end = properties.get("radius_end")
        return _blend(
            shape,
            operation,
            selected,
            details,
            distance,
            radius_end=None if radius_end is None else float(radius_end),
            on_failure=str(properties.get("on_failure") or "refuse"),
            diagnostics=diagnostics,
        )
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
    _PUBLISHED_ROUTES.clear()
    _TERMINAL_SETS.clear()
    _TERMINAL_SET_SOURCES.clear()


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
