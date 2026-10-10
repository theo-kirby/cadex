# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Production provider-facing API for the Assembly XScript domain.

The API builds an immutable assembly graph.  Component source objects are
stable document references supplied through ``inputs``; the host snapshots
their geometry before the graph is evaluated in an isolated ``FreeCADCmd``
worker.  Distances are millimetres and angles are degrees.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
import math
import re
from typing import Any, Iterable

from cadex_domain_api import DomainValue


_PUBLISHABLE_TYPES = frozenset(
    {
        "assembly",
        "component_link",
        "joint",
        "solver_diagnostics",
        "motion",
        "simulation",
        # An exported MuJoCo model is its own output type, unlike a dynamics
        # run: `dynamics` shares `simulation` because two
        # assembly_simulation_json artifacts would leave the shell baking
        # neither, and an MJCF file is baked by nothing. A script may
        # declare several (ADR-081).
        "mjcf",
        # A training task is its own type for the same reason an exported
        # model is: nothing bakes it, so two in one script is a reasonable
        # thing to write. It is also the first output that consumes another
        # output -- one api.mjcf value -- and two tasks may share one model
        # (ADR-083).
        "task",
        # A trained policy, on the same terms and for the same reasons: it is
        # the *second* output that consumes another output -- one api.task
        # value -- nothing bakes it, and two policies against one task (two
        # seeds, two reward weightings) is a reasonable script. What it
        # publishes is a receipt rather than the weights, which are an asset
        # and cannot be rebuilt from any script (ADR-084).
        "policy",
        "exploded_view",
    }
)
_JOINT_TYPES = (
    "fixed",
    "revolute",
    "cylindrical",
    "slider",
    "ball",
    "distance",
    "parallel",
    "perpendicular",
    "angle",
    "rack_pinion",
    "screw",
    "gears",
    "belt",
)
#: What each collision kind takes, and therefore what it refuses. ``mesh``
#: and ``hull`` are the same geometry -- the component's own tessellated
#: solids -- and differ only in whether a part MuJoCo would hull is refused
#: or accepted. Keeping them two *kinds* rather than one kind and a boolean
#: puts the acceptance in the script's own text, where a reader sees it.
_COLLISION_KINDS: dict[str, frozenset[str]] = {
    "box": frozenset({"size_mm"}),
    "plane": frozenset({"size_mm"}),
    "sphere": frozenset({"radius_mm"}),
    "cylinder": frozenset({"radius_mm", "length_mm"}),
    "capsule": frozenset({"radius_mm", "length_mm"}),
    "mesh": frozenset({"deflection_mm"}),
    "hull": frozenset({"deflection_mm"}),
}
#: The two kinds that come out of the component's own BREP.
_COLLISION_SHAPE_KINDS = frozenset({"mesh", "hull"})
_SUBELEMENT = re.compile(r"^(Face|Edge|Vertex)[1-9][0-9]*$")
_INTERFACE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_MOTION_FUNCTIONS = frozenset({"abs", "asin", "arcsin", "arctan", "cos", "sin"})
_MOTION_NAMES = frozenset({"time", "initialValue", "pi"})
#: A part's appearance role (docs/DESIGN-LANGUAGE.md section 2, ADR-413):
#: the printed outer forms, the joints and purchased hardware that show, and
#: the one saturated colour on a few deliberate features.
APPEARANCE_ROLES = ("shell", "mechanism", "accent")
_HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_OCCURRENCE_PATH = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*){0,15}$"
)


def _error(operation: str, parameter: str, message: str, value: Any = None) -> ValueError:
    received = "" if value is None else f" Received {value!r}."
    return ValueError(f"api.{operation}: invalid {parameter}: {message}.{received}")


def _number(
    operation: str,
    parameter: str,
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    strict_minimum: bool = False,
) -> float:
    if isinstance(value, bool):
        raise _error(operation, parameter, "expected a finite number", value)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise _error(operation, parameter, "expected a finite number", value) from exc
    if not math.isfinite(result):
        raise _error(operation, parameter, "expected a finite number", value)
    if minimum is not None and (
        result <= minimum if strict_minimum else result < minimum
    ):
        relation = "greater than" if strict_minimum else "at least"
        raise _error(operation, parameter, f"must be {relation} {minimum:g}", value)
    if maximum is not None and result > maximum:
        raise _error(operation, parameter, f"must not exceed {maximum:g}", value)
    return result


def _appearance(operation: str, value: Any) -> str:
    role = str(value).strip().lower() if isinstance(value, str) else value
    if role not in APPEARANCE_ROLES:
        raise _error(operation, "appearance", f"must be one of {list(APPEARANCE_ROLES)}", value)
    return role


def _palette(operation: str, value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise _error(
            operation, "palette",
            "expected a non-empty object of role to '#RRGGBB', e.g. {'shell': '#E9E6DF'}", value,
        )
    result = {}
    for role, colour in value.items():
        if role not in APPEARANCE_ROLES:
            raise _error(operation, "palette", f"keys must be among {list(APPEARANCE_ROLES)}", role)
        if not isinstance(colour, str) or not _HEX_COLOUR.match(colour.strip()):
            raise _error(operation, f"palette[{role!r}]", "expected a '#RRGGBB' colour", colour)
        result[role] = colour.strip().upper()
    return {role: result[role] for role in APPEARANCE_ROLES if role in result}


def _label(operation: str, value: Any) -> str:
    result = str(value or "").strip()
    if len(result) > 120:
        raise _error(operation, "label", "must contain at most 120 characters", value)
    return result


def _occurrence_path(operation: str, value: Any) -> str:
    result = str(value or "").strip()
    if not _OCCURRENCE_PATH.fullmatch(result):
        raise _error(
            operation,
            "occurrence_path",
            "must be one copy-ready source occurrence path with 1-16 '/'-separated "
            "FreeCAD object-name segments",
            value,
        )
    return result


def _vector(
    operation: str,
    parameter: str,
    value: Any,
    *,
    size: int,
) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        description = "[x, y, z]" if size == 3 else "quaternion [x, y, z, w]"
        raise _error(operation, parameter, f"expected {description}", value)
    return [
        _number(operation, f"{parameter}[{index}]", item)
        for index, item in enumerate(value)
    ]


def _placement(operation: str, parameter: str, value: Any) -> dict[str, list[float]]:
    if value is None:
        position = [0.0, 0.0, 0.0]
        rotation = [0.0, 0.0, 0.0, 1.0]
    elif isinstance(value, (list, tuple)):
        position = _vector(operation, parameter, value, size=3)
        rotation = [0.0, 0.0, 0.0, 1.0]
    elif isinstance(value, Mapping):
        extra = set(value) - {"position", "rotation", "axis", "angle_degrees"}
        if extra:
            raise _error(
                operation,
                parameter,
                "supports position plus either rotation or axis/angle_degrees; "
                f"unknown keys {sorted(extra)}",
            )
        position = _vector(
            operation,
            f"{parameter}.position",
            value.get("position", [0.0, 0.0, 0.0]),
            size=3,
        )
        has_quaternion = "rotation" in value
        has_axis = "axis" in value
        has_angle = "angle_degrees" in value
        if has_quaternion and (has_axis or has_angle):
            raise _error(
                operation,
                parameter,
                "rotation cannot be combined with axis or angle_degrees",
                value,
            )
        if has_axis != has_angle:
            missing = "angle_degrees" if has_axis else "axis"
            raise _error(
                operation,
                parameter,
                f"axis and angle_degrees must be supplied together; missing {missing}",
                value,
            )
        if has_axis:
            axis = _vector(
                operation,
                f"{parameter}.axis",
                value["axis"],
                size=3,
            )
            axis_magnitude = math.sqrt(sum(item * item for item in axis))
            if axis_magnitude <= 1.0e-12:
                raise _error(
                    operation,
                    f"{parameter}.axis",
                    "axis-angle rotation requires a non-zero axis",
                    value["axis"],
                )
            half_angle = math.radians(
                _number(
                    operation,
                    f"{parameter}.angle_degrees",
                    value["angle_degrees"],
                )
            ) / 2.0
            scale = math.sin(half_angle) / axis_magnitude
            rotation = [
                axis[0] * scale,
                axis[1] * scale,
                axis[2] * scale,
                math.cos(half_angle),
            ]
        else:
            rotation = _vector(
                operation,
                f"{parameter}.rotation",
                value.get("rotation", [0.0, 0.0, 0.0, 1.0]),
                size=4,
            )
    else:
        raise _error(
            operation,
            parameter,
            "expected [x,y,z], a position/quaternion object, or a "
            "position/axis/angle_degrees object",
            value,
        )
    magnitude = math.sqrt(sum(item * item for item in rotation))
    if magnitude <= 1.0e-12:
        raise _error(operation, f"{parameter}.rotation", "quaternion must be non-zero")
    return {
        "position": position,
        "rotation": [item / magnitude for item in rotation],
    }


def _reference(operation: str, value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"document_uid", "object_name"}:
        raise _error(
            operation,
            "source",
            "expected a stable input reference with document_uid and object_name",
            value,
        )
    result = {
        "document_uid": str(value.get("document_uid") or "").strip(),
        "object_name": str(value.get("object_name") or "").strip(),
    }
    if not result["document_uid"] or not result["object_name"]:
        raise _error(operation, "source", "document_uid and object_name must be non-empty")
    return result


def _domain_value(
    operation: str,
    parameter: str,
    value: Any,
    *,
    output_type: str,
) -> DomainValue:
    if not isinstance(value, DomainValue) or value.domain != "assembly":
        raise _error(
            operation,
            parameter,
            "expected a value returned by this Assembly api",
            type(value).__name__,
        )
    if value.output_type != output_type:
        raise _error(
            operation,
            parameter,
            f"expected an Assembly {output_type} value",
            value.output_type,
        )
    return value


def _values(
    operation: str,
    parameter: str,
    value: Any,
    *,
    output_type: str,
    minimum: int,
) -> list[DomainValue]:
    if isinstance(value, DomainValue):
        raw = [value]
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        raise _error(operation, parameter, "expected an array of Assembly api values", value)
    if len(raw) < minimum:
        raise _error(operation, parameter, f"requires at least {minimum} value(s)", value)
    result = [
        _domain_value(
            operation,
            f"{parameter}[{index}]",
            item,
            output_type=output_type,
        )
        for index, item in enumerate(raw)
    ]
    if len({id(item) for item in result}) != len(result):
        raise _error(operation, parameter, "contains the same graph value more than once")
    return result


#: Component pairs one simulation may hold apart. Every pair costs a
#: distance query per frame, and a trace is thousands of frames.
_MAX_CLEARANCE_PAIRS = 32


def _clearance_pairs(
    operation: str, value: Any, model: DomainValue
) -> list[list[DomainValue]]:
    """Validate the component pairs a swept clearance holds apart (ADR-130)."""

    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise _error(
            operation, "clearance", "expected an array of component pairs", value
        )
    if len(value) > _MAX_CLEARANCE_PAIRS:
        raise _error(
            operation,
            "clearance",
            f"expected at most {_MAX_CLEARANCE_PAIRS} pairs",
            len(value),
        )
    members = {id(item) for item in model.properties.get("components", ())}
    pairs: list[list[DomainValue]] = []
    seen: set[frozenset[int]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise _error(
                operation,
                f"clearance[{index}]",
                "expected exactly two components",
                item,
            )
        first, second = (
            _domain_value(
                operation,
                f"clearance[{index}][{position}]",
                entry,
                output_type="component_link",
            )
            for position, entry in enumerate(item)
        )
        if first is second:
            raise _error(
                operation,
                f"clearance[{index}]",
                "names one component twice; a part cannot clear itself",
            )
        for position, entry in enumerate((first, second)):
            if id(entry) not in members:
                raise _error(
                    operation,
                    f"clearance[{index}][{position}]",
                    "is not a component of this assembly",
                )
        key = frozenset((id(first), id(second)))
        if key in seen:
            raise _error(
                operation, "clearance", "names the same pair more than once"
            )
        seen.add(key)
        pairs.append([first, second])
    return pairs


def _clearance_promise(
    operation: str, clearance: Any, clearance_mm: Any, model: DomainValue
) -> tuple[list[list[DomainValue]], float]:
    """One clearance promise: the pairs and the gap, or neither (ADR-130).

    Shared by ``api.simulation``, ``api.dynamics`` and ``api.rollout``,
    which ask the same question of three different solvers. The two halves
    are refused apart because neither means anything alone: a gap with no
    pairs has no safe default -- two parts joined at a joint are supposed to
    touch -- and pairs with no gap check for "more than zero apart", which
    passes on parts that are already touching.
    """

    pairs = _clearance_pairs(operation, clearance, model)
    gap = _number(operation, "clearance_mm", clearance_mm, minimum=0.0)
    if pairs and gap <= 0.0:
        raise _error(
            operation,
            "clearance_mm",
            "must be positive when clearance pairs are named; a check for "
            "'more than zero apart' passes on parts that are touching",
            clearance_mm,
        )
    if gap > 0.0 and not pairs:
        raise _error(
            operation,
            "clearance",
            "name the component pairs the gap applies to; two parts joined "
            "at a joint are supposed to touch, so there is no safe default",
        )
    return pairs, gap


def _selection(operation: str, value: Any) -> dict[str, str]:
    if isinstance(value, str):
        clean = value.strip()
        if clean.lower() in {"", "origin", "component_origin"}:
            return {"type": "component_origin"}
        if _SUBELEMENT.fullmatch(clean):
            return {"type": "exact_subelement", "subelement": clean}
        raise _error(
            operation,
            "selection",
            "expected 'origin', FaceN, EdgeN, VertexN, or a published-interface object",
            value,
        )
    if not isinstance(value, Mapping):
        raise _error(operation, "selection", "expected a string or selection object", value)
    kind = str(value.get("type") or "").strip()
    if kind == "component_origin" and set(value) == {"type"}:
        return {"type": kind}
    if kind == "exact_subelement" and set(value) == {"type", "subelement"}:
        name = str(value.get("subelement") or "")
        if _SUBELEMENT.fullmatch(name):
            return {"type": kind, "subelement": name}
    if kind == "published_interface" and set(value) == {"type", "interface_name"}:
        name = str(value.get("interface_name") or "")
        if _INTERFACE_NAME.fullmatch(name):
            return {"type": kind, "interface_name": name}
    raise _error(
        operation,
        "selection",
        "selection must be exactly component_origin, exact_subelement, or "
        "published_interface with a valid name",
        value,
    )


def _anchor(operation: str, selection: Mapping[str, str], value: Any) -> str | None:
    if value is None:
        return None
    clean = str(value or "").strip()
    if not _SUBELEMENT.fullmatch(clean):
        raise _error(
            operation,
            "anchor",
            "expected an exact FaceN, EdgeN, or VertexN subelement",
            value,
        )
    selection_type = str(selection.get("type") or "")
    if selection_type != "exact_subelement":
        raise _error(
            operation,
            "anchor",
            "is supported only with an exact FaceN, EdgeN, or VertexN selection",
            value,
        )
    selected = str(selection.get("subelement") or "")
    if selected.startswith("Vertex") and clean != selected:
        raise _error(
            operation,
            "anchor",
            f"a vertex connector must use its selected vertex {selected}",
            value,
        )
    if clean != selected and not clean.startswith("Vertex"):
        raise _error(
            operation,
            "anchor",
            "use the selected subelement for its natural center or a VertexN "
            "belonging to the selected edge/face",
            value,
        )
    return clean


def _limits(
    operation: str,
    parameter: str,
    value: Any,
) -> list[float | None] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        if set(value) - {"minimum", "maximum"}:
            raise _error(
                operation,
                parameter,
                "limit objects support only minimum and maximum",
                value,
            )
        raw = [value.get("minimum"), value.get("maximum")]
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        raw = list(value)
    else:
        raise _error(
            operation,
            parameter,
            "expected [minimum, maximum] or {'minimum': value, 'maximum': value}; "
            "either endpoint may be null for a one-sided limit",
            value,
        )
    if raw == [None, None]:
        raise _error(operation, parameter, "at least one limit endpoint is required", value)
    result = [
        None
        if item is None
        else _number(operation, f"{parameter}[{index}]", item)
        for index, item in enumerate(raw)
    ]
    if result[0] is not None and result[1] is not None and result[0] > result[1]:
        raise _error(operation, parameter, "minimum must not exceed maximum", value)
    return result


def _tracker_datasheet(operation: str, given: Mapping[str, Any]) -> dict[str, Any]:
    """A position tracker's declaration, as the trainer applies it (ADR-588)."""

    missing = [key for key, value in given.items() if value is None]
    if missing:
        raise _error(
            operation, missing[0],
            "is required for a position_tracker: a grounded channel states "
            "what the part on the machine can measure -- range_mm, "
            "resolution_mm, rate_hz and noise_mm, as its datasheet would",
        )
    raw = given["range_mm"]
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise _error(operation, "range_mm",
                     "expected [[x0, x1], [y0, y1], [z0, z1]] in the mount's frame", raw)
    bounds = []
    for axis, pair in zip("xyz", raw):
        limits = _limits(operation, f"range_mm[{axis}]", pair)
        if limits is None or None in limits or limits[0] >= limits[1]:
            raise _error(operation, f"range_mm[{axis}]",
                         "expected a two-sided [minimum, maximum] with minimum below maximum",
                         pair)
        bounds.append([float(limits[0]), float(limits[1])])
    return {
        "range_mm": bounds,
        "resolution_mm": _number(operation, "resolution_mm", given["resolution_mm"],
                                 minimum=0.0, strict_minimum=True),
        "rate_hz": _number(operation, "rate_hz", given["rate_hz"],
                           minimum=0.0, strict_minimum=True),
        "noise_mm": _number(operation, "noise_mm", given["noise_mm"], minimum=0.0),
    }


def _load_datasheet(
    operation: str,
    actuator: DomainValue,
    given: Mapping[str, Any],
) -> dict[str, Any]:
    """A load sensor's declaration, in its actuator's unit (ADR-591).

    ``full_scale`` is the actuator's own effort limit -- the stall line a
    bus servo's load register reads 100 % at -- so an actuator with no limit
    has nothing for the reading to saturate at and is refused.
    """

    angular = str(actuator.properties.get("motion_type")) == "angular"
    unit = "nmm" if angular else "n"
    other = "n" if angular else "nmm"
    for key in ("resolution", "noise"):
        if given.get(f"{key}_{other}") is not None:
            raise _error(operation, f"{key}_{other}",
                         f"is not this actuator's unit: it drives a "
                         f"{'turning' if angular else 'sliding'} coordinate, "
                         f"so its load is declared in {key}_{unit}",
                         given[f"{key}_{other}"])
    missing = [key for key in (f"resolution_{unit}", "rate_hz", f"noise_{unit}")
               if given.get(key) is None]
    if missing:
        raise _error(
            operation, missing[0],
            "is required for a load_sensor: a grounded channel states what "
            f"the part on the machine can measure -- resolution_{unit}, "
            f"rate_hz and noise_{unit}, as its datasheet would",
        )
    limit = actuator.properties.get("torque_limit_nmm" if angular else "force_limit_n")
    if limit is None:
        raise _error(
            operation, "target",
            "is an actuator with no effort limit: a load reading saturates "
            "at the motor's stall line, so give the actuator its "
            + ("torque_limit_nmm" if angular else "force_limit_n")
            + " first",
        )
    return {
        "full_scale": float(limit),
        "resolution": _number(operation, f"resolution_{unit}", given[f"resolution_{unit}"],
                              minimum=0.0, strict_minimum=True),
        "rate_hz": _number(operation, "rate_hz", given["rate_hz"],
                           minimum=0.0, strict_minimum=True),
        "noise": _number(operation, f"noise_{unit}", given[f"noise_{unit}"], minimum=0.0),
    }


#: Which unit family each drivable joint kind's coordinate speaks. A
#: `cylindrical` joint owns one of each and is therefore absent: like
#: `api.motion`, it requires an explicit `motion_type`.
_COORDINATE_BY_JOINT_KIND = {"revolute": "angular", "slider": "linear"}

#: The four joints that relate coordinates other joints provide. FreeCAD's
#: own `isJointTypeConnecting` returns false for exactly these, so they
#: attach nothing and there is no MuJoCo joint on them to damp or drive.
_COUPLED_JOINT_KINDS = {
    "screw": "the slider and the revolute joint it relates",
    "gears": "the two revolute joints it relates",
    "belt": "the two revolute joints it relates",
    "rack_pinion": "the slider and the revolute joint it relates",
}
_PLACEMENT_ONLY_JOINT_KINDS = ("distance", "parallel", "perpendicular", "angle")

#: The three actuator kinds and, for each, the control parameter its two
#: coordinate families take. The pairing is what the kind *means*: a
#: position servo is commanded in position, a velocity one in speed, and a
#: motor in effort -- so a `control_deg` on a motor is not a unit mistake
#: but a claim about the wrong quantity, and it is refused as one.
_ACTUATOR_KINDS = {
    "motor": ("control_nmm", "control_n"),
    "position": ("control_deg", "control_mm"),
    "velocity": ("control_deg_per_s", "control_mm_per_s"),
}


def _cylinder(operation: str, coordinate: str, bore_mm: Any, rod_mm: Any,
              pressure_bar: Any, force_limit_n: Any) -> dict[str, float | None]:
    """A cylinder's bore, rod and pressure, and the two forces they make (ADR-643)."""

    if coordinate != "linear":
        raise _error(operation, "kind", "a cylinder drives a slider: its coordinate is linear",
                     "cylinder")
    if force_limit_n is not None:
        raise _error(operation, "force_limit_n",
                     "is derived for a cylinder from bore_mm and pressure_bar, not given",
                     force_limit_n)
    for name, given in (("bore_mm", bore_mm), ("pressure_bar", pressure_bar)):
        if given is None:
            raise _error(operation, name, "is required for kind='cylinder'")
    bore = _number(operation, "bore_mm", bore_mm, minimum=0.0, strict_minimum=True)
    pressure = _number(operation, "pressure_bar", pressure_bar, minimum=0.0,
                       maximum=1000.0, strict_minimum=True)
    rod = None
    if rod_mm is not None:
        rod = _number(operation, "rod_mm", rod_mm, minimum=0.0, strict_minimum=True)
        if rod >= bore:
            raise _error(operation, "rod_mm", "must be smaller than bore_mm", rod_mm)
    # The forces are CadexDynamics' to compute: every unit conversion is
    # there (test_dynamics_units), so the declaration carries only what
    # the script wrote.
    return {"bore_mm": bore, "rod_mm": rod, "pressure_bar": pressure}


def _coordinate(operation: str, joint: DomainValue, motion_type: Any) -> str:
    """Which unit family this joint's coordinate speaks, or a refusal.

    Every quantity M4 adds -- a setpoint, a gain, an effort limit, an
    armature -- has one meaning on a joint that turns and another on a joint
    that slides, so nothing can be validated until this is settled. The
    refusals are the point: a joint with no coordinate, three coordinates or
    somebody else's coordinate is an authoring mistake that would otherwise
    arrive as a MuJoCo compiler error naming an element id.
    """

    kind = str(joint.properties.get("kind") or "")
    if bool(joint.properties.get("suppressed")):
        raise _error(
            operation,
            "joint",
            "cannot damp or drive a suppressed joint: FreeCAD's solver ignored "
            "it, so the dynamics model has no joint there at all",
            kind,
        )
    if kind in _COUPLED_JOINT_KINDS:
        raise _error(
            operation,
            "joint",
            f"a {kind} joint attaches nothing -- it relates motion that other "
            f"joints provide, so there is no coordinate on it to damp or "
            f"drive. Target {_COUPLED_JOINT_KINDS[kind]} instead",
            kind,
        )
    if kind == "fixed":
        raise _error(
            operation,
            "joint",
            "a fixed joint has no coordinate: it removes all six degrees of "
            "freedom, and there is nothing left to damp or drive",
            kind,
        )
    if kind == "ball":
        raise _error(
            operation,
            "joint",
            "a ball joint has three coordinates and no scalar setpoint means "
            "anything on it. Model the axis that is actually driven as a "
            "revolute joint",
            kind,
        )
    if kind in _PLACEMENT_ONLY_JOINT_KINDS:
        raise _error(
            operation,
            "joint",
            f"a {kind} joint is a placement constraint, not a runtime one: it "
            "told the solver where to put a part and a dynamics model has no "
            "use for it",
            kind,
        )
    clean_type = str(motion_type or "").strip().lower()
    if kind == "cylindrical":
        if clean_type not in {"angular", "linear"}:
            raise _error(
                operation,
                "motion_type",
                "a cylindrical joint owns both a rotation and a slide, so it "
                "requires an explicit 'angular' or 'linear'",
                motion_type,
            )
        return clean_type
    coordinate = _COORDINATE_BY_JOINT_KIND.get(kind)
    if coordinate is None:
        raise _error(operation, "joint", f"has no drivable coordinate", kind)
    if clean_type not in {"auto", coordinate}:
        raise _error(
            operation,
            "motion_type",
            f"must be {coordinate!r} or 'auto' for a {kind} joint",
            motion_type,
        )
    return coordinate


def _unit_pair(
    operation: str,
    coordinate: str,
    angular: tuple[str, Any],
    linear: tuple[str, Any],
    *,
    minimum: float = 0.0,
    maximum: float = 1.0e9,
    strict_minimum: bool = False,
) -> tuple[str, float] | None:
    """One quantity from a suffixed pair, with the other one refused.

    This verbosity is the whole design, and it is hazard 1 answered in the
    parameter names. ``api.motion``'s single ``formula`` whose unit depends
    on a sibling argument is exactly the shape that fails silently: a
    ``control="30"`` meaning 30 radians is 57 times what the author wrote,
    runs, looks like physics and errors nowhere. Naming the unit means the
    wrong one cannot be passed at all -- ``stiffness_n_per_mm`` on a hinge is
    a refusal, not a factor of five million.
    """

    wanted, unwanted = (
        (angular, linear) if coordinate == "angular" else (linear, angular)
    )
    unwanted_name, unwanted_value = unwanted
    wanted_name, wanted_value = wanted
    if unwanted_value is not None:
        raise _error(
            operation,
            unwanted_name,
            f"is the {'linear' if coordinate == 'angular' else 'angular'} form "
            f"and this joint's coordinate is {coordinate}; use {wanted_name!r}",
            unwanted_value,
        )
    if wanted_value is None:
        return None
    return wanted_name, _number(
        operation,
        wanted_name,
        wanted_value,
        minimum=minimum,
        maximum=maximum,
        strict_minimum=strict_minimum,
    )


def _command_limits(
    operation: str,
    coordinate: str,
    angular: tuple[str, Any],
    linear: tuple[str, Any],
) -> tuple[str, list[float]] | None:
    """A command range from a suffixed pair, with the other one refused.

    :func:`_unit_pair` for two endpoints instead of one. The unit
    discrimination is that function's, verbatim and for its reason -- a
    ``command_limits_mm`` on a hinge is a refusal rather than a factor of
    five million -- and the parsing is :func:`_limits`', so ``[-25, 25]`` and
    ``{"minimum": -25, "maximum": 25}`` both work and read the same way as
    every other limit on this surface.

    **Both endpoints are required here**, which is where it parts company
    with :func:`_limits`. A one-sided *joint* limit means "free in that
    direction" and the engine fills it with a hundred turns' margin; a
    one-sided *command* limit would have to mean "and the joint's own
    endpoint for the other side", which is a second, quieter way of saying
    something the author can already say explicitly. Refusing it keeps one
    meaning per spelling.
    """

    wanted, unwanted = (
        (angular, linear) if coordinate == "angular" else (linear, angular)
    )
    unwanted_name, unwanted_value = unwanted
    wanted_name, wanted_value = wanted
    if unwanted_value is not None:
        raise _error(
            operation,
            unwanted_name,
            f"is the {'linear' if coordinate == 'angular' else 'angular'} form "
            f"and this joint's coordinate is {coordinate}; use {wanted_name!r}",
            unwanted_value,
        )
    if wanted_value is None:
        return None
    parsed = _limits(operation, wanted_name, wanted_value)
    assert parsed is not None
    if parsed[0] is None or parsed[1] is None:
        raise _error(
            operation,
            wanted_name,
            "needs both endpoints: a command range is what a policy may ask "
            "for, and half of one is not a range. State the joint's own "
            "endpoint explicitly if that is what you mean",
            wanted_value,
        )
    low, high = float(parsed[0]), float(parsed[1])
    if not low < high:
        raise _error(
            operation,
            wanted_name,
            "minimum must be below maximum: a command range of zero width "
            "leaves a policy no action to take",
            wanted_value,
        )
    return wanted_name, [low, high]


def _checked_formula(
    operation: str,
    parameter: str,
    value: Any,
    *,
    names: frozenset[str] | None,
    refusals: Mapping[str, str] = {},
    functions: frozenset[str] = _MOTION_FUNCTIONS,
) -> str:
    """One expression, whitelisted node by node, in Python syntax.

    Extracted from ``_motion_formula`` so that ``api.motion`` and
    ``api.actuator`` share one whitelist rather than two that drift. The
    difference between them is entirely in the arguments: ``api.motion``
    renders its result back to Ondsel's ``^`` and accepts ``initialValue``;
    a control formula keeps Python syntax, because it is *this* engine that
    evaluates it, and refuses ``initialValue``, because a dynamics run's
    initial value is a solved pose rather than a scalar a script can name.

    ``functions`` is the third such difference and the reason it is a
    parameter rather than a wider shared set (M6). A reward wants ``exp``,
    ``sqrt`` and ``tanh``; ``api.motion`` must not get them, because its
    formula is rendered back into an Ondsel expression and Ondsel has no
    ``tanh`` -- a shared whitelist would export something the solver on the
    other side cannot read.

    ``names=None`` means *any identifier is a variable reference*, and it is
    how a reward formula is checked. ``api.reward`` is a standalone
    intermediate: it is written before there is a task to belong to, so it
    cannot know which observation channels exist. That check is the
    engine's, where the channel list is not only known but *expanded* -- a
    vector observation becomes three names -- and where the refusal can
    therefore say which names were available. What stays here is the part a
    reader of the script could check: the syntax, and that every call is to
    a function this surface supports.

    An AST whitelist rather than a sandbox: what is accepted is enumerated,
    so a Python release growing a new expression node adds nothing here.
    """

    if not isinstance(value, str):
        raise _error(
            operation,
            parameter,
            "expected an expression written as a string -- a constant setpoint "
            'is "30", not 30',
            value,
        )
    formula = value.strip()
    if not formula:
        raise _error(operation, parameter, "must not be empty", value)
    if len(formula) > 512:
        raise _error(operation, parameter, "must contain at most 512 characters")
    if not formula.isascii():
        raise _error(operation, parameter, "must contain only ASCII expression syntax")
    try:
        tree = ast.parse(formula.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise _error(
            operation,
            parameter,
            f"invalid expression near column {exc.offset or 1}",
            value,
        ) from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise _error(operation, parameter, "expression is too complex")
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    )
    for node in nodes:
        if not isinstance(node, allowed_nodes):
            raise _error(
                operation,
                parameter,
                f"unsupported expression element {type(node).__name__}",
                value,
            )
        if isinstance(node, ast.Constant):
            if (
                isinstance(node.value, bool)
                or not isinstance(node.value, (int, float))
                or not math.isfinite(float(node.value))
            ):
                raise _error(
                    operation,
                    parameter,
                    "constants must be finite numbers",
                    node.value,
                )
        elif (
            isinstance(node, ast.Name)
            and names is not None
            and node.id not in (names | functions)
        ):
            if node.id in refusals:
                raise _error(operation, parameter, refusals[node.id], node.id)
            raise _error(
                operation,
                parameter,
                f"unknown name {node.id!r}; use "
                f"{', '.join(sorted(names))}, or a supported function "
                f"{sorted(functions)}",
            )
        elif isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in functions
                or len(node.args) != 1
                or node.keywords
            ):
                raise _error(
                    operation,
                    parameter,
                    "functions must be one-argument calls to "
                    f"{', '.join(sorted(functions))}",
                    value,
                )
    return formula.replace("^", "**")


def _motion_formula(value: Any) -> str:
    """``api.motion``'s formula, rendered back to Ondsel's ``^`` for powers."""

    return _checked_formula(
        "motion", "formula", value, names=_MOTION_NAMES
    ).replace("**", "^")


#: What a reward or termination expression may call, on top of the motion
#: set. Three additions and no more: ``exp`` for a shaped bell, ``sqrt`` for
#: a distance, ``tanh`` for a term that saturates instead of dominating.
#:
#: This set is *not* ``api.motion``'s widened -- that formula is rendered
#: back into an Ondsel expression, and Ondsel has no ``tanh``. The two are
#: separate whitelists passed to one checker, which is the extension point
#: `_checked_formula(functions=...)` exists to be.
_REWARD_FUNCTIONS = _MOTION_FUNCTIONS | frozenset({"exp", "sqrt", "tanh"})

#: Every observation kind, and what a script must hand it.
#:
#: The second copy of :data:`CadexDynamics.OBSERVATION_KINDS`, deliberately:
#: this surface does not import the pure module, and a table written twice
#: is this codebase's answer to drift wherever the alternative is attention.
#: ``test_dynamics_task_api`` asserts the two agree kind for kind, so the
#: copy costs a test rather than a maintenance promise.
#:
#: The value is the output type the target has to be, which is the whole
#: validation: a ``position`` reads a joint, a ``component_position`` reads
#: a component, an ``actuator_force`` reads a motor.
_OBSERVATION_KINDS: dict[str, str] = {
    "position": "joint",
    "velocity": "joint",
    "actuator_force": "actuator",
    "component_position": "component_link",
    "component_orientation": "component_link",
    "component_linear_velocity": "component_link",
    "component_angular_velocity": "component_link",
    "centre_of_mass": "component_link",
    "centre_of_mass_velocity": "component_link",
    "centroidal_angular_momentum": "component_link",
    "tracked_position": "component_link",
    "tracked_velocity": "component_link",
}

#: What each observation kind's declared name expands to. A vector channel
#: becomes suffixed scalars because reward formulas do arithmetic on
#: scalars, and the set of names a formula may write has to be enumerable
#: for every one of them to be checkable.
_OBSERVATION_SUFFIXES: dict[str, tuple[str, ...]] = {
    "position": ("",),
    "velocity": ("",),
    "actuator_force": ("",),
    "component_position": ("_x", "_y", "_z"),
    "component_orientation": ("_qw", "_qx", "_qy", "_qz"),
    "component_linear_velocity": ("_x", "_y", "_z"),
    "component_angular_velocity": ("_x", "_y", "_z"),
    "centre_of_mass": ("_x", "_y", "_z"),
    "centre_of_mass_velocity": ("_x", "_y", "_z"),
    "centroidal_angular_momentum": ("_x", "_y", "_z"),
    # The three coordinates a tracker reports, then whether it reported them
    # at all (ADR-588): a body outside the declared range reads zeros and a
    # flag of 0, never a clamped or a stale position.
    "tracked_position": ("_x", "_y", "_z", "_in_range"),
    # The same tracker's differenced velocity (ADR-590); it shares the
    # position's _in_range rather than carrying a second one.
    "tracked_velocity": ("_x", "_y", "_z"),
}


def _observation_channels(kind: str, name: str) -> list[str]:
    return [f"{name}{suffix}" for suffix in _OBSERVATION_SUFFIXES[kind]]


#: What a randomisation entry may vary, and what it has to be given.
_RANDOMISATION_TARGETS: dict[str, str] = {
    "mass": "component_link",
    "damping": "joint",
    "armature": "joint",
    "friction_loss": "joint",
}


def _check_randomisation(
    operation: str,
    parameter: str,
    entries: Sequence[DomainValue],
    component_ids: set[int],
    joint_ids: set[int],
) -> None:
    """Hold one randomisation list to the assembly the model came from.

    Shared by ``api.task`` and the ``api.success`` it is handed, so a list
    that judges a task is refused for exactly what a list that trains it is.
    """

    varied: set[tuple[int, str, str]] = set()
    for index, entry in enumerate(entries):
        target = entry.arguments[0]
        property_name = str(entry.properties.get("target"))
        wanted = _RANDOMISATION_TARGETS[property_name]
        if wanted == "component_link" and id(target) not in component_ids:
            raise _error(
                operation,
                f"{parameter}[{index}]",
                "varies a component that is not listed in this assembly",
            )
        if wanted == "joint" and id(target) not in joint_ids:
            raise _error(
                operation,
                f"{parameter}[{index}]",
                "varies a joint that is not listed in this assembly",
            )
        key = (
            id(target),
            property_name,
            str(entry.properties.get("motion_type") or ""),
        )
        if key in varied:
            raise _error(
                operation,
                f"{parameter}[{index}]",
                f"varies {property_name!r} on one target twice; the second "
                "draw would silently replace the first",
            )
        varied.add(key)


#: Which way a disturbance may point, and what gets drawn to decide it.
#: ``horizontal`` draws an azimuth over the full circle; ``vertical`` draws a
#: sign. Both are one scalar, which is what keeps the draw order the same
#: length whichever a script picks.
_DISTURBANCE_DIRECTIONS = frozenset({"horizontal", "vertical"})

#: A success predicate names one behaviour metric. The shape is checked here
#: and the name against the engine's vocabulary, because the vocabulary is
#: ``CadexEvaluation``'s and that module stays outside the service (ADR-455).
_SUCCESS_METRIC_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SUCCESS_PREDICATE_KEYS = frozenset({"id", "metric", "min", "max"})
_MAX_SUCCESS_PREDICATES = 32
_MAX_SUCCESS_SEEDS = 64
_MAX_SUCCESS_FEET = 16
#: What a spec may say it was written for (``success(scale=...)``). The
#: engine's ``CadexDynamics.SUCCESS_SCALE_KEYS`` is the same tuple, and
#: ``test_success_spec_model`` holds the two equal.
_SUCCESS_SCALE_KEYS = (
    "mass_kg", "weight_n", "com_height_mm", "hip_height_mm", "arm_length_mm",
)

#: What a goal may be (ADR-462). ``CadexDynamics.GOAL_KINDS`` is the same
#: tuple, and ``test_goal_api`` holds the two equal.
_GOAL_KINDS = ("value", "speed", "point", "phase")

#: An observation's name, which becomes a name a reward formula writes. The
#: same shape as a Python identifier because that is what it turns into,
#: and short enough that the suffixed forms stay readable.
#: What each onboard sensor can measure, and off what (ADR-408). A policy
#: channel is *grounded* when it names the sensor that measures it: an IMU
#: measures its own component's orientation and rotation rate, and a joint
#: encoder -- a servo's potentiometer tapped out, or a feedback servo --
#: its own joint's position and rate. Everything else a task observes is
#: `privileged`: the reward, the terminations and the critic may read it,
#: and the robot it deploys to cannot.
_SENSOR_KINDS: dict[str, tuple[str, frozenset[str]]] = {
    "imu": ("component_link",
            frozenset({"component_orientation", "component_angular_velocity"})),
    "joint_encoder": ("joint", frozenset({"position", "velocity"})),
    # A touch panel, or a camera tracking a marker (ADR-588): mounted on a
    # component, it reads *another* body's position in its own frame, with
    # a declared range, resolution, rate and noise the trainer applies.
    "position_tracker": ("component_link",
                         frozenset({"tracked_position", "tracked_velocity"})),
    # A bus servo's load register, or a current sensor on a motor's supply
    # (ADR-591): it reads the effort its own actuator applies, to a declared
    # resolution and noise, saturating at that actuator's effort limit.
    "load_sensor": ("actuator", frozenset({"actuator_force"})),
}
#: Which sensor kinds each datasheet argument of ``api.sensor`` belongs to.
_SENSOR_DATASHEET_KINDS: dict[str, tuple[str, ...]] = {
    "range_mm": ("position_tracker",),
    "resolution_mm": ("position_tracker",),
    "noise_mm": ("position_tracker",),
    "rate_hz": ("position_tracker", "load_sensor"),
    "resolution_nmm": ("load_sensor",),
    "noise_nmm": ("load_sensor",),
    "resolution_n": ("load_sensor",),
    "noise_n": ("load_sensor",),
}
_OBSERVATION_ROLES = ("policy", "privileged")

_CHANNEL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,47}$")

#: What a control formula may name. ``initialValue`` is deliberately absent
#: and refused by name below.
_CONTROL_NAMES = frozenset({"time", "pi"})
_CONTROL_REFUSALS = {
    "initialValue": (
        "is not available to a control formula: a dynamics run's initial "
        "value is a solved pose the mechanism was in, not a scalar the "
        "script can name. Write the setpoint you want in absolute terms"
    )
}


class AssemblyDomainAPI:
    """Explicit immutable graph API injected into Assembly XScript source."""

    __slots__ = ()

    domain = "assembly"
    exported_names = (
        "assembly",
        "component",
        "connector",
        "joint",
        "solve",
        "motion",
        "simulation",
        "dynamics",
        "mjcf",
        "task",
        "policy",
        # A rollout produces a `simulation`, not a type of its own, for
        # exactly the reason `dynamics` does: it is baked, a script has one
        # simulation whichever thing produced it, and two
        # assembly_simulation_json artifacts would leave the shell baking
        # neither (ADR-077, ADR-085).
        "rollout",
        "body",
        "collision",
        "joint_dynamics",
        "actuator",
        "observation",
        "sensor",
        "reward",
        "termination",
        "randomise",
        # Two more intermediates on the same terms as `randomise`, and the
        # pair that stops an episode always starting in the same place: a
        # variation on the reset pose, and a force applied while the episode
        # runs (M9, ADR-097).
        "reset_variation",
        "disturbance",
        # What a policy is judged by, which is not what it was paid for: an
        # argument to a task, like the reward it is kept apart from (ADR-456).
        "success",
        # What an episode asks the policy to do: an argument to a task and
        # to its success spec (ADR-462).
        "goal",
        "exploded_view",
        # A creature's moving anatomy: an argument to api.assembly, which
        # the build reply's anatomy block checks (ADR-613).
        "anatomy",
        # A linear relation between joint coordinates -- a belt, a cable, a
        # differential -- and a declared tool point with the work area it
        # must reach: both arguments to api.assembly (ADR-642, ADR-645).
        "coupling",
        "tool",
    )

    def __init__(self, exports: Iterable[str], output_types: Iterable[str]) -> None:
        declared = tuple(dict.fromkeys(str(item) for item in exports))
        if declared != self.exported_names:
            raise RuntimeError(
                "Assembly pack exports do not match the production runtime contract: "
                f"expected {self.exported_names!r}, received {declared!r}."
            )
        if frozenset(str(item) for item in output_types) != _PUBLISHABLE_TYPES:
            raise RuntimeError(
                "Assembly pack output types do not match the production runtime contract."
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
            domain="assembly",
            operation=operation,
            output_type=output_type,
            arguments=tuple(arguments),
            properties=properties,
        )

    def component(
        self,
        source: Mapping[str, str],
        *,
        placement: Sequence[float] | Mapping[str, Sequence[float]] | None = None,
        grounded: bool = False,
        flexible: bool = False,
        world: bool = False,
        appearance: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Create one linked occurrence from a stable input reference.

        ``placement`` is either ``[x,y,z]`` or an object with ``position`` and
        either quaternion ``rotation=[x,y,z,w]`` or ``axis=[x,y,z]`` plus
        ``angle_degrees``. Set ``grounded=True`` for a fixed base occurrence.
        Set ``flexible=True`` only for an authenticated native Assembly source;
        its internal joints and stable occurrence paths then participate in the
        parent solve. A flexible occurrence cannot be grounded.
        ``world=True`` marks environment geometry for an advisory fit failure.
        ``appearance`` is the part's role in the design language: ``"shell"``
        (printed outer forms), ``"mechanism"`` (joints, links and purchased
        hardware that show) or ``"accent"`` (one saturated colour on a few
        features). Undeclared, a purchased part draws as mechanism and a
        printed one as shell.
        Reuse the returned variable in connectors and return it exactly once as
        a ``component_link`` output.
        """

        operation = "component"
        if not isinstance(grounded, bool):
            raise _error(operation, "grounded", "expected a boolean", grounded)
        if not isinstance(flexible, bool):
            raise _error(operation, "flexible", "expected a boolean", flexible)
        if not isinstance(world, bool):
            raise _error(operation, "world", "expected a boolean", world)
        if grounded and flexible:
            raise _error(
                operation,
                "grounded",
                "a native flexible subassembly cannot be grounded; ground a rigid base "
                "component in the parent assembly instead",
            )
        return self._value(
            operation,
            "component_link",
            _reference(operation, source),
            placement=_placement(operation, "placement", placement),
            grounded=grounded,
            flexible=flexible,
            **({"world": True} if world else {}),
            **({"appearance": _appearance(operation, appearance)} if appearance is not None else {}),
            label=label,
        )

    def connector(
        self,
        component: DomainValue,
        selection: str | Mapping[str, str] = "origin",
        *,
        occurrence_path: str | None = None,
        anchor: str | None = None,
        offset: Sequence[float] | Mapping[str, Sequence[float]] | None = None,
    ) -> DomainValue:
        """Select one component origin or exact/semantic subelement as a JCS.

        ``occurrence_path`` optionally targets one copy-ready internal source
        occurrence path exposed in Assembly domain context. It is required when
        a joint targets the internals of a flexible subassembly and works with
        the same stable path when that subassembly is rigid. ``anchor``
        optionally chooses an exact VertexN on the selected native
        edge/face; omit it to use the edge midpoint/circle center or face
        center. ``offset`` is an optional local placement applied after FreeCAD
        derives the connector frame. Use a published semantic interface for a
        regenerating Part Design publication; exact topology and anchors are
        accepted only for immutable native input snapshots.
        """

        operation = "connector"
        value = _domain_value(
            operation,
            "component",
            component,
            output_type="component_link",
        )
        clean_selection = _selection(operation, selection)
        return self._value(
            operation,
            "connector",
            value,
            selection=clean_selection,
            occurrence_path=(
                _occurrence_path(operation, occurrence_path)
                if occurrence_path is not None
                else None
            ),
            anchor=_anchor(operation, clean_selection, anchor),
            offset=_placement(operation, "offset", offset),
        )

    def joint(
        self,
        kind: str,
        first: DomainValue,
        second: DomainValue,
        *,
        distance_mm: float | None = None,
        angle_degrees: float | None = None,
        pitch_radius_mm: float | None = None,
        thread_pitch_mm: float | None = None,
        radius1_mm: float | None = None,
        radius2_mm: float | None = None,
        length_limits_mm: Sequence[float | None] | Mapping[str, float | None] | None = None,
        angle_limits_degrees: Sequence[float | None] | Mapping[str, float | None] | None = None,
        suppressed: bool = False,
        label: str = "",
    ) -> DomainValue:
        """Connect two JCS values with one of FreeCAD's 13 native joint types.

        Type-specific values are required only for ``distance``, ``angle``,
        ``rack_pinion``, ``screw``, ``gears``, and ``belt``. Translation limits
        apply to slider/cylindrical joints; angular limits apply to
        revolute/cylindrical joints. Either limit endpoint may be ``None``.
        Rack/pinion pitch radius and screw pitch are signed and non-zero; their
        sign chooses motion direction. Gear and belt radii are positive.
        """

        operation = "joint"
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in _JOINT_TYPES:
            raise _error(
                operation,
                "kind",
                f"must be one of {list(_JOINT_TYPES)}",
                kind,
            )
        first_value = _domain_value(
            operation,
            "first",
            first,
            output_type="connector",
        )
        second_value = _domain_value(
            operation,
            "second",
            second,
            output_type="connector",
        )
        if first_value.arguments[0] is second_value.arguments[0]:
            raise _error(
                operation,
                "first/second",
                "connectors must belong to two different component values",
            )
        if not isinstance(suppressed, bool):
            raise _error(operation, "suppressed", "expected a boolean", suppressed)

        supplied = {
            "distance_mm": distance_mm,
            "angle_degrees": angle_degrees,
            "pitch_radius_mm": pitch_radius_mm,
            "thread_pitch_mm": thread_pitch_mm,
            "radius1_mm": radius1_mm,
            "radius2_mm": radius2_mm,
        }
        required_by_kind = {
            "distance": ("distance_mm",),
            "angle": ("angle_degrees",),
            "rack_pinion": ("pitch_radius_mm",),
            "screw": ("thread_pitch_mm",),
            "gears": ("radius1_mm", "radius2_mm"),
            "belt": ("radius1_mm", "radius2_mm"),
        }
        required = set(required_by_kind.get(clean_kind, ()))
        missing = [name for name in required if supplied[name] is None]
        if missing:
            raise _error(
                operation,
                missing[0],
                f"is required for a {clean_kind} joint",
            )
        irrelevant = [
            name for name, value in supplied.items() if value is not None and name not in required
        ]
        if irrelevant:
            raise _error(
                operation,
                irrelevant[0],
                f"does not apply to a {clean_kind} joint",
                supplied[irrelevant[0]],
            )
        parameters: dict[str, float] = {}
        for name in required:
            if name in {"radius1_mm", "radius2_mm"}:
                parameters[name] = _number(
                    operation,
                    name,
                    supplied[name],
                    minimum=0.0,
                    strict_minimum=True,
                )
            else:
                parameters[name] = _number(operation, name, supplied[name])
                if name in {"pitch_radius_mm", "thread_pitch_mm"} and abs(
                    parameters[name]
                ) <= 1.0e-12:
                    raise _error(
                        operation,
                        name,
                        "must be non-zero; use the sign to select motion direction",
                        supplied[name],
                    )

        length_limits = _limits(operation, "length_limits_mm", length_limits_mm)
        angle_limits = _limits(
            operation,
            "angle_limits_degrees",
            angle_limits_degrees,
        )
        if length_limits is not None and clean_kind not in {"slider", "cylindrical"}:
            raise _error(
                operation,
                "length_limits_mm",
                "is supported only by slider and cylindrical joints",
                length_limits_mm,
            )
        if angle_limits is not None and clean_kind not in {"revolute", "cylindrical"}:
            raise _error(
                operation,
                "angle_limits_degrees",
                "is supported only by revolute and cylindrical joints",
                angle_limits_degrees,
            )
        return self._value(
            operation,
            "joint",
            first_value,
            second_value,
            kind=clean_kind,
            parameters=parameters,
            length_limits_mm=length_limits,
            angle_limits_degrees=angle_limits,
            suppressed=suppressed,
            label=label,
        )

    def coupling(self, terms, *, label=""):
        # Unannotated on purpose: the assembly page is held under one tool
        # result (ADR-360); the types are the docstring's.
        """Hold sum(ratio * change) = 0 over two or more joint coordinates.

        ``terms`` is ``[(joint, ratio), ...]`` -- or ``(joint, ratio,
        motion_type)`` for a cylindrical joint -- each change in mm (slider)
        or degrees (revolute) from the solved pose. It is what a belt, a
        cable or a differential holds, and FreeCAD's two-joint ``gears``,
        ``belt``, ``screw`` and ``rack_pinion`` cannot: CoreXY is two of
        them, ``[(x, 1), (motor_a, -k/2), (motor_b, -k/2)]`` and ``[(y, 1),
        (motor_a, -k/2), (motor_b, k/2)]`` with ``k`` the belt mm per motor
        degree (a 20-tooth GT2 pulley: 40/360); a differential is ``[(carrier,
        2), (left, -1), (right, -1)]``. Joints must be revolute, slider or
        cylindrical tree joints of the same assembly. The dynamics model
        holds it as a joint equality (two terms) or a fixed tendon (three or
        more); the fit sweep moves every coupled coordinate with the swept
        one, unlimited ones following. Pass it to ``api.assembly(...,
        couplings=[...])``; do not return it.
        """

        operation = "coupling"
        if not isinstance(terms, (list, tuple)) or len(terms) < 2:
            raise _error(operation, "terms", "expected two or more (joint, ratio) terms", terms)
        joints, ratios, motions = [], [], []
        for index, term in enumerate(terms):
            if not isinstance(term, (list, tuple)) or len(term) not in (2, 3):
                raise _error(operation, f"terms[{index}]",
                             "expected (joint, ratio) or (joint, ratio, motion_type)", term)
            value = _domain_value(operation, f"terms[{index}]", term[0], output_type="joint")
            motion = _coordinate(operation, value, term[2] if len(term) == 3 else "auto")
            ratio = _number(operation, f"terms[{index}] ratio", term[1])
            if abs(ratio) <= 1.0e-12:
                raise _error(operation, f"terms[{index}]", "ratio must be non-zero", term[1])
            if any(other is value and m == motion for other, m in zip(joints, motions)):
                raise _error(operation, f"terms[{index}]", "names a coordinate twice")
            joints.append(value)
            ratios.append(ratio)
            motions.append(motion)
        return self._value(operation, "coupling", *joints, ratios=ratios,
                           motion_types=motions, label=label)

    def tool(self, component, *, origin_mm=(0, 0, 0), axis=(0, 0, -1), work_area_mm=None,
             work_frame=None, label=""):
        # Unannotated on purpose, as coupling.
        """Declare a tool point (a nozzle, a spindle, a blade) and its work area.

        ``origin_mm`` is the point on ``component`` in its own frame, and
        ``axis`` the direction the tool points (default -Z, down). With
        ``work_area_mm=[[x0, y0, z0], [x1, y1, z1]]`` -- a box in
        ``work_frame``'s frame (a component, such as the bed or the
        workpiece, that may itself move; default the world) -- every build
        reply's ``workspace`` block samples the limited joints that move the
        tool against that frame across their ranges, coupled joints
        following, and says whether the tool point reaches every corner of
        the box, the box it does reach, and the corners it misses. A zero
        extent on one axis is a face (a print bed's plane). Pass it to
        ``api.assembly(..., tools=[...])``; do not return it.
        """

        operation = "tool"
        value = _domain_value(operation, "component", component, output_type="component_link")
        origin = _vector(operation, "origin_mm", origin_mm, size=3)
        direction = _vector(operation, "axis", axis, size=3)
        if math.sqrt(sum(v * v for v in direction)) <= 1.0e-12:
            raise _error(operation, "axis", "must not be zero", axis)
        area = None
        if work_area_mm is not None:
            if not isinstance(work_area_mm, (list, tuple)) or len(work_area_mm) != 2:
                raise _error(operation, "work_area_mm", "expected [[x0, y0, z0], [x1, y1, z1]]",
                             work_area_mm)
            low, high = (_vector(operation, "work_area_mm", corner, size=3) for corner in work_area_mm)
            area = [[min(a, b) for a, b in zip(low, high)], [max(a, b) for a, b in zip(low, high)]]
        arguments = [value]
        if work_frame is not None:
            if area is None:
                raise _error(operation, "work_frame", "applies only with work_area_mm")
            arguments.append(_domain_value(operation, "work_frame", work_frame,
                                           output_type="component_link"))
        return self._value(operation, "tool", *arguments, origin_mm=origin, axis=direction,
                           **({"work_area_mm": area} if area is not None else {}), label=label)

    def anatomy(
        self,
        region: str,
        components: Sequence[DomainValue],
        *,
        reason: str | None = None,
        label: str = "",
    ) -> DomainValue:
        """Name one region of a creature's moving anatomy and the components it is.

        ``region`` is free text; the vocabulary the build reply reads best is
        spine, neck, head, jaw, tail, arm_l/arm_r, leg_fl/leg_fr/leg_rl/leg_rr
        (or leg_l/leg_r), wing_l/wing_r, toe. ``components`` are the
        ``api.component`` values that region is made of (each in at most one
        region). ``reason=`` is how a region is deliberately rigid -- say why,
        with the measurement ("ossified tail: raptor tails were stiff; a tail
        joint costs 0.4 kg the hip torque margin cannot carry"). Pass the list
        to ``api.assembly(..., anatomy=[...])``; do not return it. Every build
        reply then carries an ``anatomy`` block: per region, the joints that
        move it relative to the region it hangs off, which an ``api.actuator``
        or a catalog motor welded on the joint's axis drives, and ``articulated`` / ``rigid`` / ``rigid, no reason`` /
        ``passive only`` (ADR-613, ADR-614).
        """

        operation = "anatomy"
        clean_region = " ".join(str(region or "").split())
        if not clean_region or len(clean_region) > 48:
            raise _error(operation, "region", "expected a region name of 1 to 48 characters", region)
        values = _values(operation, "components", components,
                         output_type="component_link", minimum=1)
        clean_reason = None
        if reason is not None:
            if not isinstance(reason, str) or not reason.strip():
                raise _error(operation, "reason",
                             "expected the reason this region is rigid, or None", reason)
            clean_reason = " ".join(reason.split())
            if len(clean_reason) > 600:
                raise _error(operation, "reason", "is limited to 600 characters", len(clean_reason))
        return self._value(
            operation,
            "anatomy",
            *values,
            region=clean_region,
            **({"reason": clean_reason} if clean_reason else {}),
            label=label,
        )

    def assembly(
        self,
        components: Sequence[DomainValue],
        joints: Sequence[DomainValue] = (),
        *,
        sweep_step_degrees: float | None = None,
        sweep_step_mm: float | None = None,
        contacts: Sequence[Sequence[DomainValue]] = (),
        clearances: Sequence[Sequence[Any]] = (),
        palette: Mapping[str, str] | None = None,
        anatomy: Sequence[DomainValue] = (),
        couplings=(),
        tools=(),
        label: str = "",
    ) -> DomainValue:
        """Build one assembly graph from returned component and joint variables.

        Every listed component and joint must also be returned exactly once as
        its own declared output. ``contacts=[(a, b)]`` requires touching within
        0.001 mm; ``clearances=[(a, c, 0.5)]`` requires at least 0.5 mm.
        Undeclared pairs require 0.1 mm, except a pair an unsuppressed
        ``fixed`` joint welds: that is already the design declaring one rigid
        body, so it is exempt from the gap and needs no ``contacts=`` entry
        repeating it. Common volume above 1e-6 mm³ always fails, even for
        contacts. These checks report, never refuse acceptance.
        A pair may have only one declaration. World geometry belongs in the
        environment; collision planes on design bodies are reported separately.
        ``sweep_step_degrees`` samples every limited hinge and ``sweep_step_mm``
        every limited slider through its range with exact solids after the
        build; a limited joint whose step is undeclared is reported unswept.
        ``palette={"shell": "#E9E6DF", "accent": "#F26A1B"}`` sets the colour
        of any appearance role; an unnamed role keeps its default (bone
        shell, graphite mechanism, signal-orange accent).
        ``anatomy=[api.anatomy(...), ...]`` declares a creature's moving
        regions, which every build reply's ``anatomy`` block checks.
        ``couplings=[api.coupling(...)]`` ties joint coordinates together
        (belts, cables, differentials); ``tools=[api.tool(...)]`` declares
        tool points and the work areas each must reach (``workspace``).
        """

        operation = "assembly"
        component_values = _values(
            operation,
            "components",
            components,
            output_type="component_link",
            minimum=1,
        )
        joint_values = _values(
            operation,
            "joints",
            joints,
            output_type="joint",
            minimum=0,
        )
        component_ids = {id(item) for item in component_values}
        for index, joint_value in enumerate(joint_values):
            for connector_index, connector in enumerate(joint_value.arguments):
                component = connector.arguments[0]
                if id(component) not in component_ids:
                    raise _error(
                        operation,
                        f"joints[{index}].connector[{connector_index}]",
                        "references a component that is not listed in components",
                    )
        if sweep_step_degrees is not None:
            sweep_step_degrees = _number(operation, "sweep_step_degrees", sweep_step_degrees, minimum=1e-6)
        if sweep_step_mm is not None:
            sweep_step_mm = _number(operation, "sweep_step_mm", sweep_step_mm, minimum=1e-6)
        intent = []
        seen = set()
        for kind, declarations, size in (("contact", contacts, 2), ("clearance", clearances, 3)):
            if not isinstance(declarations, (list, tuple)):
                raise _error(operation, kind, "expected an array of declarations")
            for entry in declarations:
                if not isinstance(entry, (list, tuple)) or len(entry) != size:
                    raise _error(operation, kind, f"expected {size} entries")
                first, second = entry[:2]
                key = frozenset((id(first), id(second)))
                if len(key) != 2 or not key <= component_ids or key in seen:
                    raise _error(operation, kind, "expected a unique pair of distinct assembly components")
                seen.add(key)
                row = {"kind": kind, "first": first, "second": second}
                if kind == "clearance":
                    row["minimum_mm"] = _number(operation, "minimum_mm", entry[2], minimum=0)
                intent.append(row)
        joint_ids = {id(item) for item in joint_values}
        coupling_values = _values(operation, "couplings", couplings, output_type="coupling", minimum=0)
        for index, coupling in enumerate(coupling_values):
            if any(id(joint) not in joint_ids for joint in coupling.arguments):
                raise _error(operation, f"couplings[{index}]",
                             "relates a joint that is not listed in joints")
        tool_values = _values(operation, "tools", tools, output_type="tool", minimum=0)
        for index, tool in enumerate(tool_values):
            if any(id(item) not in component_ids for item in tool.arguments):
                raise _error(operation, f"tools[{index}]",
                             "names a component that is not listed in components")
        regions = _values(operation, "anatomy", anatomy, output_type="anatomy", minimum=0)
        named: set[str] = set()
        placed: set[int] = set()
        for index, region in enumerate(regions):
            name = str(region.properties.get("region") or "")
            if name in named:
                raise _error(operation, f"anatomy[{index}]",
                             "names a region another entry already declared", name)
            named.add(name)
            for component in region.arguments:
                if id(component) not in component_ids:
                    raise _error(operation, f"anatomy[{index}]",
                                 "references a component that is not listed in components", name)
                if id(component) in placed:
                    raise _error(operation, f"anatomy[{index}]",
                                 "lists a component another region already holds; a "
                                 "component belongs to one region", name)
                placed.add(id(component))
        return self._value(
            operation,
            "assembly",
            components=component_values,
            joints=joint_values,
            **({"anatomy": regions} if regions else {}),
            **({"couplings": coupling_values} if coupling_values else {}),
            **({"tools": tool_values} if tool_values else {}),
            **({"fit_intent": intent} if intent else {}),
            **({"sweep_step_degrees": sweep_step_degrees} if sweep_step_degrees is not None else {}),
            **({"sweep_step_mm": sweep_step_mm} if sweep_step_mm is not None else {}),
            **({"palette": _palette(operation, palette)} if palette is not None else {}),
            label=label,
        )

    def solve(
        self,
        assembly: DomainValue,
        *,
        require_solved: bool = True,
        label: str = "",
    ) -> DomainValue:
        """Solve the assembly in the worker and return structured native diagnostics.

        ``require_solved=True`` rejects and retains a candidate when FreeCAD
        reports conflicts, redundancy, malformed constraints, or no grounded
        component.  Set it false only when intentionally publishing a diagnostic
        snapshot of a non-solved graph.
        """

        operation = "solve"
        value = _domain_value(
            operation,
            "assembly",
            assembly,
            output_type="assembly",
        )
        if not isinstance(require_solved, bool):
            raise _error(operation, "require_solved", "expected a boolean", require_solved)
        return self._value(
            operation,
            "solver_diagnostics",
            value,
            require_solved=require_solved,
            label=label,
        )

    def motion(
        self,
        joint: DomainValue,
        formula: str,
        *,
        motion_type: str = "auto",
        label: str = "",
    ) -> DomainValue:
        """Drive one native revolute, slider, or cylindrical joint over time.

        Angular formulas produce radians and linear formulas millimetres. Use
        ``time`` in seconds; ``initialValue`` has radians for angular motion and
        millimetres for linear motion. Use ``pi``, arithmetic, powers with ``^``
        or ``**``, and the documented one-argument functions. ``auto``
        selects angular for revolute and linear for slider; cylindrical motion
        requires an explicit ``angular`` or ``linear`` choice.
        """

        operation = "motion"
        value = _domain_value(operation, "joint", joint, output_type="joint")
        joint_type = str(value.properties.get("kind") or "")
        if joint_type not in {"revolute", "slider", "cylindrical"}:
            raise _error(
                operation,
                "joint",
                "motion is supported only for revolute, slider, and cylindrical joints",
                joint_type,
            )
        if bool(value.properties.get("suppressed")):
            raise _error(operation, "joint", "cannot drive a suppressed joint")
        clean_type = str(motion_type or "").strip().lower()
        if clean_type == "auto":
            if joint_type == "cylindrical":
                raise _error(
                    operation,
                    "motion_type",
                    "cylindrical joints require explicit 'angular' or 'linear'",
                    motion_type,
                )
            clean_type = "angular" if joint_type == "revolute" else "linear"
        allowed = {
            "revolute": {"angular"},
            "slider": {"linear"},
            "cylindrical": {"angular", "linear"},
        }[joint_type]
        if clean_type not in allowed:
            raise _error(
                operation,
                "motion_type",
                f"must be one of {sorted(allowed)} for a {joint_type} joint",
                motion_type,
            )
        return self._value(
            operation,
            "motion",
            value,
            formula=_motion_formula(formula),
            motion_type=clean_type,
            label=label,
        )

    def simulation(
        self,
        assembly: DomainValue,
        motions: Sequence[DomainValue],
        *,
        start_time_s: float = 0.0,
        end_time_s: float = 1.0,
        time_step_s: float = 0.01,
        error_tolerance: float = 1.0e-6,
        frames_per_second: int = 30,
        clearance: Sequence[Sequence[DomainValue]] | None = None,
        clearance_mm: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Run native Assembly kinematics in the worker and retain its trace.

        Every motion must also be returned as a stable ``motion`` output. The
        worker records an initial frame plus native time-series frames and
        rejects simulations exceeding 100000 component-pose samples.
        ``time_step_s`` controls trace density; ``frames_per_second`` is retained
        only as the live playback rate and does not add solver samples.

        **``clearance`` is the swept-volume check** (ADR-130, slice O2b).
        It is a list of component pairs that must stay ``clearance_mm``
        apart **at every frame of the trace**, which is what "put the
        mechanism inside the skin and have everything line up" actually
        needs: a static mate proves the parts fit in one pose, and a
        mechanism has more than one. The pairs are named rather than
        inferred, because two parts joined at a joint are supposed to touch
        and only the author knows which pairs are a design promise::

            sim = assembly.simulation(asm, [swing],
                                      clearance=[(skin, thigh), (skin, shin)],
                                      clearance_mm=2.0)

        The refusal names the pair, the frame, its time, and the millimetres
        actually measured. Sampled rather than continuous: the trace is the
        sweep, so ``time_step_s`` is the resolution, and the result records
        how many poses were checked.
        """

        operation = "simulation"
        model = _domain_value(operation, "assembly", assembly, output_type="assembly")
        motion_values = _values(
            operation,
            "motions",
            motions,
            output_type="motion",
            minimum=1,
        )
        graph_joints = {id(item) for item in model.properties.get("joints", ())}
        seen_drives: set[tuple[int, str]] = set()
        for index, motion_value in enumerate(motion_values):
            joint = motion_value.arguments[0]
            if id(joint) not in graph_joints:
                raise _error(
                    operation,
                    f"motions[{index}]",
                    "drives a joint not listed in this assembly",
                )
            drive = (id(joint), str(motion_value.properties.get("motion_type") or ""))
            if drive in seen_drives:
                raise _error(
                    operation,
                    "motions",
                    "contains duplicate motion types for one joint",
                )
            seen_drives.add(drive)
        start = _number(operation, "start_time_s", start_time_s)
        end = _number(operation, "end_time_s", end_time_s)
        if end <= start:
            raise _error(
                operation,
                "end_time_s",
                "must be greater than start_time_s",
                end_time_s,
            )
        step = _number(
            operation,
            "time_step_s",
            time_step_s,
            minimum=0.0,
            strict_minimum=True,
        )
        tolerance = _number(
            operation,
            "error_tolerance",
            error_tolerance,
            minimum=1.0e-12,
            maximum=1.0,
        )
        if isinstance(frames_per_second, bool) or not isinstance(frames_per_second, int):
            raise _error(
                operation,
                "frames_per_second",
                "expected an integer from 1 through 240",
                frames_per_second,
            )
        if not 1 <= frames_per_second <= 240:
            raise _error(
                operation,
                "frames_per_second",
                "must be from 1 through 240",
                frames_per_second,
            )
        # OndselSolver retains the input state in addition to the requested
        # output-time states.  The extra slot also covers a non-integral final
        # interval without relying on a hidden solver rounding rule.
        estimated_frames = math.ceil((end - start) / step) + 2
        component_count = len(model.properties.get("components", ()))
        if estimated_frames > 10_000 or estimated_frames * component_count > 100_000:
            raise _error(
                operation,
                "time range/time_step_s",
                "would exceed 10000 native frames or 100000 component-pose samples; "
                "increase time_step_s or shorten the time range",
            )
        pairs, gap = _clearance_promise(operation, clearance, clearance_mm, model)
        return self._value(
            operation,
            "simulation",
            model,
            motions=motion_values,
            clearance=pairs,
            clearance_mm=gap,
            start_time_s=start,
            end_time_s=end,
            time_step_s=step,
            error_tolerance=tolerance,
            frames_per_second=frames_per_second,
            estimated_frame_limit=estimated_frames,
            label=label,
        )

    def collision(
        self,
        kind: str,
        *,
        size_mm: Sequence[float] | None = None,
        radius_mm: float | None = None,
        length_mm: float | None = None,
        deflection_mm: float | None = None,
        offset: Sequence[float] | Mapping[str, Sequence[float]] | None = None,
        friction: float | Sequence[float] | None = None,
        restitution: float = 0.0,
        condim: int | None = None,
        margin_mm: float | None = None,
        contact_group: int = 0,
        collides_with: Sequence[int] | None = None,
        label: str = "",
    ) -> DomainValue:
        """Declare what one dynamics body may touch things with.

        A body with no collision shape has none: it is held in place by its
        joints and passes through everything, which is what every dynamics
        run did before this existed. Contact is opted into, per body, by
        saying what shape does the touching.

        Seven kinds, in two groups.

        **Primitives** -- ``box`` (``size_mm=[x, y, z]``, the full extents),
        ``sphere`` (``radius_mm``), ``cylinder`` and ``capsule``
        (``radius_mm`` plus ``length_mm``, along the component's local +Z),
        and ``plane``. ``offset`` places the shape in the component's own
        frame, in the same form ``api.connector`` takes. These are exact,
        cheap and the recommended answer: a bracket's real collision
        behaviour is usually two boxes, not its own outline.

        **``plane`` is the floor, and it is not a thin box.** Its
        ``size_mm=[x, y, grid]`` is two full widths and a rendering grid
        spacing -- not three extents -- and a width of ``0`` means the plane
        has no edge in that direction at all. Its surface passes through the
        component's own origin facing local +Z, where a box's colliding
        surface is its *top face*, so a floor built as a box needs an
        ``offset`` of half its thickness and a plane needs none. Prefer it
        for legacy environment models: a box floor is a six-faced solid whose corners and sides
        MuJoCo has to consider on every step, and two MuJoCo builds asked
        the same question about one can answer differently -- measured on
        this mechanism, a box floor made MJX and MuJoCo disagree about the
        contact count on a fifth of all steps, and a plane took the same
        disagreement from 2.3e-7 to 4.4e-16 (ADR-103).

        A plane carries no volume and therefore no mass, which does not
        matter here: a body's mass comes from its *solids*, never from its
        collision shapes. In a mechanism design the floor belongs to the
        environment: declaring a plane on a design body now produces a
        world-geometry fit failure (ADR-347), without refusing acceptance.

        **A primitive is placed in the component frame, which is not the
        solid's bounding box.** With no ``offset`` a primitive is centred on
        the component's origin -- and that coincides with the solid only if
        the solid was authored centred on its own origin, which
        ``part.box`` does not do: its ``origin`` is a *corner*. Nothing ties
        the two together and nothing checks them, so a shape can be the
        right size, in the right units, on the right body, and 20 mm from
        the surface it is supposed to be.

        The worked failure, from a one-leg hopper. The floor is
        ``part.box(4000, 600, 40, origin=[-2000, -300, -40])`` -- so its
        solid spans z = -40..0 and its visible top is z = 0. Its collision
        is ``collision("box", size_mm=[4000, 600, 40])``, correct extents,
        no offset -- so the box is centred on the component origin and spans
        z = -20..+20. The collision top stands **20 mm above the floor you
        can see**, and the foot rested on that invisible shelf from frame 0.
        The two boxes overlap across half their span, so no containment or
        overlap rule would have caught it; ``offset={"position":
        [0, 0, -20]}`` is the fix. What does catch it is the evidence:
        ``initial_contact_count`` is non-zero at the exported keyframe, with
        the geom names and the world position of the contact beside it
        (ADR-087). Read it after ``api.mjcf`` on anything that is supposed
        to start clear of the ground.

        **The component's own shape** -- ``mesh`` tessellates the
        component's solids and hands MuJoCo the result. MuJoCo takes the
        *convex hull* of any collision mesh without saying so, so a bracket
        with a slot silently becomes a solid block. ``mesh`` therefore
        measures its own convexity and **refuses** a part the hull would
        change, naming the volume error. ``hull`` is the same geometry with
        the refusal turned off: it is how an author says, in the script,
        that they have read the number and accept the hull. There is no way
        to get a hull by accident.

        ``deflection_mm`` is the chord tolerance the mesh is built at, and
        it is deliberately not the display deflection -- that one is chosen
        for looks and scales with the bounding box, so a collision mesh
        derived from it would be a physics result that changes when the
        view does. It defaults to a fixed length, and a deflection too
        coarse to represent the part is refused rather than accepted
        quietly.

        **What happens on contact.** ``friction`` is one number -- the
        sliding coefficient, 1.0 by default -- or a triple of sliding,
        torsional and rolling. ``condim`` is 1 (frictionless), 3 (sliding,
        the default), 4 (plus torsional) or 6 (plus rolling); declaring
        friction on a frictionless contact is refused rather than ignored.
        ``margin_mm`` starts the contact before the surfaces meet.

        ``restitution`` is bounce, from 0 (the default, and exact) or
        between 0.3 and 0.9. MuJoCo has no restitution coefficient at all:
        bounce is a consequence of the contact spring's damping, and the
        translation between them is honest only in that band -- below it
        the solver damps the bounce away, above it the integrator adds
        energy. A restitution above zero also needs a solver step fine
        enough to resolve the impact, and asking for one without the other
        is refused with the step it would take. Note that MuJoCo *averages*
        the two geoms' springs, so a bouncy part dropped on a dead floor
        bounces about half as much as it asked to; declare the restitution
        on both sides of the contact you care about.

        ``contact_group`` and ``collides_with`` say what may touch what:
        a shape is in one group (0 to 30, 0 by default) and collides with
        all of them unless ``collides_with`` names a shorter list. Components that
        a joint connects never collide with each other -- they overlap at
        the joint by construction -- and that exclusion is automatic.

        A collision shape is an intermediate value like ``connector``: pass
        it to ``api.body``, and do not return it as an output of its own.
        """

        operation = "collision"
        clean_kind = str(kind or "").strip()
        if clean_kind not in _COLLISION_KINDS:
            raise _error(
                operation,
                "kind",
                f"expected one of {list(_COLLISION_KINDS)}",
                kind,
            )
        required = _COLLISION_KINDS[clean_kind]
        supplied = {
            "size_mm": size_mm,
            "radius_mm": radius_mm,
            "length_mm": length_mm,
            "deflection_mm": deflection_mm,
        }
        for name, value in supplied.items():
            if value is not None and name not in required:
                raise _error(
                    operation,
                    name,
                    f"is not a {clean_kind} parameter; {clean_kind} takes "
                    f"{sorted(required)}",
                    value,
                )
        properties: dict[str, Any] = {"kind": clean_kind}
        if "size_mm" in required:
            if size_mm is None:
                raise _error(
                    operation, "size_mm", f"is required for a {clean_kind}"
                )
            extents = _vector(operation, "size_mm", size_mm, size=3)
            if clean_kind == "plane":
                # A plane's three numbers are not three extents, which is why
                # this cannot share the box's check. The first two are the
                # half-widths of the *drawn* patch and zero means infinite --
                # a legal, and for a floor the usual, value. The third is a
                # rendering grid spacing with no collision meaning at all,
                # and it is required to be positive so that nobody writes
                # [0, 0, 0] believing they have declared three sizes.
                for index, extent in enumerate(extents[:2]):
                    if not 0.0 <= extent <= 1.0e6:
                        raise _error(
                            operation,
                            f"size_mm[{index}]",
                            "is a plane's full width along that axis, or 0 "
                            "for a plane with no edge at all; it cannot be "
                            "negative and is at most 1e6 mm",
                            extent,
                        )
                if not 0.0 < extents[2] <= 1.0e6:
                    raise _error(
                        operation,
                        "size_mm[2]",
                        "is a plane's grid SPACING, not a thickness: a plane "
                        "has no third dimension. It is what the viewer rules "
                        "the surface with, and it must be greater than 0",
                        extents[2],
                    )
            else:
                for index, extent in enumerate(extents):
                    if not 0.0 < extent <= 1.0e6:
                        raise _error(
                            operation,
                            f"size_mm[{index}]",
                            "must be a full extent greater than 0 and at most 1e6 mm",
                            extent,
                        )
            properties["size_mm"] = extents
        if "radius_mm" in required:
            if radius_mm is None:
                raise _error(operation, "radius_mm", f"is required for a {clean_kind}")
            properties["radius_mm"] = _number(
                operation,
                "radius_mm",
                radius_mm,
                minimum=0.0,
                maximum=1.0e6,
                strict_minimum=True,
            )
        if "length_mm" in required:
            if length_mm is None:
                raise _error(operation, "length_mm", f"is required for a {clean_kind}")
            properties["length_mm"] = _number(
                operation,
                "length_mm",
                length_mm,
                minimum=0.0,
                maximum=1.0e6,
                strict_minimum=True,
            )
        if "deflection_mm" in required:
            properties["deflection_mm"] = (
                None
                if deflection_mm is None
                else _number(
                    operation,
                    "deflection_mm",
                    deflection_mm,
                    minimum=0.0,
                    maximum=100.0,
                    strict_minimum=True,
                )
            )
        if clean_kind in _COLLISION_SHAPE_KINDS:
            if offset is not None:
                raise _error(
                    operation,
                    "offset",
                    f"does not apply to a {clean_kind}: the geometry comes out of "
                    "the component's own solids, already in the component's frame, "
                    "and moving it there would put the physics somewhere the part "
                    "is not",
                    offset,
                )
            properties["offset"] = _placement(operation, "offset", None)
        else:
            properties["offset"] = _placement(operation, "offset", offset)
        properties.update(
            self._contact_arguments(
                operation,
                friction=friction,
                restitution=restitution,
                condim=condim,
                margin_mm=margin_mm,
                contact_group=contact_group,
                collides_with=collides_with,
            )
        )
        return self._value(operation, "collision", label=label, **properties)

    @staticmethod
    def _contact_arguments(
        operation: str,
        *,
        friction: Any,
        restitution: Any,
        condim: Any,
        margin_mm: Any,
        contact_group: Any,
        collides_with: Any,
    ) -> dict[str, Any]:
        """Bounds and shapes only. Every conversion is in CadexDynamics.

        The split M2 established and M3 must not leak a second copy of:
        this checks that a number is a number in a plausible range, and the
        pure module turns coefficients into MuJoCo's packed vectors, groups
        into bitmasks and restitution into a damping ratio. Contact
        parameters were named as the most likely place a second conversion
        site would appear, so none of them is converted here.
        """

        if friction is None:
            clean_friction: Any = None
        elif isinstance(friction, (list, tuple)):
            clean_friction = _vector(operation, "friction", friction, size=3)
            for index, value in enumerate(clean_friction):
                if value < 0.0:
                    raise _error(
                        operation, f"friction[{index}]", "must not be negative", value
                    )
        else:
            clean_friction = _number(
                operation, "friction", friction, minimum=0.0, maximum=100.0
            )
        clean_restitution = _number(
            operation, "restitution", restitution, minimum=0.0, maximum=1.0
        )
        if clean_restitution and not 0.3 <= clean_restitution <= 0.9:
            raise _error(
                operation,
                "restitution",
                "must be 0, or from 0.3 through 0.9. MuJoCo has no restitution "
                "coefficient: bounce falls out of the contact spring's damping, "
                "and outside that band the translation is not honest -- below it "
                "the solver damps the bounce away and above it the integrator "
                "adds energy",
                restitution,
            )
        if condim is None:
            clean_condim: Any = None
        else:
            if isinstance(condim, bool) or condim not in (1, 3, 4, 6):
                raise _error(
                    operation,
                    "condim",
                    "expected 1 (frictionless), 3 (sliding), 4 (+torsional) or "
                    "6 (+rolling)",
                    condim,
                )
            clean_condim = int(condim)
        clean_margin = (
            None
            if margin_mm is None
            else _number(
                operation, "margin_mm", margin_mm, minimum=0.0, maximum=1000.0
            )
        )
        if isinstance(contact_group, bool) or not isinstance(contact_group, int):
            raise _error(
                operation, "contact_group", "expected an integer from 0 to 30",
                contact_group,
            )
        if not 0 <= contact_group <= 30:
            raise _error(
                operation, "contact_group", "must be from 0 to 30", contact_group
            )
        if collides_with is None:
            clean_collides: Any = None
        else:
            if not isinstance(collides_with, (list, tuple)) or len(collides_with) > 31:
                raise _error(
                    operation,
                    "collides_with",
                    "expected a list of at most 31 group indices",
                    collides_with,
                )
            clean_collides = []
            for index, group in enumerate(collides_with):
                if isinstance(group, bool) or not isinstance(group, int):
                    raise _error(
                        operation,
                        f"collides_with[{index}]",
                        "expected an integer from 0 to 30",
                        group,
                    )
                if not 0 <= group <= 30:
                    raise _error(
                        operation,
                        f"collides_with[{index}]",
                        "must be from 0 to 30",
                        group,
                    )
                clean_collides.append(int(group))
        return {
            "friction": clean_friction,
            "restitution": clean_restitution,
            "condim": clean_condim,
            "margin_mm": clean_margin,
            "contact_group": int(contact_group),
            "collides_with": clean_collides,
        }

    def joint_dynamics(
        self,
        joint: DomainValue,
        *,
        motion_type: str = "auto",
        damping_nmms_per_deg: float | None = None,
        damping_ns_per_mm: float | None = None,
        armature_kgmm2: float | None = None,
        armature_kg: float | None = None,
        friction_loss_nmm: float | None = None,
        friction_loss_n: float | None = None,
        label: str = "",
    ) -> DomainValue:
        """Give one joint the resistance a real one has, which MuJoCo's has not.

        MuJoCo's defaults for all three of these are **zero**: a joint out of
        the box is frictionless, massless in its own rotor, and undamped.
        That is a perfectly good model of nothing in particular, and a
        position actuator stiff enough to hold an arm against gravity will
        ring on it forever -- measured, sixty degrees peak to peak, not
        decaying. So this is not tuning: it is the difference between a
        mechanism and a mechanism-shaped oscillator, and it is declared
        rather than defaulted for the same reason density is.

        ``damping_*`` is viscous resistance, proportional to speed, and it is
        the one that stops the ringing. ``armature_*`` is the rotor inertia a
        motor and its gearbox add on the far side of the reduction, which is
        often more than the link's own -- it also raises the gain the joint
        can carry before the solver step has to shrink. ``friction_loss_*``
        is dry friction: a constant resisting effort that does not care how
        fast the joint moves, and it is what makes a joint stay where it is
        left.

        **Units are in the names and the wrong one is a refusal.** A joint
        that turns takes ``damping_nmms_per_deg``, ``armature_kgmm2`` and
        ``friction_loss_nmm``; a joint that slides takes ``damping_ns_per_mm``,
        ``armature_kg`` and ``friction_loss_n``. A ``cylindrical`` joint owns
        one coordinate of each, so it needs an explicit
        ``motion_type='angular'`` or ``'linear'`` exactly as ``api.motion``
        does.

        Loop-closing, coupled (``screw``, ``gears``, ``belt``,
        ``rack_pinion``), ``fixed``, ``ball`` and suppressed joints are all
        refused, each with the reason: none of them owns a scalar coordinate
        in the dynamics model.

        A joint_dynamics is an intermediate value like ``connector``: pass it
        to ``api.dynamics``, and do not return it as an output of its own.
        """

        operation = "joint_dynamics"
        value = _domain_value(operation, "joint", joint, output_type="joint")
        coordinate = _coordinate(operation, value, motion_type)
        damping = _unit_pair(
            operation,
            coordinate,
            ("damping_nmms_per_deg", damping_nmms_per_deg),
            ("damping_ns_per_mm", damping_ns_per_mm),
        )
        armature = _unit_pair(
            operation,
            coordinate,
            ("armature_kgmm2", armature_kgmm2),
            ("armature_kg", armature_kg),
        )
        friction_loss = _unit_pair(
            operation,
            coordinate,
            ("friction_loss_nmm", friction_loss_nmm),
            ("friction_loss_n", friction_loss_n),
        )
        if damping is None and armature is None and friction_loss is None:
            raise _error(
                operation,
                "damping/armature/friction_loss",
                "declares nothing: give at least one of damping, armature or "
                "friction loss, or leave the joint out entirely. An empty "
                "joint_dynamics reads like a joint that was configured and is "
                "a joint that was not",
            )
        properties: dict[str, Any] = {
            "motion_type": coordinate,
            "damping_nmms_per_deg": None,
            "damping_ns_per_mm": None,
            "armature_kgmm2": None,
            "armature_kg": None,
            "friction_loss_nmm": None,
            "friction_loss_n": None,
        }
        for entry in (damping, armature, friction_loss):
            if entry is not None:
                properties[entry[0]] = entry[1]
        return self._value(
            operation, "joint_dynamics", value, label=label, **properties
        )

    def actuator(
        self,
        joint: DomainValue,
        *,
        kind: str = "position",
        motion_type: str = "auto",
        control_deg: str | None = None,
        control_mm: str | None = None,
        control_deg_per_s: str | None = None,
        control_mm_per_s: str | None = None,
        control_nmm: str | None = None,
        control_n: str | None = None,
        stiffness_nmm_per_deg: float | None = None,
        stiffness_n_per_mm: float | None = None,
        damping_nmms_per_deg: float | None = None,
        damping_ns_per_mm: float | None = None,
        torque_limit_nmm: float | None = None,
        force_limit_n: float | None = None,
        command_limits_degrees: Any = None,
        command_limits_mm: Any = None,
        bore_mm=None,
        rod_mm=None,
        pressure_bar=None,
        label: str = "",
    ) -> DomainValue:
        """Put a motor on one joint, and tell it what to hold.

        This is what makes a mechanism *driven* rather than merely dropped.
        Three kinds, and the difference between them is what the control
        signal means:

        * ``position`` -- a servo. ``control_deg`` (or ``control_mm``) is
          where the joint should be, ``stiffness_*`` is how hard it pulls
          per unit of error, ``damping_*`` is how much it resists moving
          while it does. This is the closed loop, and it runs inside
          MuJoCo's own solver rather than in any script.
        * ``velocity`` -- a speed controller. ``control_deg_per_s`` is how
          fast the joint should turn and ``damping_*`` is the gain.
        * ``motor`` -- no loop at all. ``control_nmm`` *is* the torque, and
          nothing corrects it.
        * ``cylinder`` -- a hydraulic or pneumatic cylinder on a slider
          (ADR-643): a position servo (the proportional valve) whose force
          is what the oil can push, ``pressure_bar`` x the piston area.
          ``bore_mm`` and ``pressure_bar`` are required, ``rod_mm``
          optional: extending pushes ``p*pi*bore^2/4``, retracting pulls
          ``p*pi*(bore^2-rod^2)/4``, and the slider's +Z is the extending
          direction (barrel on the first connector, rod on the second).
          ``control_mm``, ``stiffness_n_per_mm`` and ``damping_ns_per_mm``
          are a position servo's; ``force_limit_n`` is derived, never
          given. It reads back as a ``position`` actuator carrying a
          ``cylinder`` block.

        **The control is a formula of ``time``, in seconds**, written as a
        string exactly as ``api.motion`` writes one: ``"30"`` holds thirty
        degrees, ``"30*sin(2*pi*time)"`` sweeps. It may use ``time``, ``pi``,
        arithmetic, powers, and the one-argument functions ``abs``,
        ``asin``/``arcsin``, ``arctan``, ``cos`` and ``sin``. There is no
        ``initialValue``: a dynamics run starts from a solved pose, not from
        a number a script can name.

        **Units are in the names and the wrong one is a refusal**, joint by
        joint. A joint that turns takes ``control_deg``,
        ``stiffness_nmm_per_deg``, ``damping_nmms_per_deg`` and
        ``torque_limit_nmm``; one that slides takes ``control_mm``,
        ``stiffness_n_per_mm``, ``damping_ns_per_mm`` and ``force_limit_n``.
        A ``cylindrical`` joint owns one coordinate of each and needs an
        explicit ``motion_type``.

        ``torque_limit_nmm`` is the most a real motor can produce, and a
        mechanism that saturates against it holds short of its setpoint --
        the run's evidence reports the peak effort each actuator reached, so
        "the arm sagged" comes with the number that explains it.

        **``command_limits_degrees`` narrows what a policy may ask for,
        without narrowing the joint.** A position actuator's action range is
        its joint's own travel, because a setpoint outside that travel is a
        command the joint cannot obey. That is right as a *ceiling* and wrong
        as the only choice: a joint may legitimately move further than any
        controller should command it to. Give
        ``command_limits_degrees=[-25, 25]`` on a joint that turns +/-45 and
        a trained policy's action space is the narrower range, while the
        mechanism keeps every degree of travel it really has --
        disturbances, gravity and the solver still put the joint wherever
        physics puts it.

        Optional, and it changes nothing for anyone who does not pass it.
        Both endpoints are required, it must lie **within** the joint's
        declared limits, and it applies only to a ``position`` actuator --
        a motor is bounded by its effort limit and a velocity actuator has no
        derivable range at all. ``command_limits_mm`` is the sliding twin,
        and passing the wrong one for the coordinate is a refusal like every
        other unit here.

        It does **not** touch the exported joint range. Two runs that differ
        only in this differ only in the action table.

        The gear ratio is fixed at one and cannot be set: MuJoCo's ``gear``
        rescales the setpoint as well as the effort, so a surface with both
        would have two ways to say a ratio and one of them would be silently
        wrong. Model the reduction as the joint it really is.

        Loop-closing, coupled, ``fixed``, ``ball`` and suppressed joints are
        all refused with the reason, and a joint may carry at most one
        actuator per coordinate.

        An actuator is an intermediate value like ``connector``: pass it to
        ``api.dynamics``, and do not return it as an output of its own.
        """

        operation = "actuator"
        value = _domain_value(operation, "joint", joint, output_type="joint")
        coordinate = _coordinate(operation, value, motion_type)
        clean_kind = str(kind or "").strip().lower()
        cylinder = None
        if clean_kind == "cylinder":
            cylinder = _cylinder(operation, coordinate, bore_mm, rod_mm, pressure_bar,
                                 force_limit_n)
            clean_kind = "position"
        else:
            for name, given in (("bore_mm", bore_mm), ("rod_mm", rod_mm),
                                ("pressure_bar", pressure_bar)):
                if given is not None:
                    raise _error(operation, name, "applies only to kind='cylinder'", given)
        if clean_kind not in _ACTUATOR_KINDS:
            raise _error(
                operation,
                "kind",
                f"must be one of {sorted([*_ACTUATOR_KINDS, 'cylinder'])}",
                kind,
            )
        controls = {
            "control_deg": control_deg,
            "control_mm": control_mm,
            "control_deg_per_s": control_deg_per_s,
            "control_mm_per_s": control_mm_per_s,
            "control_nmm": control_nmm,
            "control_n": control_n,
        }
        angular_name, linear_name = _ACTUATOR_KINDS[clean_kind]
        wanted = angular_name if coordinate == "angular" else linear_name
        for name, supplied in controls.items():
            if supplied is not None and name != wanted:
                raise _error(
                    operation,
                    name,
                    f"is not what a {clean_kind} actuator on a {coordinate} "
                    f"joint coordinate is controlled by; use {wanted!r}",
                    supplied,
                )
        if controls[wanted] is None:
            raise _error(
                operation,
                wanted,
                f"is required for a {clean_kind} actuator on a {coordinate} "
                "joint coordinate",
            )
        control = _checked_formula(
            operation,
            wanted,
            controls[wanted],
            names=_CONTROL_NAMES,
            refusals=_CONTROL_REFUSALS,
        )
        stiffness = _unit_pair(
            operation,
            coordinate,
            ("stiffness_nmm_per_deg", stiffness_nmm_per_deg),
            ("stiffness_n_per_mm", stiffness_n_per_mm),
            strict_minimum=True,
        )
        damping = _unit_pair(
            operation,
            coordinate,
            ("damping_nmms_per_deg", damping_nmms_per_deg),
            ("damping_ns_per_mm", damping_ns_per_mm),
        )
        effort = _unit_pair(
            operation,
            coordinate,
            ("torque_limit_nmm", torque_limit_nmm),
            ("force_limit_n", force_limit_n),
            strict_minimum=True,
        )
        if clean_kind == "position" and stiffness is None:
            raise _error(
                operation,
                "stiffness_nmm_per_deg"
                if coordinate == "angular"
                else "stiffness_n_per_mm",
                "is required for a position actuator: it is how hard the servo "
                "pulls per unit of error, and there is no defensible default -- "
                "too little and the arm sags, too much and the solver needs a "
                "finer step",
            )
        if clean_kind != "position" and stiffness is not None:
            raise _error(
                operation,
                stiffness[0],
                f"does not apply to a {clean_kind} actuator: only a position "
                "servo has a position gain",
                stiffness[1],
            )
        if clean_kind == "velocity" and damping is None:
            raise _error(
                operation,
                "damping_nmms_per_deg"
                if coordinate == "angular"
                else "damping_ns_per_mm",
                "is required for a velocity actuator: it is the gain, and "
                "without it the actuator produces no effort at all",
            )
        if clean_kind == "motor" and damping is not None:
            raise _error(
                operation,
                damping[0],
                "does not apply to a motor: a motor has no loop to damp, its "
                "control is the effort itself. Declare the damping on the "
                "joint with api.joint_dynamics instead",
                damping[1],
            )
        command_limits = _command_limits(
            operation,
            coordinate,
            ("command_limits_degrees", command_limits_degrees),
            ("command_limits_mm", command_limits_mm),
        )
        if clean_kind != "position" and command_limits is not None:
            raise _error(
                operation,
                command_limits[0],
                f"does not apply to a {clean_kind} actuator: only a position "
                "servo's action range is derived from a joint's travel, so "
                "only a position servo has travel to narrow. A motor is "
                "bounded by its effort limit",
                command_limits[1],
            )
        properties: dict[str, Any] = {
            "kind": clean_kind,
            "motion_type": coordinate,
            **{name: None for name in controls},
            "stiffness_nmm_per_deg": None,
            "stiffness_n_per_mm": None,
            "damping_nmms_per_deg": None,
            "damping_ns_per_mm": None,
            "torque_limit_nmm": None,
            "force_limit_n": None,
            "command_limits_degrees": None,
            "command_limits_mm": None,
        }
        properties[wanted] = control
        for entry in (stiffness, damping, effort, command_limits):
            if entry is not None:
                properties[entry[0]] = entry[1]
        if cylinder is not None:
            # Present only on a cylinder, so every other actuator's value --
            # and the digest it carries -- is what it was before ADR-643.
            properties["cylinder"] = cylinder
        return self._value(operation, "actuator", value, label=label, **properties)

    def body(
        self,
        component: DomainValue,
        *,
        density_kg_m3: float,
        collision: DomainValue | Sequence[DomainValue] | None = None,
        label: str = "",
    ) -> DomainValue:
        """Give one component the mass properties a dynamics run needs.

        ``density_kg_m3`` is required and has no default: mass, inertia and
        every fall time scale with it, and a guessed density produces an
        animation that looks entirely plausible and is wrong. Steel is 7850,
        aluminium 2700, ABS 1040. Mass and the inertia tensor are computed
        exactly from the component's own solids -- nothing is estimated
        from a bounding box.

        ``collision`` takes one ``api.collision`` value or a list of them,
        and giving none means this body touches nothing -- it is carried by
        its joints and passes through the rest of the mechanism. That is
        the default because it is what a kinematics-shaped model already
        assumed, and because the alternative default would be to infer a
        collision shape, which is the one thing ``api.collision`` exists to
        stop. Mass never comes from these shapes: inertia stays exactly what
        the BREP says regardless of what the body collides with.

        A body is an intermediate value like ``connector``: pass it to
        ``api.dynamics``, and do not return it as an output of its own.
        """

        operation = "body"
        value = _domain_value(
            operation,
            "component",
            component,
            output_type="component_link",
        )
        density = _number(
            operation,
            "density_kg_m3",
            density_kg_m3,
            minimum=0.0,
            maximum=30000.0,
            strict_minimum=True,
        )
        if collision is None:
            shapes: list[DomainValue] = []
        elif isinstance(collision, (list, tuple)):
            shapes = _values(
                operation,
                "collision",
                collision,
                output_type="collision",
                minimum=1,
            )
        else:
            shapes = [
                _domain_value(
                    operation, "collision", collision, output_type="collision"
                )
            ]
        if len(shapes) > 16:
            raise _error(
                operation,
                "collision",
                "accepts at most 16 collision shapes for one body",
                len(shapes),
            )
        derived = [
            shape
            for shape in shapes
            if str(shape.properties.get("kind")) in _COLLISION_SHAPE_KINDS
        ]
        if len(derived) > 1:
            raise _error(
                operation,
                "collision",
                "takes at most one mesh or hull shape per body: they are both "
                "the whole component, so a second one is the same geometry twice",
            )
        return self._value(
            operation,
            "body",
            value,
            density_kg_m3=density,
            collision=shapes,
            label=label,
        )

    @staticmethod
    def _one_per_coordinate(
        operation: str,
        parameter: str,
        values: Sequence[DomainValue],
        output_type: str,
        joint_ids: set[int],
        duplicate: str,
    ) -> list[DomainValue]:
        """One list of per-coordinate joint declarations, checked for both.

        Keyed by *coordinate*, not by joint: a cylindrical joint owns a
        rotation and a slide, so damping one of them says nothing about the
        other and driving one is not driving both. Two declarations on the
        same coordinate is a script whose second one silently wins, which is
        the shape of failure this whole slice is organised against.
        """

        entries = _values(
            operation, parameter, values, output_type=output_type, minimum=0
        )
        declared: set[tuple[int, str]] = set()
        for index, entry in enumerate(entries):
            target = entry.arguments[0]
            if id(target) not in joint_ids:
                raise _error(
                    operation,
                    f"{parameter}[{index}]",
                    "targets a joint that is not listed in this assembly",
                )
            coordinate = (id(target), str(entry.properties.get("motion_type")))
            if coordinate in declared:
                raise _error(
                    operation,
                    f"{parameter}[{index}]",
                    f"gives one {coordinate[1]} joint coordinate {duplicate}",
                )
            declared.add(coordinate)
        return entries

    def _mujoco_model(
        self,
        operation: str,
        assembly: DomainValue,
        bodies: Sequence[DomainValue],
        actuators: Sequence[DomainValue],
        joint_dynamics: Sequence[DomainValue],
        gravity_m_s2: Sequence[float] | None,
        solver_step_s: float | None,
    ) -> dict[str, Any]:
        """Everything ``api.dynamics`` and ``api.mjcf`` both have to check.

        The two surfaces share six parameters and every one of their
        validations -- one ``api.body`` per component, one actuator and one
        joint_dynamics per joint *coordinate*, gravity in metres, a solver
        step inside its bounds. Extracted rather than copied because two
        copies of the "steel is 7850" refusal is two places for it to
        drift, and the refusal texts are the part of this API that a model
        actually reads.

        What is *not* here is what counts a trace: ``start_time_s``,
        ``end_time_s``, ``frames_per_second`` and the frame and pose caps
        all measure what leaves the engine as an animation, and an exported
        model is not one.
        """

        model = _domain_value(operation, "assembly", assembly, output_type="assembly")
        body_values = _values(
            operation,
            "bodies",
            bodies,
            output_type="body",
            minimum=1,
        )
        components = list(model.properties.get("components", ()))
        component_ids = {id(item) for item in components}
        seen: set[int] = set()
        for index, body_value in enumerate(body_values):
            component = body_value.arguments[0]
            if id(component) not in component_ids:
                raise _error(
                    operation,
                    f"bodies[{index}]",
                    "gives mass to a component that is not listed in this assembly",
                )
            if id(component) in seen:
                raise _error(
                    operation,
                    f"bodies[{index}]",
                    "gives one component two densities",
                )
            seen.add(id(component))
        if len(seen) != len(components):
            raise _error(
                operation,
                "bodies",
                f"requires one api.body per component; this assembly has "
                f"{len(components)} component(s) and {len(seen)} body value(s). "
                "A component with no density has no mass, and a massless part "
                "in a dynamics model is not a lighter part -- it is an "
                "unsolvable one",
            )
        joint_ids = {id(item) for item in model.properties.get("joints", ())}
        actuator_values = self._one_per_coordinate(
            operation,
            "actuators",
            actuators,
            "actuator",
            joint_ids,
            "two motors",
        )
        joint_dynamics_values = self._one_per_coordinate(
            operation,
            "joint_dynamics",
            joint_dynamics,
            "joint_dynamics",
            joint_ids,
            "two sets of damping, armature and friction loss",
        )
        gravity = (
            None
            if gravity_m_s2 is None
            else _vector(operation, "gravity_m_s2", gravity_m_s2, size=3)
        )
        if gravity is not None:
            magnitude = math.sqrt(sum(value * value for value in gravity))
            if magnitude > 1000.0:
                raise _error(
                    operation,
                    "gravity_m_s2",
                    "must be at most 1000 m/s2 in magnitude. This is metres per "
                    "second squared, not millimetres: Earth is 9.81 and the Moon "
                    "is 1.62",
                    gravity_m_s2,
                )
        step = (
            None
            if solver_step_s is None
            else _number(
                operation,
                "solver_step_s",
                solver_step_s,
                minimum=0.0,
                maximum=1.0,
                strict_minimum=True,
            )
        )
        return {
            "model": model,
            "components": components,
            "bodies": body_values,
            "actuators": actuator_values,
            "joint_dynamics": joint_dynamics_values,
            "gravity_m_s2": gravity,
            "solver_step_s": step,
        }

    def dynamics(
        self,
        assembly: DomainValue,
        bodies: Sequence[DomainValue],
        *,
        actuators: Sequence[DomainValue] = (),
        joint_dynamics: Sequence[DomainValue] = (),
        start_time_s: float = 0.0,
        end_time_s: float = 1.0,
        frames_per_second: int = 60,
        gravity_m_s2: Sequence[float] | None = None,
        solver_step_s: float | None = None,
        clearance: Sequence[Sequence[DomainValue]] | None = None,
        clearance_mm: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Simulate the assembly under gravity and retain its trace.

        The dynamics counterpart of ``api.simulation``: instead of
        prescribing motion with formulas of ``time``, this gives every
        component mass and lets the mechanism fall, swing and settle. Every
        component in the assembly needs exactly one ``api.body``.

        The trace is the same ``simulation`` output kind the kinematics
        solver produces -- a script has one simulation, whichever solver
        ran it. Frames are sampled at ``frames_per_second``; the solver
        steps far finer than that internally.

        A body touches nothing until ``api.body`` is given ``collision``
        shapes, so a mechanism with none is held together by its joints
        alone and passes through everything -- which is exactly what a
        kinematics-shaped model already assumed.

        ``clearance`` and ``clearance_mm`` are the same promise
        ``api.simulation`` takes, measured over the poses the solver
        *reached* rather than the ones a formula drove: the named pairs are
        checked as exact BREP at every frame of the trace. It is the only
        honest answer to "does the motion hit anything", because the model
        that produced the motion collides as boxes and capsules (ADR-281)
        and knows nothing about the parts.

        Unlike ``api.simulation`` a breach here is **reported, not
        refused**. A prescribed travel that collides is a design error the
        script asked about; a dynamics result is a measurement, and
        refusing it would delete the trace that shows the problem. The
        finding lands on the simulation output under ``clearance``, with
        the closest approach and the frame it happened at.

        ``actuators`` takes ``api.actuator`` values, at most one per joint
        coordinate, and is what turns a mechanism that falls into one that
        is driven. ``joint_dynamics`` takes ``api.joint_dynamics`` values
        under the same one-per-coordinate rule. Without them every joint is
        frictionless, undamped and has no rotor inertia, because those are
        MuJoCo's defaults -- fine for a mechanism falling under gravity, and
        not fine under a motor stiff enough to hold it.

        ``gravity_m_s2`` is a vector in **metres** per second squared --
        the one place besides density where this surface is SI, because
        9.81 is how gravity is quoted and −9810 mm/s² is how a typo hides.
        It defaults to Earth's, and ``[0, 0, 0]`` is the way to isolate a
        joint's own behaviour from the falling.

        ``solver_step_s`` is how finely the solver integrates *between*
        trace frames, which is a different number from ``frames_per_second``
        and always finer. It is rounded so that a whole number of steps
        lands exactly on each frame, and the step that actually ran is
        reported in the trace's evidence. A bouncing contact needs 0.001 s
        or finer and says so.
        """

        operation = "dynamics"
        shared = self._mujoco_model(
            operation,
            assembly,
            bodies,
            actuators,
            joint_dynamics,
            gravity_m_s2,
            solver_step_s,
        )
        model = shared["model"]
        components = shared["components"]
        start = _number(operation, "start_time_s", start_time_s)
        end = _number(operation, "end_time_s", end_time_s)
        if end <= start:
            raise _error(
                operation,
                "end_time_s",
                "must be greater than start_time_s",
                end_time_s,
            )
        if isinstance(frames_per_second, bool) or not isinstance(
            frames_per_second, int
        ):
            raise _error(
                operation,
                "frames_per_second",
                "expected an integer from 1 through 240",
                frames_per_second,
            )
        if not 1 <= frames_per_second <= 240:
            raise _error(
                operation,
                "frames_per_second",
                "must be from 1 through 240",
                frames_per_second,
            )
        step = shared["solver_step_s"]
        if step is not None and step > 1.0 / frames_per_second:
            raise _error(
                operation,
                "solver_step_s",
                f"must not exceed one frame interval ({1.0 / frames_per_second:g} s "
                f"at {frames_per_second} fps): the solver steps between frames, "
                "never across them",
                solver_step_s,
            )
        # One sample per frame plus the input frame, under the same caps
        # api.simulation declares. Unlike the kinematics solver the trace
        # step and the solver step are separate here, so the frame count is
        # exactly what was asked for.
        #
        # These two numbers count what *leaves* the engine -- artifact
        # bytes, keyframes the shell bakes, memory in Blender -- and they
        # are deliberately not the whole budget (M3 phase 4). What the
        # solver *does* is bounded separately, in CadexDynamics, because
        # since solver_step_s became authorable the two costs stopped being
        # proportional: the same 600-frame trace is 4800 solver steps at
        # the default step and 1 200 000 at the finest one allowed. A
        # policy rollout will want exactly that trade -- integrate for
        # minutes, report a hundred poses -- and one combined cap cannot
        # express it.
        estimated_frames = math.ceil((end - start) * frames_per_second) + 2
        if estimated_frames > 10_000 or estimated_frames * len(components) > 100_000:
            raise _error(
                operation,
                "time range/frames_per_second",
                "would exceed 10000 frames or 100000 component-pose samples; "
                "lower frames_per_second or shorten the time range",
            )
        pairs, gap = _clearance_promise(operation, clearance, clearance_mm, model)
        return self._value(
            operation,
            "simulation",
            model,
            bodies=shared["bodies"],
            actuators=shared["actuators"],
            joint_dynamics=shared["joint_dynamics"],
            clearance=pairs,
            clearance_mm=gap,
            start_time_s=start,
            end_time_s=end,
            frames_per_second=frames_per_second,
            gravity_m_s2=shared["gravity_m_s2"],
            solver_step_s=step,
            estimated_frame_limit=estimated_frames,
            label=label,
        )

    def sensor(
        self,
        target: DomainValue,
        kind: str,
        *,
        name: str,
        motion_type: str = "auto",
        range_mm: Any = None,
        resolution_mm: Any = None,
        rate_hz: Any = None,
        noise_mm: Any = None,
        resolution_nmm: Any = None,
        noise_nmm: Any = None,
        resolution_n: Any = None,
        noise_n: Any = None,
        label: str = "",
    ) -> DomainValue:
        """Declare one onboard sensor, so a policy channel can say what measures it.

        ``kind`` is ``imu`` -- ``target`` is the ``api.component`` the IMU
        board is, and it measures that component's own orientation and
        rotation rate -- or ``joint_encoder`` -- ``target`` is an
        ``api.joint``, and it measures that joint's position and rate (a
        servo's potentiometer tapped out, or a servo that reports position).
        A stock hobby servo reports nothing: its joint has no encoder unless
        one is declared.

        ``position_tracker`` (ADR-588) is a touch panel, or a camera
        tracking a marker: ``target`` is the component it is mounted on, and
        it reads *another* body's position in that component's frame through
        a ``tracked_position`` observation. It is declared like a datasheet,
        and all four are required: ``range_mm`` (``[[x0, x1], [y0, y1],
        [z0, z1]]`` in the mount's frame), ``resolution_mm``, ``rate_hz``
        and ``noise_mm`` (one standard deviation per axis). The trainer adds
        the noise and rounds to the resolution; a body outside the range
        reads zeros with ``<name>_in_range`` 0, which a termination can
        name. ``rate_hz`` must be at least the task's control rate. A
        ``tracked_velocity`` of the same body (ADR-590) is the tracker's
        firmware differencing successive readings: listed after the
        position, it reads mm/s with noise ``sqrt(2) * noise_mm * rate_hz``
        and resolution ``resolution_mm * rate_hz``, and zeros while the
        position is out of range.

        ``load_sensor`` (ADR-591) reads the effort an ``api.actuator``
        applies -- a bus servo's load register, or a current sensor on a
        motor's supply -- through an ``actuator_force`` observation of that
        same actuator. ``resolution_nmm``, ``noise_nmm`` (``_n`` on a
        sliding coordinate) and ``rate_hz`` are required; the reading rounds
        to the resolution, the trainer adds the noise, and it saturates at
        the actuator's own effort limit, its stall line. A catalog servo
        declares its own: ``lib.servo(sku).load_sensor(actuator, name=...)``
        fills a bus servo's figures and refuses a PWM servo, which reports
        nothing back. Declared here directly, it is a claim that the machine
        carries a part measuring this motor's current.

        A sensor is an argument to ``api.observation(..., sensor=...)`` and
        nothing else: pass it there, and do not return it. A channel the
        policy reads (``role="policy"``, the default) that names no sensor
        is *ungrounded* -- the exported task says so, and ``cadex train``
        refuses to train on it, because the robot the policy deploys to
        could not feed it that input (ADR-408).
        """

        operation = "sensor"
        clean_kind = str(kind or "").strip().lower()
        wanted = _SENSOR_KINDS.get(clean_kind)
        if wanted is None:
            raise _error(operation, "kind", f"must be one of {sorted(_SENSOR_KINDS)}", kind)
        value = _domain_value(operation, "target", target, output_type=wanted[0])
        clean_name = str(name or "").strip()
        if not _CHANNEL_NAME.fullmatch(clean_name):
            raise _error(operation, "name",
                         "must be a short identifier: a letter followed by up to 47 "
                         "letters, digits or underscores", name)
        properties: dict[str, Any] = {"kind": clean_kind, "name": clean_name}
        if wanted[0] == "joint":
            properties["motion_type"] = _coordinate(operation, value, motion_type)
        datasheet = {"range_mm": range_mm, "resolution_mm": resolution_mm,
                     "rate_hz": rate_hz, "noise_mm": noise_mm}
        load = {"resolution_nmm": resolution_nmm, "noise_nmm": noise_nmm,
                "resolution_n": resolution_n, "noise_n": noise_n}
        if clean_kind == "position_tracker":
            properties["tracker"] = _tracker_datasheet(operation, datasheet)
        elif clean_kind == "load_sensor":
            properties["load"] = _load_datasheet(operation, value,
                                                 {**load, "rate_hz": rate_hz})
        for parameter, given in (*datasheet.items(), *load.items()):
            owners = _SENSOR_DATASHEET_KINDS[parameter]
            if given is not None and clean_kind not in owners:
                raise _error(operation, parameter,
                             f"applies to a {' or a '.join(owners)}, not a {clean_kind}",
                             given)
        return self._value(operation, "sensor", value, label=label, **properties)

    def observation(
        self,
        target: DomainValue,
        kind: str,
        *,
        name: str,
        motion_type: str = "auto",
        role: str = "policy",
        sensor: DomainValue | None = None,
        frame: DomainValue | None = None,
        label: str = "",
    ) -> DomainValue:
        """Declare one channel of a task's observation space.

        An observation is a **sensor in the exported model**, so the
        observation vector is computed by stock MuJoCo and no Cadex code is
        anywhere between the mechanism and the array a trainer reads. What
        this declares is the naming: which quantity, off which part, called
        what.

        ``kind`` is one of:

        * ``position`` / ``velocity`` -- a joint's own coordinate, in
          degrees or millimetres and their per-second forms. ``target`` is
          an ``api.joint``.
        * ``component_position`` / ``component_orientation`` /
          ``component_linear_velocity`` / ``component_angular_velocity`` --
          where a part is and how it is moving, in the world frame.
          ``target`` is an ``api.component``. A ``component_position`` may
          name ``frame=`` another component to be read in that one's frame
          instead (ADR-592) -- the tip as the base sees it, which is what a
          reward compares with a goal held in the base's frame.
        * ``centre_of_mass`` / ``centre_of_mass_velocity`` -- the centre of
          mass of a component *and everything hanging off it*, and how fast
          that point is moving. These are the quantities a balance reward
          wants: a capture point is built from the pair, and neither is the
          same as the corresponding frame channel on the same part.
        * ``centroidal_angular_momentum`` -- that same subtree's angular
          momentum about that same centre of mass, in N·mm·s. The
          rotational half of the pair above and the quantity a *tipping*
          failure is written in: a machine can be upright, still, and
          already going over, which is something this channel says and an
          orientation cannot. Not the same as a
          ``component_angular_velocity`` on the same part, which reads how
          fast one link's frame is turning.
        * ``actuator_force`` -- the effort a motor is actually producing, in
          N·mm or N. ``target`` is an ``api.actuator``.

        **A vector channel expands to suffixed names.** ``name="hand"`` on a
        ``component_position`` gives ``hand_x``, ``hand_y`` and ``hand_z``;
        an orientation gives ``hand_qw`` through ``hand_qz``. Reward
        formulas do arithmetic on scalars, so those suffixed names are what
        a formula writes -- and two channels that would produce one name are
        refused, including when the collision comes from an expansion.

        **Units are the surface's, not MuJoCo's.** An angle observed here is
        degrees and a position is millimetres, exactly as everywhere else in
        this API. The conversion is one number per channel carried in the
        task bundle, so the trainer multiplies rather than converts.

        **Who reads it is ``role``** (ADR-408). ``policy``, the default, is
        an input the trained network reads on the robot, so it must name the
        ``sensor=`` (an ``api.sensor``) that measures it there: an IMU for
        the orientation or rotation rate of the component it is, a joint
        encoder for a joint's position or rate. ``privileged`` is a
        simulation-only quantity -- a centre of mass, a world position, a
        velocity no onboard sensor reads -- which rewards, terminations and
        the trainer's critic may use and the policy never sees. A policy
        channel with no sensor still builds, and the exported task marks it
        ungrounded; ``cadex train`` refuses it.

        An observation is an intermediate value like ``api.collision``: pass
        it to ``api.mjcf``, and do not return it as an output of its own.
        """

        operation = "observation"
        clean_kind = str(kind or "").strip().lower()
        wanted = _OBSERVATION_KINDS.get(clean_kind)
        if wanted is None:
            raise _error(
                operation,
                "kind",
                f"must be one of {sorted(_OBSERVATION_KINDS)}",
                kind,
            )
        value = _domain_value(operation, "target", target, output_type=wanted)
        clean_name = str(name or "").strip()
        if not _CHANNEL_NAME.fullmatch(clean_name):
            raise _error(
                operation,
                "name",
                "must be a short identifier: a letter followed by up to 47 "
                "letters, digits or underscores. It becomes a name reward "
                "formulas write, so it has to be one they can",
                name,
            )
        properties: dict[str, Any] = {"kind": clean_kind, "name": clean_name}
        if frame is not None:
            if clean_kind != "component_position":
                raise _error(
                    operation, "frame",
                    "reads a component_position in another component's "
                    f"frame; a {clean_kind} is read in its own",
                )
            frame = _domain_value(operation, "frame", frame, output_type="component_link")
            if frame is value:
                raise _error(
                    operation, "frame",
                    "is the component being read; name the component whose "
                    "frame it is read in",
                )
            if sensor is not None:
                raise _error(
                    operation, "sensor",
                    "names no sensor a component_position in another "
                    "component's frame is measured by; a body read from "
                    "another one on the machine is a tracked_position",
                    sensor.properties.get("name"),
                )
            clean_role = str(role or "").strip().lower()
            if clean_role not in _OBSERVATION_ROLES:
                raise _error(operation, "role", f"must be one of {list(_OBSERVATION_ROLES)}", role)
            if clean_role != "policy":
                properties["role"] = clean_role
            return self._value(operation, "observation", value, frame,
                               label=label, **properties)
        if wanted == "actuator":
            # An actuator is identified by the coordinate it drives and the
            # kind it is, because that is what the model names it after. Its
            # own coordinate is already resolved, so there is nothing for
            # ``motion_type`` to disambiguate here.
            if str(motion_type or "auto").strip().lower() != "auto":
                raise _error(
                    operation,
                    "motion_type",
                    "does not apply to an actuator_force channel: the actuator "
                    "already names the coordinate it drives",
                    motion_type,
                )
            properties["motion_type"] = str(value.properties.get("motion_type"))
            properties["actuator_kind"] = str(value.properties.get("kind"))
        elif wanted == "joint":
            # A cylindrical joint owns a rotation and a slide, so observing
            # "the position" of one says nothing about which -- the same
            # reason api.actuator and api.joint_dynamics ask.
            properties["motion_type"] = _coordinate(operation, value, motion_type)
        if clean_kind in ("tracked_position", "tracked_velocity") and sensor is None:
            raise _error(
                operation, "sensor",
                f"a {clean_kind} is what a position_tracker reads, so it "
                "names one: its frame is the tracker's mount and its noise is "
                "the tracker's declaration. A world position the robot cannot "
                "measure is a privileged component_position",
                sensor,
            )
        clean_role = str(role or "").strip().lower()
        if clean_role not in _OBSERVATION_ROLES:
            raise _error(operation, "role", f"must be one of {list(_OBSERVATION_ROLES)}", role)
        # Only a non-default role or a sensor reaches the entry, so a task
        # written before ADR-408 exports byte-identical and every policy
        # trained on it still verifies against its digest.
        if clean_role != "policy":
            properties["role"] = clean_role
        if sensor is not None:
            if not isinstance(sensor, DomainValue) or sensor.operation != "sensor":
                raise _error(operation, "sensor", "must be an api.sensor value", sensor)
            sensor_kind = str(sensor.properties.get("kind"))
            measures = _SENSOR_KINDS[sensor_kind][1]
            if clean_kind not in measures:
                raise _error(
                    operation, "sensor",
                    f"a {sensor_kind} measures {sorted(measures)}, not {clean_kind}",
                    sensor.properties.get("name"),
                )
            if sensor_kind == "position_tracker":
                # A tracker reads some *other* body, in its mount's frame:
                # the mount travels as the observation's second argument so
                # the worker can name it.
                if sensor.arguments[0] is value:
                    raise _error(
                        operation, "sensor",
                        f"{sensor.properties.get('name')!r} is mounted on this "
                        "component; a position_tracker reads another body "
                        "relative to its mount",
                        sensor.properties.get("name"),
                    )
                properties["grounded_sensor"] = str(sensor.properties.get("name"))
                properties["grounded_kind"] = sensor_kind
                properties["tracker"] = dict(sensor.properties["tracker"])
                return self._value(operation, "observation", value, sensor.arguments[0],
                                   label=label, **properties)
            if sensor.arguments[0] is not value or (
                wanted == "joint"
                and sensor.properties.get("motion_type") != properties.get("motion_type")
            ):
                raise _error(
                    operation, "sensor",
                    f"{sensor.properties.get('name')!r} measures its own "
                    f"{'joint' if wanted == 'joint' else 'component'}, not this "
                    "observation's target: observe what the sensor is mounted on",
                    sensor.properties.get("name"),
                )
            properties["grounded_sensor"] = str(sensor.properties.get("name"))
            properties["grounded_kind"] = sensor_kind
            if sensor_kind == "load_sensor":
                properties["load"] = dict(sensor.properties["load"])
        return self._value(operation, "observation", value, label=label, **properties)

    def reward(
        self,
        expression: str,
        *,
        weight: float = 1.0,
        label: str = "",
    ) -> DomainValue:
        """One term of a task's reward, as arithmetic on its channels.

        The reward a policy maximises is the weighted sum of these. Terms
        rather than one expression because a training run's most common
        question is *which part of the reward is doing the work*, and a sum
        that was written as one string cannot answer it -- an episode
        reports every term's own contribution separately.

        ``expression`` names the channels the task's ``api.observation``
        values declare, remembering that a vector channel expands:
        ``"-(hand_x - 300)^2"`` rather than ``"hand"``. It may use
        arithmetic, powers, and the one-argument functions ``abs``,
        ``asin``/``arcsin``, ``arctan``, ``cos``, ``sin``, ``exp``, ``sqrt``
        and ``tanh``. Naming a channel the task does not declare is a
        refusal, not a zero.

        ``weight`` is what the term is multiplied by, and its sign is how a
        cost is written: a control cost is a positive quantity with a
        negative weight, which keeps the expression readable as the thing it
        measures.

        A reward is an intermediate value: pass it to ``api.task``.
        """

        operation = "reward"
        formula = _checked_formula(
            operation,
            "expression",
            expression,
            names=None,
            functions=_REWARD_FUNCTIONS,
        )
        return self._value(
            operation,
            "reward",
            expression=formula,
            weight=_number(operation, "weight", weight, minimum=-1.0e12,
                           maximum=1.0e12),
            label=_label(operation, label),
        )

    def termination(
        self,
        expression: str,
        *,
        above: float | None = None,
        below: float | None = None,
        label: str = "",
    ) -> DomainValue:
        """End an episode early when something goes out of range.

        A termination rule is an expression over the task's channels and a
        bound it must not cross. Exactly one of ``above`` and ``below`` is
        required -- a rule with neither is not a rule, and one with both
        reads as an interval when it would mean a union.

        This is what separates a failure from a horizon. An episode that
        used its whole budget and one that was cut short by a mechanism
        spinning out are different outcomes, and a trainer that cannot tell
        them apart learns from the difference anyway.

        A termination is an intermediate value: pass it to ``api.task``.
        """

        operation = "termination"
        formula = _checked_formula(
            operation,
            "expression",
            expression,
            names=None,
            functions=_REWARD_FUNCTIONS,
        )
        if (above is None) == (below is None):
            raise _error(
                operation,
                "above",
                "requires exactly one of above or below: a rule with neither "
                "never fires, and one with both would read as an interval "
                "when it means a union. Declare two terminations instead",
            )
        return self._value(
            operation,
            "termination",
            expression=formula,
            above=(
                None if above is None else _number(operation, "above", above)
            ),
            below=(
                None if below is None else _number(operation, "below", below)
            ),
            label=_label(operation, label),
        )

    def randomise(
        self,
        target: DomainValue,
        property_name: str,
        *,
        scale: Sequence[float],
        label: str = "",
    ) -> DomainValue:
        """Vary one physical property between episodes.

        Domain randomisation, and the reason it belongs in the script rather
        than in a trainer's configuration: the properties worth varying are
        the ones the assembly computed, and the amount worth varying them by
        is a statement about how well the real part is known. A forearm
        whose density is a guess to ten per cent is
        ``scale=[0.9, 1.1]`` here.

        ``property_name`` is one of:

        * ``mass`` on an ``api.component`` -- scales the part's mass **and
          its inertia tensor together**, which is what changing the density
          of a fixed shape means. Scaling one alone would leave a body whose
          rotational inertia no longer matches its mass.
        * ``damping`` / ``armature`` / ``friction_loss`` on an
          ``api.joint`` -- the three ``api.joint_dynamics`` properties. A
          joint whose declared value is zero stays zero however it is
          scaled, which is worth knowing before expecting a spread.

        ``scale`` is a multiplicative range ``[low, high]``, drawn uniformly
        once per episode. Multiplicative rather than additive so that one
        range means the same thing on a 20 g link and a 20 kg one.

        A randomisation is an intermediate value: pass it to ``api.task``.
        """

        operation = "randomise"
        clean_property = str(property_name or "").strip().lower()
        wanted = _RANDOMISATION_TARGETS.get(clean_property)
        if wanted is None:
            raise _error(
                operation,
                "property_name",
                f"must be one of {sorted(_RANDOMISATION_TARGETS)}",
                property_name,
            )
        value = _domain_value(operation, "target", target, output_type=wanted)
        bounds = _vector(operation, "scale", scale, size=2)
        low, high = bounds
        if low <= 0.0:
            raise _error(
                operation,
                "scale",
                "is a multiplicative range and must stay positive: [0.9, 1.1] "
                "is a ten per cent spread. A zero or negative factor is not a "
                "scale, and on a mass it is a body with undefined acceleration",
                scale,
            )
        if high < low:
            raise _error(
                operation, "scale", "must be ordered [low, high]", scale
            )
        properties: dict[str, Any] = {
            "target": clean_property,
            "low": low,
            "high": high,
        }
        if wanted == "joint":
            properties["motion_type"] = _coordinate(operation, value, "auto")
        return self._value(
            operation, "randomise", value, label=label, **properties
        )

    def reset_variation(
        self,
        target: DomainValue,
        *,
        tilt_degrees: Sequence[float] | None = None,
        height_mm: Sequence[float] | None = None,
        angular_velocity_dps: Sequence[float] | None = None,
        linear_velocity_mm_s: Sequence[float] | None = None,
        label: str = "",
    ) -> DomainValue:
        """Start each episode somewhere else, and already moving.

        Without this every episode of a task begins at exactly the same
        keyframe with every velocity zero, and a posture that survives once
        survives forever. A policy trained that way has not learned to
        balance -- it has learned one pose, and nothing in the task ever
        asked it a second question. This is what asks.

        ``target`` is the ``api.component`` carrying the mechanism's
        **floating base**: the body the MJCF gives a free joint. A mechanism
        bolted to the world has no base to vary and this refuses, naming the
        bodies that do.

        What varies, and deliberately what does not:

        * ``tilt_degrees=[low, high]`` -- a lean, drawn as a magnitude with
          its azimuth drawn uniformly over the full circle. The whole
          mechanism rotates **rigidly** about the base's own frame origin:
          every joint angle is left exactly as the solve left it.
        * ``height_mm=[low, high]`` -- an upward offset, never downward. A
          tilt swings the far side of a wide stance downward, and the reset
          pose is the *solved* one with the soles exactly on the floor, so a
          tilt with no lift drives a sole through it. The engine measures
          the penetration the widest declared tilt would cause and refuses
          a pairing that does not clear it.
        * ``angular_velocity_dps=[low, high]`` -- each of the base's three
          angular velocity components, drawn independently, in the **base's
          own frame**, which is where MuJoCo keeps a free joint's angular
          velocity.
        * ``linear_velocity_mm_s=[low, high]`` -- a speed, drawn as a
          magnitude with its azimuth drawn over the full circle exactly as
          the tilt's is, written into the base's linear velocity in the
          **world frame**. Note the asymmetry, which is MuJoCo's and not
          ours: a free joint's *linear* velocity is world-frame and its
          *angular* velocity is body-frame, in the same six numbers.

        **A stumble is an initial velocity**, and that is what this one is
        for. A machine that begins every episode at rest has nothing to
        recover from until something pushes it, so the first second or so of
        every episode teaches only how to stand still; starting it already
        moving gives every episode a recovery to do from step 1. It is safe
        for the same reason the rigid tilt is -- it cannot change the
        mechanism's shape, so it cannot drive a sole through the floor --
        and so it needs no clearance check.

        **Joint angles are never perturbed, and that is the load-bearing
        decision.** The reset pose is the configuration the solver found with
        the soles on the ground; a few degrees at a knee moves a foot
        millimetres through the floor and MuJoCo answers that with a contact
        impulse nothing could stand up to. A rigid tilt plus a lift cannot
        do that, because it cannot change the mechanism's shape at all.

        A reset variation is an intermediate value: pass it to ``api.task``.
        """

        operation = "reset_variation"
        value = _domain_value(
            operation, "target", target, output_type="component_link"
        )
        properties: dict[str, Any] = {}
        given = 0
        for parameter, source, floor in (
            ("tilt_degrees", tilt_degrees, 0.0),
            ("height_mm", height_mm, 0.0),
            ("angular_velocity_dps", angular_velocity_dps, None),
            ("linear_velocity_mm_s", linear_velocity_mm_s, 0.0),
        ):
            if source is None:
                low, high = 0.0, 0.0
            else:
                low, high = _vector(operation, parameter, source, size=2)
                given += 1
            if floor is not None and low < floor:
                raise _error(
                    operation,
                    parameter,
                    "is a magnitude and cannot be negative: a tilt's and a "
                    "speed's direction are drawn rather than declared, and a "
                    "downward height offset is a sole through the floor",
                    source,
                )
            if high < low:
                raise _error(
                    operation, parameter, "must be ordered [low, high]", source
                )
            properties[f"{parameter}_low"] = low
            properties[f"{parameter}_high"] = high
        if not given:
            raise _error(
                operation,
                "tilt_degrees",
                "varies nothing: give at least one of tilt_degrees, "
                "height_mm, angular_velocity_dps or linear_velocity_mm_s. An "
                "entry that draws only zeros costs an episode's arithmetic "
                "and changes no episode",
            )
        return self._value(
            operation,
            "reset_variation",
            value,
            label=_label(operation, label),
            **properties,
        )

    def disturbance(
        self,
        target: DomainValue,
        *,
        newtons: Sequence[float],
        direction: str = "horizontal",
        azimuth_degrees: Sequence[float] | None = None,
        at_seconds: Sequence[float] | None = None,
        duration_s: float | None = None,
        sustained: bool = False,
        label: str = "",
    ) -> DomainValue:
        """Push the mechanism mid-episode and see whether it comes back.

        One entry is **one event**: three shoves an episode is three
        entries, which is the shape ``api.randomise`` already has and what
        keeps the draw order statable in a sentence. The force is applied at
        the target body's **centre of mass**, in the **world frame** -- both
        measured rather than assumed, because a shove applied at a frame
        origin instead would be a torque nobody declared.

        ``newtons=[low, high]`` is the magnitude, drawn per episode.
        ``direction`` is ``"horizontal"``, whose azimuth is drawn uniformly
        over the full circle, or ``"vertical"``, whose sign is drawn.

        ``azimuth_degrees=[low, high]`` narrows a horizontal push to an arc,
        where **0 degrees is world +X** and the angle runs anticlockwise seen
        from above. It is a *world* frame and nothing else: the engine has no
        concept of which way a mechanism faces, so which world azimuth is
        your machine's forward is something you work out from its geometry
        before you declare an arc. Omitted means the full circle, exactly as
        before.

        It exists because a mechanism is not symmetric and its task should
        not have to be: a biped with hip pitch but no ankle roll can answer a
        shove in the plane its actuators work in and cannot answer one across
        it, and drawing uniformly over the whole circle spends most of every
        batch in the direction the machine has no actuator for. Declaring the
        arc is how a task asks the question the mechanism can be trained to
        answer -- so aim it at the machine's *actuated* plane, whichever world
        axis that turns out to be -- and widening it later is how the question
        gets harder.

        It is **refused on a vertical disturbance**, not ignored. A vertical
        push reads the same uniform draw as a *sign*, so an arc there would
        silently mean something else -- and a parameter that means one thing
        on one direction and another thing on the other is a parameter that
        will eventually be read wrong.

        ``at_seconds=[low, high]`` draws when the push starts and
        ``duration_s`` says how long it lasts -- a fixed number, because a
        drawn duration and a drawn magnitude are the same knob twice.
        ``sustained=True`` is the other shape: the force acts for the whole
        episode, which is what wind is, and it takes neither of those two.

        Both are checked against the schedule the task fixes. A push shorter
        than one control interval can fall between two steps and never
        happen, and a push whose window runs past the horizon is partly a
        push and partly nothing -- the engine refuses both with the
        arithmetic in the message rather than quietly delivering less force
        than the script asked for.

        A disturbance is an intermediate value: pass it to ``api.task``.
        """

        operation = "disturbance"
        value = _domain_value(
            operation, "target", target, output_type="component_link"
        )
        clean_direction = str(direction or "").strip().lower()
        if clean_direction not in _DISTURBANCE_DIRECTIONS:
            raise _error(
                operation,
                "direction",
                f"must be one of {sorted(_DISTURBANCE_DIRECTIONS)}",
                direction,
            )
        low, high = _vector(operation, "newtons", newtons, size=2)
        if low < 0.0:
            raise _error(
                operation,
                "newtons",
                "is a magnitude and cannot be negative: which way the push "
                "goes is drawn, not signed",
                newtons,
            )
        if high < low:
            raise _error(
                operation, "newtons", "must be ordered [low, high]", newtons
            )
        if not isinstance(sustained, bool):
            raise _error(
                operation, "sustained", "expected True or False", sustained
            )
        # The full circle when nothing is declared, so that the bundle always
        # carries an arc and the draw is one remap with no special case in
        # it. `[0, 360]` maps a drawn angle onto itself, exactly.
        arc_low, arc_high = 0.0, 360.0
        if azimuth_degrees is not None:
            if clean_direction != "horizontal":
                raise _error(
                    operation,
                    "azimuth_degrees",
                    f"is not accepted on a {clean_direction} disturbance: a "
                    "vertical push reads its draw as a sign, up or down, so "
                    "an arc of the ground plane would silently mean "
                    "something other than what it says",
                    azimuth_degrees,
                )
            arc_low, arc_high = _vector(
                operation, "azimuth_degrees", azimuth_degrees, size=2
            )
            if arc_high < arc_low:
                raise _error(
                    operation,
                    "azimuth_degrees",
                    "must be ordered [low, high]; to sweep through 0 give a "
                    "negative low, as [-60, 60] does",
                    azimuth_degrees,
                )
            if arc_high - arc_low > 360.0:
                raise _error(
                    operation,
                    "azimuth_degrees",
                    "spans more than one full circle, so part of it is drawn "
                    "twice as often as the rest. Give at most 360 degrees, or "
                    "omit it for the whole circle",
                    azimuth_degrees,
                )
        properties: dict[str, Any] = {
            "direction": clean_direction,
            "newtons_low": low,
            "newtons_high": high,
            "azimuth_degrees_low": arc_low,
            "azimuth_degrees_high": arc_high,
            "sustained": bool(sustained),
        }
        if sustained:
            for parameter, source in (
                ("at_seconds", at_seconds),
                ("duration_s", duration_s),
            ):
                if source is not None:
                    raise _error(
                        operation,
                        parameter,
                        "is not accepted with sustained=True: a sustained "
                        "disturbance acts for the whole episode, which is "
                        "the one window that needs no start and no length",
                        source,
                    )
            properties["at_seconds_low"] = 0.0
            properties["at_seconds_high"] = 0.0
            properties["duration_s"] = 0.0
        else:
            if at_seconds is None or duration_s is None:
                raise _error(
                    operation,
                    "at_seconds",
                    "a disturbance that is not sustained needs both "
                    "at_seconds=[low, high] and duration_s=...: when it "
                    "happens and how long it lasts",
                )
            start_low, start_high = _vector(
                operation, "at_seconds", at_seconds, size=2
            )
            if start_low < 0.0:
                raise _error(
                    operation,
                    "at_seconds",
                    "cannot start before the episode does",
                    at_seconds,
                )
            if start_high < start_low:
                raise _error(
                    operation, "at_seconds", "must be ordered [low, high]",
                    at_seconds,
                )
            properties["at_seconds_low"] = start_low
            properties["at_seconds_high"] = start_high
            properties["duration_s"] = _number(
                operation, "duration_s", duration_s,
                minimum=0.0, strict_minimum=True,
            )
        return self._value(
            operation,
            "disturbance",
            value,
            label=_label(operation, label),
            **properties,
        )

    def goal(
        self,
        name: str,
        *,
        kind: str = "value",
        between: Sequence[float] | None = None,
        tip: DomainValue | None = None,
        tip_offset_mm: Sequence[float] | None = None,
        joint_fraction: float = 0.8,
        min_z_mm: float | None = None,
        min_separation_mm: float = 0.0,
        frame: DomainValue | None = None,
        period_seconds: float | None = None,
        resample_seconds: float | None = None,
        label: str = "",
    ) -> DomainValue:
        """Tell the policy where to go: a number or a place drawn per episode.

        A task without a goal asks one question -- stand, hold this pose --
        and a policy answers it once. A goal is what makes the question
        change: a speed to walk at, a point to reach, a width to close to.
        It is drawn afresh every episode, **the policy observes it**, the
        reward and the terminations name it exactly as they name an
        observation channel, and a rollout's trace records it frame by
        frame.

        ``kind`` says what it is:

        * ``"value"`` -- one number between ``between=[low, high]``, in
          whatever unit the reward reads it in. Its channel is ``name``.
        * ``"speed"`` -- the **commanded forward speed**, in millimetres per
          second, between ``between=[low, high]``. Its channel is ``name``.
          It is a ``value`` with a meaning the engine knows: a success spec
          reads ``speed_ratio`` and ``lateral_ratio`` against it. The reward
          still has to pay for it -- naming the goal is what ties the two.
        * ``"point"`` -- a place in the world, in millimetres, that ``tip``
          can reach. Its channels are ``name_x``, ``name_y`` and ``name_z``.
          The engine draws a joint configuration with every joint the task
          drives in the middle ``joint_fraction`` of its own range, and the
          target is where the point ``tip_offset_mm`` on ``tip`` is there.
          A draw is taken again, up to a hundred times, when the point is
          under ``min_z_mm`` (world Z), when the configuration puts the
          mechanism in a contact it is not in at rest, or when the point is
          within ``min_separation_mm`` of where the tip starts the segment.
          A success spec reads the reach metrics against it.

          ``frame=component`` holds the point in that component's frame
          (ADR-592): it is drawn as above, then kept relative to the
          component, so it travels with it. Its channels read it in the
          component's frame, in millimetres -- the target as a base would
          see it -- and the reach metrics measure the tip against where it
          was at every frame. A reward compares it with the tip read in
          the same frame: ``observation(tip, "component_position",
          frame=component, role="privileged")``. Use it when the part that
          carries the mechanism moves during an episode -- a tracked or
          wheeled base, a platform that slides -- and the target belongs
          to the machine's own workspace. A spec's goals must be held in
          the frame the task's are.
        * ``"phase"`` -- a clock (ADR-598): an angle that turns once every
          ``period_seconds``, anticlockwise (increasing), from a start drawn
          uniformly over one turn per episode. Its channels are
          ``name_sin`` and ``name_cos``, computed from the episode's step
          counter. Nothing else a policy or a reward reads carries time, so
          this is how a task asks for a motion that keeps going -- a body
          led round a circle, a gait at a set cadence: the target angle is
          ``atan2(name_sin, name_cos)``, and the cosine of a body's lag
          behind it at ``(x, y)`` is ``(x*name_cos + y*name_sin) /
          sqrt(x*x + y*y)``. It is the controller's own timer, not a
          sensor reading. Turn the other way with ``-name_sin``.

        A task states at most one ``speed`` and one ``point``; ``value``
        and ``phase`` goals are free.

        ``resample_seconds`` draws the goal again that often during the
        episode, which is what makes a policy learn to *change* what it is
        doing. It must be a whole number of control steps. Omitted, the goal
        is held for the episode.

        An episode played without a seed holds the middle of a range, or
        the point the tip already occupies.

        A goal is an intermediate value: pass it to ``api.task(goals=[...])``.
        """

        operation = "goal"
        clean_name = str(name or "").strip()
        if not _CHANNEL_NAME.fullmatch(clean_name):
            raise _error(
                operation,
                "name",
                "must be a short identifier: a letter followed by up to 47 "
                "letters, digits or underscores. It becomes a name reward "
                "formulas write, so it has to be one they can",
                name,
            )
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in _GOAL_KINDS:
            raise _error(
                operation, "kind", f"must be one of {list(_GOAL_KINDS)}", kind
            )
        properties: dict[str, Any] = {"name": clean_name, "kind": clean_kind}
        if clean_kind != "phase" and period_seconds is not None:
            raise _error(
                operation, "period_seconds",
                f"is how long a phase goal takes to turn once, and this is "
                f"a {clean_kind}", period_seconds,
            )
        if clean_kind == "point":
            if between is not None:
                raise _error(
                    operation, "between",
                    "is the range of a value or a speed; a point is drawn "
                    "from the poses its tip can reach", between,
                )
            if tip is None:
                raise _error(
                    operation, "tip",
                    "a point goal needs the component whose point is to "
                    "reach it: tip=component",
                )
            properties["tip"] = _domain_value(
                operation, "tip", tip, output_type="component_link"
            )
            properties["tip_offset_mm"] = (
                [0.0, 0.0, 0.0] if tip_offset_mm is None
                else _vector(operation, "tip_offset_mm", tip_offset_mm, size=3)
            )
            properties["joint_fraction"] = _number(
                operation, "joint_fraction", joint_fraction,
                minimum=0.0, maximum=1.0, strict_minimum=True,
            )
            if min_z_mm is not None:
                properties["min_z_mm"] = _number(operation, "min_z_mm", min_z_mm)
            if frame is not None:
                properties["frame"] = _domain_value(
                    operation, "frame", frame, output_type="component_link"
                )
                if properties["frame"] is properties["tip"]:
                    raise _error(
                        operation, "frame",
                        "is the tip itself; a target held in the tip's own "
                        "frame never moves relative to it. Name the component "
                        "the target travels with",
                    )
            properties["min_separation_mm"] = _number(
                operation, "min_separation_mm", min_separation_mm, minimum=0.0
            )
        else:
            for parameter, source, default in (
                ("tip", tip, None),
                ("tip_offset_mm", tip_offset_mm, None),
                ("min_z_mm", min_z_mm, None),
                ("joint_fraction", joint_fraction, 0.8),
                ("min_separation_mm", min_separation_mm, 0.0),
                ("frame", frame, None),
            ):
                if source is not None and source != default:
                    raise _error(
                        operation, parameter,
                        "describes how a point goal is drawn, and this is "
                        f"a {clean_kind}", source,
                    )
        if clean_kind == "phase":
            if between is not None:
                raise _error(
                    operation, "between",
                    "is the range of a value or a speed; a phase starts "
                    "anywhere on its turn", between,
                )
            if period_seconds is None:
                raise _error(
                    operation, "period_seconds",
                    "a phase goal turns once every period_seconds: give it",
                )
            properties["period_seconds"] = _number(
                operation, "period_seconds", period_seconds,
                minimum=0.0, maximum=3600.0, strict_minimum=True,
            )
        elif clean_kind != "point":
            if between is None:
                raise _error(
                    operation, "between",
                    f"a {clean_kind} goal is drawn between two numbers: "
                    "between=[low, high]",
                )
            low, high = _vector(operation, "between", between, size=2)
            if high < low:
                raise _error(
                    operation, "between", "must be ordered [low, high]", between
                )
            properties["low"] = low
            properties["high"] = high
        if resample_seconds is not None:
            properties["resample_seconds"] = _number(
                operation, "resample_seconds", resample_seconds,
                minimum=0.0, maximum=3600.0, strict_minimum=True,
            )
        return self._value(
            operation, "goal", label=_label(operation, label), **properties
        )

    def success(
        self,
        predicates: Sequence[Mapping[str, Any]],
        *,
        seeds: Sequence[int],
        feet: Sequence[DomainValue] = (),
        tip: DomainValue | None = None,
        tip_offset_mm: Sequence[float] | None = None,
        body: DomainValue | None = None,
        body_offset_mm: Sequence[float] | None = None,
        centre: DomainValue | None = None,
        centre_mm: Sequence[float] | None = None,
        centre_axis: Sequence[float] | None = None,
        episode_seconds: float | None = None,
        randomisation: Sequence[DomainValue] | None = None,
        reset_variation: Sequence[DomainValue] | None = None,
        disturbance: Sequence[DomainValue] | None = None,
        goals: Sequence[DomainValue] | None = None,
        scale: Mapping[str, float] | None = None,
        label: str = "",
    ) -> DomainValue:
        """Say what a policy must *do* to have succeeded, apart from its reward.

        A reward is what a policy is paid for, and a policy that was paid
        and shuffled is the failure this exists to catch. A success spec is
        the other reading: bounds on **behaviour metrics** measured from a
        rollout's poses -- how far it tilted, how many real steps each foot
        took, how long it took to come to rest after a shove -- on seeds and
        under conditions the spec states itself. **It can never read the
        reward**: a predicate names a metric from the engine's fixed list,
        none of which is the reward, a reward term or an observation
        channel, and anything else is refused by name.

        ``predicates`` is a list of ``{"id": ..., "metric": ..., "min": ...,
        "max": ...}`` with at least one bound each; ``id`` defaults to the
        metric's name. A seed passes when **every** predicate holds, and a
        metric that could not be measured -- a foot that never stepped has
        no step clearance -- fails rather than passing on nothing.

        The metrics, by what they need:

        * always: ``completed`` (1 when the episode ran to its horizon with
          no termination) and ``duration_s``;
        * a floating base: ``max_tilt_deg``, ``max_heading_deg``,
          ``final_heading_deg``, ``max_drift_mm``, ``final_drift_mm``,
          ``mean_speed_mm_s``, and on a floor ``max_drift_com_heights``;
        * a shove in the spec's conditions: ``recovery_s_max``;
        * ``feet``: ``steps_min``, ``step_share_min``, ``step_count_ratio``,
          ``step_clearance_hip_heights_min``, ``slip_share_max``,
          ``duty_factor_min``, ``duty_factor_max``,
          ``foot_lowest_hip_heights_min``, ``mean_forward_speed_mm_s`` and
          ``mean_lateral_speed_mm_s``. "Every foot" is the worst foot;
        * a goal the task states (``api.goal``): against its ``speed``
          goal, ``speed_ratio`` and ``lateral_ratio`` (with ``feet``) --
          the mean forward and lateral speed as a ratio of the commanded
          one; against its ``point`` goal and with ``tip``, the reach
          metrics ``final_error_mm_max``, ``final_error_arm_lengths_max``,
          ``time_to_target_s_max`` and ``overshoot_ratio_max``, each the
          worst over the targets the episode held. **A spec that bounds one
          of these on a task with no such goal is refused**: nothing a
          rollout did can be measured against a command it was never given.
        * ``body``: the motion of that body about a centre (ADR-587) --
          ``turns``, its net signed turns about ``centre_axis`` through the
          centre (anticlockwise seen from the axis tip is positive), so a
          body that rocks on an arc reads about zero; ``laps``, the whole
          turns completed in the net direction; and ``final_distance_mm``,
          ``mean_distance_mm`` and ``max_distance_mm`` from the centre
          point. None needs a goal. An episode that did not run to its
          horizon measures none of them, so a spec bounding one fails it.

        ``feet`` names the ``api.component`` values that are feet; each
        needs a primitive collision shape, because a foot's height is its
        lowest collision point above the floor. ``tip`` names the component
        carrying the point a reach is measured at, ``tip_offset_mm`` where
        on it, in its own frame.

        ``body`` names the component whose motion is judged, and
        ``body_offset_mm`` the point on it, in its own frame (a ball's
        centre is its origin). ``centre`` names the component the centre is
        fixed in -- a plate that tilts carries it -- and is the world when
        omitted; ``centre_mm`` is the point in that frame (default the
        origin) and ``centre_axis`` the axis turns are counted about
        (default +Z of that frame).

        ``seeds`` are the evaluation seeds, fixed in the script so that two
        evaluations of one policy are the same episodes. **They are never
        training seeds.**

        ``randomisation``, ``reset_variation`` and ``disturbance`` are the
        conditions an evaluation episode runs under, as the same values
        ``api.task`` takes. Omitted, each is the task's own; ``[]`` is none.
        They are separate from the task's because a test is not a lesson: a
        policy trained against 1 N shoves may be asked to survive 2 N, and a
        policy trained on a varied mass may be judged on the mechanism as
        built -- ``randomisation=[]``. The randomisation draws come first in
        a seed's stream, so stating it also fixes which start and which
        shove that seed draws. ``episode_seconds`` likewise defaults to the
        task's.

        ``goals`` is the same kind of condition: omitted, the evaluation
        draws the task's own goals. Given, it must name **the task's goals
        again** -- the same names and kinds, in the same order, because the
        policy reads them by position -- and may change what each is drawn
        from: a wider range of speeds, a target further from the start,
        another ``resample_seconds``. A goal's draws come last in a seed's
        stream, so stating one moves no reset and no shove.

        ``scale`` states the mechanism the spec's own numbers were written
        for: ``{"hip_height_mm": HIP_MM, "weight_n": WEIGHT_N}``, any of
        ``mass_kg``, ``weight_n``, ``com_height_mm``, ``hip_height_mm`` and
        ``arm_length_mm``. A spec that draws a commanded speed in hip
        heights per second, or a shove in body weights, is only the spec it
        claims to be on the body it was measured from. **Stated, the engine
        refuses the spec when the mechanism measures otherwise** -- to one
        part in a million, which is a copied digit and never physics -- and
        names the values it measured, so a mechanism change cannot leave a
        stale constant behind. Omitted, nothing is checked.

        A success spec is an intermediate value: pass it to ``api.task``.
        """

        operation = "success"
        if not isinstance(predicates, (list, tuple)) or not (
            1 <= len(predicates) <= _MAX_SUCCESS_PREDICATES
        ):
            raise _error(
                operation,
                "predicates",
                f"expected an array of 1 through {_MAX_SUCCESS_PREDICATES} "
                "predicate objects: a spec with none passes everything",
                predicates,
            )
        rows: list[dict[str, Any]] = []
        taken: set[str] = set()
        for index, raw in enumerate(predicates):
            where = f"predicates[{index}]"
            if not isinstance(raw, Mapping):
                raise _error(operation, where, "expected an object", raw)
            extra = set(raw) - _SUCCESS_PREDICATE_KEYS
            if extra:
                raise _error(
                    operation, where,
                    f"unknown keys {sorted(str(key) for key in extra)}; a "
                    "predicate is id, metric, min and max", dict(raw),
                )
            metric = raw.get("metric")
            if not isinstance(metric, str) or not _SUCCESS_METRIC_NAME.fullmatch(metric):
                raise _error(
                    operation, f"{where}.metric",
                    "must be the name of one behaviour metric. A predicate "
                    "is a name and a bound, never an expression: what it "
                    "bounds is measured from the rollout, not computed from "
                    "the task's channels or its reward", metric,
                )
            identifier = str(raw.get("id") or metric).strip()
            if not identifier or len(identifier) > 64:
                raise _error(
                    operation, f"{where}.id", "must contain 1-64 characters",
                    raw.get("id"),
                )
            if identifier in taken:
                raise _error(
                    operation, f"{where}.id",
                    "is used by an earlier predicate; a report names each "
                    "predicate by its id", identifier,
                )
            taken.add(identifier)
            low = (
                None if raw.get("min") is None
                else _number(operation, f"{where}.min", raw.get("min"))
            )
            high = (
                None if raw.get("max") is None
                else _number(operation, f"{where}.max", raw.get("max"))
            )
            if low is None and high is None:
                raise _error(
                    operation, where,
                    "states no bound: give min, max or both", dict(raw),
                )
            if low is not None and high is not None and high < low:
                raise _error(
                    operation, where,
                    "has max below min, which nothing can satisfy", dict(raw),
                )
            rows.append({"id": identifier, "metric": metric, "min": low, "max": high})

        if not isinstance(seeds, (list, tuple)) or not (
            1 <= len(seeds) <= _MAX_SUCCESS_SEEDS
        ):
            raise _error(
                operation, "seeds",
                f"expected an array of 1 through {_MAX_SUCCESS_SEEDS} "
                "evaluation seeds", seeds,
            )
        clean_seeds: list[int] = []
        for index, seed in enumerate(seeds):
            if isinstance(seed, bool) or not isinstance(seed, int) or not (
                0 <= seed <= 2**31 - 1
            ):
                raise _error(
                    operation, f"seeds[{index}]",
                    "expected an integer from 0 through 2147483647", seed,
                )
            clean_seeds.append(seed)
        if len(set(clean_seeds)) != len(clean_seeds):
            raise _error(
                operation, "seeds",
                "repeats a seed: the same episode twice is one result "
                "counted twice", list(seeds),
            )

        foot_values = _values(
            operation, "feet", feet, output_type="component_link", minimum=0
        )
        if len(foot_values) > _MAX_SUCCESS_FEET:
            raise _error(
                operation, "feet",
                f"may name at most {_MAX_SUCCESS_FEET} components",
            )
        properties: dict[str, Any] = {
            "predicates": rows,
            "seeds": clean_seeds,
            "feet": foot_values,
        }
        if tip is None:
            if tip_offset_mm is not None:
                raise _error(
                    operation, "tip_offset_mm",
                    "is a point on the tip component, and no tip is named",
                    tip_offset_mm,
                )
        else:
            properties["tip"] = _domain_value(
                operation, "tip", tip, output_type="component_link"
            )
            properties["tip_offset_mm"] = (
                [0.0, 0.0, 0.0] if tip_offset_mm is None
                else _vector(operation, "tip_offset_mm", tip_offset_mm, size=3)
            )
        if body is None:
            for name, value in (
                ("body_offset_mm", body_offset_mm), ("centre", centre),
                ("centre_mm", centre_mm), ("centre_axis", centre_axis),
            ):
                if value is not None:
                    raise _error(
                        operation, name,
                        "describes the motion of a body, and no body is named",
                        value if name != "centre" else "component",
                    )
        else:
            properties["body"] = _domain_value(
                operation, "body", body, output_type="component_link"
            )
            properties["body_offset_mm"] = (
                [0.0, 0.0, 0.0] if body_offset_mm is None
                else _vector(operation, "body_offset_mm", body_offset_mm, size=3)
            )
            if centre is not None:
                properties["centre"] = _domain_value(
                    operation, "centre", centre, output_type="component_link"
                )
            properties["centre_mm"] = (
                [0.0, 0.0, 0.0] if centre_mm is None
                else _vector(operation, "centre_mm", centre_mm, size=3)
            )
            axis = (
                [0.0, 0.0, 1.0] if centre_axis is None
                else _vector(operation, "centre_axis", centre_axis, size=3)
            )
            if math.sqrt(sum(v * v for v in axis)) <= 1.0e-9:
                raise _error(
                    operation, "centre_axis",
                    "is zero, and turns are counted about a direction", list(axis),
                )
            properties["centre_axis"] = axis
        if episode_seconds is not None:
            properties["episode_seconds"] = _number(
                operation, "episode_seconds", episode_seconds,
                minimum=0.0, maximum=3600.0, strict_minimum=True,
            )
        # ``None`` is "the task's own" and is simply absent; an empty list
        # is a statement -- evaluate the mechanism as built, with no
        # variation, or with no shove.
        if randomisation is not None:
            properties["randomisation"] = _values(
                operation, "randomisation", randomisation,
                output_type="randomise", minimum=0,
            )
        if reset_variation is not None:
            properties["reset_variation"] = _values(
                operation, "reset_variation", reset_variation,
                output_type="reset_variation", minimum=0,
            )
        if disturbance is not None:
            properties["disturbance"] = _values(
                operation, "disturbance", disturbance,
                output_type="disturbance", minimum=0,
            )
        if goals is not None:
            properties["goals"] = _values(
                operation, "goals", goals, output_type="goal", minimum=0
            )
        if scale is not None:
            if not isinstance(scale, Mapping) or not scale:
                raise _error(
                    operation, "scale",
                    "expected an object naming at least one of "
                    f"{list(_SUCCESS_SCALE_KEYS)}", scale,
                )
            unknown = set(scale) - set(_SUCCESS_SCALE_KEYS)
            if unknown:
                raise _error(
                    operation, "scale",
                    f"unknown keys {sorted(str(key) for key in unknown)}; a "
                    f"stated scale names {list(_SUCCESS_SCALE_KEYS)}",
                    dict(scale),
                )
            properties["scale"] = {
                key: _number(
                    operation, f"scale.{key}", scale[key],
                    minimum=0.0, strict_minimum=True,
                )
                for key in _SUCCESS_SCALE_KEYS if key in scale
            }
        return self._value(
            operation, "success", label=_label(operation, label), **properties
        )

    def mjcf(
        self,
        assembly: DomainValue,
        bodies: Sequence[DomainValue],
        *,
        actuators: Sequence[DomainValue] = (),
        joint_dynamics: Sequence[DomainValue] = (),
        observations: Sequence[DomainValue] = (),
        gravity_m_s2: Sequence[float] | None = None,
        solver_step_s: float | None = None,
        label: str = "",
    ) -> DomainValue:
        """Export the assembly as a MuJoCo MJCF model file.

        The same model ``api.dynamics`` would simulate, written out instead
        of run: one self-contained ``.xml`` retained as a program artifact,
        carrying mass and inertia computed exactly from each component's
        solids rather than estimated from a bounding box. It loads in a
        stock MuJoCo with no Cadex anywhere near it.

        Every parameter means what it means in ``api.dynamics`` and is
        checked the same way -- one ``assembly.body`` per component, at most
        one actuator and one ``joint_dynamics`` per joint coordinate,
        gravity in metres per second squared. What is absent is everything
        that counts a *trace*: there is no time range and no
        ``frames_per_second``, because nothing is integrated.

        **The file opens where the assembly was solved.** MuJoCo's own
        reference configuration is the one where each joint's connector
        frames coincide, which is not the solved pose; the export writes a
        keyframe named ``solved`` and anything reading the file should reset
        to it.

        **Collision geometry only.** A component with no
        ``assembly.collision`` shapes exports no geom, exactly as it
        contributes none in a dynamics run -- which means a mechanism with
        no collision shapes at all opens *invisible* in MuJoCo's viewer,
        held together by joints that are drawn as nothing. Give the parts
        that matter a collision shape if the file is meant to be looked at.

        Unlike ``api.simulation`` and ``api.dynamics`` a script may declare
        **more than one** ``api.mjcf`` output: the "exactly one simulation"
        rule exists because the shell bakes one animation, and an exported
        model is not baked. An ``api.mjcf`` may sit beside an
        ``api.dynamics`` in the same script, or beside ``api.motion``
        outputs -- kinematics on screen and a dynamics model on disk is a
        useful pair and a legal one.

        ``observations`` takes ``api.observation`` values and writes them
        into the file as MJCF sensors, which is what makes the exported
        model readable as a task rather than only as a mechanism. They are
        dynamically inert -- measured, not assumed -- so a model that gains
        channels integrates identically to the one that had none, and
        everything this docstring promises above stays true of it.
        """

        operation = "mjcf"
        shared = self._mujoco_model(
            operation,
            assembly,
            bodies,
            actuators,
            joint_dynamics,
            gravity_m_s2,
            solver_step_s,
        )
        channels = self._observations(
            operation, observations, shared, assembly=shared["model"]
        )
        return self._value(
            operation,
            "mjcf",
            shared["model"],
            bodies=shared["bodies"],
            actuators=shared["actuators"],
            joint_dynamics=shared["joint_dynamics"],
            observations=channels,
            gravity_m_s2=shared["gravity_m_s2"],
            solver_step_s=shared["solver_step_s"],
            label=label,
        )

    @staticmethod
    def _observations(
        operation: str,
        observations: Sequence[DomainValue],
        shared: Mapping[str, Any],
        *,
        assembly: DomainValue,
    ) -> list[DomainValue]:
        """Every declared channel, against the model it claims to observe.

        The API's half of the resolution. It can check that a channel reads
        a part this assembly lists and a motor this model carries, and that
        two channels do not collide by name once the vector ones expand --
        which is everything a reader of the script could check by looking.

        What it cannot check is whether the joint survives into the dynamics
        model: a joint the spanning forest turns into a loop closure owns no
        coordinate, and only the engine knows which one that is. That
        refusal is :func:`CadexDynamics.observation_records`'s, and it names
        the reason rather than the absence.
        """

        entries = _values(
            operation, "observations", observations, output_type="observation",
            minimum=0,
        )
        component_ids = {id(item) for item in assembly.properties.get("components", ())}
        joint_ids = {id(item) for item in assembly.properties.get("joints", ())}
        actuator_ids = {id(item) for item in shared["actuators"]}
        taken: dict[str, str] = {}
        for index, entry in enumerate(entries):
            where = f"observations[{index}]"
            target = entry.arguments[0]
            kind = str(entry.properties.get("kind"))
            wanted = _OBSERVATION_KINDS[kind]
            if wanted == "component_link" and id(target) not in component_ids:
                raise _error(
                    operation, where,
                    "observes a component that is not listed in this assembly",
                )
            if len(entry.arguments) > 1 and id(entry.arguments[1]) not in component_ids:
                raise _error(
                    operation, where,
                    "is read in the frame of a component that is not listed "
                    "in this assembly",
                )
            if wanted == "joint" and id(target) not in joint_ids:
                raise _error(
                    operation, where,
                    "observes a joint that is not listed in this assembly",
                )
            if wanted == "actuator" and id(target) not in actuator_ids:
                raise _error(
                    operation, where,
                    "reads the effort of an actuator this model does not "
                    "carry; pass the same api.actuator value given to "
                    f"api.{operation}(actuators=...)",
                )
            name = str(entry.properties.get("name"))
            for channel in _observation_channels(kind, name):
                if channel in taken:
                    raise _error(
                        operation, where,
                        f"declares a channel {channel!r} that "
                        f"{taken[channel]!r} already declares. A vector "
                        "observation expands: one named 'hand' occupies "
                        "hand_x, hand_y and hand_z",
                    )
                taken[channel] = name
        return entries

    def task(
        self,
        model: DomainValue,
        *,
        actions: Sequence[DomainValue],
        reward: Sequence[DomainValue],
        episode_seconds: float,
        control_hz: int,
        termination: Sequence[DomainValue] = (),
        randomisation: Sequence[DomainValue] = (),
        reset_variation: Sequence[DomainValue] = (),
        disturbance: Sequence[DomainValue] = (),
        goals: Sequence[DomainValue] = (),
        success: DomainValue | None = None,
        label: str = "",
    ) -> DomainValue:
        """Turn one exported model into a trainable task.

        A model is not a task. Training needs an observation space, an
        action space, a reward, a termination rule, an episode length and
        domain randomisation -- none of which is geometry, all of which is
        data, and the script is already the sole source of truth for data.

        This consumes an ``api.mjcf`` value and writes **one JSON bundle**
        that references that model by relative path and sha256. One output,
        one artifact: there is no second XML, and a bundle whose model moved
        is detectable rather than merely unlucky.

        ``actions`` names the ``api.actuator`` values a policy drives. **Each
        one's range is derived from the mechanism**, and where it cannot be
        derived this refuses rather than defaulting:

        * a ``motor`` is bounded by its ``torque_limit_nmm`` /
          ``force_limit_n``;
        * a ``position`` servo is bounded by its joint's own limits, both
          endpoints declared;
        * a ``velocity`` actuator has no derivable range at all, because a
          joint states position limits and never a speed.

        A joint with no limits, or with only one endpoint, is the same
        refusal. The missing endpoint of a one-sided limit is filled in with
        a margin worth a hundred turns so the solver treats the joint as
        free; that is a convenience, not a mechanical bound, and an action
        range taken from it would be a limit nobody designed.

        ``episode_seconds`` and ``control_hz`` set the horizon and the rate
        a policy acts at. The rate is rounded so that a whole number of
        solver steps lands exactly on each action, the way ``api.dynamics``
        rounds frames, and the rate that really ran is what the bundle
        records.

        **The actuators keep their control formulas.** A policy-driven
        actuator's formula becomes its deterministic fallback action, which
        is what lets the episode run -- and be compared against a stock
        MuJoCo -- before any policy exists.

        ``randomisation``, ``reset_variation`` and ``disturbance`` are the
        three ways an episode differs from the one before it, and they are
        not interchangeable. A randomisation varies the *mechanism* -- a
        mass, a damping -- and a trainer holds one draw per environment for
        a whole run. A reset variation varies where the episode *starts*,
        and a disturbance is a force that arrives while it is *running*;
        both are drawn afresh every episode, because a posture that is never
        disturbed is a posture that was never tested. A task with neither of
        the last two asks a policy exactly one question and accepts one
        answer, which is what makes bracing a winning strategy.

        ``goals`` takes ``api.goal`` values: what each episode asks the
        policy to do -- a speed, a point to reach, a number -- drawn afresh
        every episode and optionally again during it. The policy observes
        every goal, after its sensor channels, and ``reward`` and
        ``termination`` expressions name a goal's channels as they name an
        observation's. A task with none asks the same thing every episode.

        ``success`` takes one ``api.success`` value: what the behaviour
        must measurably be, on which seeds and under which conditions. It is
        written into the bundle beside the reward and is **not part of what
        the task is** -- a policy trained on this task stays a policy for it
        when the spec is revised, which is what lets a stricter spec be held
        against every earlier policy.

        Like ``api.mjcf`` and for the same reason, ``api.task`` is not under
        the "exactly one simulation" rule: a script may declare several,
        each named from its own output, and two tasks may share one model.
        """

        operation = "task"
        value = _domain_value(operation, "model", model, output_type="mjcf")
        action_values = _values(
            operation, "actions", actions, output_type="actuator", minimum=1
        )
        declared_actuators = {
            id(item) for item in value.properties.get("actuators", ())
        }
        # One actuator is one action, and ``_values`` already refuses a list
        # that repeats a graph value -- so what is left to check here is
        # only that each one belongs to *this* model.
        for index, entry in enumerate(action_values):
            if id(entry) not in declared_actuators:
                raise _error(
                    operation,
                    f"actions[{index}]",
                    "drives an actuator this model does not carry; pass the "
                    "same api.actuator value given to api.mjcf(actuators=...)",
                )
        reward_values = _values(
            operation, "reward", reward, output_type="reward", minimum=1
        )
        termination_values = _values(
            operation, "termination", termination, output_type="termination",
            minimum=0,
        )
        randomisation_values = _values(
            operation, "randomisation", randomisation, output_type="randomise",
            minimum=0,
        )
        # The assembly the model was exported from is its one argument, so
        # a randomisation is checked against the same lists api.mjcf was.
        assembly = value.arguments[0]
        component_ids = {
            id(item) for item in assembly.properties.get("components", ())
        }
        joint_ids = {id(item) for item in assembly.properties.get("joints", ())}
        _check_randomisation(
            operation, "randomisation", randomisation_values,
            component_ids, joint_ids,
        )
        # The two M9 lists, checked against the same component list. Their
        # sizing -- whether a tilt clears the floor, whether a shove is
        # longer than a control interval and lands inside the horizon -- is
        # the engine's, because every one of those questions needs the
        # compiled model or the rounded schedule and this surface has
        # neither.
        variation_values = _values(
            operation, "reset_variation", reset_variation,
            output_type="reset_variation", minimum=0,
        )
        disturbance_values = _values(
            operation, "disturbance", disturbance,
            output_type="disturbance", minimum=0,
        )
        for parameter, entries in (
            ("reset_variation", variation_values),
            ("disturbance", disturbance_values),
        ):
            for index, entry in enumerate(entries):
                if id(entry.arguments[0]) not in component_ids:
                    raise _error(
                        operation,
                        f"{parameter}[{index}]",
                        "names a component that is not listed in this "
                        "assembly",
                    )
        # What each episode asks for (ADR-462). Whether a name collides with
        # an observation channel, whether a period lands on control steps
        # and whether a point can be reached at all are the engine's, for
        # the reason the shove checks are: each needs the compiled model or
        # the rounded schedule.
        goal_values = _values(
            operation, "goals", goals, output_type="goal", minimum=0
        )
        for index, entry in enumerate(goal_values):
            for part in ("tip", "frame"):
                component = entry.properties.get(part)
                if component is not None and id(component) not in component_ids:
                    raise _error(
                        operation,
                        f"goals[{index}]",
                        f"names a {part} that is not listed in this assembly",
                    )
        # Absent rather than ``None`` when no spec is declared, so a task
        # that has none is the value it always was.
        judged: dict[str, Any] = {}
        if success is not None:
            spec = _domain_value(
                operation, "success", success, output_type="success"
            )
            named = [
                (f"success.feet[{index}]", entry)
                for index, entry in enumerate(spec.properties.get("feet", ()))
            ]
            if spec.properties.get("tip") is not None:
                named.append(("success.tip", spec.properties["tip"]))
            for parameter in ("body", "centre"):
                if spec.properties.get(parameter) is not None:
                    named.append((f"success.{parameter}", spec.properties[parameter]))
            for parameter in ("reset_variation", "disturbance"):
                named.extend(
                    (f"success.{parameter}[{index}]", entry.arguments[0])
                    for index, entry in enumerate(
                        spec.properties.get(parameter) or ()
                    )
                )
            named.extend(
                (f"success.goals[{index}]", entry.properties[part])
                for index, entry in enumerate(spec.properties.get("goals") or ())
                for part in ("tip", "frame")
                if entry.properties.get(part) is not None
            )
            for where, component in named:
                if id(component) not in component_ids:
                    raise _error(
                        operation,
                        where,
                        "names a component that is not listed in this "
                        "assembly",
                    )
            _check_randomisation(
                operation, "success.randomisation",
                spec.properties.get("randomisation") or (),
                component_ids, joint_ids,
            )
            judged["success"] = spec
        seconds = _number(
            operation, "episode_seconds", episode_seconds,
            minimum=0.0, maximum=3600.0, strict_minimum=True,
        )
        if isinstance(control_hz, bool) or not isinstance(control_hz, int):
            raise _error(
                operation, "control_hz",
                "expected an integer from 1 through 1000", control_hz,
            )
        if not 1 <= control_hz <= 1000:
            raise _error(
                operation, "control_hz", "must be from 1 through 1000", control_hz
            )
        return self._value(
            operation,
            "task",
            value,
            actions=action_values,
            reward=reward_values,
            termination=termination_values,
            randomisation=randomisation_values,
            reset_variation=variation_values,
            disturbance=disturbance_values,
            episode_seconds=seconds,
            control_hz=control_hz,
            label=label,
            # Absent when the task states none, like the spec below, so a
            # task without a goal is the value it always was.
            **({"goals": goal_values} if goal_values else {}),
            **judged,
        )

    def policy(
        self,
        task: DomainValue,
        *,
        weights: str,
        sha256: str,
        trained_task: str = "",
        label: str = "",
    ) -> DomainValue:
        """Declare a trained control policy for one task, by name and digest.

        Training does not happen here and cannot: it needs JAX on a GPU, and
        the engine is a geometry-and-dynamics service. ``training/`` carries
        the trainer, it runs on a machine that has one, and the ``.cxpolicy``
        it writes comes back into the project store through the same
        ``put_asset`` path an imported mesh travels (ADR-084). **There is no
        train button and nothing to press** -- the agent authors the task,
        dispatches the run with its own shell, and declares the result here.

        ``weights`` names a file in the project's ``assets`` directory.
        ``sha256`` is **required and never inferred**, and that is the whole
        point of the surface: VISION principle 3 says any state that cannot
        be rebuilt from the script is a bug, and a trained policy is hours of
        stochastic GPU compute that genuinely cannot be. So the script
        carries the one thing that *can* be checked -- which bytes it meant --
        and the engine refuses anything else, naming the digest it observed
        so it can be pasted back.

        What the worker verifies, before publishing anything, is that the
        policy and the task agree about the mechanism: the task bundle's own
        digest, the model that bundle references, the observation channels in
        their exact order, the action table verbatim, and the output map the
        task's derived action ranges imply. Then it re-evaluates the witness
        the trainer recorded -- observation vectors and the actions the
        trainer's own network produced for them -- with the engine's forward
        pass, and refuses past a measured tolerance. A policy whose weights
        survived the trip but whose architecture the engine reads differently
        is a refusal rather than a bad gait.

        ``trained_task`` names the bundle the policy was **actually trained
        on**, as a ``.json`` file in the same ``assets`` directory, and it is
        how a policy outlives the exact bytes of the script that produced its
        task (ADR-134). Given it, the engine checks the policy against *that*
        bundle -- the same whole-file digest check as ever, unweakened -- and
        then proves the bundle this script just built **equivalent** to it:
        every field that decides behaviour, plus the two models compared as
        models rather than as hashes. A difference is a refusal that names the
        field.

        It exists because two things that are not mechanism changes move a
        whole-file hash. ADR-133's inertial snap changes every model digest, so
        every policy trained before it would otherwise be orphaned; and
        ADR-131's honest ``source`` string changes the bundle of an arm whose
        every action number is identical. Neither is a different robot, and
        ``verify_policy`` refuses both. Without ``trained_task`` the only
        remedies were retraining or reverting a correctness fix.

        **It is strictly stronger than relaxing the digest check would be.**
        The policy is still bound to one exact bundle; what is new is a proof
        that a second bundle is the same task. Omit it and nothing changes: the
        script-built bundle is checked whole-file, as before.

        Like ``api.mjcf`` and ``api.task``, this is *not* under the "exactly
        one simulation" rule: nothing bakes a policy, so several against one
        task -- two seeds, two reward weightings -- is a reasonable script.
        It is the second output that consumes another output, after
        ``api.task`` itself.
        """

        operation = "policy"
        value = _domain_value(operation, "task", task, output_type="task")
        clean_weights = str(weights or "").strip()
        if not clean_weights or len(clean_weights) > 120:
            raise _error(
                operation, "weights",
                "must name a policy file in the project assets directory, "
                "1-120 characters", weights,
            )
        if any(separator in clean_weights for separator in ("/", "\\")) or (
            ".." in clean_weights
        ):
            raise _error(
                operation, "weights",
                "must name a file directly inside the project assets "
                "directory", weights,
            )
        if not clean_weights.lower().endswith(".cxpolicy"):
            raise _error(
                operation, "weights",
                "must be a .cxpolicy file, which is what training/"
                "cadex_train.py writes", weights,
            )
        clean_digest = str(sha256 or "").strip().lower()
        if len(clean_digest) != 64 or any(
            character not in "0123456789abcdef" for character in clean_digest
        ):
            raise _error(
                operation, "sha256",
                "expected the 64 hex characters of the policy file's SHA-256. "
                "put_asset reports it when the file is stored",
                sha256,
            )
        # The same confinement ``weights`` gets, and for the same reason: the
        # name came out of a script and names a file the worker will open.
        clean_trained = str(trained_task or "").strip()
        if clean_trained:
            if len(clean_trained) > 120:
                raise _error(
                    operation, "trained_task",
                    "must name a task bundle in the project assets directory, "
                    "1-120 characters", trained_task,
                )
            if any(separator in clean_trained for separator in ("/", "\\")) or (
                ".." in clean_trained
            ):
                raise _error(
                    operation, "trained_task",
                    "must name a file directly inside the project assets "
                    "directory", trained_task,
                )
            if not clean_trained.lower().endswith(".json"):
                raise _error(
                    operation, "trained_task",
                    "must be the .json task bundle the policy was trained on, "
                    "which is what api.task publishes", trained_task,
                )
            if clean_trained == clean_weights:
                raise _error(
                    operation, "trained_task",
                    "must not be the weights file; it is the task bundle "
                    "beside them", trained_task,
                )
        return self._value(
            operation,
            "policy",
            value,
            weights=clean_weights,
            sha256=clean_digest,
            trained_task=clean_trained,
            label=label,
        )

    def rollout(
        self,
        policy: DomainValue,
        *,
        frames_per_second: int | None = None,
        seed: int | None = None,
        clearance: Sequence[Sequence[DomainValue]] | None = None,
        clearance_mm: float = 0.0,
        label: str = "",
    ) -> DomainValue:
        """Play one trained policy against its own task, as a simulation.

        The end of the arc that ``api.mjcf``, ``api.task`` and ``api.policy``
        begin: the network that was trained offboard drives the mechanism it
        was trained on, and what comes back is an ordinary ``simulation``
        output -- the same trace the shell has baked since the kinematics
        solver produced the first one. Nothing new reaches the viewport;
        what reaches it is a learned gait instead of a prescribed motion.

        ``policy`` is an ``api.policy`` value, and it must be **returned as
        an output too**: a policy that nothing published has no verified
        receipt, and an unverified policy is one the engine has not checked
        against the task it claims. The model is then reloaded from the file
        the task bundle names, so the rollout runs the exact model the
        policy's digest attests to rather than whichever one is in memory --
        phase 0 measured that those two are not the same trajectory.

        This *is* under the "exactly one simulation" rule (ADR-077), unlike
        ``api.mjcf``, ``api.task`` and ``api.policy``. A rollout is baked, so
        a script with a rollout and an ``api.dynamics`` in it is a refusal
        rather than a scene ``cadex_animate`` silently clears -- and for the
        same reason a rollout cannot sit beside ``api.motion``.

        ``frames_per_second`` **must divide the task's ``control_hz``
        exactly** and defaults to it, which is one frame per control step.
        The trace samples on control-step boundaries the way a dynamics run
        samples on solver-step boundaries: a frame between two actions would
        depend on floating-point accumulation. A policy picks its own control
        rate, so the refusal names the rates that task can be played at.

        ``seed`` draws the task's ``api.randomise`` entries for this one
        episode, by the algorithm the bundle states. Without it nothing is
        randomised and the rollout is the nominal mechanism.

        ``clearance`` and ``clearance_mm`` measure the named component pairs
        as exact BREP **at every pose the gait actually reached**, and
        report rather than refuse -- the same terms ``api.dynamics`` takes,
        for the same reason. Without it the only clearance number a project
        carries is the one at the initial solved pose, which says nothing
        about a mechanism that has since walked: a policy is trained against
        collision geoms that are boxes and capsules (ADR-281), so what it
        learned to avoid is not the part.
        """

        operation = "rollout"
        value = _domain_value(operation, "policy", policy, output_type="policy")
        task = value.arguments[0] if value.arguments else None
        if (
            not isinstance(task, DomainValue)
            or task.output_type != "task"
        ):
            raise _error(
                operation,
                "policy",
                "must come from api.policy, which consumes one api.task value",
            )
        control_hz = int(task.properties.get("control_hz") or 0)
        episode_seconds = float(task.properties.get("episode_seconds") or 0.0)
        if control_hz < 1 or episode_seconds <= 0.0:
            raise _error(
                operation,
                "policy",
                "names a task with no episode to play; pass the api.policy "
                "value built from an api.task",
            )
        if frames_per_second is None:
            # One frame per control step, which is the only rate that is
            # always available: it divides control_hz by construction.
            rate = control_hz
        else:
            if isinstance(frames_per_second, bool) or not isinstance(
                frames_per_second, int
            ):
                raise _error(
                    operation,
                    "frames_per_second",
                    "expected an integer from 1 through 240",
                    frames_per_second,
                )
            if not 1 <= frames_per_second <= 240:
                raise _error(
                    operation,
                    "frames_per_second",
                    "must be from 1 through 240",
                    frames_per_second,
                )
            rate = frames_per_second
        if seed is not None:
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise _error(
                    operation, "seed",
                    "expected a non-negative integer, or None for no "
                    "randomisation", seed,
                )
            if not 0 <= seed <= 2**31 - 1:
                raise _error(
                    operation, "seed",
                    "must be from 0 through 2147483647", seed,
                )
        # The same two caps api.dynamics declares, from the schedule the task
        # already fixed rather than from a time range: an episode's length is
        # episode_seconds and its step count is not known until the bundle is
        # built, so this is an upper bound the worker re-checks against the
        # frames that really came out.
        model = task.arguments[0] if task.arguments else None
        assembly = (
            model.arguments[0]
            if isinstance(model, DomainValue) and model.arguments
            else None
        )
        components = (
            list(assembly.properties.get("components") or ())
            if isinstance(assembly, DomainValue)
            else []
        )
        estimated_frames = math.ceil(episode_seconds * rate) + 2
        if estimated_frames > 10_000 or (
            components and estimated_frames * len(components) > 100_000
        ):
            raise _error(
                operation,
                "frames_per_second",
                "would exceed 10000 frames or 100000 component-pose samples; "
                "lower frames_per_second or shorten the task's episode_seconds",
            )
        pairs, gap = (
            _clearance_promise(operation, clearance, clearance_mm, assembly)
            if isinstance(assembly, DomainValue)
            else ([], _number(operation, "clearance_mm", clearance_mm, minimum=0.0))
        )
        if gap > 0.0 and not pairs:
            raise _error(
                operation,
                "clearance",
                "name the component pairs the gap applies to; two parts joined "
                "at a joint are supposed to touch, so there is no safe default",
            )
        return self._value(
            operation,
            "simulation",
            value,
            clearance=pairs,
            clearance_mm=gap,
            frames_per_second=rate,
            seed=seed,
            estimated_frame_limit=estimated_frames,
            label=label,
        )

    def exploded_view(
        self,
        assembly: DomainValue,
        moves: Sequence[Mapping[str, Any]],
        *,
        label: str = "",
    ) -> DomainValue:
        """Create one native exploded view from ordered component moves.

        Each move contains ``components`` plus exactly one of ``transform`` or
        ``radial_distance_mm``. A normal ``transform`` uses the same placement
        form as ``api.component`` and is applied in order. A radial move uses
        FreeCAD's native radial control distance: displacement equals the vector
        from assembly-centre to component-centre, scaled by four times that
        distance divided by the assembly diagonal. Components may appear in
        later moves for staged explosions. The worker validates native final
        placements and explosion-line endpoints without changing solved state.
        """

        operation = "exploded_view"
        model = _domain_value(operation, "assembly", assembly, output_type="assembly")
        if not isinstance(moves, (list, tuple)) or not 1 <= len(moves) <= 64:
            raise _error(
                operation,
                "moves",
                "expected an array containing 1 through 64 ordered move objects",
                moves,
            )
        graph_components = {
            id(component): component
            for component in model.properties.get("components", ())
        }
        normalized_moves: list[dict[str, Any]] = []
        reference_count = 0
        for index, raw in enumerate(moves):
            path = f"moves[{index}]"
            if not isinstance(raw, Mapping):
                raise _error(operation, path, "expected an object", raw)
            extra = set(raw) - {"components", "transform", "radial_distance_mm"}
            if extra:
                raise _error(operation, path, f"unknown keys {sorted(extra)}", raw)
            has_transform = "transform" in raw
            has_radial = "radial_distance_mm" in raw
            if has_transform == has_radial:
                raise _error(
                    operation,
                    path,
                    "requires exactly one of transform or radial_distance_mm",
                    raw,
                )
            components = _values(
                operation,
                f"{path}.components",
                raw.get("components"),
                output_type="component_link",
                minimum=1,
            )
            for component_index, component in enumerate(components):
                if id(component) not in graph_components:
                    raise _error(
                        operation,
                        f"{path}.components[{component_index}]",
                        "is not listed in this assembly",
                    )
            reference_count += len(components)
            if reference_count > 256:
                raise _error(
                    operation,
                    "moves",
                    "may contain at most 256 component references across all moves",
                )
            if has_transform:
                transform = _placement(operation, f"{path}.transform", raw["transform"])
                translation_magnitude = math.sqrt(
                    sum(value * value for value in transform["position"])
                )
                rotation_change = math.sqrt(
                    sum(value * value for value in transform["rotation"][:3])
                )
                if translation_magnitude <= 1.0e-12 and rotation_change <= 1.0e-12:
                    raise _error(
                        operation,
                        f"{path}.transform",
                        "must translate or rotate at least one component",
                        raw["transform"],
                    )
                normalized_moves.append(
                    {
                        "kind": "normal",
                        "components": components,
                        "transform": transform,
                    }
                )
            else:
                distance = _number(
                    operation,
                    f"{path}.radial_distance_mm",
                    raw["radial_distance_mm"],
                    minimum=0.0,
                    maximum=1.0e6,
                    strict_minimum=True,
                )
                normalized_moves.append(
                    {
                        "kind": "radial",
                        "components": components,
                        "radial_distance_mm": distance,
                    }
                )
        return self._value(
            operation,
            "exploded_view",
            model,
            moves=normalized_moves,
            label=label,
        )
