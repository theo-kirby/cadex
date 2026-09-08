# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ``lib`` script namespace: catalogued parts as parametric recipes.

``lib.bolt("m3", length=10)`` and its siblings compose ordinary part-domain
recipe values out of the spec rows in ``CadexCatalog``, so a library part
is a ``DomainValue`` like any other: it books, fillets, transforms,
assembles and digests with machinery that never learns the library exists.

Every generator returns a :class:`LibraryPart` — ``.body`` is the geometry,
``.spec`` is the catalog row it was built from (including density where
supported), so a script can read the numbers it is designing around instead
of restating them.

Frame conventions, uniform across the library and stated once here:

- Every part is built with its **axis along ``direction``** (default +Z)
  and its **datum at ``origin``**.
- A bolt's datum is the **head-seat plane**: the head sits on +direction,
  the shank runs along -direction. Place it by naming the surface point the
  head lands on and the surface normal.
- Nuts, washers, inserts, bearings and bushings sit with their
  **base face in the datum plane** and bodies extending along +direction.
- Servos and gearmotors use the shaft's intersection with the case/front
  face as datum; the body extends backwards. BLDC motors use the rear
  mounting plane with the case forwards. Boards use a PCB corner.

This module imports nothing from FreeCAD; generators run identically in
the sandboxed worker and the stubbed test suite.
"""

from __future__ import annotations

import json
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import CadexCatalog as catalog
from CadexCatalog import CatalogError

__all__ = [
    "LibraryError",
    "LibraryPart",
    "LibraryAPI",
    "create_library_api",
    "library_catalog_identity",
    "library_listing",
]


#: ``{canonical definition JSON: {"family", "part_number"}}`` for every body a
#: generator handed back during THIS run (ADR-236).
#:
#: A ``LibraryPart`` knows its catalog identity and its ``.body`` is an
#: ordinary part value, so the identity died the moment a script wrote
#: ``result = {"m3": lib.bolt("M3", 12).body}`` — the report carried a solid
#: and nothing said which catalogue row it came off. Recording it here rather
#: than in the value's ``properties`` is deliberate and is the whole reason
#: this is a side table: the properties feed ``_canonical_json(definition)``,
#: which feeds the content digest, so a catalog key inside them would move
#: every existing ``lib.*`` project's digest and lock it out — the class of
#: change ADR-064 had to force a re-accept for. The definition is instead the
#: *join key*, exactly as
#: ``artifact_by_definition`` already joins a component source to its output.
_CATALOG_IDENTITY: dict[str, dict[str, str]] = {}


def _definition_key(body: Any) -> str:
    payload = body.to_payload() if hasattr(body, "to_payload") else None
    if payload is None:
        return ""
    try:
        return json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return ""


def library_catalog_identity() -> dict[str, dict[str, str]]:
    """Catalog identity by canonical definition, for the run just executed."""

    return {key: dict(value) for key, value in _CATALOG_IDENTITY.items()}


class LibraryError(ValueError):
    """A library call violates the generator contract."""


_SQRT3 = math.sqrt(3.0)
_DEFAULT_ORIGIN = (0.0, 0.0, 0.0)
_DEFAULT_DIRECTION = (0.0, 0.0, 1.0)


class LibraryPart:
    """One generated part: the geometry plus the spec it was built from."""

    __slots__ = ("family", "part_number", "body", "spec")

    def __init__(
        self,
        family: str,
        part_number: str,
        body: Any,
        spec: Mapping[str, Any],
    ) -> None:
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "part_number", part_number)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "spec", MappingProxyType(dict(spec)))
        key = _definition_key(body)
        if key:
            _CATALOG_IDENTITY[key] = {
                "family": str(family),
                "part_number": str(part_number),
            }

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("A library part is immutable; build another instead.")

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"LibraryPart({self.family}:{self.part_number})"


# -- rotation helpers -------------------------------------------------------
#
# part.transform takes ONE axis-angle rotation, and a placed servo needs two
# (roll about its own shaft, then the shaft aimed along `direction`), so the
# generators compose quaternions in Python and emit a single rotation.


def _quaternion(axis: Sequence[float], angle_degrees: float) -> tuple:
    half = math.radians(angle_degrees) / 2.0
    s = math.sin(half)
    return (math.cos(half), axis[0] * s, axis[1] * s, axis[2] * s)


def _compose(first_applied: tuple, then_applied: tuple) -> tuple:
    """The rotation that applies ``first_applied`` and then ``then_applied``."""

    w1, x1, y1, z1 = then_applied
    w2, x2, y2, z2 = first_applied
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def _axis_angle(quaternion: tuple) -> tuple:
    w, x, y, z = quaternion
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1.0e-12:
        return (0.0, 0.0, 1.0), 0.0
    angle = 2.0 * math.degrees(math.atan2(norm, w))
    return (x / norm, y / norm, z / norm), angle


def _rotate(quaternion: tuple, vector: Sequence[float]) -> tuple:
    w, x, y, z = quaternion
    vx, vy, vz = vector
    # v' = v + 2*q_vec x (q_vec x v + w*v)
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


def _alignment_quaternion(unit_direction: Sequence[float]) -> tuple:
    cos_angle = max(-1.0, min(1.0, unit_direction[2]))
    if cos_angle > 1.0 - 1.0e-12:
        return _quaternion((0.0, 0.0, 1.0), 0.0)
    if cos_angle < -1.0 + 1.0e-12:
        return _quaternion((1.0, 0.0, 0.0), 180.0)
    axis = (-unit_direction[1], unit_direction[0], 0.0)
    norm = math.sqrt(axis[0] * axis[0] + axis[1] * axis[1])
    axis = (axis[0] / norm, axis[1] / norm, 0.0)
    return _quaternion(axis, math.degrees(math.acos(cos_angle)))


def _clean_vector(operation: str, name: str, value: Any) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise LibraryError(f"lib.{operation}: {name} must be a 3-vector.")
    cleaned = []
    for component in value:
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise LibraryError(f"lib.{operation}: {name} must be numeric.")
        component = float(component)
        if not math.isfinite(component):
            raise LibraryError(f"lib.{operation}: {name} must be finite.")
        cleaned.append(component)
    return (cleaned[0], cleaned[1], cleaned[2])


def _positive(operation: str, name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LibraryError(f"lib.{operation}: {name} must be a number.")
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise LibraryError(f"lib.{operation}: {name} must be positive and finite.")
    return value


class ServoPart(LibraryPart):
    """A placed servo: geometry, datasheet numbers, horn and actuator.

    The local frame is uniform across the family: the origin is the point
    where the **output shaft axis meets the case top**, +Z runs out through
    the spline, and +X points through the front (shaft-side) face — the
    case extends in -X and -Z, the spline in +Z. ``spec['mount_holes']``
    lists the mounting-hole centres in that frame.
    """

    __slots__ = ("_lib", "_frame_placement")

    def __init__(
        self,
        lib: "LibraryAPI",
        part_number: str,
        body: Any,
        spec: Mapping[str, Any],
        frame_placement: tuple,
    ) -> None:
        super().__init__("servo", part_number, body, spec)
        object.__setattr__(self, "_lib", lib)
        object.__setattr__(self, "_frame_placement", frame_placement)

    def horn(
        self,
        style: str = "single_arm",
        *,
        roll_degrees: float = 0.0,
        label: str = "",
    ) -> LibraryPart:
        """The matching horn, seated on this servo's spline.

        Micro-family styles (measured, AUS TA0132): ``single_arm``,
        ``double_arm``, ``cross``. The horn lands with its hub on the
        spline top, arms along the servo's +X spun by ``roll_degrees``.
        The 25T standard servos ship undimensioned horn sets, so there the
        call refuses rather than inventing geometry.
        """

        return self._lib._servo_horn(self, style, roll_degrees, label)

    def actuator(
        self,
        joint: Any,
        *,
        control_deg: str,
        voltage: float | None = None,
        stiffness_nmm_per_deg: float | None = None,
        damping_nmms_per_deg: float | None = None,
        command_limits_degrees: Any = None,
        label: str = "",
    ) -> Any:
        """A position actuator bounded by this servo's real stall torque.

        ``torque_limit_nmm`` is the datasheet stall torque at ``voltage``
        (which must be one the manufacturer rates; default is the lowest
        rated, the conservative choice), converted from kg*cm once, here.
        ``stiffness_nmm_per_deg`` defaults to reaching stall within 5
        degrees of error — the proportional band a hobby servo actually
        holds — and ``damping_nmms_per_deg`` to a twentieth of that, since
        a geared drivetrain does not ring; both are overridable. Everything
        lands on ``assembly.actuator`` unchanged, so the refusals are its.
        """

        return self._lib._servo_actuator(
            self,
            joint,
            control_deg=control_deg,
            voltage=voltage,
            stiffness_nmm_per_deg=stiffness_nmm_per_deg,
            damping_nmms_per_deg=damping_nmms_per_deg,
            command_limits_degrees=command_limits_degrees,
            label=label,
        )


class BoardPart(LibraryPart):
    """A board whose solder-pad rows can enter the existing wiring table."""

    __slots__ = ("_frame_placement",)

    def __init__(self, part_number, body, spec, frame_placement):
        super().__init__("board", part_number, body, spec)
        object.__setattr__(self, "_frame_placement", frame_placement)

    def terminals(self) -> list[dict]:
        """Fresh term() rows in the generated body's frame, for board().

        Names are physical connector/pin ids; .spec['terminals'] maps them
        to signals. Origins are solder pads, axes point into the PCB.
        Optional fitted headers and connector bodies are not modelled.
        """
        from CadexBoards import term

        origin, _unit, rotation = self._frame_placement
        return [term(row["name"],
                     origin=tuple(a+b for a, b in zip(origin, _rotate(rotation, row["origin"]))),
                     axis=_rotate(rotation, row["axis"]), hole_dia=row["hole_dia"])
                for row in self.spec["terminals"]]



# -- involute gearing ----------------------------------------------------------

_FLANK_SAMPLES = 8


def _involute_function(angle: float) -> float:
    return math.tan(angle) - angle


def _spur_gear_outline(spec: Mapping[str, Any]) -> list[tuple[float, float, float]]:
    """One counter-clockwise polygon around an ISO 53 spur gear, in the XY plane.

    Each tooth is: root arc, rising flank, tip arc, falling flank, root arc.
    The flank is the involute of the base circle sampled ``_FLANK_SAMPLES``
    times between the base (or root, when that is larger) and tip circles;
    below the base circle it is a radial line down to the root circle. Tip
    and root vertices lie exactly on their circles, so a bound or a vertex
    radius measures the standard's diameters directly.
    """

    teeth = spec["teeth"]
    base_radius = spec["base_diameter_mm"] / 2.0
    tip_radius = spec["tip_diameter_mm"] / 2.0
    root_radius = spec["root_diameter_mm"] / 2.0
    pressure = math.radians(spec["pressure_angle_degrees"])
    half_pitch_angle = math.pi / (2.0 * teeth)

    def half_angle(radius: float) -> float:
        # Half the tooth's angular thickness at ``radius`` on the involute.
        pressure_at_radius = math.acos(base_radius / radius) if radius > base_radius else 0.0
        return half_pitch_angle + _involute_function(pressure) - _involute_function(pressure_at_radius)

    flank_start = max(base_radius, root_radius)
    radii = [flank_start + (tip_radius - flank_start) * index / (_FLANK_SAMPLES - 1)
             for index in range(_FLANK_SAMPLES)]
    if root_radius < base_radius:
        radii.insert(0, root_radius)
    half_at_root = half_angle(radii[0])
    half_at_tip = half_angle(tip_radius)
    if half_at_tip <= 0.0 or half_at_root >= math.pi / teeth:
        raise LibraryError(
            f"lib.spur_gear: {teeth} teeth on module {spec['module_mm']:g} leaves no tip land or no root space."
        )

    def polar(radius: float, angle: float) -> tuple[float, float, float]:
        return (radius * math.cos(angle), radius * math.sin(angle), 0.0)

    points: list[tuple[float, float, float]] = []
    for tooth in range(teeth):
        centre = 2.0 * math.pi * tooth / teeth
        space_edge = centre - math.pi / teeth
        points.append(polar(root_radius, space_edge))
        points.append(polar(root_radius, (space_edge + centre - half_at_root) / 2.0))
        for radius in radii:
            points.append(polar(radius, centre - half_angle(radius)))
        points.append(polar(tip_radius, centre))
        for radius in reversed(radii):
            points.append(polar(radius, centre + half_angle(radius)))
        points.append(polar(root_radius, (centre + half_at_root + centre + math.pi / teeth) / 2.0))
    return points


def _rack_outline(spec: Mapping[str, Any], height: float) -> list[tuple[float, float, float]]:
    """One counter-clockwise polygon around an ISO 53 rack, pitch line on Y=0.

    Teeth point along +Y with tips at ``addendum`` and roots at
    ``-dedendum``; the back face sits ``height`` below the tips. Tooth ``i``
    is centred on ``(i + 1/2)`` pitches from X=0.
    """

    pitch = spec["circular_pitch_mm"]
    tip_y = spec["addendum_mm"]
    root_y = -spec["dedendum_mm"]
    tangent = math.tan(math.radians(spec["pressure_angle_degrees"]))
    half_at_tip = pitch / 4.0 - tip_y * tangent
    half_at_root = pitch / 4.0 - root_y * tangent
    length = spec["length_mm"]
    points = [(0.0, tip_y - height, 0.0), (length, tip_y - height, 0.0), (length, root_y, 0.0)]
    for tooth in reversed(range(spec["teeth"])):
        centre = (tooth + 0.5) * pitch
        points.append((centre + half_at_root, root_y, 0.0))
        points.append((centre + half_at_tip, tip_y, 0.0))
        points.append((centre - half_at_tip, tip_y, 0.0))
        points.append((centre - half_at_root, root_y, 0.0))
    points.append((0.0, root_y, 0.0))
    return points


class LibraryAPI:
    """The ``lib`` global staged into every project script."""

    __slots__ = ("_part", "_assembly")

    def __init__(self, part_api: Any, assembly_api: Any = None) -> None:
        object.__setattr__(self, "_part", part_api)
        object.__setattr__(self, "_assembly", assembly_api)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("The library API is immutable inside the script.")

    # -- placement ---------------------------------------------------------

    def _frame(
        self,
        operation: str,
        origin: Sequence[float],
        direction: Sequence[float],
        roll_degrees: float = 0.0,
    ) -> tuple:
        """Validate a placement into (origin, unit direction, quaternion)."""

        clean_origin = _clean_vector(operation, "origin", origin)
        clean_direction = _clean_vector(operation, "direction", direction)
        if isinstance(roll_degrees, bool) or not isinstance(
            roll_degrees, (int, float)
        ):
            raise LibraryError(f"lib.{operation}: roll_degrees must be a number.")
        roll = float(roll_degrees)
        if not math.isfinite(roll):
            raise LibraryError(f"lib.{operation}: roll_degrees must be finite.")
        length = math.sqrt(sum(v * v for v in clean_direction))
        if length <= 1.0e-12:
            raise LibraryError(f"lib.{operation}: direction must not be zero.")
        unit = tuple(v / length for v in clean_direction)
        rotation = _compose(
            _quaternion((0.0, 0.0, 1.0), roll),
            _alignment_quaternion(unit),
        )
        return clean_origin, unit, rotation

    def _place(
        self,
        operation: str,
        body: Any,
        origin: Sequence[float],
        direction: Sequence[float],
        roll_degrees: float = 0.0,
    ) -> Any:
        """Move a canonical-frame body onto (origin, direction, roll).

        Parts are generated with their axis along +Z and their datum at
        (0,0,0); this spins the part ``roll_degrees`` about its own axis,
        rotates +Z onto ``direction`` and translates to ``origin`` with one
        ``part.transform``, or returns the body untouched when everything
        is the default.
        """

        clean_origin, _unit, rotation = self._frame(
            operation, origin, direction, roll_degrees
        )
        axis, angle = _axis_angle(rotation)
        if clean_origin == _DEFAULT_ORIGIN and abs(angle) <= 1.0e-9:
            return body
        return self._part.transform(
            body,
            translation=clean_origin,
            rotation_axis=axis,
            rotation_degrees=angle,
        )

    # -- hole data ---------------------------------------------------------

    def clearance_hole(self, size: str, *, fit: str = "normal") -> float:
        """Clearance-hole diameter (mm) for one metric size; fit close|normal."""

        row = catalog.thread_spec(size)
        if fit == "normal":
            return row["clearance_normal_mm"]
        if fit == "close":
            return row["clearance_close_mm"]
        raise LibraryError("lib.clearance_hole: fit must be 'close' or 'normal'.")

    def tap_drill(self, size: str) -> float:
        """Tapping-drill diameter (mm) for one metric size."""

        return catalog.thread_spec(size)["tap_drill_mm"]

    def insert_hole(self, size: str) -> float:
        """Pilot-hole diameter (mm) for the heat-set insert of one size."""

        return catalog.heat_set_insert_spec(size)["hole_dia_mm"]

    # -- fasteners ---------------------------------------------------------

    def bolt(
        self,
        size: str,
        length: float,
        *,
        head: str = "socket",
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """A metric bolt; datum is the head-seat plane, shank along -direction.

        ``head='socket'`` is ISO 4762 (length excludes the head, per the
        standard); ``head='countersunk'`` is DIN 7991 (length includes the
        head, per the standard, and the datum plane is the flush top face).
        No thread helix is modelled — the shank is the nominal cylinder;
        pair with lib.clearance_hole/tap_drill for the mating hole.
        """

        operation = "bolt"
        thread = catalog.thread_spec(size)
        clean_length = _positive(operation, "length", length)
        radius = thread["nominal_dia_mm"] / 2.0
        shank = self._part.cylinder(
            radius, clean_length, origin=(0.0, 0.0, -clean_length)
        )
        if head == "socket":
            head_row = catalog.socket_head_spec(size)
            cap = self._part.cylinder(
                head_row["head_dia_mm"] / 2.0, head_row["head_height_mm"]
            )
        elif head == "countersunk":
            head_row = catalog.countersunk_spec(size)
            depth = head_row["head_height_mm"]
            if clean_length <= depth:
                raise LibraryError(
                    f"lib.bolt: a countersunk {size} is {depth} mm of head; "
                    f"length must exceed that."
                )
            cap = self._part.cone(
                radius,
                head_row["head_dia_mm"] / 2.0,
                depth,
                origin=(0.0, 0.0, -depth),
            )
        else:
            raise LibraryError("lib.bolt: head must be 'socket' or 'countersunk'.")
        body = self._part.fuse([shank, cap], label=label)
        spec = dict(thread)
        spec.update(head_row)
        spec.update(
            {
                "length_mm": clean_length,
                "head": head,
                "density_kg_m3": catalog.STEEL_DENSITY_KG_M3,
            }
        )
        part_number = f"{catalog.normalise_thread_size(size)}x{clean_length:g}-{head}"
        return LibraryPart(
            "bolt",
            part_number,
            self._place(operation, body, origin, direction),
            spec,
        )

    def nut(
        self,
        size: str,
        *,
        style: str = "hex",
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """A metric nut; base face in the datum plane, body along +direction.

        ``style='hex'`` is ISO 4032; ``style='nyloc'`` is DIN 985 (same
        across-flats, taller). The bore is the thread's minor diameter.
        """

        operation = "nut"
        thread = catalog.thread_spec(size)
        if style == "hex":
            row = catalog.hex_nut_spec(size)
        elif style == "nyloc":
            row = catalog.nyloc_nut_spec(size)
        else:
            raise LibraryError("lib.nut: style must be 'hex' or 'nyloc'.")
        height = row["height_mm"]
        blank = self._part.prism(
            6, row["across_flats_mm"] / _SQRT3, height
        )
        bore = self._part.cylinder(
            thread["minor_dia_mm"] / 2.0, height + 2.0, origin=(0.0, 0.0, -1.0)
        )
        body = self._part.cut(blank, bore, label=label)
        spec = dict(thread)
        spec.update(row)
        spec.update({"style": style, "density_kg_m3": catalog.STEEL_DENSITY_KG_M3})
        part_number = f"{catalog.normalise_thread_size(size)}-{style}"
        return LibraryPart(
            "nut",
            part_number,
            self._place(operation, body, origin, direction),
            spec,
        )

    def washer(
        self,
        size: str,
        *,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """An ISO 7089 flat washer; base face in the datum plane."""

        operation = "washer"
        row = catalog.washer_spec(size)
        thickness = row["thickness_mm"]
        disc = self._part.cylinder(row["od_mm"] / 2.0, thickness)
        bore = self._part.cylinder(
            row["bore_mm"] / 2.0, thickness + 2.0, origin=(0.0, 0.0, -1.0)
        )
        body = self._part.cut(disc, bore, label=label)
        spec = dict(row)
        spec["density_kg_m3"] = catalog.STEEL_DENSITY_KG_M3
        return LibraryPart(
            "washer",
            catalog.normalise_thread_size(size),
            self._place(operation, body, origin, direction),
            spec,
        )

    def heat_insert(
        self,
        size: str,
        *,
        length: str = "standard",
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """A brass heat-set insert; base face in the datum plane.

        ``length='standard'`` or ``'short'``. The knurl is not modelled —
        the body is the insert's outer diameter; lib.insert_hole(size) is
        the pilot hole the plastic boss wants.
        """

        operation = "heat_insert"
        thread = catalog.thread_spec(size)
        row = catalog.heat_set_insert_spec(size)
        if length == "standard":
            insert_length = row["length_mm"]
        elif length == "short":
            insert_length = row["short_length_mm"]
        else:
            raise LibraryError(
                "lib.heat_insert: length must be 'standard' or 'short'."
            )
        sleeve = self._part.cylinder(row["od_mm"] / 2.0, insert_length)
        bore = self._part.cylinder(
            thread["minor_dia_mm"] / 2.0,
            insert_length + 2.0,
            origin=(0.0, 0.0, -1.0),
        )
        body = self._part.cut(sleeve, bore, label=label)
        spec = dict(row)
        spec.update(
            {
                "length_selected_mm": insert_length,
                "nominal_dia_mm": thread["nominal_dia_mm"],
                "density_kg_m3": catalog.BRASS_DENSITY_KG_M3,
            }
        )
        part_number = f"{catalog.normalise_thread_size(size)}-{length}"
        return LibraryPart(
            "heat_insert",
            part_number,
            self._place(operation, body, origin, direction),
            spec,
        )

    # -- bearings ----------------------------------------------------------

    def bearing(
        self,
        code: str | None = None,
        *,
        bore: float | None = None,
        od: float | None = None,
        width: float | None = None,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """A deep-groove ball bearing; base face in the datum plane.

        Name a catalogued code (``'608'``, shield suffixes accepted) or give
        all three of bore/od/width for one the catalog does not carry. The
        body is the exact annulus — rings and balls are not distinguished.
        """

        operation = "bearing"
        if code is not None:
            if bore is not None or od is not None or width is not None:
                raise LibraryError(
                    "lib.bearing: give a code OR bore/od/width, not both."
                )
            row = catalog.bearing_spec(code)
            part_number = catalog.normalise_bearing_code(code)
        else:
            if bore is None or od is None or width is None:
                raise LibraryError(
                    "lib.bearing: without a code, bore, od and width are all "
                    "required."
                )
            row = {
                "bore_mm": _positive(operation, "bore", bore),
                "od_mm": _positive(operation, "od", od),
                "width_mm": _positive(operation, "width", width),
            }
            part_number = (
                f"custom-{row['bore_mm']:g}x{row['od_mm']:g}x{row['width_mm']:g}"
            )
        if row["bore_mm"] >= row["od_mm"]:
            raise LibraryError("lib.bearing: bore must be smaller than od.")
        ring = self._part.cylinder(row["od_mm"] / 2.0, row["width_mm"])
        hole = self._part.cylinder(
            row["bore_mm"] / 2.0, row["width_mm"] + 2.0, origin=(0.0, 0.0, -1.0)
        )
        body = self._part.cut(ring, hole, label=label)
        spec = dict(row)
        spec["density_kg_m3"] = catalog.STEEL_DENSITY_KG_M3
        return LibraryPart(
            "bearing",
            part_number,
            self._place(operation, body, origin, direction),
            spec,
        )

    def bushing(
        self,
        *,
        bore: float,
        od: float,
        length: float,
        flange_od: float | None = None,
        flange_thickness: float | None = None,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        label: str = "",
    ) -> LibraryPart:
        """A plain bushing, fully parametric; base face in the datum plane.

        With ``flange_od``/``flange_thickness`` (both or neither) the flange
        sits in the datum plane and the sleeve extends beyond it.
        """

        operation = "bushing"
        clean_bore = _positive(operation, "bore", bore)
        clean_od = _positive(operation, "od", od)
        clean_length = _positive(operation, "length", length)
        if clean_bore >= clean_od:
            raise LibraryError("lib.bushing: bore must be smaller than od.")
        if (flange_od is None) != (flange_thickness is None):
            raise LibraryError(
                "lib.bushing: flange_od and flange_thickness come together."
            )
        sleeve = self._part.cylinder(clean_od / 2.0, clean_length)
        blank = sleeve
        spec: dict[str, Any] = {
            "bore_mm": clean_bore,
            "od_mm": clean_od,
            "length_mm": clean_length,
            "density_kg_m3": catalog.BRASS_DENSITY_KG_M3,
        }
        if flange_od is not None:
            clean_flange_od = _positive(operation, "flange_od", flange_od)
            clean_flange_t = _positive(
                operation, "flange_thickness", flange_thickness
            )
            if clean_flange_od <= clean_od:
                raise LibraryError(
                    "lib.bushing: flange_od must exceed the sleeve od."
                )
            if clean_flange_t >= clean_length:
                raise LibraryError(
                    "lib.bushing: flange_thickness must be less than length."
                )
            flange = self._part.cylinder(clean_flange_od / 2.0, clean_flange_t)
            blank = self._part.fuse([sleeve, flange])
            spec["flange_od_mm"] = clean_flange_od
            spec["flange_thickness_mm"] = clean_flange_t
        hole = self._part.cylinder(
            clean_bore / 2.0, clean_length + 2.0, origin=(0.0, 0.0, -1.0)
        )
        body = self._part.cut(blank, hole, label=label)
        part_number = f"{clean_bore:g}x{clean_od:g}x{clean_length:g}"
        return LibraryPart(
            "bushing",
            part_number,
            self._place(operation, body, origin, direction),
            spec,
        )

    def gearmotor(
        self, sku: str, *, origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """Pololu N20 gearmotor envelope with D shaft and M1.6 mounting bores.

        Datum: shaft axis at gearbox front face; body in -Z, shaft in +Z,
        flat towards +Y, mounting centres along X. .spec coordinates stay
        in this canonical frame. Rear envelope is filled, not internal
        geometry; use mass_g separately, never infer density or inertia.
        Stall ratings at 6 V are extrapolations, not continuous torque.
        """
        spec = catalog.gearmotor_spec(sku)
        width, height, rear = (spec[k] for k in
                               ("width_mm", "height_mm", "rear_envelope_mm"))
        case = self._part.box(width, height, rear,
                              origin=(-width/2, -height/2, -rear))
        radius = spec["shaft_dia_mm"]/2
        tip = spec["shaft_tip_z_mm"]
        flat_start = spec["shaft_flat_start_z_mm"]
        shaft = self._part.cut(self._part.cylinder(radius, tip), [
            self._part.box(2*radius+2, 2*radius, tip-flat_start+1,
                           origin=(-radius-1,
                                   spec["shaft_flat_to_opposite_mm"]-radius,
                                   flat_start))])
        boss = self._part.cylinder(spec["boss_dia_mm"]/2, spec["boss_height_mm"])
        depth = spec["mount_bore_depth_mm"]
        holes = [self._part.cylinder(spec["mount_bore_dia_mm"]/2, depth+1,
                                     origin=(x, y, -depth))
                 for x, y in spec["mount_holes"]]
        body = self._part.cut(self._part.fuse([case, shaft, boss]), holes, label=label)
        return LibraryPart("gearmotor", sku.strip().lower(),
                           self._place("gearmotor", body, origin, direction, roll_degrees),
                           spec)

    def joint(
        self, sku: str, *, tilt_degrees: float = 0.0,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """SKF GE 6 C nominal spherical plain bearing, as a two-solid compound.

        Datum: common sphere centre, housing axis +Z; inner tilt about +Y
        before placement, bounded to ±13 degrees conditional on shaft shoulder
        diameter at most 8 mm. Spec stays canonical. Coincident spherical
        surfaces omit clearance, chamfers and liner: no fit, installed motion,
        conservative collision envelope, load or physical inertia guarantee.
        """
        spec = catalog.joint_spec(sku)
        if (isinstance(tilt_degrees, bool) or not isinstance(tilt_degrees, (int, float))
                or not math.isfinite(tilt_degrees)
                or abs(tilt_degrees) > spec["maximum_tilt_degrees"]):
            raise LibraryError("lib.joint: tilt_degrees must be finite in [-13, 13].")
        spec["tilt_degrees"] = float(tilt_degrees)
        part = self._part
        sphere = part.sphere(spec["sphere_dia_mm"]/2)
        outer_width, inner_width = spec["outer_width_mm"], spec["inner_width_mm"]
        outer = part.cut(part.cylinder(spec["outside_dia_mm"]/2, outer_width,
                                       origin=(0, 0, -outer_width/2)), sphere)
        inner = part.cut(part.common([sphere,
            part.cylinder(spec["sphere_dia_mm"]/2+1, inner_width,
                          origin=(0, 0, -inner_width/2))]),
            part.cylinder(spec["bore_dia_mm"]/2, inner_width+2,
                          origin=(0, 0, -inner_width/2-1)))
        inner = part.transform(inner, rotation_axis=(0, 1, 0),
                               rotation_degrees=tilt_degrees)
        body = part.compound([outer, inner], label=label)
        return LibraryPart("joint", sku.strip().lower(),
                           self._place("joint", body, origin, direction, roll_degrees),
                           spec)

    def linear_actuator(
        self, sku: str, *, extension: float = 0.0,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """Nominal L12-50-210-12-S exterior with supplied clevis.

        Datum: rear bore centre; travel +Z, both bore axes X. Extension is
        geometric millimetres in [0,50], not S-switch powered reachability.
        Spec coordinates stay canonical after placement. Primitive housing
        and clevis transitions are approximations: no installation fit,
        conservative collision envelope or physical inertia guarantee.
        """
        spec = catalog.linear_actuator_spec(sku)
        if (isinstance(extension, bool) or not isinstance(extension, (int, float))
                or not math.isfinite(extension) or not 0 <= extension <= spec["stroke_mm"]):
            raise LibraryError("lib.linear_actuator: extension must be finite in [0, 50] mm.")
        extension = float(extension)
        centre = spec["retracted_centres_mm"] + extension
        spec.update(extension_mm=extension, mount_centres_mm=[[0, 0, 0], [0, 0, centre]])
        part = self._part
        housing = part.box(14.9, 18, 37, origin=(-7.45, -7.5, 4.5))
        rear = part.box(spec["rear_lug_width_mm"], 9, 12.5, origin=(-4, -4.5, -4.5))
        sleeve = part.box(12, 12, 60, origin=(-6, -6, 35.5))
        shaft = part.cylinder(4.5, 8 + extension, origin=(0, 0, 90))
        eye = part.common([part.cylinder(4.5, 9, origin=(0, 0, centre-4.5)),
                          part.box(spec["clevis_width_mm"], 10, 9,
                                   origin=(-3, -5, centre-4.5))])
        holes = [part.cylinder(spec["mount_bore_dia_mm"]/2, 20,
                               origin=(-10, 0, z), direction=(1, 0, 0))
                 for z in (0, centre)]
        body = part.cut(part.fuse([housing, rear, sleeve, shaft, eye]), holes, label=label)
        return LibraryPart("linear_actuator", sku.strip().lower(),
                           self._place("linear_actuator", body, origin, direction, roll_degrees),
                           spec)

    def bldc(
        self, sku: str, *, origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """HOBBYWING BLDC rear-mount envelope, not a shaft coupling fit model.

        Datum: rear mounting plane on axis; case and shaft point along +Z,
        rear boss along -Z. X/Y align with the 19/25 mm mounting pairs,
        not cable clocking. The undimensioned collar reserves its maximum
        diameter over the entire shaft projection. See .spec approximate
        and rating_notes; no torque, screw engagement or inertia guarantee.
        .spec coordinates remain canonical after placement.
        """
        spec = catalog.bldc_spec(sku)
        length = spec["case_length_mm"]
        rear = spec["rear_boss_height_mm"]
        body = self._part.fuse([
            self._part.cylinder(spec["case_dia_mm"]/2, length),
            self._part.cylinder(spec["rear_boss_dia_mm"]/2, rear,
                                origin=(0, 0, -rear)),
            self._part.cylinder(spec["shaft_collar_envelope_dia_mm"]/2,
                                spec["shaft_projection_mm"], origin=(0, 0, length)),
        ])
        depth = spec["mount_bore_depth_mm"]
        holes = [self._part.cylinder(spec["mount_bore_dia_mm"]/2, depth+1,
                                     origin=(x, y, -1))
                 for x, y in spec["mount_holes"]]
        body = self._part.cut(body, holes, label=label)
        return LibraryPart("bldc", sku.strip().lower(),
                           self._place("bldc", body, origin, direction, roll_degrees),
                           spec)

    # -- boards ------------------------------------------------------------

    def board(
        self, sku: str, *, origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> BoardPart:
        """A named PCB variant with mounting holes and solder-pad terminals.

        Datum: lower-left PCB corner, bottom face; +Z is component side.
        .terminals() supplies board(..., terminals=...) rows, following this
        placement. .spec names signals, sources and approximate dimensions.
        Geometry is a rectangular PCB plus a simple chip/module marker, not
        a connector clearance envelope. Density is nominal FR4, not measured
        board mass. ESP32 DevKitC V4 has no mounting holes.
        """
        spec = catalog.board_spec(sku)
        frame = self._frame("board", origin, direction, roll_degrees)
        thickness = spec["thickness_mm"]
        pcb = self._part.box(spec["width_mm"], spec["length_mm"], thickness)
        holes = [self._part.cylinder(spec["mount_hole_dia_mm"] / 2,
                                    thickness+2, origin=(x, y, -1))
                 for x, y in spec["mount_holes"]]
        holes.extend(self._part.cylinder(row["hole_dia"] / 2, thickness+2,
                                         origin=(*row["origin"][:2], -1))
                     for row in spec["terminals"])
        pcb = self._part.cut(pcb, holes)
        marker = self._part.box(*spec["cosmetic_size"], origin=spec["cosmetic_origin"])
        body = self._part.fuse([pcb, marker], label=label)
        return BoardPart(sku.strip().lower(),
                         self._place("board", body, origin, direction, roll_degrees),
                         spec, frame)

    # -- servos ------------------------------------------------------------

    def servo(
        self,
        sku: str,
        *,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0,
        label: str = "",
    ) -> ServoPart:
        """A catalogued hobby servo, placed by its output shaft.

        ``origin`` is where the shaft axis meets the case top, ``direction``
        is the shaft axis (the joint's axis), ``roll_degrees`` spins the
        case about it. The interface is datasheet-exact — mounting holes,
        flange height, shaft position — and ``spec['approximate']`` names
        any field no datasheet dimensions. ``.horn(...)`` seats the matching
        horn on the spline; ``.actuator(joint, control_deg=...)`` puts this
        servo's real torque limit on a joint; ``spec`` carries the mass and
        the effective density ``assembly.body`` wants.
        """

        operation = "servo"
        spec = catalog.servo_spec(sku)
        length = spec["body_length_mm"]
        width = spec["body_width_mm"]
        height = spec["case_height_mm"]
        tab_span = spec["overall_tab_length_mm"]
        tab_thickness = spec["tab_thickness_mm"]
        flange_height = spec["flange_height_mm"]
        hole_dia = spec["hole_dia_mm"]
        hole_spacing = spec["hole_spacing_mm"]
        cross = spec["hole_cross_spacing_mm"]
        front = spec["shaft_offset_from_front_mm"]
        spline_radius = spec["spline_dia_mm"] / 2.0
        spline_height = spec["spline_height_mm"]

        case = self._part.box(
            length, width, height, origin=(front - length, -width / 2.0, -height)
        )
        centre_x = front - length / 2.0
        plate_z = flange_height - height
        plate = self._part.box(
            tab_span,
            width,
            tab_thickness,
            origin=(centre_x - tab_span / 2.0, -width / 2.0, plate_z),
        )
        spline = self._part.cylinder(spline_radius, spline_height)
        hole_centres = []
        for side in (-1.0, 1.0):
            hole_x = centre_x + side * hole_spacing / 2.0
            if cross > 0.0:
                hole_centres.extend([(hole_x, -cross / 2.0), (hole_x, cross / 2.0)])
            else:
                hole_centres.append((hole_x, 0.0))
        drills = [
            self._part.cylinder(
                hole_dia / 2.0,
                tab_thickness + 2.0,
                origin=(x, y, plate_z - 1.0),
            )
            for x, y in hole_centres
        ]
        body = self._part.cut(
            self._part.fuse([case, plate, spline]), drills, label=label
        )

        volume_mm3 = (
            length * width * height
            + (tab_span - length) * width * tab_thickness
            + math.pi * spline_radius * spline_radius * spline_height
            - len(hole_centres) * math.pi * (hole_dia / 2.0) ** 2 * tab_thickness
        )
        spec["mount_holes"] = [[x, y] for x, y in hole_centres]
        spec["mount_hole_z_mm"] = plate_z
        spec["stall_torque_nmm"] = [
            {"volts": entry["volts"], "nmm": entry["kg_cm"] * catalog.KG_CM_TO_NMM}
            for entry in spec["stall_torque"]
        ]
        spec["effective_density_kg_m3"] = spec["mass_g"] * 1.0e6 / volume_mm3
        frame_placement = self._frame(operation, origin, direction, roll_degrees)
        return ServoPart(
            self,
            catalog.normalise_servo_sku(sku),
            self._place(operation, body, origin, direction, roll_degrees),
            spec,
            frame_placement,
        )

    def _servo_horn(
        self, servo: ServoPart, style: str, roll_degrees: float, label: str
    ) -> LibraryPart:
        operation = "servo.horn"
        if servo.spec["family"] != "micro":
            raise LibraryError(
                f"lib.{operation}: no dimensioned horn source exists yet for "
                f"the {servo.spec['family']} (25T) class; only the micro "
                "family's shipped horns are measured."
            )
        horn_row = catalog.MICRO_HORNS.get(style)
        if horn_row is None:
            raise LibraryError(
                f"lib.{operation}: style must be one of "
                + ", ".join(sorted(catalog.MICRO_HORNS)) + "."
            )
        hub = catalog.MICRO_HORN_HUB
        hub_radius = hub["hub_dia_mm"] / 2.0
        hub_height = hub["hub_height_mm"]
        arm_thickness = hub["arm_thickness_mm"]
        arm_width = hub["arm_width_mm"]
        reach = horn_row["arm_reach_mm"]
        arm_z = hub_height - arm_thickness

        pieces = [self._part.cylinder(hub_radius, hub_height)]
        arms = horn_row["arms"]
        if arms == 1:
            pieces.append(
                self._part.box(
                    reach, arm_width, arm_thickness,
                    origin=(0.0, -arm_width / 2.0, arm_z),
                )
            )
        else:
            pieces.append(
                self._part.box(
                    2.0 * reach, arm_width, arm_thickness,
                    origin=(-reach, -arm_width / 2.0, arm_z),
                )
            )
        if arms == 4:
            pieces.append(
                self._part.box(
                    arm_width, 2.0 * reach, arm_thickness,
                    origin=(-arm_width / 2.0, -reach, arm_z),
                )
            )
        directions = {
            1: [(1.0, 0.0)],
            2: [(1.0, 0.0), (-1.0, 0.0)],
            4: [(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)],
        }[arms]
        drills = [
            self._part.cylinder(
                servo.spec["spline_dia_mm"] / 2.0,
                hub_height + 2.0,
                origin=(0.0, 0.0, -1.0),
            )
        ]
        for dx, dy in directions:
            for radius in horn_row["hole_radii_mm"]:
                drills.append(
                    self._part.cylinder(
                        hub["hole_dia_mm"] / 2.0,
                        arm_thickness + 2.0,
                        origin=(dx * radius, dy * radius, arm_z - 1.0),
                    )
                )
        body = self._part.cut(self._part.fuse(pieces), drills, label=label)

        # Seat the horn on the spline top of the servo as placed: the local
        # +Z offset rides the servo's own rotation.
        servo_origin, _unit, rotation = servo._frame_placement
        lift = _rotate(rotation, (0.0, 0.0, servo.spec["spline_height_mm"]))
        placed = self._place(
            operation,
            body,
            tuple(o + l for o, l in zip(servo_origin, lift)),
            _rotate(rotation, (0.0, 0.0, 1.0)),
            roll_degrees,
        )
        spec = dict(horn_row)
        spec.update(hub)
        spec.update(
            {
                "style": style,
                "spline_dia_mm": servo.spec["spline_dia_mm"],
                # The shipped micro horns are nylon.
                "density_kg_m3": 1150.0,
            }
        )
        return LibraryPart("servo_horn", f"{servo.part_number}-{style}", placed, spec)

    def _servo_actuator(
        self,
        servo: ServoPart,
        joint: Any,
        *,
        control_deg: str,
        voltage: float | None,
        stiffness_nmm_per_deg: float | None,
        damping_nmms_per_deg: float | None,
        command_limits_degrees: Any,
        label: str,
    ) -> Any:
        operation = "servo.actuator"
        if self._assembly is None:
            raise LibraryError(
                f"lib.{operation}: the assembly API is not staged here."
            )
        rated = servo.spec["stall_torque_nmm"]
        if voltage is None:
            chosen = min(rated, key=lambda entry: entry["volts"])
        else:
            matches = [
                entry for entry in rated
                if abs(entry["volts"] - float(voltage)) <= 1.0e-6
            ]
            if not matches:
                raise LibraryError(
                    f"lib.{operation}: {servo.part_number} is rated at "
                    + ", ".join(f"{entry['volts']:g} V" for entry in rated)
                    + f"; {voltage!r} is not one of them and nothing is "
                    "interpolated."
                )
            chosen = matches[0]
        torque = chosen["nmm"]
        stiffness = (
            torque / 5.0
            if stiffness_nmm_per_deg is None
            else stiffness_nmm_per_deg
        )
        damping = (
            stiffness / 20.0
            if damping_nmms_per_deg is None
            else damping_nmms_per_deg
        )
        extra: dict[str, Any] = {}
        if command_limits_degrees is not None:
            extra["command_limits_degrees"] = command_limits_degrees
        return self._assembly.actuator(
            joint,
            kind="position",
            control_deg=control_deg,
            stiffness_nmm_per_deg=stiffness,
            damping_nmms_per_deg=damping,
            torque_limit_nmm=torque,
            label=label,
            **extra,
        )

    def spur_gear(
        self, module: float, teeth: int, face_width: float, *,
        bore: float | None = None,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """ISO 53 involute spur gear on an ISO 54 series I module.

        Datum: gear axis +Z with the base face in the datum plane and the
        body extending face_width along +Z; tooth 0 is centred on +X. Bore
        (optional) must stay inside the root circle. .spec carries pitch,
        base, root and tip diameters, tooth thickness at the pitch circle
        and the undercut warning below 17 teeth. Sampled involute polygon:
        no fillets, backlash, strength rating or density.
        """
        operation = "spur_gear"
        spec = catalog.gear_spec(module, teeth)
        width = _positive(operation, "face_width", face_width)
        spec["face_width_mm"] = width
        spec["bore_mm"] = None
        outline = self._part.wire(_spur_gear_outline(spec), closed=True)
        blank = self._part.face(outline)
        if bore is None:
            body = self._part.extrude(blank, (0.0, 0.0, width), label=label)
        else:
            clean_bore = _positive(operation, "bore", bore)
            if clean_bore >= spec["root_diameter_mm"]:
                raise LibraryError("lib.spur_gear: bore must be smaller than the root diameter.")
            spec["bore_mm"] = clean_bore
            hole = self._part.cylinder(clean_bore / 2.0, width + 2.0, origin=(0.0, 0.0, -1.0))
            body = self._part.cut(self._part.extrude(blank, (0.0, 0.0, width)), hole, label=label)
        part_number = f"m{spec['module_mm']:g}z{teeth}"
        return LibraryPart("gear", part_number,
                           self._place(operation, body, origin, direction, roll_degrees),
                           spec)

    def rack(
        self, module: float, teeth: int, face_width: float, height: float, *,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """ISO 53 basic rack on an ISO 54 series I module, teeth counted.

        Datum: pitch line along +X on Y=0 from X=0 to teeth*pi*module, teeth
        pointing +Y (tips at +module, roots at -1.25 module), back face
        height below the tips, face in the datum plane extending face_width
        along +Z. height must exceed the 2.25 module whole depth. Straight
        20 degree flanks: no fillets, backlash, strength rating or density.
        """
        operation = "rack"
        spec = catalog.gear_spec(module, teeth, rack=True)
        width = _positive(operation, "face_width", face_width)
        clean_height = _positive(operation, "height", height)
        if clean_height <= spec["whole_depth_mm"]:
            raise LibraryError(
                f"lib.rack: height must exceed the whole depth {spec['whole_depth_mm']:g} mm."
            )
        spec["face_width_mm"] = width
        spec["height_mm"] = clean_height
        outline = self._part.wire(_rack_outline(spec, clean_height), closed=True)
        body = self._part.extrude(self._part.face(outline), (0.0, 0.0, width), label=label)
        part_number = f"m{spec['module_mm']:g}z{teeth}"
        return LibraryPart("rack", part_number,
                           self._place(operation, body, origin, direction, roll_degrees),
                           spec)

    def rack_and_pinion(
        self, module: float, pinion_teeth: int, rack_teeth: int, face_width: float, *,
        backlash: float = 0.0, bore: float | None = None,
        rack_height: float | None = None, rotation_degrees: float = 0.0,
        origin: Sequence[float] = _DEFAULT_ORIGIN,
        direction: Sequence[float] = _DEFAULT_DIRECTION,
        roll_degrees: float = 0.0, label: str = "",
    ) -> LibraryPart:
        """An ISO 53 pinion meshed with an ISO 53 rack, as a two-solid compound.

        Datum: the pinion axis is +Z through the origin with its base face
        in the datum plane; the rack runs along X with its pitch line at
        Y = -centre_distance (pitch radius plus the backlash shift) and a
        tooth space under the axis; pinion tooth 0 points at that space.
        rotation_degrees turns the pinion counter-clockwise about +Z and
        slides the rack +X by the matching travel, so one value can be
        published at any phase. rack_height defaults to 3.5 module. .spec
        carries centre distance, travel per revolution, root clearance, the
        rack X range and both members' specs. Geometric mesh only: no
        contact ratio, load, stiffness or efficiency.
        """
        operation = "rack_and_pinion"
        spec = catalog.rack_and_pinion_spec(module, pinion_teeth, rack_teeth, backlash=backlash)
        if isinstance(rotation_degrees, bool) or not isinstance(rotation_degrees, (int, float)) \
                or not math.isfinite(rotation_degrees):
            raise LibraryError("lib.rack_and_pinion: rotation_degrees must be a finite number.")
        m = spec["module_mm"]
        height = 3.5 * m if rack_height is None else rack_height
        pitch = spec["pinion"]["circular_pitch_mm"]
        travel = spec["travel_per_degree_mm"] * float(rotation_degrees)
        rack_x0 = -(rack_teeth // 2) * pitch + travel
        pinion = self.spur_gear(m, pinion_teeth, face_width, bore=bore,
                                roll_degrees=-90.0 + float(rotation_degrees))
        rack = self.rack(m, rack_teeth, face_width, height,
                         origin=(rack_x0, -spec["centre_distance_mm"], 0.0))
        spec.update({
            "face_width_mm": pinion.spec["face_width_mm"],
            "bore_mm": pinion.spec["bore_mm"],
            "rack_height_mm": rack.spec["height_mm"],
            "rotation_degrees": float(rotation_degrees),
            "rack_travel_mm": travel,
            "rack_x_range_mm": [rack_x0, rack_x0 + spec["rack_length_mm"]],
            "datums": {
                "pinion_axis": "+Z through the origin, base face in the datum plane",
                "rack_pitch_line": f"Y = {-spec['centre_distance_mm']:g}, along X",
                "rack_travel_direction": "+X for counter-clockwise pinion rotation about +Z",
            },
        })
        body = self._part.compound([pinion.body, rack.body], label=label)
        return LibraryPart("rack_and_pinion", f"m{m:g}z{pinion_teeth}r{rack_teeth}",
                           self._place(operation, body, origin, direction, roll_degrees),
                           spec)

    # -- browsing ----------------------------------------------------------

    def catalog(self) -> dict[str, Any]:
        """The browsable catalog: families, part numbers, deciding specs."""

        return catalog.catalog_families()


def create_library_api(part_api: Any, assembly_api: Any = None) -> LibraryAPI:
    """The one constructor the worker stages ``lib`` from.

    ``assembly_api`` is what ``servo.actuator(...)`` builds on; a lib
    staged without one still generates every part and refuses only that
    call, naming why.
    """

    if not callable(getattr(part_api, "cylinder", None)):
        raise RuntimeError("create_library_api needs the staged part API.")
    if assembly_api is not None and not callable(
        getattr(assembly_api, "actuator", None)
    ):
        raise RuntimeError("create_library_api got a non-assembly assembly_api.")
    # One staging per run, so the side table is emptied here rather than
    # carried across scripts by a module that outlives one of them.
    _CATALOG_IDENTITY.clear()
    return LibraryAPI(part_api, assembly_api)


def library_listing() -> dict[str, Any]:
    """Name/signature/doc for every lib export, plus the catalog — the
    describe_api section, generated from the runtime class so it cannot
    drift from what a script can actually call."""

    import inspect as _inspect

    exports = []
    for name in sorted(vars(LibraryAPI)):
        if name.startswith("_"):
            continue
        member = getattr(LibraryAPI, name)
        if not callable(member):
            continue
        exports.append(
            {
                "name": name,
                "signature": str(_inspect.signature(member)),
                "description": str(_inspect.getdoc(member) or ""),
            }
        )
    return {
        "api_global": "lib",
        "exports": exports,
        "catalog": catalog.catalog_families(),
        "notes": (
            "Catalogued hardware as parametric part values. Every generator "
            "returns a LibraryPart: .body is an ordinary part solid "
            "(transform it, cut with it, hand it to assembly.component), "
            ".spec is the catalog row it was built from; density only where supported. "
            "Frames are uniform: the axis runs along direction (default +Z) "
            "and the datum sits at origin — a bolt's datum is its head-seat "
            "plane with the shank along -direction. Servos/gearmotors use "
            "the shaft at the case/front face; BLDC uses the rear mounting plane "
            "with the case forwards; boards use a PCB corner; "
            "other parts stand on their base face. Interface dimensions are the standard's; "
            "threads and knurls are deliberately not modelled, so cut "
            "mating holes with lib.clearance_hole/tap_drill/insert_hole "
            "rather than measuring the shank."
        ),
    }
