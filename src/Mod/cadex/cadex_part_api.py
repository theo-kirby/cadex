# SPDX-License-Identifier: LGPL-2.1-or-later

"""Production provider-facing API for the Part XScript domain.

All distances are millimetres and all angles are degrees.  Methods validate
their declarative contract before returning a :class:`DomainValue`, so source
errors identify the exact operation and parameter before OCC execution begins.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any, Iterable, Sequence

from CadexSubshapeQuery import SELECTOR_KEYS
from CadexCage import CageSet
from CadexMounts import Mount, MountSet
from CadexTerminals import Terminal, TerminalError, TerminalSet, declared_layout, selector_layout
from cadex_domain_api import DomainValue
from cadex_mesh_api import _asset_filename, payload_tree_is_deterministic


_TOPOLOGY_TYPES = frozenset({"edge", "wire", "face", "shell", "solid", "compound"})
#: The shape classes an operation may be *asked* to return. This is what
#: validates a caller's ``output_type=``, so it must stay shapes only —
#: ``sew(..., output_type="measurement")`` is a typo, not a request.
_PUBLISHABLE_TYPES = frozenset({"wire", "face", "shell", "solid", "compound"})
#: What the pack may publish, which is the above plus the one output type that
#: is not a shape at all: a measurement carries two points and a number and no
#: geometry (ADR-139). Deliberately a second constant rather than a widened
#: first one — the pack contract and the ``output_type=`` argument were the
#: same set only for as long as every output was a shape.
_PACK_OUTPUT_TYPES = _PUBLISHABLE_TYPES | frozenset({"measurement"})
_JOIN_TYPES = frozenset({"arc", "tangent", "intersection"})
_TRANSITION_TYPES = frozenset({"transformed", "right_corner", "round_corner"})
#: What a loft does when its surface escapes the sections it interpolates
#: (ADR-129). There is no "reduce" here: the fix is a different table or a
#: lower degree, and choosing one for the model would be inventing a shape.
_LOFT_BULGE_MODES = frozenset({"refuse", "allow"})
#: What a swept section does about its guide curve (ADR-128). The names are
#: ours and the meanings are measured: OCCT spells these ``BRepFill_NoContact``,
#: ``BRepFill_Contact`` and ``BRepFill_ContactOnBorder``, and "contact" there
#: **translates** the section to touch the guide rather than scaling it — the
#: reading everyone has, and the wrong one.
_GUIDE_MODES = frozenset({"orient", "touch", "follow"})
#: How the conductors of a ``part.bundle`` are laid about their shared route.
_LAY_STYLES = frozenset({"twisted", "flat"})
_SUBSHAPE_TYPES = frozenset({"edge", "wire", "face", "shell", "solid"})
#: Part topologies that enclose a volume a route can be tested against.
_OBSTACLE_TYPES = frozenset({"solid", "shell", "compound"})
_HELIX_REPRESENTATIONS = frozenset({"standard", "segmented"})
_PROJECTION_MODES = frozenset({"parallel", "perspective"})
#: What ``fillet``/``chamfer`` do when the kernel refuses part of a selection
#: (ADR-125). ``refuse`` is the default and reports which edges failed, how
#: many worked and the largest radius that would have; the other two are how
#: a model opts into partial work *after* being told what it is accepting.
_BLEND_FAILURE_MODES = frozenset({"refuse", "skip", "reduce"})
#: What ``import_part`` reads: one part authored in another project (ADR-138).
#: Named here rather than reaching for the store's union, because this is the
#: one format *this* operation accepts — the same reason ``_asset_filename``
#: takes a ``suffixes`` argument at all.
_LINKED_PART_SUFFIXES = frozenset({".cxpart"})

#: What ``measurement`` can measure (ADR-139). Closed, and each member is a
#: different *drawing* rather than a different formula: a distance is a line
#: between two anchors, a diameter is a line whose ends are chosen per frame,
#: and an extent is a distance whose anchors nothing had to name.
_MEASUREMENT_KINDS = frozenset({"distance", "diameter", "extent"})
#: Which topology a measurement's selectors resolve against. Faces and edges
#: only: those are the two ``resolve_pin`` speaks and the two the viewport can
#: put a number on. Applies to both ends of a distance — a face-to-edge
#: measurement is a later slice, not an oversight.
_MEASURED_ELEMENT_TYPES = frozenset({"face", "edge"})
_MEASURED_AXES = frozenset({"x", "y", "z"})
#: Decimals a measurement's number is formatted to. Bounded because the text
#: is drawn in a fixed pixel space: at twelve places the label is wider than
#: the part and the dimension line disappears behind its own value.
_MAXIMUM_MEASUREMENT_PLACES = 6


def _places(operation: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(operation, "places", "must be an integer", value)
    if not 0 <= value <= _MAXIMUM_MEASUREMENT_PLACES:
        raise _error(
            operation,
            "places",
            f"must be between 0 and {_MAXIMUM_MEASUREMENT_PLACES}",
            value,
        )
    return int(value)


def _error(operation: str, parameter: str, message: str, value: Any = None) -> ValueError:
    received = "" if value is None else f" Received {value!r}."
    return ValueError(f"api.{operation}: invalid {parameter}: {message}.{received}")


def _number(
    operation: str,
    parameter: str,
    value: Any,
    *,
    minimum: float | None = None,
    strict: bool = False,
) -> float:
    if isinstance(value, bool):
        raise _error(operation, parameter, "expected a finite number", value)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise _error(operation, parameter, "expected a finite number", value) from exc
    if not math.isfinite(result):
        raise _error(operation, parameter, "expected a finite number", value)
    if minimum is not None and (result <= minimum if strict else result < minimum):
        relation = "greater than" if strict else "at least"
        raise _error(operation, parameter, f"must be {relation} {minimum:g}", value)
    return result


def _nonzero_number(operation: str, parameter: str, value: Any) -> float:
    result = _number(operation, parameter, value)
    if abs(result) <= 1.0e-12:
        raise _error(operation, parameter, "magnitude must be greater than zero", value)
    return result


def _integer(
    operation: str,
    parameter: str,
    value: Any,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(operation, parameter, "expected an integer", value)
    if minimum is not None and value < minimum:
        raise _error(operation, parameter, f"must be at least {minimum}", value)
    if maximum is not None and value > maximum:
        raise _error(operation, parameter, f"must not exceed {maximum}", value)
    return value


def _vector(
    operation: str,
    parameter: str,
    value: Any,
    *,
    nonzero: bool = False,
) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise _error(operation, parameter, "expected [x, y, z]", value)
    result = [_number(operation, f"{parameter}[{index}]", item) for index, item in enumerate(value)]
    if nonzero and math.sqrt(sum(item * item for item in result)) <= 1.0e-12:
        raise _error(operation, parameter, "vector magnitude must be non-zero", value)
    return result


def _label(operation: str, value: Any) -> str:
    result = str(value or "").strip()
    if len(result) > 120:
        raise _error(operation, "label", "must contain at most 120 characters", value)
    return result


def _shape(
    operation: str,
    parameter: str,
    value: Any,
    *,
    allowed: Iterable[str] = _TOPOLOGY_TYPES,
) -> DomainValue:
    allowed_types = frozenset(allowed)
    if not isinstance(value, DomainValue) or value.domain != "part":
        raise _error(
            operation,
            parameter,
            "expected a value returned by this Part api",
            type(value).__name__,
        )
    if value.output_type not in allowed_types:
        raise _error(
            operation,
            parameter,
            f"expected topology type {sorted(allowed_types)}",
            value.output_type,
        )
    return value


def _mesh_value(operation: str, parameter: str, value: Any) -> DomainValue:
    """The mirror of ``cadex_mesh_api._part_shape``, pointing the other way."""

    if not isinstance(value, DomainValue) or value.domain != "mesh":
        raise _error(
            operation,
            parameter,
            "expected a value returned by the Mesh api",
            type(value).__name__,
        )
    return value


def _port(operation: str, parameter: str, value: Any) -> Any:
    """One connection point: where a wire attaches and which way it leaves.

    Two forms, interchangeable at either end of any run.

    A **terminal** from ``part.terminals`` or ``mesh.terminals`` (ADR-062) —
    named, and derived from the component's geometry on every rebuild, so it
    rides a slider instead of going stale. It converts to plain JSON here,
    *before* the :class:`DomainValue` is constructed, with the component's
    payload nested inside; that is the whole reason a terminal never needs to
    be a domain value, an output type, or a row in the tree.

    A literal ``(point, direction)`` pair, which is what ADR-056 took and
    what ``resolve_pin`` already answers a pick with — ``center_mm`` plus
    ``normal``, so a picked pad is a port with no conversion.
    """

    if isinstance(value, Terminal):
        return value.to_port()
    if isinstance(value, TerminalSet):
        raise _error(
            operation,
            parameter,
            "expected one terminal, not the whole set; subscript it by name, "
            f"e.g. component[{value.names[0]!r}]",
        )
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise _error(
            operation,
            parameter,
            "expected a terminal from part.terminals/mesh.terminals, or a "
            "literal ([x, y, z], [dx, dy, dz])",
            value,
        )
    return [
        _vector(operation, f"{parameter}[0]", value[0]),
        _vector(operation, f"{parameter}[1]", value[1], nonzero=True),
    ]


def _solder_terminal(operation: str, parameter: str, value: Any) -> dict[str, Any]:
    """One terminal, and never a literal port (ADR-063).

    The one place in this api where a literal ``(point, direction)`` pair is
    *not* interchangeable with a terminal, and the reason is not strictness for
    its own sake: a joint is built from a bore's radius and depth and the two
    faces it runs between, and a literal carries none of them.  There is
    nothing to refuse *later* either — a literal port would leave the operation
    with no numbers at all, so it is named here, where the correction can be
    "declare the attachment" rather than "the kernel produced a null shape".
    """

    if isinstance(value, Terminal):
        return value.to_port()
    if isinstance(value, TerminalSet):
        raise _error(
            operation,
            parameter,
            "expected one terminal, not the whole set; a joint is soldered per "
            f"terminal, so subscript it by name, e.g. component[{value.names[0]!r}]",
        )
    raise _error(
        operation,
        parameter,
        "expected a terminal from part.terminals/mesh.terminals. A literal "
        "(point, direction) port carries no bore radius, no depth and no face, "
        "so there is nothing to build a joint from",
        value,
    )


def _mount(operation: str, parameter: str, value: Any) -> dict[str, Any]:
    """One mount handle, to plain JSON with its component's payload nested.

    The same conversion ``_port`` performs on a terminal, for the same
    reason: a mount never needs to be a domain value, an output type, or a
    row in the tree — it is a frame plus the shape it is measured on.
    """

    if isinstance(value, MountSet):
        raise _error(
            operation,
            parameter,
            "expected one mount, not the whole set; subscript it by name, "
            f"e.g. component[{value.names[0]!r}]" if value.names
            else "expected one mount, not the whole set",
        )
    if not isinstance(value, Mount):
        raise _error(
            operation,
            parameter,
            "expected a mount from mounts(...), subscripted by name, e.g. "
            "m['skin']['hip_l']",
            value,
        )
    row = dict(value.row)
    component = value.component
    payload = None
    if isinstance(component, DomainValue):
        payload = component.to_payload()
    elif isinstance(component, Mapping):
        payload = dict(component)
    if payload is None:
        raise _error(
            operation,
            parameter,
            f"mount {row.get('name')!r} is declared on a value that is not a "
            "part or mesh shape, so nothing can be placed against it",
        )
    return {
        "name": str(row.get("name") or ""),
        "component": str(row.get("component") or ""),
        "origin": [float(item) for item in row["origin"]],
        "axis": [float(item) for item in row["axis"]],
        "roll": [float(item) for item in row["roll"]],
        "clearance": (
            None if row.get("clearance") is None else float(row["clearance"])
        ),
        "fastener": row.get("fastener"),
        "shape": payload,
    }


def _port_separation(operation: str, parameter: str, start: Any, end: Any) -> None:
    """Refuse two literal ports at one point, while a terminal is still opaque.

    Only literals can be compared here: a terminal's point is geometry, and
    geometry is resolved in the worker.  The worker refuses the same case —
    ``RoutingError`` with reason ``bounds`` for a cable, the ``reach`` check
    for a bundle — so nothing is lost, it is just reported later.
    """

    if not isinstance(start, list) or not isinstance(end, list):
        return
    separation = math.sqrt(
        sum((end[0][index] - start[0][index]) ** 2 for index in range(3))
    )
    if separation <= 1.0e-9:
        raise _error(
            operation,
            parameter,
            "the two ports must be at different points for there to be a run",
        )


def _terminal_layout(operation: str, builder: Any, **arguments: Any) -> dict[str, Any]:
    """Build one terminal layout, naming the operation in whatever it refuses."""

    try:
        return builder(**arguments)
    except TerminalError as exc:
        raise TerminalError(f"api.{operation}: {exc}", details=exc.details) from exc


#: How many interior points a hand-authored path may state (ADR-118). A route
#: someone dragged has a handful of corners in it; a hundred is a subdivided
#: curve or a tessellation that arrived by mistake, and the honest answer is
#: that this argument is not the way to state that shape.
MAX_WAYPOINTS = 64


def _waypoints(operation: str, parameter: str, values: Any) -> list[list[float]]:
    """The interior of an authored path: points, in the ports' own frame.

    Refused rather than coerced, and each refusal names the index — these
    arrive transcribed from a viewport gesture, so the failure mode is one bad
    row in a list of good ones.
    """

    if isinstance(values, DomainValue) or not isinstance(values, (list, tuple)):
        raise _error(
            operation,
            parameter,
            "expected a list of interior [x, y, z] points the wire should "
            "pass through",
            values,
        )
    if not values:
        raise _error(
            operation,
            parameter,
            "is empty; leave it out entirely to search the route instead of "
            "authoring it",
        )
    if len(values) > MAX_WAYPOINTS:
        raise _error(
            operation,
            parameter,
            f"states {len(values)} points and a hand-authored path is capped "
            f"at {MAX_WAYPOINTS}",
        )
    result: list[list[float]] = []
    for index, value in enumerate(values):
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise _error(
                operation, f"{parameter}[{index}]", "expected [x, y, z]", value
            )
        result.append(
            [
                _number(operation, f"{parameter}[{index}][{axis}]", value[axis])
                for axis in range(3)
            ]
        )
    return result


def _obstacles(operation: str, parameter: str, values: Any) -> list[DomainValue]:
    """Part solids and Mesh values, mixed, that a route must go around.

    The one place in this api that takes both domains by design: a harness
    runs between imported STL components and printed BREP structure, and
    demanding one be converted to the other would make ``avoid`` useless for
    exactly the model that needs it.
    """

    if isinstance(values, DomainValue):
        sequence = [values]
    elif isinstance(values, (list, tuple)):
        sequence = list(values)
    else:
        raise _error(
            operation, parameter, "expected an array of Part or Mesh values", values
        )
    result: list[DomainValue] = []
    for index, value in enumerate(sequence):
        name = f"{parameter}[{index}]"
        if isinstance(value, DomainValue) and value.domain == "mesh":
            if not payload_tree_is_deterministic(value.to_payload()):
                raise _error(
                    operation,
                    name,
                    "the obstacle was built with decimate, whose result is not "
                    "reproducible, so the route around it would change on every "
                    "rebuild; decimate the file offline and import the reduced "
                    "mesh, or avoid the undecimated value",
                )
            result.append(value)
            continue
        result.append(_shape(operation, name, value, allowed=_OBSTACLE_TYPES))
    return result


def _shapes(
    operation: str,
    parameter: str,
    values: Any,
    *,
    minimum: int = 1,
    allowed: Iterable[str] = _TOPOLOGY_TYPES,
) -> list[DomainValue]:
    if isinstance(values, DomainValue):
        sequence = [values]
    elif isinstance(values, (list, tuple)):
        sequence = list(values)
    else:
        raise _error(
            operation, parameter, "expected a Part value or an array of Part values", values
        )
    if len(sequence) < minimum:
        raise _error(operation, parameter, f"requires at least {minimum} value(s)", values)
    return [
        _shape(operation, f"{parameter}[{index}]", value, allowed=allowed)
        for index, value in enumerate(sequence)
    ]


def _result_type(operation: str, value: Any) -> str:
    result = str(value or "").strip().lower()
    if result not in _PUBLISHABLE_TYPES:
        raise _error(
            operation, "output_type", f"must be one of {sorted(_PUBLISHABLE_TYPES)}", value
        )
    return result


def _topology_type(operation: str, value: Any) -> str:
    result = str(value or "").strip().lower()
    if result not in _TOPOLOGY_TYPES:
        raise _error(
            operation,
            "output_type",
            f"must be one of {sorted(_TOPOLOGY_TYPES)}",
            value,
        )
    return result


def _document_reference(operation: str, value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"document_uid", "object_name"}:
        raise _error(
            operation,
            "reference",
            "expected a validated input reference with document_uid and object_name",
            value,
        )
    result = {
        "document_uid": str(value.get("document_uid") or "").strip(),
        "object_name": str(value.get("object_name") or "").strip(),
    }
    if not all(result.values()):
        raise _error(operation, "reference", "document_uid and object_name must be non-empty")
    return result


def _inferred_result_type(
    operation: str,
    declared: Any,
    inferred: str,
    *,
    exact: bool = False,
) -> str:
    if declared is None:
        return inferred
    clean = _result_type(operation, declared)
    if exact and clean != inferred:
        raise _error(
            operation,
            "output_type",
            f"must be {inferred!r} for the supplied topology and options",
            declared,
        )
    return clean


_SELECTOR_HINT = (
    "a selector names geometry, not an ordinal: "
    "{'geometry_type': 'Cylinder', 'radius': 3.0, 'expected_count': 4}. "
    "Keys: " + ", ".join(sorted(SELECTOR_KEYS))
)


def _selector(
    operation: str,
    parameter: str,
    value: Any,
    *,
    allow_all: bool = False,
    fixed_count: int | None = None,
) -> str | dict[str, Any]:
    """Validate one geometric selector (Phase 10b — ADR-029).

    Indices are gone: they addressed a subshape by its position in the kernel
    enumeration, which is stable for a given shape but *not* across any edit
    that changes topology. A saved ``edges=[3, 7]`` silently starts filleting
    different edges the moment a parameter adds a hole. A selector states what
    the geometry *is*, so the same statement either keeps meaning the same
    thing or fails loudly.
    """

    if value == "all":
        if not allow_all:
            raise _error(
                operation,
                parameter,
                f"does not accept 'all'; {_SELECTOR_HINT}",
                value,
            )
        return "all"
    if isinstance(value, (list, tuple)):
        raise _error(
            operation,
            parameter,
            (
                "1-based index lists were removed in Phase 10b because they "
                f"break on any change that alters topology — {_SELECTOR_HINT}"
            ),
            value,
        )
    if not isinstance(value, Mapping) or not value:
        raise _error(
            operation, parameter, f"expected a non-empty selector mapping; {_SELECTOR_HINT}", value
        )

    unknown = sorted(set(map(str, value)) - SELECTOR_KEYS)
    if unknown:
        raise _error(
            operation,
            parameter,
            f"has unrecognised selector keys {unknown}; allowed: {sorted(SELECTOR_KEYS)}",
            value,
        )

    result = {str(key): item for key, item in value.items()}
    count = result.get("expected_count")
    if fixed_count is not None:
        if count is not None and count != fixed_count:
            raise _error(
                operation,
                f"{parameter}.expected_count",
                f"must be {fixed_count} for {operation}, which returns one subshape",
                count,
            )
        result["expected_count"] = fixed_count
        return result
    if count is None:
        raise _error(
            operation,
            parameter,
            (
                "must declare expected_count — the cardinality is what makes a "
                "wrong selector fail instead of silently doing less work"
            ),
            value,
        )
    result["expected_count"] = _integer(
        operation, f"{parameter}.expected_count", count, minimum=1
    )
    return result


def _in_plane_direction(
    operation: str, parameter: str, value: Any, normal: list[float]
) -> list[float]:
    """A direction that spans a plane with ``normal`` — parallel is refused.

    The same check ``plane`` makes of its own ``x_direction``, factored out
    now that ``ellipse`` takes one too.
    """

    clean = _vector(operation, parameter, value, nonzero=True)
    cross = [
        normal[1] * clean[2] - normal[2] * clean[1],
        normal[2] * clean[0] - normal[0] * clean[2],
        normal[0] * clean[1] - normal[1] * clean[0],
    ]
    if math.sqrt(sum(item * item for item in cross)) <= 1.0e-12:
        raise _error(operation, parameter, "must not be parallel to normal", value)
    return clean


def _scale_law(operation: str, value: Any) -> list[list[float]]:
    """Validate a sweep's ``[[position, factor], ...]`` taper.

    Positions run 0…1 along the path, strictly increasing, and must span
    both ends: a law that starts at 0.3 leaves the first third undefined,
    and guessing what it meant is how a silhouette changes without anyone
    editing it.
    """

    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise _error(
            operation, "scale_law", "expected at least two [position, factor] pairs", value
        )
    if len(value) > 64:
        raise _error(operation, "scale_law", "expected at most 64 control points", len(value))
    law: list[list[float]] = []
    for index, item in enumerate(value):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise _error(
                operation, f"scale_law[{index}]", "expected [position, factor]", item
            )
        position = _number(operation, f"scale_law[{index}][0]", item[0], minimum=0.0)
        factor = _number(
            operation, f"scale_law[{index}][1]", item[1], minimum=0.0, strict=True
        )
        if position > 1.0:
            raise _error(
                operation, f"scale_law[{index}][0]", "must be between 0 and 1", item[0]
            )
        if law and position <= law[-1][0]:
            raise _error(
                operation,
                f"scale_law[{index}][0]",
                "positions must strictly increase along the path",
                item[0],
            )
        law.append([position, factor])
    if law[0][0] > 0.0 or law[-1][0] < 1.0:
        raise _error(
            operation,
            "scale_law",
            "must span the whole path: the first position is 0 and the last is 1",
            [law[0][0], law[-1][0]],
        )
    return law


def _blend_failure_mode(operation: str, value: Any) -> str:
    """Validate ``on_failure`` for the blending ops (ADR-125)."""

    clean = str(value or "").strip().lower()
    if clean not in _BLEND_FAILURE_MODES:
        raise _error(
            operation,
            "on_failure",
            f"must be one of {sorted(_BLEND_FAILURE_MODES)}",
            value,
        )
    return clean


def _bulge_mode(operation: str, value: Any) -> str:
    """Validate ``on_bulge`` for the lofting ops (ADR-129)."""

    clean = str(value or "").strip().lower()
    if clean not in _LOFT_BULGE_MODES:
        raise _error(
            operation,
            "on_bulge",
            f"must be one of {sorted(_LOFT_BULGE_MODES)}",
            value,
        )
    return clean


def _weights(
    operation: str,
    value: Any,
    *,
    pole_count: int,
    required: bool = False,
) -> list[float]:
    if value in (None, ()) and not required:
        return []
    if not isinstance(value, (list, tuple)) or len(value) != pole_count:
        raise _error(
            operation,
            "weights",
            f"expected exactly {pole_count} positive weights",
            value,
        )
    return [
        _number(
            operation,
            f"weights[{index}]",
            weight,
            minimum=0.0,
            strict=True,
        )
        for index, weight in enumerate(value)
    ]


class PartDomainAPI:
    """Explicit, immutable construction API injected into Part XScript source."""

    __slots__ = ()

    domain = "part"

    def __init__(self, exports: Iterable[str], output_types: Iterable[str]) -> None:
        declared = tuple(dict.fromkeys(str(item) for item in exports))
        missing = [name for name in declared if not callable(getattr(self, name, None))]
        if missing:
            raise RuntimeError(f"Part runtime is missing declared exports: {', '.join(missing)}.")
        undeclared = [name for name in self.exported_names if name not in declared]
        if undeclared:
            raise RuntimeError(
                f"Part pack does not declare runtime exports: {', '.join(undeclared)}."
            )
        if frozenset(str(item) for item in output_types) != _PACK_OUTPUT_TYPES:
            raise RuntimeError(
                "Part pack output types do not match the production runtime contract."
            )

    @staticmethod
    def _value(
        operation: str,
        output_type: str,
        *arguments: Any,
        label: str = "",
        **properties: Any,
    ) -> DomainValue:
        clean_label = _label(operation, label)
        if clean_label:
            properties["label"] = clean_label
        return DomainValue(
            domain="part",
            operation=operation,
            output_type=output_type,
            arguments=tuple(arguments),
            properties=properties,
        )

    def from_object(
        self,
        reference: Mapping[str, str],
        *,
        output_type: str,
        label: str = "",
    ) -> DomainValue:
        """Snapshot a referenced live object's exact Shape for isolated Part operations."""

        operation = "from_object"
        return self._value(
            operation,
            _topology_type(operation, output_type),
            _document_reference(operation, reference),
            label=label,
        )

    def box(
        self,
        length: float,
        width: float,
        height: float,
        *,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        label: str = "",
    ) -> DomainValue:
        """Create an oriented rectangular solid; dimensions must be positive."""

        operation = "box"
        return self._value(
            operation,
            "solid",
            _number(operation, "length", length, minimum=0.0, strict=True),
            _number(operation, "width", width, minimum=0.0, strict=True),
            _number(operation, "height", height, minimum=0.0, strict=True),
            origin=_vector(operation, "origin", origin),
            direction=_vector(operation, "direction", direction, nonzero=True),
            label=label,
        )

    def wedge(
        self,
        length: float,
        width: float,
        height: float,
        *,
        ridge_x: float = 0.0,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        label: str = "",
    ) -> DomainValue:
        """Create a right-angular wedge whose ridge runs along width at ridge_x."""

        operation = "wedge"
        clean_length = _number(operation, "length", length, minimum=0.0, strict=True)
        clean_ridge = _number(operation, "ridge_x", ridge_x, minimum=0.0)
        if clean_ridge > clean_length:
            raise _error(operation, "ridge_x", "must not exceed length", ridge_x)
        return self._value(
            operation,
            "solid",
            clean_length,
            _number(operation, "width", width, minimum=0.0, strict=True),
            _number(operation, "height", height, minimum=0.0, strict=True),
            ridge_x=clean_ridge,
            origin=_vector(operation, "origin", origin),
            direction=_vector(operation, "direction", direction, nonzero=True),
            label=label,
        )

    def plane(
        self,
        length: float,
        width: float,
        *,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
        normal: Sequence[float] = (0.0, 0.0, 1.0),
        x_direction: Sequence[float] = (1.0, 0.0, 0.0),
        label: str = "",
    ) -> DomainValue:
        """Create an oriented rectangular planar face."""

        operation = "plane"
        clean_normal = _vector(operation, "normal", normal, nonzero=True)
        clean_x = _vector(operation, "x_direction", x_direction, nonzero=True)
        cross = [
            clean_normal[1] * clean_x[2] - clean_normal[2] * clean_x[1],
            clean_normal[2] * clean_x[0] - clean_normal[0] * clean_x[2],
            clean_normal[0] * clean_x[1] - clean_normal[1] * clean_x[0],
        ]
        if math.sqrt(sum(value * value for value in cross)) <= 1.0e-12:
            raise _error(operation, "x_direction", "must not be parallel to normal", x_direction)
        return self._value(
            operation,
            "face",
            _number(operation, "length", length, minimum=0.0, strict=True),
            _number(operation, "width", width, minimum=0.0, strict=True),
            origin=_vector(operation, "origin", origin),
            normal=clean_normal,
            x_direction=clean_x,
            label=label,
        )

    def prism(
        self,
        sides: int,
        circumradius: float,
        height: float,
        *,
        center: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        rotation_degrees: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Create a regular 3-64 sided prism from its base circumradius."""

        operation = "prism"
        return self._value(
            operation,
            "solid",
            _integer(operation, "sides", sides, minimum=3, maximum=64),
            _number(operation, "circumradius", circumradius, minimum=0.0, strict=True),
            _number(operation, "height", height, minimum=0.0, strict=True),
            center=_vector(operation, "center", center),
            direction=_vector(operation, "direction", direction, nonzero=True),
            rotation_degrees=_number(operation, "rotation_degrees", rotation_degrees),
            label=label,
        )

    def cylinder(
        self,
        radius: float,
        height: float,
        *,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        angle: float = 360.0,
        label: str = "",
    ) -> DomainValue:
        """Create a full or partial cylinder along an explicit axis."""

        operation = "cylinder"
        clean_angle = _number(operation, "angle", angle, minimum=0.0, strict=True)
        if clean_angle > 360.0:
            raise _error(operation, "angle", "must not exceed 360 degrees", angle)
        return self._value(
            operation,
            "solid",
            _number(operation, "radius", radius, minimum=0.0, strict=True),
            _number(operation, "height", height, minimum=0.0, strict=True),
            origin=_vector(operation, "origin", origin),
            direction=_vector(operation, "direction", direction, nonzero=True),
            angle=clean_angle,
            label=label,
        )

    def cone(
        self,
        radius1: float,
        radius2: float,
        height: float,
        *,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        angle: float = 360.0,
        label: str = "",
    ) -> DomainValue:
        """Create a cone or frustum; at least one end radius must be positive."""

        operation = "cone"
        first = _number(operation, "radius1", radius1, minimum=0.0)
        second = _number(operation, "radius2", radius2, minimum=0.0)
        if first == 0.0 and second == 0.0:
            raise _error(operation, "radius1/radius2", "at least one radius must be positive")
        clean_angle = _number(operation, "angle", angle, minimum=0.0, strict=True)
        if clean_angle > 360.0:
            raise _error(operation, "angle", "must not exceed 360 degrees", angle)
        return self._value(
            operation,
            "solid",
            first,
            second,
            _number(operation, "height", height, minimum=0.0, strict=True),
            origin=_vector(operation, "origin", origin),
            direction=_vector(operation, "direction", direction, nonzero=True),
            angle=clean_angle,
            label=label,
        )

    def sphere(
        self,
        radius: float,
        *,
        center: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        latitude1: float = -90.0,
        latitude2: float = 90.0,
        longitude: float = 360.0,
        label: str = "",
    ) -> DomainValue:
        """Create a sphere or angular spherical segment with explicit limits."""

        operation = "sphere"
        low = _number(operation, "latitude1", latitude1)
        high = _number(operation, "latitude2", latitude2)
        sweep = _number(operation, "longitude", longitude, minimum=0.0, strict=True)
        if not -90.0 <= low < high <= 90.0:
            raise _error(
                operation, "latitude1/latitude2", "must satisfy -90 <= latitude1 < latitude2 <= 90"
            )
        if sweep > 360.0:
            raise _error(operation, "longitude", "must not exceed 360 degrees", longitude)
        return self._value(
            operation,
            "solid",
            _number(operation, "radius", radius, minimum=0.0, strict=True),
            center=_vector(operation, "center", center),
            direction=_vector(operation, "direction", direction, nonzero=True),
            latitude1=low,
            latitude2=high,
            longitude=sweep,
            label=label,
        )

    def torus(
        self,
        major_radius: float,
        minor_radius: float,
        *,
        center: Sequence[float] = (0.0, 0.0, 0.0),
        direction: Sequence[float] = (0.0, 0.0, 1.0),
        angle1: float = -180.0,
        angle2: float = 180.0,
        sweep: float = 360.0,
        label: str = "",
    ) -> DomainValue:
        """Create a torus or toroidal segment; major radius must exceed minor radius."""

        operation = "torus"
        major = _number(operation, "major_radius", major_radius, minimum=0.0, strict=True)
        minor = _number(operation, "minor_radius", minor_radius, minimum=0.0, strict=True)
        if major <= minor:
            raise _error(
                operation, "major_radius", "must be greater than minor_radius", major_radius
            )
        first = _number(operation, "angle1", angle1)
        second = _number(operation, "angle2", angle2)
        clean_sweep = _number(operation, "sweep", sweep, minimum=0.0, strict=True)
        if first >= second:
            raise _error(operation, "angle1/angle2", "angle1 must be less than angle2")
        if clean_sweep > 360.0:
            raise _error(operation, "sweep", "must not exceed 360 degrees", sweep)
        return self._value(
            operation,
            "solid",
            major,
            minor,
            center=_vector(operation, "center", center),
            direction=_vector(operation, "direction", direction, nonzero=True),
            angle1=first,
            angle2=second,
            sweep=clean_sweep,
            label=label,
        )

    def line(self, start: Sequence[float], end: Sequence[float]) -> DomainValue:
        """Create one straight edge between two distinct 3D points."""

        operation = "line"
        first = _vector(operation, "start", start)
        second = _vector(operation, "end", end)
        if math.dist(first, second) <= 1.0e-9:
            raise _error(operation, "end", "must differ from start", end)
        return self._value(operation, "edge", first, second)

    def arc(
        self,
        start: Sequence[float],
        point: Sequence[float],
        end: Sequence[float],
    ) -> DomainValue:
        """Create a circular arc through three non-coincident points."""

        operation = "arc"
        first = _vector(operation, "start", start)
        middle = _vector(operation, "point", point)
        last = _vector(operation, "end", end)
        first_leg = [middle[index] - first[index] for index in range(3)]
        second_leg = [last[index] - first[index] for index in range(3)]
        cross = [
            first_leg[1] * second_leg[2] - first_leg[2] * second_leg[1],
            first_leg[2] * second_leg[0] - first_leg[0] * second_leg[2],
            first_leg[0] * second_leg[1] - first_leg[1] * second_leg[0],
        ]
        if math.sqrt(sum(value * value for value in cross)) <= 1.0e-9:
            raise _error(
                operation,
                "start/point/end",
                "three distinct, non-collinear points are required",
            )
        return self._value(operation, "edge", first, middle, last)

    def circle(
        self,
        radius: float,
        *,
        center: Sequence[float] = (0.0, 0.0, 0.0),
        normal: Sequence[float] = (0.0, 0.0, 1.0),
        start_angle: float = 0.0,
        end_angle: float = 360.0,
    ) -> DomainValue:
        """Create a circular edge or arc in a plane defined by its normal."""

        operation = "circle"
        start = _number(operation, "start_angle", start_angle)
        end = _number(operation, "end_angle", end_angle)
        if end <= start or end - start > 360.0:
            raise _error(
                operation,
                "start_angle/end_angle",
                "must define a positive sweep no greater than 360 degrees",
            )
        return self._value(
            operation,
            "edge",
            _number(operation, "radius", radius, minimum=0.0, strict=True),
            center=_vector(operation, "center", center),
            normal=_vector(operation, "normal", normal, nonzero=True),
            start_angle=start,
            end_angle=end,
        )

    def ellipse(
        self,
        major_radius: float,
        minor_radius: float,
        *,
        center: Sequence[float] = (0.0, 0.0, 0.0),
        normal: Sequence[float] = (0.0, 0.0, 1.0),
        x_direction: Sequence[float] | None = None,
    ) -> DomainValue:
        """Create a closed elliptical edge with major_radius >= minor_radius.

        ``x_direction`` aims the MAJOR axis, the way ``plane`` aims its own.
        Without it the major axis lands wherever rotating +Z onto ``normal``
        happens to send +X, which is why a section table that wants its wide
        axis vertical has to follow every ellipse with rotations
        (``docs/ORGANIC.md`` §1 measured thirty of them in one script).
        """

        operation = "ellipse"
        major = _number(operation, "major_radius", major_radius, minimum=0.0, strict=True)
        minor = _number(operation, "minor_radius", minor_radius, minimum=0.0, strict=True)
        if major < minor:
            raise _error(operation, "major_radius", "must be at least minor_radius", major_radius)
        clean_normal = _vector(operation, "normal", normal, nonzero=True)
        properties: dict[str, Any] = {
            "center": _vector(operation, "center", center),
            "normal": clean_normal,
        }
        if x_direction is not None:
            properties["x_direction"] = _in_plane_direction(
                operation, "x_direction", x_direction, clean_normal
            )
        return self._value(operation, "edge", major, minor, **properties)

    def bezier(
        self,
        poles: Sequence[Sequence[float]],
        *,
        weights: Sequence[float] = (),
    ) -> DomainValue:
        """Create a polynomial or exactly weighted rational Bezier edge."""

        operation = "bezier"
        if not isinstance(poles, (list, tuple)) or not 2 <= len(poles) <= 25:
            raise _error(operation, "poles", "expected 2-25 control points", poles)
        clean_poles = [
            _vector(operation, f"poles[{index}]", point)
            for index, point in enumerate(poles)
        ]
        return self._value(
            operation,
            "edge",
            clean_poles,
            weights=_weights(operation, weights, pole_count=len(clean_poles)),
        )

    def bspline(
        self,
        points: Sequence[Sequence[float]],
        *,
        periodic: bool = False,
        tolerance: float = 1.0e-7,
    ) -> DomainValue:
        """Interpolate a B-spline edge through at least three points."""

        operation = "bspline"
        if not isinstance(points, (list, tuple)) or len(points) < 3:
            raise _error(
                operation, "points", "expected at least three interpolation points", points
            )
        return self._value(
            operation,
            "edge",
            [_vector(operation, f"points[{index}]", point) for index, point in enumerate(points)],
            periodic=bool(periodic),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0, strict=True),
        )

    def nurbs_curve(
        self,
        poles: Sequence[Sequence[float]],
        degree: int,
        knots: Sequence[float],
        multiplicities: Sequence[int],
        *,
        weights: Sequence[float] = (),
        periodic: bool = False,
    ) -> DomainValue:
        """Create an exact polynomial or rational B-spline from its NURBS data."""

        operation = "nurbs_curve"
        if not isinstance(poles, (list, tuple)) or not 2 <= len(poles) <= 512:
            raise _error(operation, "poles", "expected 2-512 control poles", poles)
        clean_degree = _integer(operation, "degree", degree, minimum=1, maximum=25)
        if clean_degree >= len(poles):
            raise _error(operation, "degree", "must be smaller than the pole count", degree)
        if not isinstance(knots, (list, tuple)) or not 2 <= len(knots) <= 1024:
            raise _error(operation, "knots", "expected 2-1024 knot values", knots)
        clean_knots = [
            _number(operation, f"knots[{index}]", value)
            for index, value in enumerate(knots)
        ]
        if any(right <= left for left, right in zip(clean_knots, clean_knots[1:])):
            raise _error(operation, "knots", "values must be strictly increasing", knots)
        if not isinstance(multiplicities, (list, tuple)) or len(multiplicities) != len(
            clean_knots
        ):
            raise _error(
                operation,
                "multiplicities",
                f"expected exactly {len(clean_knots)} integer values",
                multiplicities,
            )
        clean_multiplicities = [
            _integer(
                operation,
                f"multiplicities[{index}]",
                value,
                minimum=1,
                maximum=clean_degree + 1,
            )
            for index, value in enumerate(multiplicities)
        ]
        if any(value > clean_degree for value in clean_multiplicities[1:-1]):
            raise _error(
                operation,
                "multiplicities",
                "interior knot multiplicities must not exceed degree",
                multiplicities,
            )
        if periodic:
            if clean_multiplicities[0] != clean_multiplicities[-1]:
                raise _error(
                    operation,
                    "multiplicities",
                    "a periodic curve requires equal first and last multiplicities",
                    multiplicities,
                )
            relation = sum(clean_multiplicities[:-1])
            expected_relation = len(poles)
        else:
            relation = sum(clean_multiplicities)
            expected_relation = len(poles) + clean_degree + 1
        if relation != expected_relation:
            raise _error(
                operation,
                "multiplicities",
                f"sum relation is {relation}, but this curve requires {expected_relation}",
                multiplicities,
            )
        clean_poles = [
            _vector(operation, f"poles[{index}]", point)
            for index, point in enumerate(poles)
        ]
        return self._value(
            operation,
            "edge",
            clean_poles,
            clean_degree,
            clean_knots,
            clean_multiplicities,
            weights=_weights(operation, weights, pole_count=len(clean_poles)),
            periodic=bool(periodic),
        )

    def helix(
        self,
        pitch: float,
        height: float,
        radius: float,
        *,
        angle: float = 0.0,
        left_handed: bool = False,
        vertical_height: bool = False,
        representation: str = "standard",
    ) -> DomainValue:
        """Create a standard or long-path segmented cylindrical/conical helix."""

        operation = "helix"
        clean_representation = str(representation or "").strip().lower()
        if clean_representation not in _HELIX_REPRESENTATIONS:
            raise _error(
                operation,
                "representation",
                f"must be one of {sorted(_HELIX_REPRESENTATIONS)}",
                representation,
            )
        if clean_representation == "segmented" and vertical_height:
            raise _error(
                operation,
                "vertical_height",
                "is available only for the standard representation",
                vertical_height,
            )
        return self._value(
            operation,
            "wire",
            _number(operation, "pitch", pitch, minimum=0.0, strict=True),
            _number(operation, "height", height, minimum=0.0, strict=True),
            _number(operation, "radius", radius, minimum=0.0, strict=True),
            angle=_number(operation, "angle", angle),
            left_handed=bool(left_handed),
            vertical_height=bool(vertical_height),
            representation=clean_representation,
        )

    def wire(
        self,
        items: Sequence[Any],
        *,
        closed: bool = False,
        label: str = "",
    ) -> DomainValue:
        """Create a wire from ordered Part edges or from ordered 3D points."""

        operation = "wire"
        if not isinstance(items, (list, tuple)) or len(items) < 1:
            raise _error(
                operation, "items", "expected one or more edges or at least two points", items
            )
        if all(isinstance(item, DomainValue) for item in items):
            values: list[Any] = _shapes(operation, "items", items, allowed={"edge", "wire"})
        else:
            if len(items) < 2:
                raise _error(operation, "items", "a point wire requires at least two points", items)
            values = [
                _vector(operation, f"items[{index}]", point) for index, point in enumerate(items)
            ]
        return self._value(operation, "wire", values, closed=bool(closed), label=label)

    def face(
        self,
        outer: DomainValue,
        *,
        holes: Sequence[DomainValue] = (),
        label: str = "",
    ) -> DomainValue:
        """Create a planar face from one closed outer wire and optional closed hole wires."""

        operation = "face"
        clean_holes = _shapes(operation, "holes", holes, minimum=0, allowed={"wire"})
        return self._value(
            operation,
            "face",
            _shape(operation, "outer", outer, allowed={"wire"}),
            holes=clean_holes,
            label=label,
        )

    def shell(self, faces: Sequence[DomainValue], *, label: str = "") -> DomainValue:
        """Sew an ordered set of faces into a shell."""

        operation = "shell"
        return self._value(
            operation,
            "shell",
            _shapes(operation, "faces", faces, allowed={"face"}),
            label=label,
        )

    def solid(self, shell: DomainValue, *, label: str = "") -> DomainValue:
        """Create a solid from one closed shell."""

        operation = "solid"
        return self._value(
            operation,
            "solid",
            _shape(operation, "shell", shell, allowed={"shell"}),
            label=label,
        )

    def compound(self, shapes: Sequence[DomainValue], *, label: str = "") -> DomainValue:
        """Publish heterogeneous Part topology as one compound without fusing it."""

        operation = "compound"
        return self._value(
            operation,
            "compound",
            _shapes(operation, "shapes", shapes),
            label=label,
        )

    def subshape(
        self,
        shape: DomainValue,
        kind: str,
        where: Mapping[str, Any],
        *,
        label: str = "",
    ) -> DomainValue:
        """Extract the one edge, wire, face, shell, or solid a selector names.

        ``where`` is a geometric selector, e.g.
        ``{"geometry_type": "Plane", "normal": [0, 0, 1]}``. It must match
        exactly one subshape or the operation fails with the candidates it
        did see.
        """

        operation = "subshape"
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in _SUBSHAPE_TYPES:
            raise _error(operation, "kind", f"must be one of {sorted(_SUBSHAPE_TYPES)}", kind)
        return self._value(
            operation,
            clean_kind,
            _shape(operation, "shape", shape),
            clean_kind,
            _selector(operation, "where", where, fixed_count=1),
            label=label,
        )

    def extrude(
        self,
        shape: DomainValue,
        vector: Sequence[float],
        *,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Extrude an edge to a face, a wire to a shell, or a face to a solid."""

        operation = "extrude"
        clean_shape = _shape(operation, "shape", shape, allowed={"edge", "wire", "face"})
        inferred = {"edge": "face", "wire": "shell", "face": "solid"}[clean_shape.output_type]
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred, exact=True),
            clean_shape,
            _vector(operation, "vector", vector, nonzero=True),
            label=label,
        )

    def revolve(
        self,
        shape: DomainValue,
        axis_origin: Sequence[float],
        axis_direction: Sequence[float],
        *,
        angle: float = 360.0,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Revolve an edge to a face, a wire to a shell, or a face to a solid."""

        operation = "revolve"
        clean_angle = _number(operation, "angle", angle, minimum=0.0, strict=True)
        if clean_angle > 360.0:
            raise _error(operation, "angle", "must not exceed 360 degrees", angle)
        clean_shape = _shape(operation, "shape", shape, allowed={"edge", "wire", "face"})
        inferred = {"edge": "face", "wire": "shell", "face": "solid"}[clean_shape.output_type]
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred, exact=True),
            clean_shape,
            _vector(operation, "axis_origin", axis_origin),
            _vector(operation, "axis_direction", axis_direction, nonzero=True),
            angle=clean_angle,
            label=label,
        )

    def loft(
        self,
        sections: Sequence[DomainValue],
        *,
        solid: bool = False,
        ruled: bool = False,
        closed: bool = False,
        max_degree: int = 5,
        on_bulge: str = "refuse",
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Loft through at least two wire sections; optionally create a solid.

        ``on_bulge`` guards the one way a loft lies to you: the surface is
        interpolated, so on an unevenly spaced table it can swing far outside
        the sections it was built from and still be a valid solid. The
        default refuses that with the millimetres; ``"allow"`` keeps the
        shape (ADR-129).
        """

        operation = "loft"
        inferred = "solid" if bool(solid) else "shell"
        clean_type = _inferred_result_type(operation, output_type, inferred, exact=True)
        return self._value(
            operation,
            clean_type,
            _shapes(operation, "sections", sections, minimum=2, allowed={"wire"}),
            solid=bool(solid),
            ruled=bool(ruled),
            closed=bool(closed),
            max_degree=_integer(operation, "max_degree", max_degree, minimum=1, maximum=25),
            on_bulge=_bulge_mode(operation, on_bulge),
            label=label,
        )

    def sweep(
        self,
        profile: DomainValue | Sequence[DomainValue],
        path: DomainValue,
        *,
        solid: bool = False,
        frenet: bool = False,
        transition: str = "transformed",
        scale_law: Sequence[Sequence[float]] | None = None,
        guide: DomainValue | None = None,
        guide_mode: str = "follow",
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Sweep one or more ordered wire profiles along one wire path.

        ``scale_law`` tapers the section as it travels: a list of
        ``[position, factor]`` control points, position running 0…1 along
        the path and factor scaling the profile about the path at that
        position. ``[[0, 1], [1, 0.1]]`` is a limb or a tail — the shape the
        wolf built by hand-placing five tilted circles and lofting them
        (``docs/ORGANIC.md`` §1).

        ``guide`` is a second wire the section obeys, and ``guide_mode``
        says how:

        - ``"follow"`` (the default) — the section is **scaled** at every
          station so its boundary rides the guide. This is the one you want:
          draw the silhouette you can see and the sweep takes that shape.
        - ``"touch"`` — the section is **moved** to touch the guide, keeping
          its size.
        - ``"orient"`` — the guide steers the section's orientation and
          nothing else.

        **One guide, not a list** — the kernel's pipe-shell takes exactly
        one auxiliary spine.
        """

        operation = "sweep"
        if isinstance(profile, DomainValue):
            clean_profile: DomainValue | list[DomainValue] = _shape(
                operation, "profile", profile, allowed={"wire"}
            )
        else:
            clean_profile = _shapes(
                operation,
                "profile",
                profile,
                allowed={"wire"},
            )
            if len(clean_profile) > 64:
                raise _error(
                    operation,
                    "profile",
                    "must contain at most 64 ordered wire profiles",
                    len(clean_profile),
                )
        clean_transition = str(transition or "").strip().lower()
        if clean_transition not in _TRANSITION_TYPES:
            raise _error(
                operation, "transition", f"must be one of {sorted(_TRANSITION_TYPES)}", transition
            )
        extra: dict[str, Any] = {}
        if scale_law is not None:
            if isinstance(clean_profile, list) and len(clean_profile) != 1:
                raise _error(
                    operation,
                    "scale_law",
                    "applies to a single profile; pass one profile, or place "
                    "the ordered sections yourself and leave the law out",
                    len(clean_profile),
                )
            extra["scale_law"] = _scale_law(operation, scale_law)
        positional: list[Any] = [
            clean_profile,
            _shape(operation, "path", path, allowed={"wire"}),
        ]
        if guide is not None:
            clean_mode = str(guide_mode or "").strip().lower()
            if clean_mode not in _GUIDE_MODES:
                raise _error(
                    operation,
                    "guide_mode",
                    f"must be one of {sorted(_GUIDE_MODES)}",
                    guide_mode,
                )
            positional.append(_shape(operation, "guide", guide, allowed={"wire"}))
            extra["guide_mode"] = clean_mode
        inferred = "solid" if bool(solid) else "shell"
        clean_type = _inferred_result_type(operation, output_type, inferred, exact=True)
        return self._value(
            operation,
            clean_type,
            *positional,
            solid=bool(solid),
            frenet=bool(frenet),
            transition=clean_transition,
            label=label,
            **extra,
        )

    def terminals(
        self,
        component: DomainValue,
        *,
        holes: Mapping[str, Any] | None = None,
        pads: Mapping[str, Any] | None = None,
        terminals: Sequence[Mapping[str, Any]] | None = None,
        header: Mapping[str, Any] | None = None,
        exit: Sequence[float] | None = None,
        order_by: Sequence[float] | None = None,
        names: Sequence[str],
    ) -> TerminalSet:
        """Name the places a wire attaches to one component (ADR-062).

        A **terminal** is a port that rides the geometry.  Where ``part.cable``
        took two hand-measured ``(point, direction)`` literals, this names
        them once, from the shape itself, and every wire that lands on this
        component refers to them by signal::

            fc = part.terminals(board,
                                holes={"geometry_type": "Cylinder",
                                       "radius": 0.5, "expected_count": 8},
                                exit=(0, 0, 1), order_by=(1, 0, 0),
                                names=["vbat", "gnd", "tx", "rx",
                                       "sda", "scl", "io4", "io5"])

            wire = part.cable(esp["sda"], fc["sda"], gauge_mm=0.4,
                              avoid=[frame])

        The result is **not** geometry.  It publishes nothing, appears in no
        tree row, and cannot be returned as an output; it exists to be
        subscripted by name and handed to ``part.cable`` or ``part.bundle``.

        **The selector forms.**  ``holes=`` and ``pads=`` are ADR-029
        selectors over this shape's faces, the same vocabulary ``fillet`` and
        ``subshape`` take, so the terminals move when the geometry does.

        - ``holes=`` names drilled barrels.  The terminal lands in the
          **near** face — the rim the wire arrives at, with its axis
          perpendicular to that rim's plane — and the bore behind it is left
          empty (ADR-117).  ``part.solder`` is what closes the gap, and it
          sits on the same rim.  ``exit=`` is **required** — a cylindrical
          face states an axis but not which end of it is outward, and
          inferring that from the solid's shape is wrong on any board that is
          not roughly symmetric.
        - ``pads=`` names flat contacts.  The terminal is the face's centre
          of mass, leaving along its normal (flipped to agree with ``exit=``
          when you give one, so a face's orientation in the shell is not
          something the script has to know about).

        ``order_by=`` is a **direction**, and it is what matches ``names`` to
        the matched faces: they are projected onto it and taken in ascending
        order, ties broken by a fixed secondary axis.  It is required as soon
        as there is more than one name.  Ordering is never the kernel's
        enumeration order — that is precisely the index reference ADR-029
        deleted, and a saved ``names`` list ordered that way would silently
        start naming different holes the moment a parameter changed topology.
        ``len(names)`` is the selector's ``expected_count``, so a selector
        that matches a different number of faces fails loudly, reporting both
        counts and every candidate it did see.

        **The declared form.**  ``header=`` (one row) or ``terminals=``
        (several) state a layout directly, for geometry that has no face to
        select::

            header=dict(origin=(-11.3, -4.0, 3.8), along=(0, 1, 0),
                        axis=(-1, 0, 0), pitch=2.54, count=4,
                        hole_dia=1.0, depth=1.6)

        ``origin`` is the first terminal's landing point — the mouth of the
        hole, on the surface the wire arrives at — ``along`` and ``pitch``
        step the row, and ``axis`` is the direction the holes are drilled
        *into* the body, so the wire leaves back along ``-axis``.  ``names``
        runs over the rows in declaration order.

        **``hole_dia`` is what makes a row a row of holes** (ADR-117); a row
        without one is pads.  ``depth`` is optional and descriptive: since
        the terminal lands in the mouth it sizes nothing, and it is reported
        rather than built from.

        On a *part* value the declared form is a fallback and the selector
        form is the recommended one: a part value is built in final
        coordinates, so declared numbers are world coordinates and go stale
        exactly like the literals they replace.  ``mesh.terminals`` is the
        other way round — there is no BREP face on a triangle mesh, so the
        declared form is all there is, and there the coordinates are the
        asset's own and ride its placement.
        """

        operation = "terminals"
        forms = {
            "holes": holes,
            "pads": pads,
            "terminals": terminals,
            "header": header,
        }
        given = sorted(name for name, value in forms.items() if value is not None)
        if len(given) != 1:
            raise _error(
                operation,
                "holes/pads/terminals/header",
                "state exactly one of holes= (drilled barrels), pads= (flat "
                "contacts), header= (one declared row) or terminals= (several "
                f"declared rows); received {given or 'none'}",
            )
        clean_component = _shape(operation, "component", component)
        form = given[0]
        if form in {"holes", "pads"}:
            if not isinstance(names, (list, tuple)) or isinstance(names, str) or not names:
                raise _error(
                    operation, "names", "expected a non-empty list of signal names", names
                )
            layout = _terminal_layout(
                operation,
                selector_layout,
                kind=form,
                selector=_selector(
                    operation, form, forms[form], fixed_count=len(names)
                ),
                exit=exit,
                order_by=order_by,
                names=names,
            )
        else:
            if exit is not None or order_by is not None:
                raise _error(
                    operation,
                    "exit/order_by",
                    "a declared layout already states its own axis and its own "
                    "order, so exit= and order_by= have nothing to do here",
                )
            layout = _terminal_layout(
                operation,
                declared_layout,
                entries=terminals,
                header=header,
                names=names,
            )
        return TerminalSet(clean_component, layout)

    def cable(
        self,
        start: Sequence[Sequence[float]],
        end: Sequence[Sequence[float]],
        *,
        gauge_mm: float,
        clearance_mm: float = 1.0,
        avoid: Sequence[DomainValue] = (),
        slack: float = 1.05,
        min_bend_radius_mm: float | None = None,
        cell_mm: float | None = None,
        waypoints: Sequence[Sequence[float]] | None = None,
        label: str = "",
    ) -> DomainValue:
        """Route a wire between two connection points and sweep it as a solid.

        The harness operation: you declare where the wire attaches, not where
        it goes.  ``gauge_mm`` is the outer diameter of the insulated
        conductor, and the result is one ``solid``.

        **Two or more wires are a harness, and a harness is declared with**
        ``nets(ports=..., wires=...)`` **and built from its rows** (ADR-065).
        Calling this directly is right for a one-off; a set of bare calls is
        read-only in the wiring editor, because nothing outside the script
        text names a row for the user to edit.

        Each end is a **terminal** from ``part.terminals``/``mesh.terminals``,
        or a literal ``(point, direction)`` pair — interchangeably, at either
        end.  Prefer the terminal: it is named, and it is derived from the
        component's geometry on every rebuild, so it rides a slider instead
        of going stale (ADR-062).  A literal's point sits on a component's
        surface and its direction points away from it, which is exactly the
        ``center_mm`` and ``normal`` a picked pad resolves to::

            part.cable(esp["sda"], board["sda"],
                       gauge_mm=0.4, avoid=[frame])
            part.cable(((0, 4, 8.6), (0, 1, 0)),
                       ((12, 9, 6.2), (0, 0, 1)),
                       gauge_mm=0.8, avoid=[frame, flight_controller])

        A terminal on a through-hole lands **in the mouth** of the hole — in
        the plane of the rim, with its axis perpendicular to it — and not at
        the bottom of the barrel (ADR-117). The bore behind it is left empty;
        ``part.solder`` is what closes the gap, and it sits on the same rim.

        The route is searched afresh on every rebuild, so a cable follows the
        things it connects: change a parameter that moves a component and the
        wire re-routes and stays attached.  **Never paste a computed route
        back into the script to save the search** — a cache of what the search
        would produce anyway is wrong the moment a parameter moves, and
        silently so.

        ``waypoints`` is the other thing, and it is not that (ADR-118).  It is
        a list of interior points, in the same coordinates the ports resolve
        in, stating a path the search cannot be asked for::

            part.cable(esp["sda"], board["sda"], gauge_mm=0.4,
                       avoid=[frame], waypoints=[(12, 4, 20), (30, 4, 20)])

        When it is given **the search does not run at all**: the spine is the
        stub out of each port, these points, and the stub back into the other.
        That is authored intent, exactly as ``avoid`` is — the difference from
        a cached route is that nothing would ever have computed these.

        **Only the interior is authored.**  Both ends still ride their
        terminals, so a slider that moves a board still moves both ends of the
        wire and a joint still grips a straight lead.  What does *not* move is
        the middle: a hand-placed waypoint stays where it was put, so a
        parameter that moves a component past it will drag the wire through
        whatever is there.  That is real, and it is why this is a deliberate
        gesture rather than a default.

        The path is still checked.  It is rasterised against the same ``avoid``
        occupancy the search would have used and refused with
        ``reason="waypoints_blocked"`` and the index of the first blocked
        segment; ``min_bend_radius_mm`` still applies, and matters *more* here,
        because a dragged hairpin is easy to make and folds the sweep.
        ``slack`` and ``cell_mm`` are search parameters and are **ignored**
        when ``waypoints`` is given — neither can be told apart from its own
        default, so they are documented rather than refused.

        ``avoid`` is what the wire must go around, and it takes ``part``
        values and ``mesh`` values mixed, because a real harness runs between
        printed structure and imported modules.  Obstacles are inflated by
        ``clearance_mm``, and the wire leaves each port along that port's own
        direction before the search starts — a port is *on* a surface, so its
        own neighbourhood is inside something by construction.

        **Name everything the run passes over, including the wires already
        routed.**  An empty ``avoid`` is an empty lattice: the route is then a
        straight line, and ``slack`` sags it through whatever happens to be
        under it — most often the two boards the wire lands on.  Feeding each
        finished cable into the next one's ``avoid`` is what stops a set of
        wires between the same two components sharing one corridor.

        **A mesh obstacle is tested by its bounding box, not its triangles.**
        Accurate enough for the roughly box-shaped modules a harness connects,
        and wrong for anything concave or enclosing: pass such a body as the
        ``part`` solid it is.  A frame handed over as a mesh has a bounding
        box containing the whole model and would block every route.

        That box is also why a component **cannot avoid itself as a mesh**: a
        pad on its top face is inside its own bounding box, so the route has
        nowhere to start and refuses with ``blocked`` — "no clear corridor
        connects the two ports".  Convert it with ``part.shape_from_mesh``
        (only the surface is rasterised, so its own pad stays reachable) when
        the import is watertight enough to convert, and otherwise keep it out
        of ``avoid`` and hold the wire off it with ``slack`` near 1.0.

        ``slack`` (at least 1.0) is how much longer than taut the wire hangs.
        It is a *sag*, applied downward along the run, so on a short hop
        between two boards the default 1.05 is already several millimetres of
        drop: state ``1.01`` there rather than inheriting a droop the run has
        no room for.  Not ``1.0``, when the route comes back straight — a
        sweep along a perfectly collinear spine fails in the kernel
        (``BRepOffsetAPI_MakePipeShell::MakeSolid``), and the hundredth of a
        millimetre of sag is what keeps the spine a curve.
        ``min_bend_radius_mm`` rejects a route that kinks tighter than the
        conductor tolerates, rather than modelling an impossible wire.
        ``cell_mm`` overrides the search resolution, which otherwise follows
        the gauge and clearance; finer finds tighter gaps and costs more.

        Like ``shape_from_mesh``, it refuses an obstacle built with
        ``mesh.decimate``: that result is not reproducible (ADR-016), and a
        route around a moving obstacle is a moving route, which changes the
        project digest on every rebuild.
        """

        operation = "cable"
        clean_start = _port(operation, "start", start)
        clean_end = _port(operation, "end", end)
        _port_separation(operation, "start/end", clean_start, clean_end)
        clean_slack = _number(operation, "slack", slack, minimum=1.0)
        properties: dict[str, Any] = {
            "gauge_mm": _number(operation, "gauge_mm", gauge_mm, minimum=0.0, strict=True),
            "clearance_mm": _number(operation, "clearance_mm", clearance_mm, minimum=0.0),
            "slack": clean_slack,
            "avoid": _obstacles(operation, "avoid", avoid),
        }
        if min_bend_radius_mm is not None:
            properties["min_bend_radius_mm"] = _number(
                operation, "min_bend_radius_mm", min_bend_radius_mm, minimum=0.0, strict=True
            )
        if cell_mm is not None:
            properties["cell_mm"] = _number(
                operation, "cell_mm", cell_mm, minimum=0.0, strict=True
            )
        if waypoints is not None:
            properties["waypoints"] = _waypoints(operation, "waypoints", waypoints)
        return self._value(
            operation,
            "solid",
            clean_start,
            clean_end,
            label=label,
            **properties,
        )

    def bundle(
        self,
        connections: Sequence[Sequence[Sequence[float]]],
        *,
        gauge_mm: float,
        conductor: int,
        style: str = "twisted",
        twist_pitch_mm: float | None = None,
        left_handed: bool = False,
        spacing_mm: float | None = None,
        up: Sequence[float] | None = None,
        breakout_mm: float | None = None,
        clearance_mm: float = 1.0,
        avoid: Sequence[DomainValue] = (),
        slack: float = 1.05,
        min_bend_radius_mm: float | None = None,
        cell_mm: float | None = None,
        label: str = "",
    ) -> DomainValue:
        """Route several wires along one shared path and sweep one of them.

        The multi-conductor harness operation.  A battery lead is a red/black
        pair, a brushless motor takes three phase wires and an I2C run is four:
        modelled as separate ``part.cable`` calls those route independently and
        drift apart, which is neither what the object looks like nor what it
        costs.  A bundle searches **one** route for all of them and lays the
        conductors around it — twisted helically, or flat side by side —
        separating only at the ends, where each lands on its own port.

        ``connections`` is one ``(start_port, end_port)`` pair per conductor,
        and each port is whatever ``part.cable`` takes — a terminal or a
        literal pair, mixed freely.  ``conductor`` is the 0-based index of
        the one *this call* returns, so N conductors are N calls that differ
        only in that index::

            pair = [(batt_pos, esc_pos), (batt_neg, esc_neg)]
            red   = part.bundle(pair, gauge_mm=1.6, conductor=0, avoid=[frame])
            black = part.bundle(pair, gauge_mm=1.6, conductor=1, avoid=[frame])

        Each call is one ``solid`` and therefore **one row in the model tree**,
        which is what lets you select, colour and measure a single wire.  The
        shared route is searched once and reused, so the pair above costs one
        search, not two.

        ``style`` is ``"twisted"`` (the default) or ``"flat"``.

        **Twisted.**  ``twist_pitch_mm`` is the lay length — how far along the
        run the bundle turns through one full revolution — and defaults to a
        real-harness value derived from the gauge and the conductor count.
        ``left_handed`` reverses the lay.  The radius the conductors sit at is
        *computed*, not chosen: it is the smallest radius at which no two
        conductors touch.  Because neighbouring helices reach their closest
        approach at an axial offset rather than in a shared cross-section, a
        lay only exists at all when ``twist_pitch_mm > len(connections) *
        gauge_mm``; a tighter pitch is refused with that floor named.

        **Flat.**  ``spacing_mm`` is the centre-to-centre lane pitch and
        defaults to ``gauge_mm``, so the conductors touch.  They are separate
        tangent solids — there is no web between them and nothing is fused.
        ``up`` orients the ribbon where the run starts (default ``(0, 0, 1)``,
        which makes it lie flat); the ribbon then carries that orientation
        along the route rather than re-levelling itself, which is what a real
        ribbon cable does.

        **The order of ``connections`` is the order around the bundle.**
        Conductor ``k`` takes phase ``k`` of the lay, or lane ``k`` of the
        ribbon, counting from one edge.  Two conductors whose ports are laid
        out opposite to their order will cross once near the breakout — which
        is what a real harness does, and which you fix by reordering
        ``connections``.  It is not fixed automatically, because on a twisted
        run the phase rotates along the route and the two ends cannot both be
        matched.

        ``breakout_mm`` is how far the bundle stands off each end before the
        conductors fan out to their own ports; it defaults to a multiple of the
        bundle's own diameter, which is the room the fan-out actually needs.
        ``avoid``, ``clearance_mm``, ``slack``, ``cell_mm`` and
        ``min_bend_radius_mm`` mean what they do on ``part.cable``, and apply
        to the bundle as a whole: the route is searched at the bundle's outer
        diameter, so the corridor clears the whole lay rather than one wire.
        ``min_bend_radius_mm`` is checked against each conductor's own path,
        where the lay's curvature and the route's add up.  Read ``part.cable``
        on what belongs in ``avoid`` and on ``slack`` over a short hop: the
        same rules apply here, per bundle rather than per conductor.

        A bundle's *membership* is a script decision and never a table one, so
        ``nets(...)`` does not own it — but the wires it lays are still rows
        the editor draws, and a project with a bundle in it declares the rest
        of its harness with ``nets`` exactly as it would otherwise.

        Like ``part.cable`` it refuses an obstacle built with ``mesh.decimate``,
        whose result is not reproducible (ADR-016).
        """

        operation = "bundle"
        if not isinstance(connections, (list, tuple)) or len(connections) < 2:
            raise _error(
                operation,
                "connections",
                "expected at least two (start_port, end_port) pairs; a single "
                "wire is part.cable",
                connections,
            )
        clean_connections: list[list[list[list[float]]]] = []
        for index, pair in enumerate(connections):
            name = f"connections[{index}]"
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise _error(
                    operation, name, "expected a (start_port, end_port) pair", pair
                )
            start = _port(operation, f"{name}[0]", pair[0])
            end = _port(operation, f"{name}[1]", pair[1])
            _port_separation(operation, name, start, end)
            clean_connections.append([start, end])
        clean_style = str(style)
        if clean_style not in _LAY_STYLES:
            raise _error(
                operation,
                "style",
                f"expected one of {sorted(_LAY_STYLES)}",
                style,
            )
        properties: dict[str, Any] = {
            "conductor": _integer(
                operation,
                "conductor",
                conductor,
                minimum=0,
                maximum=len(clean_connections) - 1,
            ),
            "gauge_mm": _number(operation, "gauge_mm", gauge_mm, minimum=0.0, strict=True),
            "style": clean_style,
            "left_handed": bool(left_handed),
            "clearance_mm": _number(operation, "clearance_mm", clearance_mm, minimum=0.0),
            "slack": _number(operation, "slack", slack, minimum=1.0),
            "avoid": _obstacles(operation, "avoid", avoid),
        }
        if twist_pitch_mm is not None:
            properties["twist_pitch_mm"] = _number(
                operation, "twist_pitch_mm", twist_pitch_mm, minimum=0.0, strict=True
            )
        if spacing_mm is not None:
            properties["spacing_mm"] = _number(
                operation, "spacing_mm", spacing_mm, minimum=0.0, strict=True
            )
        if up is not None:
            properties["up"] = _vector(operation, "up", up, nonzero=True)
        if breakout_mm is not None:
            properties["breakout_mm"] = _number(
                operation, "breakout_mm", breakout_mm, minimum=0.0, strict=True
            )
        if min_bend_radius_mm is not None:
            properties["min_bend_radius_mm"] = _number(
                operation, "min_bend_radius_mm", min_bend_radius_mm, minimum=0.0, strict=True
            )
        if cell_mm is not None:
            properties["cell_mm"] = _number(
                operation, "cell_mm", cell_mm, minimum=0.0, strict=True
            )
        return self._value(
            operation,
            "solid",
            clean_connections,
            label=label,
            **properties,
        )

    def solder(
        self,
        terminal: Any,
        *,
        gauge_mm: float,
        pad_dia_mm: float | None = None,
        fillet_mm: float | None = None,
        refine: bool = True,
        label: str = "",
    ) -> DomainValue:
        """Build the joint that lands a wire on the component it connects to.

        The third harness operation.  ``part.cable`` and ``part.bundle`` sweep
        a conductor that stops flush on a face or in a bore, and nothing joins
        it to the board — which is visibly wrong on a render, and is the last
        thing between a routed harness and a model that looks like the object.
        One call is one joint and one ``solid``::

            fc = part.terminals(board, holes={"geometry_type": "Cylinder"},
                                exit=(0, 0, 1), order_by=(1, 0, 0),
                                names=["vcc", "gnd", "sda", "scl"])
            wire  = part.cable(esp["sda"], fc["sda"], gauge_mm=0.4)
            joint = part.solder(fc["sda"], gauge_mm=0.4, label="sda joint")

        **It takes a terminal, never a literal port.**  A joint is built from
        the bore's radius and depth and the two faces it runs between, and a
        literal ``(point, direction)`` pair carries none of that.  This is the
        first operation a terminal *unlocks* rather than merely improves.

        **A hole and a pad build the same joint** (ADR-117): a meniscus fillet
        sitting on the face the lead lands on, a short collar hugging the lead
        and a round-over onto it.  A hole terminal lands in the mouth of its
        bore rather than at the bottom of it, so there is no barrel to fill and
        no far face to cap — the bore interior is left empty by design.  What
        the hole still contributes is its own radius: the joint defaults to
        twice that diameter across, and refuses to be narrower than the rim it
        rings.  Everything is sized from the terminal, so the joint moves when
        the terminal does — which is the whole point of both.

        The meniscus is **concave**: it sweeps up off the pad, flattens as it
        reaches the lead, and then runs parallel to the wire for a short collar
        that stands a tenth of the lead's radius clear of it.  That is what
        stops a joint reading as a cone on a render.

        ``gauge_mm`` is required, and is the same number the ``cable`` or
        ``bundle`` that lands here was given.

        ``pad_dia_mm`` is how far the joint spreads across the face.  It
        defaults to twice the bore diameter on a hole, and to the
        equivalent-area diameter of the matched face on a ``pads=`` terminal.
        A *declared* pad carries no area, so there it is required.  It sizes a
        bore joint exactly as it sizes a pad joint.

        ``fillet_mm`` is how far the meniscus climbs the lead, and defaults to
        the width of pad the meniscus sweeps across — which makes the arc an
        exact quarter round, tangent to the board where it lands and tangent to
        the lead where it arrives.  That default is also the floor: a shorter
        fillet spreads further than it climbs, so it would meet the board from
        underneath.  The collar's height and the cap's both derive from it; a
        joint has enough numbers.

        **``bore_dia_mm`` was removed in ADR-117** and passing it is a
        ``TypeError``.  It only ever sized the barrel of plating, and there is
        no barrel: state how far the joint spreads with ``pad_dia_mm``, and how
        wide the hole itself is with ``hole_dia`` on the layout.

        Every refusal names the value it measured and the one it conflicts
        with: a lead that does not fit its bore, a pad narrower than the hole
        it rings, a hole whose width was never measured.
        """

        operation = "solder"
        clean_terminal = _solder_terminal(operation, "terminal", terminal)
        properties: dict[str, Any] = {
            "gauge_mm": _number(
                operation, "gauge_mm", gauge_mm, minimum=0.0, strict=True
            ),
            "refine": bool(refine),
        }
        # Each override is omitted when unset rather than defaulted here: what
        # it falls back to is geometry, and geometry resolves in the worker.
        for name, value in (
            ("pad_dia_mm", pad_dia_mm),
            ("fillet_mm", fillet_mm),
        ):
            if value is not None:
                properties[name] = _number(
                    operation, name, value, minimum=0.0, strict=True
                )
        return self._value(
            operation,
            "solid",
            clean_terminal,
            label=label,
            **properties,
        )

    def ruled_surface(
        self,
        first: DomainValue,
        second: DomainValue,
        *,
        label: str = "",
    ) -> DomainValue:
        """Create a ruled face between edges or a ruled shell between wires."""

        operation = "ruled_surface"
        clean_first = _shape(operation, "first", first, allowed={"edge", "wire"})
        clean_second = _shape(operation, "second", second, allowed={"edge", "wire"})
        if clean_first.output_type != clean_second.output_type:
            raise _error(
                operation,
                "first/second",
                "both sections must have the same topology type",
            )
        output_type = "face" if clean_first.output_type == "edge" else "shell"
        return self._value(operation, output_type, clean_first, clean_second, label=label)

    def filled_surface(
        self,
        boundaries: Sequence[DomainValue],
        *,
        label: str = "",
    ) -> DomainValue:
        """Fill ordered edges/wires or the boundary of a face with an OCC surface."""

        operation = "filled_surface"
        return self._value(
            operation,
            "face",
            _shapes(
                operation,
                "boundaries",
                boundaries,
                minimum=1,
                allowed={"edge", "wire", "face"},
            ),
            label=label,
        )

    def fuse(
        self,
        shapes: Sequence[DomainValue],
        *,
        tolerance: float = 0.0,
        refine: bool = True,
        blend: float | None = None,
        blend_on_failure: str = "refuse",
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Boolean-union shapes in one OCC operation with optional fuzzy tolerance.

        ``blend`` rounds the SEAMS the union just made — the edges that lie
        on two or more of the inputs — and nothing else. That is the one
        selection a script cannot write for itself: how many intersection
        curves a boolean produced is knowable only to the boolean
        (``docs/ORGANIC.md`` §1). ``blend_on_failure`` is ``fillet``'s
        ``on_failure``, applied to that seam set.
        """

        operation = "fuse"
        clean_shapes = _shapes(operation, "shapes", shapes, minimum=2)
        inferred = clean_shapes[0].output_type
        if inferred == "edge" or any(shape.output_type != inferred for shape in clean_shapes[1:]):
            if output_type is None:
                raise _error(
                    operation,
                    "output_type",
                    "is required when input topology types differ or are non-publishable edges",
                )
            inferred = "compound"
        extra: dict[str, Any] = {}
        if blend is not None:
            extra["blend"] = _number(operation, "blend", blend, minimum=0.0, strict=True)
            extra["blend_on_failure"] = _blend_failure_mode(operation, blend_on_failure)
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred),
            clean_shapes,
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0),
            refine=bool(refine),
            label=label,
            **extra,
        )

    def cut(
        self,
        base: DomainValue,
        tools: Sequence[DomainValue] | DomainValue,
        *,
        tolerance: float = 0.0,
        refine: bool = True,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Subtract tools in one OCC operation with optional fuzzy tolerance."""

        operation = "cut"
        clean_base = _shape(operation, "base", base)
        if clean_base.output_type == "edge" and output_type is None:
            raise _error(operation, "output_type", "is required when the base is an edge")
        inferred = clean_base.output_type if clean_base.output_type != "edge" else "compound"
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred),
            clean_base,
            _shapes(operation, "tools", tools),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0),
            refine=bool(refine),
            label=label,
        )

    def common(
        self,
        shapes: Sequence[DomainValue],
        *,
        tolerance: float = 0.0,
        refine: bool = True,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Boolean-intersect shapes in one OCC operation with optional fuzzy tolerance."""

        operation = "common"
        clean_shapes = _shapes(operation, "shapes", shapes, minimum=2)
        inferred = clean_shapes[0].output_type
        if inferred == "edge" or any(shape.output_type != inferred for shape in clean_shapes[1:]):
            if output_type is None:
                raise _error(
                    operation,
                    "output_type",
                    "is required when input topology types differ or are non-publishable edges",
                )
            inferred = "compound"
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred),
            clean_shapes,
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0),
            refine=bool(refine),
            label=label,
        )

    def section(
        self,
        left: DomainValue,
        right: DomainValue,
        *,
        tolerance: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Compute intersection edges between two shapes as a compound."""

        operation = "section"
        return self._value(
            operation,
            "compound",
            _shape(operation, "left", left),
            _shape(operation, "right", right),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0),
            label=label,
        )

    def general_fuse(
        self,
        shapes: Sequence[DomainValue],
        *,
        tolerance: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Fragment all inputs at intersections and return every touching piece."""

        operation = "general_fuse"
        return self._value(
            operation,
            "compound",
            _shapes(operation, "shapes", shapes, minimum=2),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0),
            label=label,
        )

    def slice(
        self,
        shape: DomainValue,
        normal: Sequence[float],
        offsets: Sequence[float],
        *,
        label: str = "",
    ) -> DomainValue:
        """Intersect a shape with planes normal to a direction at signed offsets."""

        operation = "slice"
        if not isinstance(offsets, (list, tuple)) or not offsets:
            raise _error(operation, "offsets", "expected one or more signed distances", offsets)
        clean_offsets = [
            _number(operation, f"offsets[{index}]", value) for index, value in enumerate(offsets)
        ]
        if len(set(clean_offsets)) != len(clean_offsets):
            raise _error(operation, "offsets", "must not contain duplicates", offsets)
        return self._value(
            operation,
            "compound",
            _shape(operation, "shape", shape),
            _vector(operation, "normal", normal, nonzero=True),
            clean_offsets,
            label=label,
        )

    def defeature(
        self,
        shape: DomainValue,
        faces: Mapping[str, Any],
        *,
        label: str = "",
    ) -> DomainValue:
        """Heal a solid after removing the feature faces a selector names.

        ``faces`` is a geometric selector, e.g. removing four drilled holes:
        ``{"geometry_type": "Cylinder", "radius": 3.0, "expected_count": 4}``.
        """

        operation = "defeature"
        clean_shape = _shape(operation, "shape", shape, allowed={"solid"})
        return self._value(
            operation,
            "solid",
            clean_shape,
            _selector(operation, "faces", faces),
            label=label,
        )

    def to_nurbs(self, shape: DomainValue, *, label: str = "") -> DomainValue:
        """Convert analytic curves and surfaces to an exact NURBS representation."""

        operation = "to_nurbs"
        clean_shape = _shape(operation, "shape", shape)
        return self._value(operation, clean_shape.output_type, clean_shape, label=label)

    def reverse(self, shape: DomainValue, *, label: str = "") -> DomainValue:
        """Return a copy with its OCC topology orientation reversed."""

        operation = "reverse"
        clean_shape = _shape(operation, "shape", shape)
        return self._value(operation, clean_shape.output_type, clean_shape, label=label)

    def fillet(
        self,
        shape: DomainValue,
        radius: float,
        *,
        edges: str | Mapping[str, Any] = "all",
        radius_end: float | None = None,
        on_failure: str = "refuse",
        label: str = "",
    ) -> DomainValue:
        """Round the edges a selector names, or every edge with edges='all'.

        ``edges`` is ``'all'`` or a geometric selector, e.g.
        ``{"geometry_type": "Circle", "radius": 3.0, "expected_count": 8}``.

        ``radius_end`` makes the blend VARIABLE: the radius evolves from
        ``radius`` at the start of each edge to ``radius_end`` at its end.
        That is the difference between a machined transition and a muscular
        one, and it costs one argument.

        ``on_failure`` says what to do when the kernel accepts some of the
        selection and not the rest — which is the normal case on a fused
        organic body, where one impossible edge used to throw away every
        other one. ``'refuse'`` (default) fails and reports which edges were
        refused, how many did blend, and the largest radius the whole
        selection accepts. ``'skip'`` blends the ones that work and leaves
        the rest sharp. ``'reduce'`` applies the largest radius that works
        everywhere, and the applied radius is reported.
        """

        operation = "fillet"
        clean_shape = _shape(operation, "shape", shape, allowed={"solid", "shell"})
        extra: dict[str, Any] = {}
        if radius_end is not None:
            extra["radius_end"] = _number(
                operation, "radius_end", radius_end, minimum=0.0, strict=True
            )
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            _number(operation, "radius", radius, minimum=0.0, strict=True),
            edges=_selector(operation, "edges", edges, allow_all=True),
            on_failure=_blend_failure_mode(operation, on_failure),
            label=label,
            **extra,
        )

    def sew(
        self,
        shapes: Sequence[DomainValue],
        *,
        output_type: str = "shell",
        label: str = "",
    ) -> DomainValue:
        """Sew touching faces/shells; a closed sewn shell may be promoted to a solid."""

        operation = "sew"
        clean_type = _result_type(operation, output_type)
        if clean_type not in {"shell", "solid", "compound"}:
            raise _error(
                operation,
                "output_type",
                "must be 'shell', 'solid', or 'compound'",
                output_type,
            )
        return self._value(
            operation,
            clean_type,
            _shapes(
                operation,
                "shapes",
                shapes,
                allowed={"face", "shell", "compound"},
            ),
            label=label,
        )

    def shape_from_mesh(
        self,
        mesh: DomainValue,
        *,
        tolerance: float = 0.1,
        sew: bool = True,
        solid: bool = True,
        label: str = "",
    ) -> DomainValue:
        """Convert a Mesh api value into BREP topology this api can build on.

        The way an imported STL/OBJ/PLY component becomes real geometry:
        ``part.cut(plate, part.shape_from_mesh(mesh.import_file("scan.stl")))``.
        Yields a ``solid`` (or a ``shell`` with ``solid=False``), consumable by
        the part, partdesign and assembly domains.

        Two things it is not. **It is not feature-editable**: a converted STL
        is a shell of thousands of planar triangle faces, so geometric
        selectors (``subshape``, ``fillet``, ``chamfer``) are near-useless on
        it and BREP booleans against it are slow. It is for cutting clearance
        against, not for editing. **It refuses an approximating mesh tree**:
        ``mesh.decimate`` is not reproducible (ADR-016), and a BREP output's
        digest identity *is* its exported bytes, with no by-definition
        fallback — so decimate offline and import the reduced file, or publish
        the decimated value as a ``mesh`` output instead.
        """

        operation = "shape_from_mesh"
        clean_mesh = _mesh_value(operation, "mesh", mesh)
        if solid and not sew:
            raise _error(
                operation,
                "sew",
                "a solid needs sewn faces; pass sew=True, or solid=False for "
                "the unsewn shell",
                sew,
            )
        if not payload_tree_is_deterministic(clean_mesh.to_payload()):
            raise _error(
                operation,
                "mesh",
                "the mesh was built with decimate, whose result is not "
                "reproducible, so a BREP built from it would change the "
                "project digest on every rebuild; decimate the file offline "
                "and import the reduced mesh, or publish the decimated value "
                "as a mesh output",
            )
        return self._value(
            operation,
            "solid" if solid else "shell",
            clean_mesh,
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0, strict=True),
            sew=bool(sew),
            label=label,
        )

    def import_part(self, filename: str, *, label: str = "") -> DomainValue:
        """Build on a part authored in **another project**, losslessly.

        ``part.import_part("sensor.cxpart")`` reads one ``.cxpart`` container
        placed directly in this project's assets directory, and yields the
        exact OCCT solid the other project accepted — not a tessellation of
        it::

            sensor = part.import_part("sensor.cxpart")
            mount = part.cut(plate, sensor)
            body = assembly.component(sensor, grounded=True)

        This is the lossless half of the pair ``shape_from_mesh`` opens. That
        one takes an STL through triangles and lands a shell of thousands of
        planar faces that selectors are near-useless on; this one carries the
        BREP itself, so the imported part has the forty faces it was authored
        with and ``subshape``, ``fillet`` and a boolean all behave as they do
        on a solid built here. It is consumable everywhere a part value is,
        ``assembly.component`` included.

        **A snapshot, not a live link** (ADR-138). The container holds one
        accepted revision of the other project, and it changes when — and
        only when — somebody links it again. That is deliberate: a rebuild of
        this project must not depend on another project's current state, and
        a part that moved under a model without being asked is worse than one
        that is out of date and says so.

        The container arrives through the ``link_part`` op, which pulls it
        from the source project and stores it here. Its bytes are
        authenticated against the digest its own header records before
        anything is built from them.
        """

        operation = "import_part"
        return self._value(
            operation,
            "solid",
            _asset_filename(operation, filename, suffixes=_LINKED_PART_SUFFIXES),
            label=label,
        )

    def measurement(
        self,
        shape: DomainValue,
        *,
        kind: str = "distance",
        start: Mapping[str, Any] | None = None,
        end: Mapping[str, Any] | None = None,
        at: Mapping[str, Any] | None = None,
        axis: str = "",
        element_type: str = "face",
        label: str = "",
        places: int = 2,
    ) -> DomainValue:
        """Declare a dimension on this shape, drawn like a drawing's (ADR-139).

        A measurement is a **declared output that carries no geometry**. It
        publishes two exact anchor points and a formatted number; the shell
        draws them as an architectural dimension — an extension line at each
        anchor, a dimension line between them, the number in the middle::

            plate  = part.box(60, 40, 10)
            bored  = part.cut(plate, part.cylinder(3, 20))

            height = part.measurement(bored, kind="extent", axis="z",
                                      label="overall height")
            bore   = part.measurement(bored, kind="diameter",
                                      at={"geometry_type": "Cylinder",
                                          "radius": 3.0})

            result = {"bored": bored, "height": height, "bore": bore}

        Three kinds:

        - ``"distance"`` — between the two subshapes ``start`` and ``end``
          name. The kernel's own closest-approach calculation supplies both
          the value and the two anchor points, so a plate's thickness, a
          boss's height and the gap between two ribs are all the same call.
        - ``"diameter"`` — of the one circular edge or cylindrical face ``at``
          names.
        - ``"extent"`` — the shape's overall span along ``axis``. This is what
          "from the top of the part to the bottom" means on anything that is
          not a box: a dome has no pair of planar faces to name, and its
          height is a property of the whole solid.

        ``element_type`` says whether ``start``/``end``/``at`` resolve against
        faces or edges, exactly as ``fillet``'s ``edges=`` names its own kind.
        It applies to both ends; measuring a face to an edge is not in this
        slice.

        **It is anchored by selector, not by ordinal**, so it survives a
        rebuild the way every other selector does — and fails loudly, naming
        the selector, when a change removes what it measured. A measurement
        moves when a parameter moves it, because it is recomputed from the
        shape rather than remembered.

        ``places`` is how many decimals the number is formatted to. The text
        is formatted here rather than in the viewport, so a screenshot and a
        chat reply can never disagree about what a part measures.
        """

        operation = "measurement"
        clean_shape = _shape(operation, "shape", shape)
        clean_kind = str(kind or "")
        if clean_kind not in _MEASUREMENT_KINDS:
            raise _error(
                operation,
                "kind",
                f"must be one of {sorted(_MEASUREMENT_KINDS)}",
                kind,
            )
        clean_elements = str(element_type or "")
        if clean_elements not in _MEASURED_ELEMENT_TYPES:
            raise _error(
                operation,
                "element_type",
                f"must be one of {sorted(_MEASURED_ELEMENT_TYPES)}",
                element_type,
            )

        properties: dict[str, Any] = {
            "kind": clean_kind,
            "element_type": clean_elements,
            "places": _places(operation, places),
        }
        if clean_kind == "distance":
            if start is None or end is None:
                raise _error(
                    operation,
                    "start/end",
                    "kind='distance' needs both start= and end= selectors",
                )
            properties["start"] = _selector(operation, "start", start, fixed_count=1)
            properties["end"] = _selector(operation, "end", end, fixed_count=1)
        elif clean_kind == "diameter":
            if at is None:
                raise _error(
                    operation, "at", "kind='diameter' needs an at= selector"
                )
            properties["at"] = _selector(operation, "at", at, fixed_count=1)
        else:
            clean_axis = str(axis or "").lower()
            if clean_axis not in _MEASURED_AXES:
                raise _error(
                    operation,
                    "axis",
                    f"kind='extent' needs axis= to be one of {sorted(_MEASURED_AXES)}",
                    axis,
                )
            properties["axis"] = clean_axis

        return self._value(
            operation,
            "measurement",
            clean_shape,
            label=label,
            **properties,
        )

    def repair(
        self,
        shape: DomainValue,
        *,
        working_tolerance: float = 1.0e-7,
        minimum_tolerance: float = 1.0e-7,
        maximum_tolerance: float = 1.0e-3,
        label: str = "",
    ) -> DomainValue:
        """Run ShapeFix on a copy using explicit bounded tolerance limits."""

        operation = "repair"
        minimum = _number(
            operation,
            "minimum_tolerance",
            minimum_tolerance,
            minimum=0.0,
            strict=True,
        )
        working = _number(
            operation,
            "working_tolerance",
            working_tolerance,
            minimum=0.0,
            strict=True,
        )
        maximum = _number(
            operation,
            "maximum_tolerance",
            maximum_tolerance,
            minimum=0.0,
            strict=True,
        )
        if not minimum <= working <= maximum:
            raise _error(
                operation,
                "minimum_tolerance/working_tolerance/maximum_tolerance",
                "must satisfy minimum <= working <= maximum",
            )
        clean_shape = _shape(operation, "shape", shape)
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            working_tolerance=working,
            minimum_tolerance=minimum,
            maximum_tolerance=maximum,
            label=label,
        )

    def chamfer(
        self,
        shape: DomainValue,
        distance: float,
        *,
        edges: str | Mapping[str, Any] = "all",
        on_failure: str = "refuse",
        label: str = "",
    ) -> DomainValue:
        """Chamfer the edges a selector names, or every edge with edges='all'.

        ``edges`` is ``'all'`` or a geometric selector, e.g.
        ``{"direction": [0, 0, 1], "expected_count": 4}``.

        ``on_failure`` behaves exactly as it does on ``fillet``: 'refuse'
        (default), 'skip' the edges the kernel will not take, or 'reduce' to
        the largest distance the whole selection accepts.
        """

        operation = "chamfer"
        clean_shape = _shape(operation, "shape", shape, allowed={"solid", "shell"})
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            _number(operation, "distance", distance, minimum=0.0, strict=True),
            edges=_selector(operation, "edges", edges, allow_all=True),
            on_failure=_blend_failure_mode(operation, on_failure),
            label=label,
        )

    def offset(
        self,
        shape: DomainValue,
        distance: float,
        *,
        tolerance: float = 1.0e-7,
        join: str = "arc",
        fill: bool = False,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Create a 3D skin offset of a face, shell, or solid."""

        operation = "offset"
        clean_join = str(join or "").strip().lower()
        if clean_join not in _JOIN_TYPES:
            raise _error(operation, "join", f"must be one of {sorted(_JOIN_TYPES)}", join)
        clean_shape = _shape(operation, "shape", shape, allowed={"face", "shell", "solid"})
        if bool(fill) and clean_shape.output_type != "shell":
            raise _error(operation, "fill", "is supported only when offsetting a shell", fill)
        if clean_shape.output_type == "shell" and bool(fill):
            inferred = "solid"
        elif clean_shape.output_type == "face":
            inferred = "shell"
        else:
            inferred = clean_shape.output_type
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred),
            clean_shape,
            _nonzero_number(operation, "distance", distance),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0, strict=True),
            join=clean_join,
            fill=bool(fill),
            label=label,
        )

    def offset2d(
        self,
        shape: DomainValue,
        distance: float,
        *,
        join: str = "arc",
        fill: bool = False,
        open_result: bool = False,
        intersection: bool = False,
        output_type: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Planar-offset an edge, wire, or face; optionally fill the swept region."""

        operation = "offset2d"
        clean_join = str(join or "").strip().lower()
        if clean_join not in _JOIN_TYPES:
            raise _error(operation, "join", f"must be one of {sorted(_JOIN_TYPES)}", join)
        clean_shape = _shape(operation, "shape", shape, allowed={"edge", "wire", "face"})
        inferred = "face" if bool(fill) else "wire"
        return self._value(
            operation,
            _inferred_result_type(operation, output_type, inferred, exact=True),
            clean_shape,
            _nonzero_number(operation, "distance", distance),
            join=clean_join,
            fill=bool(fill),
            open_result=bool(open_result),
            intersection=bool(intersection),
            label=label,
        )

    def thicken(
        self,
        shape: DomainValue,
        faces: Mapping[str, Any],
        thickness: float,
        *,
        tolerance: float = 1.0e-7,
        join: str = "arc",
        label: str = "",
    ) -> DomainValue:
        """Remove the faces a selector names and thicken the rest into a solid.

        ``faces`` is a geometric selector, e.g. opening the top of a box:
        ``{"normal": [0, 0, 1], "expected_count": 1}``.
        """

        operation = "thicken"
        clean_join = str(join or "").strip().lower()
        if clean_join not in _JOIN_TYPES:
            raise _error(operation, "join", f"must be one of {sorted(_JOIN_TYPES)}", join)
        return self._value(
            operation,
            "solid",
            _shape(operation, "shape", shape, allowed={"solid", "shell"}),
            _selector(operation, "faces", faces),
            _nonzero_number(operation, "thickness", thickness),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0, strict=True),
            join=clean_join,
            label=label,
        )

    def transform(
        self,
        shape: DomainValue,
        *,
        translation: Sequence[float] = (0.0, 0.0, 0.0),
        rotation_axis: Sequence[float] = (0.0, 0.0, 1.0),
        rotation_degrees: float = 0.0,
        scale: float | Sequence[float] = 1.0,
        pivot: Sequence[float] = (0.0, 0.0, 0.0),
        label: str = "",
    ) -> DomainValue:
        """Copy, scale and rotate about pivot, then translate a shape."""

        operation = "transform"
        if isinstance(scale, (list, tuple)):
            clean_scale = _vector(operation, "scale", scale)
            if any(value <= 0.0 for value in clean_scale):
                raise _error(operation, "scale", "all scale factors must be positive", scale)
        else:
            factor = _number(operation, "scale", scale, minimum=0.0, strict=True)
            clean_scale = [factor, factor, factor]
        clean_shape = _shape(operation, "shape", shape)
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            translation=_vector(operation, "translation", translation),
            rotation_axis=_vector(operation, "rotation_axis", rotation_axis, nonzero=True),
            rotation_degrees=_number(operation, "rotation_degrees", rotation_degrees),
            scale=clean_scale,
            pivot=_vector(operation, "pivot", pivot),
            label=label,
        )

    def loft_cage(
        self,
        cage: Any,
        *,
        solid: bool = True,
        closed: bool = False,
        ruled: bool = False,
        on_bulge: str = "refuse",
        label: str = "",
    ) -> DomainValue:
        """Loft the sections of one declared cage (ADR-127).

        ``cage`` is one entry of a ``cage(...)`` table — ``c["torso"]`` — and
        each of its rings is a superellipse: ``exponent`` 2.0 is an ellipse,
        larger fills the corners out towards a rounded rectangle, which is
        the difference between a limb that reads as tubular and one that
        reads as muscled.

        The same loft the script could write by hand, over a table it can
        also drag. ``ruled`` lofts straight between sections instead of
        fairing a spline through them, and ``on_bulge`` is ``part.loft``'s
        guard against a spline that swings outside the rings it was given
        (ADR-129) — a cage is a table of the shape, so a loft that ignores it
        is exactly the failure the table exists to prevent.
        """

        operation = "loft_cage"
        if not isinstance(cage, CageSet):
            raise _error(
                operation,
                "cage",
                "expected one cage from cage(...), subscripted by name, e.g. "
                "c['torso']",
                cage,
            )
        if len(cage) < 2:
            raise _error(
                operation, "cage", "needs at least two rings to loft between",
                len(cage),
            )
        return self._value(
            operation,
            "solid" if bool(solid) else "shell",
            cage.to_payload(),
            solid=bool(solid),
            closed=bool(closed),
            ruled=bool(ruled),
            on_bulge=_bulge_mode(operation, on_bulge),
            label=label,
        )

    def mate(
        self,
        shape: DomainValue,
        source: Any,
        target: Any,
        *,
        flip: bool = False,
        offset: float = 0.0,
        check_interference: bool = True,
        label: str = "",
    ) -> DomainValue:
        """Place ``shape`` so its mount lands on another component's (ADR-126).

        ``source`` and ``target`` are mounts, subscripted by name out of a
        ``mounts(...)`` table — ``m["leg"]["root"]`` — which is the idiom
        ``part.cable(esp["sda"], fc["sda"])` already uses.

        The convention is face to face: each mount's axis points the way the
        other part approaches from, so mating opposes them and aligns the
        rolls. ``flip`` turns the part half a turn about the mating axis;
        ``offset`` moves it along the target's axis afterwards, positive
        being a gap.

        ``check_interference`` booleans the placed shape against the target's
        component and refuses a non-zero common volume, **naming the cubic
        millimetres**. Two parts that overlap are not mated, they are
        colliding, and the number is the difference between reading a refusal
        and reading a picture.
        """

        operation = "mate"
        clean_shape = _shape(operation, "shape", shape,
                             allowed={"solid", "shell", "compound"})
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            _mount(operation, "source", source),
            _mount(operation, "target", target),
            flip=bool(flip),
            offset=_number(operation, "offset", offset),
            check_interference=bool(check_interference),
            label=label,
        )

    def mirror(
        self,
        shape: DomainValue,
        plane_origin: Sequence[float],
        plane_normal: Sequence[float],
        *,
        label: str = "",
    ) -> DomainValue:
        """Copy and mirror a shape across an explicit plane."""

        operation = "mirror"
        clean_shape = _shape(operation, "shape", shape)
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            _vector(operation, "plane_origin", plane_origin),
            _vector(operation, "plane_normal", plane_normal, nonzero=True),
            label=label,
        )

    def project(
        self,
        target: DomainValue,
        profile: DomainValue,
        vector: Sequence[float],
        *,
        mode: str = "parallel",
        output_type: str = "wire",
        label: str = "",
    ) -> DomainValue:
        """Project a profile onto a target by direction or from a viewpoint."""

        operation = "project"
        clean_mode = str(mode or "").strip().lower()
        if clean_mode not in _PROJECTION_MODES:
            raise _error(
                operation,
                "mode",
                f"must be one of {sorted(_PROJECTION_MODES)}",
                mode,
            )
        clean_type = _result_type(operation, output_type)
        if clean_type not in {"wire", "compound"}:
            raise _error(
                operation,
                "output_type",
                "must be 'wire' or 'compound'",
                output_type,
            )
        return self._value(
            operation,
            clean_type,
            _shape(operation, "target", target, allowed={"face", "shell", "solid", "compound"}),
            _shape(operation, "profile", profile, allowed={"edge", "wire"}),
            _vector(
                operation,
                "vector",
                vector,
                nonzero=clean_mode == "parallel",
            ),
            mode=clean_mode,
            label=label,
        )

    def refine(self, shape: DomainValue, *, label: str = "") -> DomainValue:
        """Copy a shape and remove redundant splitter edges and faces."""

        operation = "refine"
        clean_shape = _shape(operation, "shape", shape)
        return self._value(
            operation,
            clean_shape.output_type,
            clean_shape,
            label=label,
        )

    @property
    def exported_names(self) -> tuple[str, ...]:
        return (
            "from_object",
            "box",
            "wedge",
            "plane",
            "prism",
            "cylinder",
            "cone",
            "sphere",
            "torus",
            "line",
            "arc",
            "circle",
            "ellipse",
            "bezier",
            "bspline",
            "nurbs_curve",
            "helix",
            "wire",
            "face",
            "shell",
            "solid",
            "compound",
            "subshape",
            "extrude",
            "revolve",
            "loft",
            "sweep",
            "terminals",
            "cable",
            "bundle",
            "solder",
            "ruled_surface",
            "filled_surface",
            "fuse",
            "cut",
            "common",
            "section",
            "general_fuse",
            "slice",
            "defeature",
            "to_nurbs",
            "reverse",
            "sew",
            "shape_from_mesh",
            "import_part",
            "measurement",
            "repair",
            "fillet",
            "chamfer",
            "offset",
            "offset2d",
            "thicken",
            "transform",
            "loft_cage",
            "mate",
            "mirror",
            "project",
            "refine",
        )
