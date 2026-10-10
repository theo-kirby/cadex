# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Panels cut from what they cover, housings grown around drives.

The script half of ``part.envelope`` and ``part.panel`` (ADR-635),
``lib.housing`` (ADR-611), and the arithmetic the panel check measures with
(ADR-634, ADR-636).

**A panel is a thin, open patch of a smooth offset surface of the mechanism
it covers.** ``part.envelope(over=[...])`` declares that surface: what is
covered (exact solids, catalog parts, meshes made solid), how far the cover
stands off (``clearance``), how much it bridges and smooths (``radius``, the
rolling ball: small hugs, large is the hull) and which motions it must stay
clear of. ``part.panel(env, side=...)`` declares one region of it seen from
``side`` -- the surface turning less than ``max_angle`` from that direction,
optionally ``within`` a box -- its wall, its seams, its openings, its return
flange, the frame it is screwed to and the one stocked screw that holds every
piece. Nothing is computed here: the worker builds the field, the surface,
the pieces, the bosses and the fastener frames on the exact solids
(``CadexEnvelope``), and publishes the frames, so the script places each
screw with ``part.mate`` and the frame's pilots with ``part.cut``.

**How a housing finds its shape.** A drive publishes its envelope: a QDD's
coaxial ``segments`` and stator bolt circles, a servo's case, tabs and
holes. The housing is that envelope at ``clearance``, wrapped in ``wall``,
seated on the drive's own mounting face and screwed to it through its own
holes, open where the output and the leads come out. It is the envelope of
one drive at an infinite radius about its axis, and it is exact already.

Like ``CadexCage`` this module imports nothing from FreeCAD at module scope;
only :func:`gap_statistics` and :func:`first_hits` (the check's measuring
half, run in the assembly worker) import numpy, and only when called.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from CadexMounts import Mount

__all__ = [
    "PanelError",
    "Envelope",
    "Panel",
    "PanelMount",
    "envelope",
    "panel",
    "build_housing",
    "Housing",
    "gap_statistics",
    "first_hits",
    "STANDARD_SCREW_LENGTHS_MM",
]


class PanelError(ValueError):
    """A panel or housing request that cannot be met, with the reason."""


#: Socket-head lengths a hardware store stocks, the ones a screw is rounded to.
STANDARD_SCREW_LENGTHS_MM = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0,
                             18.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0)

#: How many pieces one part.panel may be cut into, and seams per group.
MAX_PIECES = 16
#: How many screws hold one piece, at most.
MAX_SCREWS_PER_PIECE = 8


def _choose_length(needed, longest=None):
    for length in STANDARD_SCREW_LENGTHS_MM:
        if length >= needed - 1e-6 and (longest is None or length <= longest + 1e-6):
            return length
    return None


def _number(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise PanelError(f"{name} must be a finite number; received {value!r}")
    value = float(value)
    if not low <= value <= high:
        raise PanelError(f"{name} must be between {low:g} and {high:g}; received {value:g}")
    return value


def _triple(name, value, *, nonzero=False):
    try:
        clean = [float(v) for v in value]
    except (TypeError, ValueError):
        raise PanelError(f"{name} must be three numbers; received {value!r}") from None
    if len(clean) != 3 or not all(math.isfinite(v) for v in clean):
        raise PanelError(f"{name} must be three finite numbers; received {value!r}")
    if nonzero and sum(v * v for v in clean) <= 1e-18:
        raise PanelError(f"{name} must not be zero")
    return clean


def _solid_value(name, value):
    """A part value to cover or bolt to: a part.* solid or a lib.* part's body."""

    from cadex_domain_api import DomainValue

    body = getattr(value, "body", None)
    if isinstance(body, DomainValue):
        value = body
    if not isinstance(value, DomainValue) or value.domain != "part" \
            or value.output_type not in ("solid", "compound", "shell"):
        raise PanelError(
            f"{name} must be a part.* solid or a lib.* part; received {value!r}")
    return value


def _motion(name, entry, *, with_shape):
    if not isinstance(entry, Mapping):
        raise PanelError(
            f"{name} must be a dict: {{'shape': link, 'origin': o, 'axis': a, 'range': "
            "(lo, hi)}} for a hinge (degrees) or {'shape': s, 'direction': d, 'range': "
            "(lo, hi)} for a slider (mm)")
    allowed = {"shape", "origin", "axis", "direction", "range"}
    if not with_shape:
        allowed.discard("shape")
    unknown = set(entry) - allowed
    if unknown:
        raise PanelError(f"{name} has unknown keys {sorted(unknown)}; it takes {sorted(allowed)}")
    rng = entry.get("range")
    if not isinstance(rng, (list, tuple)) or len(rng) != 2:
        raise PanelError(f"{name}['range'] must be (lo, hi)")
    lo = _number(f"{name}['range'][0]", rng[0], -3600.0, 3600.0)
    hi = _number(f"{name}['range'][1]", rng[1], -3600.0, 3600.0)
    clean: dict[str, Any] = {"range": [min(lo, hi), max(lo, hi)]}
    if with_shape:
        clean["shape"] = _solid_value(f"{name}['shape']", entry.get("shape"))
    if "axis" in entry:
        clean.update(kind="hinge", axis=_triple(f"{name}['axis']", entry["axis"], nonzero=True),
                     origin=_triple(f"{name}['origin']", entry.get("origin", (0, 0, 0))))
    elif "direction" in entry:
        clean.update(kind="slider",
                     direction=_triple(f"{name}['direction']", entry["direction"], nonzero=True))
    else:
        raise PanelError(f"{name} needs 'axis' (and 'origin') for a hinge or 'direction' "
                         "for a slider")
    return clean


class Envelope:
    """What ``part.envelope`` returns: the surface panels are cut from.

    Not a shape on its own: hand it to ``part.panel``. ``spec`` is what was
    declared.
    """

    __slots__ = ("spec",)

    def __init__(self, spec):
        object.__setattr__(self, "spec", spec)

    def __setattr__(self, _name, _value):
        raise TypeError("An envelope is immutable; declare another instead.")

    def __repr__(self):  # pragma: no cover - debugging convenience
        return f"Envelope({len(self.spec['over'])} parts, r={self.spec['radius']:g})"


def envelope(over, *, clearance=1.5, radius=20.0, motion=(), resolution=None):
    """Validate a ``part.envelope`` declaration (see its docstring)."""

    items = list(over) if isinstance(over, (list, tuple)) else [over]
    if not items:
        raise PanelError("over= must name at least one part to cover")
    if len(items) > 64:
        raise PanelError("over= takes at most 64 parts; one envelope covers one assembly region")
    spec = {
        "over": [_solid_value(f"over[{k}]", item) for k, item in enumerate(items)],
        "clearance": _number("clearance", clearance, 0.2, 30.0),
        "radius": "hull" if radius == "hull" else _number("radius", radius, 0.0, 400.0),
        "motion": [_motion(f"motion[{k}]", entry, with_shape=True)
                   for k, entry in enumerate(list(motion or ()))],
        "resolution": None if resolution is None else _number("resolution", resolution, 0.4, 6.0),
    }
    return Envelope(spec)


class PanelMount(Mount):
    """One fastener frame a ``part.panel`` piece publishes (``p.mounts["p0"]["b0"]``).

    A mount like any other for ``part.mate``, except that its frame is the
    worker's: the head seat of the boss's counterbore, axis out of the
    panel along ``side``. Its numbers are only known once the worker has
    cast the boss onto the frame, so it carries the piece instead.
    """

    __slots__ = ()


class Panel:
    """What ``part.panel`` returns.

    ``parts`` -- one solid per piece, ``names`` beside them (``p0``, ``p1``,
    ... in seam order); each is its own component, ``role="panel"``,
    ``covers=[...]``. ``screws`` -- one ``lib.bolt`` per boss, already
    mated onto its fastener frame: one component each, welded to its piece.
    ``pilots`` -- the frame's tap-drill holes: ``frame = part.cut(frame,
    p.pilots)`` (None with no screws). ``mounts`` -- ``{piece: {"b0": mount,
    ...}}`` for ``part.mate`` of anything else onto a boss. ``spec`` -- what
    was declared. Every number the worker measured (where each boss landed,
    its reach and seat, the field) is in the piece's build facts:
    ``inspect scope=output target=<name>``.
    """

    __slots__ = ("parts", "names", "screws", "pilots", "mounts", "spec")

    def __init__(self, **values):
        for key in self.__slots__:
            object.__setattr__(self, key, values.get(key))

    def __setattr__(self, _name, _value):
        raise TypeError("A panel is immutable; declare another instead.")

    def __repr__(self):  # pragma: no cover - debugging convenience
        return f"Panel({len(self.parts)} pieces, {len(self.screws)} screws)"


def _openings(entries):
    result = []
    for k, entry in enumerate(list(entries or ())):
        name = f"openings[{k}]"
        if not isinstance(entry, Mapping):
            raise PanelError(f"{name} must be a dict: {{'around': part, 'clearance': mm, "
                             "'motion': {...}}, {'cone': (apex, axis, half_angle)} or "
                             "{'at': point, 'radius': mm}")
        if "around" in entry:
            unknown = set(entry) - {"around", "clearance", "motion"}
            if unknown:
                raise PanelError(f"{name} has unknown keys {sorted(unknown)}")
            clean = {"around": _solid_value(f"{name}['around']", entry["around"]),
                     "clearance": _number(f"{name}['clearance']",
                                          entry.get("clearance", 2.0), 0.0, 50.0)}
            if entry.get("motion") is not None:
                clean["motion"] = _motion(f"{name}['motion']", entry["motion"], with_shape=False)
            result.append(clean)
        elif "cone" in entry:
            cone = entry["cone"]
            if not isinstance(cone, (list, tuple)) or len(cone) != 3:
                raise PanelError(f"{name}['cone'] must be (apex, axis, half_angle_degrees)")
            result.append({"cone": [_triple(f"{name} apex", cone[0]),
                                    _triple(f"{name} axis", cone[1], nonzero=True),
                                    _number(f"{name} half angle", cone[2], 1.0, 85.0)]})
        elif "at" in entry:
            result.append({"at": _triple(f"{name}['at']", entry["at"]),
                           "radius": _number(f"{name}['radius']", entry.get("radius", 5.0),
                                             0.5, 200.0)})
        else:
            raise PanelError(f"{name} needs 'around', 'cone' or 'at'")
    return result


def _seams(entries):
    groups = []
    for k, entry in enumerate(list(entries or ())):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise PanelError(
                f"seams[{k}] must be (normal, [positions]): the parting planes "
                "normal . p = position, e.g. ((1, 0, 0), [-40.0, 60.0])")
        normal, positions = entry
        at = [positions] if isinstance(positions, (int, float)) else list(positions)
        if not at:
            raise PanelError(f"seams[{k}] names no position")
        groups.append({"normal": _triple(f"seams[{k}] normal", normal, nonzero=True),
                       "at": sorted(_number(f"seams[{k}] position", v, -1e5, 1e5) for v in at)})
    return groups


def _avoided(index, other):
    if not isinstance(other, Panel):
        raise PanelError(f"avoid[{index}] must be a part.panel(...) declared before this one")
    return dict(other.spec)


def panel(part, env, *, side=(0.0, 0.0, 1.0), max_angle=60.0, within=None, thickness=2.0,
          seams=(), seam_gap=0.6, inset=0.0, openings=(), flange=0.0, frame=None, screw=None,
          screws=2, max_piece=None, avoid=(), label=""):
    """Validate a ``part.panel`` declaration and make its values (see its docstring)."""

    if not isinstance(env, Envelope):
        raise PanelError("the first argument must be a part.envelope(...)")
    groups = _seams(seams)
    count = 1
    for group in groups:
        count *= len(group["at"]) + 1
    if count > MAX_PIECES:
        raise PanelError(f"the seams cut {count} pieces; one panel is at most {MAX_PIECES}")
    spec: dict[str, Any] = {
        "envelope": dict(env.spec),
        "side": _triple("side", side, nonzero=True),
        "max_angle": _number("max_angle", max_angle, 5.0, 85.0),
        "within": None if within is None else [_triple("within[0]", within[0]),
                                               _triple("within[1]", within[1])],
        "thickness": _number("thickness", thickness, 0.6, 8.0),
        "seams": groups,
        "seam_gap": _number("seam_gap", seam_gap, 0.1, 5.0),
        "edge_inset": _number("inset", inset, 0.0, 20.0),
        "openings": _openings(openings),
        "flange": "frame" if flange == "frame" else _number("flange", flange or 0.0, 0.0, 60.0),
        "frame": None if frame is None else _solid_value("frame", frame),
        "screw": None,
        "screws": 0,
        "max_piece": None if max_piece is None else _triple("max_piece", max_piece),
        "avoid": [_avoided(k, other) for k, other in enumerate(list(avoid or ()))],
    }
    if spec["flange"] == "frame" and frame is None:
        raise PanelError('flange="frame" needs frame=: the part the skirt comes down to')
    bolt = None
    if screw is not None:
        if frame is None:
            raise PanelError("screw= needs frame=: the part the bosses land on")
        if getattr(screw, "family", None) != "bolt":
            raise PanelError("screw= is a lib.bolt(size, length): the one stocked screw "
                             "every boss is seated for")
        if str(screw.spec.get("head") or "") != "socket":
            raise PanelError("screw= must be a socket-head lib.bolt; a countersunk head "
                             "needs a countersink this panel does not cut")
        per_piece = int(_number("screws", screws, 1, MAX_SCREWS_PER_PIECE))
        # A fresh one at its datum, so a template placed anywhere still mates.
        from cadex_library_api import LibraryAPI

        size = str(screw.part_number).split("x", 1)[0]
        bolt = LibraryAPI(part).bolt(size, float(screw.spec["length_mm"]))
        spec["screw"] = {key: bolt.spec[key] for key in (
            "nominal_dia_mm", "clearance_normal_mm", "tap_drill_mm", "head_dia_mm",
            "head_height_mm", "length_mm")}
        spec["screw"]["size"] = size
        spec["screws"] = per_piece
    names = [f"p{k}" for k in range(count)]
    parts = [part._value("panel", "solid", spec, piece=name, label=label) for name in names]
    screws_out, mounts = [], {}
    pilots = None
    if bolt is not None:
        from cadex_library_api import LibraryPart

        seat = Mount("seat", bolt.body, {"name": "seat", "component": "", "origin": (0, 0, 0),
                                         "axis": (0, 0, -1), "roll": (1, 0, 0)})
        for name, piece in zip(names, parts):
            mounts[name] = {}
            for index in range(spec["screws"]):
                handle = f"b{index}"
                target = PanelMount(handle, piece, {
                    "name": handle, "component": name, "origin": (0, 0, 0),
                    "axis": (0, 0, 1), "roll": (1, 0, 0), "panel_fastener": handle})
                mounts[name][handle] = target
                placed = part.mate(bolt.body, seat, target, check_interference=False)
                screws_out.append(LibraryPart("bolt", bolt.part_number, placed, bolt.spec))
        pilots = part._value("panel", "compound", spec, piece="pilots", label=label)
    return Panel(parts=parts, names=names, screws=screws_out, pilots=pilots, mounts=mounts,
                 spec=spec)


class Housing:
    """What ``lib.housing`` returns: a printed part grown around one drive.

    ``body`` -- the housing solid (give it ``appearance="shell"`` or
    ``"mechanism"``, and weld the drive to it with a fixed joint). ``screws``
    -- the ``lib.bolt`` parts through its seat into the drive's own holes,
    one component each. ``cavity`` and ``holes`` -- what was cut, so a link
    fused on later can be cut again: ``housing.fuse(link)`` does exactly
    that. ``spec`` -- the numbers it was grown with (``wall_mm``,
    ``clearance_mm``, ``outer_dia_mm`` or ``outer_size_mm``, ``seat``,
    ``screw``, ``screw_length_mm``, ``engagement_mm``).
    """

    __slots__ = ("body", "screws", "cavity", "holes", "drive", "spec", "_lib")

    def __init__(self, lib, **values):
        object.__setattr__(self, "_lib", lib)
        for key in self.__slots__[:-1]:
            object.__setattr__(self, key, values.get(key))

    def __setattr__(self, _name, _value):
        raise TypeError("A housing is immutable; build another instead.")

    def fuse(self, *links, label=""):
        """The housing with ``links`` grown on, cavity and screw holes cut again.

        A link fused onto a housing usually reaches into the drive's
        envelope; cutting the cavity and holes after the fuse keeps the
        drive's seat and its screws' paths clear.
        """

        part = self._lib._part
        shapes = [self.body] + [getattr(link, "body", link) for link in links]
        if len(shapes) < 2:
            return self.body
        return part.cut(part.fuse(shapes), [self.cavity] + list(self.holes), label=label)

    def __repr__(self):  # pragma: no cover - debugging convenience
        return f"Housing({self.spec.get('drive')})"


def _place_local(lib, body, frame):
    return lib._place_frame("housing", body, frame)


def _world_point(frame, local):
    from cadex_library_api import _rotate

    origin, _unit_dir, rotation = frame
    return [o + v for o, v in zip(origin, _rotate(rotation, local))]


def _world_vector(frame, local):
    from cadex_library_api import _rotate

    return list(_rotate(frame[2], local))


def _bolt_for_hole(hole_dia):
    """The largest catalogued metric bolt a clearance hole of this size takes."""

    import CadexCatalog as catalog

    best = None
    for key, row in catalog.METRIC_THREADS.items():
        if row["nominal_dia_mm"] <= hole_dia + 1e-6 and key in catalog.SOCKET_HEAD_SCREWS:
            if best is None or row["nominal_dia_mm"] > best[1]:
                best = (key, row["nominal_dia_mm"])
    if best is None:
        raise PanelError(f"no catalogued screw fits a {hole_dia:g} mm hole")
    return best[0]


def build_housing(lib, drive, *, wall=2.0, clearance=0.5, seat=None, plate=None,
                  lead_room=None, label=""):
    family = getattr(drive, "family", None)
    wall = _number("lib.housing wall", wall, 0.8, 10.0)
    clearance = _number("lib.housing clearance", clearance, 0.0, 5.0)
    if family == "qdd":
        return _qdd_housing(lib, drive, wall, clearance, seat or "rear", plate, label)
    if family == "servo":
        return _servo_housing(lib, drive, wall, clearance, lead_room, label)
    raise PanelError(
        "lib.housing grows around a lib.qdd(...) or lib.servo(...) part; received "
        f"{drive!r}")


def _qdd_housing(lib, qdd, wall, c, seat, plate, label):
    import CadexCatalog as catalog

    part = lib._part
    spec = qdd.spec
    frame = qdd._frame_placement
    if seat not in ("rear", "front"):
        raise PanelError(f"lib.housing seat must be 'rear' or 'front'; received {seat!r}")
    plate = _number("lib.housing plate", plate if plate is not None else max(3.0, 1.5 * wall),
                    1.0, 20.0)
    segments = [tuple(float(v) for v in row) for row in spec["segments"]]
    case_dia = float(spec["case_dia_mm"])
    stator = [row for row in segments if abs(row[0] - case_dia) <= 1e-6]
    body_low = min(row[1] for row in stator)
    body_high = max(row[2] for row in stator)
    r_in = case_dia / 2.0 + c
    r_out = r_in + wall
    thread = spec["mount_thread"].lower()
    screw = catalog.normalise_thread_size(thread)
    thread_row = catalog.thread_spec(screw)
    clear_r = thread_row["clearance_normal_mm"] / 2.0
    pcd_r = float(spec["mount_pcd_mm"]) / 2.0
    hole_edge = pcd_r - clear_r
    if seat == "rear":
        seat_z = float(spec["rear_mount_z_mm"])
        depth = float(spec["rear_mount_depth_mm"])
        behind = [row for row in segments if row[1] < seat_z - 1e-6]
        opening = max([row[0] / 2.0 + c for row in behind] + [0.0])
        if opening <= 0.0:
            opening = hole_edge - 2.0
        z0, z1 = seat_z - plate, body_high
        plate_low, plate_high = seat_z - plate, seat_z
        head_z, screw_dir = seat_z - plate, (0.0, 0.0, -1.0)
    else:
        seat_z = float(spec["front_mount_z_mm"])
        depth = float(spec["front_mount_depth_mm"])
        ahead = [row for row in segments if row[2] > seat_z + 1e-6]
        opening = max([row[0] / 2.0 + c for row in ahead] + [0.0])
        if opening <= 0.0:
            opening = hole_edge - 2.0
        z0, z1 = body_low, seat_z + plate
        plate_low, plate_high = seat_z, seat_z + plate
        head_z, screw_dir = seat_z + plate, (0.0, 0.0, 1.0)
    if opening > hole_edge - 0.6:
        raise PanelError(
            f"lib.housing: a {seat} seat on {qdd.part_number} leaves "
            f"{hole_edge - opening:.2f} mm between the {opening * 2:.1f} mm opening and "
            f"the {screw.upper()} holes; seat it on the other face")
    longest = plate + depth - 0.3
    length = None
    for candidate in reversed(STANDARD_SCREW_LENGTHS_MM):
        if plate + 1.5 <= candidate <= longest + 1e-6:
            length = candidate
            break
    if length is None:
        raise PanelError(
            f"lib.housing: no stocked {screw.upper()} length fits a {plate:g} mm plate "
            f"into {qdd.part_number}'s {depth:g} mm {seat} holes; thin the plate")
    drum = part.cylinder(r_out, z1 - z0, origin=(0.0, 0.0, z0))
    cavity_pieces = []
    for dia, low, high in segments:
        lo, hi = low - c, high + c
        if seat == "rear":
            lo = max(lo, seat_z)
            if hi <= seat_z:
                continue
            if abs(high - max(r[2] for r in segments)) <= 1e-6 or high >= body_high - 1e-6:
                hi = max(hi, z1 + 1.0)
        else:
            hi = min(hi, seat_z)
            if lo >= seat_z:
                continue
            if low <= body_low + 1e-6:
                lo = min(lo, z0 - 1.0)
        cavity_pieces.append(part.cylinder(dia / 2.0 + c, hi - lo, origin=(0.0, 0.0, lo)))
    # The opening the output (front seat) or the rear cover and leads
    # (rear seat) pass through.
    cavity_pieces.append(part.cylinder(opening, plate + 2.0, origin=(0.0, 0.0, plate_low - 1.0)))
    cavity_local = part.fuse(cavity_pieces) if len(cavity_pieces) > 1 else cavity_pieces[0]
    holes_local = [part.cylinder(clear_r, plate + 2.0, origin=(x, y, plate_low - 1.0))
                   for x, y in spec["mount_holes"]]
    cavity = _place_local(lib, cavity_local, frame)
    holes = [_place_local(lib, hole, frame) for hole in holes_local]
    body = part.cut(_place_local(lib, drum, frame), [cavity] + holes, label=label)
    screws = [lib.bolt(screw, length, origin=_world_point(frame, (x, y, head_z)),
                       direction=_world_vector(frame, screw_dir))
              for x, y in spec["mount_holes"]]
    return Housing(lib, body=body, screws=screws, cavity=cavity, holes=holes, drive=qdd,
                   spec={"drive": f"qdd/{qdd.part_number}", "seat": seat, "wall_mm": wall,
                         "clearance_mm": c, "plate_mm": plate, "outer_dia_mm": 2 * r_out,
                         "span_z_mm": [z0, z1], "opening_dia_mm": 2 * opening,
                         "screw": screw, "screw_count": len(screws),
                         "screw_length_mm": length, "engagement_mm": length - plate})


def _servo_housing(lib, servo, wall, c, lead_room, label):
    import CadexCatalog as catalog

    part = lib._part
    spec = servo.spec
    frame = servo._frame_placement
    front = float(spec["shaft_offset_from_front_mm"])
    length = float(spec["body_length_mm"])
    back = front - length
    half = float(spec["body_width_mm"]) / 2.0
    height = float(spec["case_height_mm"])

    def box(low, high):
        return part.box(*(b - a for a, b in zip(low, high)), origin=tuple(low))

    if spec.get("mount_style") == "case_holes":
        room = 15.0 if lead_room is None else float(lead_room)
        floor_low = -height - c - wall
        outer = box((back - c - wall, -half - c - wall, floor_low),
                    (front + c + wall, half + c + wall, 0.0))
        bay = servo.bay(clearance=c, lead_room=room)
        # The floor the rear face is screwed down onto: the bay leaves `c`
        # under the case, and a screwed face wants its seat.
        pad = box((back, -half, -height - c - 0.5), (front, half, -height))
        rear = [p for p in spec["mount_points"] if p["face"] == "rear"]
        screw = catalog.normalise_thread_size("m2")
        thread_row = catalog.thread_spec(screw)
        boss_hole = part.cylinder(spec["rear_boss_dia_mm"] / 2.0 + c, wall + c + 2.0,
                                  origin=(0.0, 0.0, floor_low - 1.0))
        holes_local = [part.cylinder(thread_row["clearance_normal_mm"] / 2.0, wall + c + 2.0,
                                     origin=(p["origin"][0], p["origin"][1], floor_low - 1.0))
                       for p in rear]
        floor = c + wall  # under the case, the pad included
        longest = floor + float(spec["hole_depth_mm"]) - 0.3
        screw_length = None
        for candidate in reversed(STANDARD_SCREW_LENGTHS_MM):
            if floor + 1.5 <= candidate <= longest + 1e-6:
                screw_length = candidate
                break
        if screw_length is None:
            raise PanelError("lib.housing: no stocked M2 length fits this floor; thin the wall")
        placed_holes = [_place_local(lib, hole, frame) for hole in holes_local + [boss_hole]]
        body = part.cut(
            part.fuse([part.cut(_place_local(lib, outer, frame), [bay]),
                       _place_local(lib, pad, frame)]),
            placed_holes, label=label)
        screws = [lib.bolt(screw, screw_length,
                           origin=_world_point(frame, (p["origin"][0], p["origin"][1], floor_low)),
                           direction=_world_vector(frame, (0.0, 0.0, -1.0)))
                  for p in rear]
        return Housing(lib, body=body, screws=screws, cavity=bay, holes=placed_holes,
                       drive=servo, spec={
                           "drive": f"servo/{servo.part_number}", "seat": "rear face",
                           "wall_mm": wall, "clearance_mm": c, "lead_room_mm": room,
                           "outer_size_mm": [length + 2 * (c + wall), 2 * (half + c + wall),
                                             height + c + wall],
                           "screw": screw, "screw_count": len(screws),
                           "screw_length_mm": screw_length,
                           "engagement_mm": screw_length - floor})

    room = 6.0 if lead_room is None else float(lead_room)
    plate_z = float(spec["mount_hole_z_mm"])
    tab_t = float(spec["tab_thickness_mm"])
    centre = front - length / 2.0
    tab_half = float(spec["overall_tab_length_mm"]) / 2.0
    x_low = min(back - c - wall, centre - tab_half)
    x_high = max(front + c + wall, centre + tab_half)
    bottom = -height - c - wall
    outer = box((x_low, -half - c - wall, bottom), (x_high, half + c + wall, plate_z))
    bay = servo.bay(clearance=c, lead_room=room, ledge=4.0)
    # Seats under the tabs: the bay grows the tab plate by `c` below, and a
    # screwed tab wants to land on the rim, not across a gap.
    pads = [box((front + c, -half, plate_z - c - 1.0), (centre + tab_half, half, plate_z)),
            box((centre - tab_half, -half, plate_z - c - 1.0), (back - c, half, plate_z))]
    screw = _bolt_for_hole(float(spec["hole_dia_mm"]))
    thread_row = catalog.thread_spec(screw)
    d = float(thread_row["nominal_dia_mm"])
    screw_length = _choose_length(tab_t + max(2.5 * d, 4.0))
    rim = plate_z - bottom
    engage = screw_length - tab_t
    if engage + 1.0 > rim:
        raise PanelError("lib.housing: the servo's housing is too shallow for its screws")
    pilots = [part.cylinder(thread_row["tap_drill_mm"] / 2.0, engage + 1.5,
                            origin=(x, y, plate_z - engage - 1.0))
              for x, y in spec["mount_holes"]]
    placed_pilots = [_place_local(lib, pilot, frame) for pilot in pilots]
    body = part.cut(
        part.fuse([part.cut(_place_local(lib, outer, frame), [bay])]
                  + [_place_local(lib, p, frame) for p in pads]),
        placed_pilots, label=label)
    screws = [lib.bolt(screw, screw_length,
                       origin=_world_point(frame, (x, y, plate_z + tab_t)),
                       direction=_world_vector(frame, (0.0, 0.0, 1.0)))
              for x, y in spec["mount_holes"]]
    return Housing(lib, body=body, screws=screws, cavity=bay, holes=placed_pilots,
                   drive=servo, spec={
                       "drive": f"servo/{servo.part_number}", "seat": "tabs",
                       "wall_mm": wall, "clearance_mm": c, "lead_room_mm": room,
                       "outer_size_mm": [x_high - x_low, 2 * (half + c + wall), plate_z - bottom],
                       "screw": screw, "screw_count": len(screws),
                       "screw_length_mm": screw_length, "engagement_mm": engage})




# ---------------------------------------------------------------------------
# the panel check's measuring half (run in the assembly worker)


def gap_statistics(samples, normals, triangles, *, reach=250.0, sample_area=None):
    """How far a panel's inner face stands off what it covers.

    ``samples`` and ``normals`` are points on the panel and the panel's
    outward normals there; ``triangles`` the contents' surface, an
    ``(n, 3, 3)`` array-like. For every sample the nearest content point is
    found exactly (point-to-triangle). A sample faces the contents when its
    normal points towards that nearest point: on a hollow panel that is the
    inner face, whose distance is the gap a designer means. Returns the
    inner-face count and the gap's percentiles (p10, p25, median, p90, max),
    or ``None`` when no sample faces any content within ``reach`` mm. With
    ``sample_area`` (the area each sample stands for) it also returns
    ``air_volume_mm3``, the gap summed over the inner face: the volume a
    panel encloses that is not the parts under it (ADR-636's egg ratio).
    """

    import numpy as np

    P = np.asarray(samples, dtype=float).reshape(-1, 3)
    N = np.asarray(normals, dtype=float).reshape(-1, 3)
    T = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
    if not len(P) or not len(T):
        return None
    best_d = np.full(len(P), np.inf)
    best_q = np.zeros_like(P)
    for start in range(0, len(T), 512):
        chunk = T[start:start + 512]
        q = _closest_on_triangles(P, chunk)  # (S, C, 3)
        d = np.linalg.norm(q - P[:, None, :], axis=2)
        index = np.argmin(d, axis=1)
        dmin = d[np.arange(len(P)), index]
        better = dmin < best_d
        best_d[better] = dmin[better]
        best_q[better] = q[np.arange(len(P)), index][better]
    toward = np.einsum("ij,ij->i", N, best_q - P)
    facing = (toward > 0.0) & (best_d <= reach)
    gaps = np.sort(best_d[facing])
    if not len(gaps):
        return None
    stats = {
        "samples": int(len(P)),
        "inner_samples": int(len(gaps)),
        "gap_p10_mm": round(float(np.percentile(gaps, 10)), 3),
        "gap_p25_mm": round(float(np.percentile(gaps, 25)), 3),
        "gap_median_mm": round(float(np.percentile(gaps, 50)), 3),
        "gap_p90_mm": round(float(np.percentile(gaps, 90)), 3),
        "gap_max_mm": round(float(gaps[-1]), 3),
        "hug_fraction": round(float(np.mean(gaps <= HUG_GAP_MM)), 3),
    }
    if sample_area is not None:
        stats["air_volume_mm3"] = round(float(np.sum(gaps)) * float(sample_area), 1)
    return stats


def first_hits(origins, directions, triangles, *, reach=float("inf")):
    """Distance along each ray to the first triangle it crosses, or ``inf``.

    Möller-Trumbore over an ``(n, 3, 3)`` triangle array, chunked so a few
    hundred rays against tens of thousands of triangles stay in memory. Hits
    closer than a micrometre are the ray's own start and are ignored. The
    panel check reads a wall's thickness (a ray from the outer face inward
    to the inner one) and whether a covered part's surface is hidden (a ray
    from it outward that meets a panel) with it (ADR-636).
    """

    import numpy as np

    O = np.asarray(origins, dtype=float).reshape(-1, 3)
    D = np.asarray(directions, dtype=float).reshape(-1, 3)
    T = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
    best = np.full(len(O), np.inf)
    if not len(O) or not len(T):
        return best
    for start in range(0, len(T), 1024):
        chunk = T[start:start + 1024]
        a = chunk[:, 0][None]
        e1 = (chunk[:, 1] - chunk[:, 0])[None]
        e2 = (chunk[:, 2] - chunk[:, 0])[None]
        d = D[:, None, :]
        p = np.cross(d, e2)
        det = np.einsum("ijk,ijk->ij", e1, p)
        with np.errstate(divide="ignore", invalid="ignore"):
            inv = np.where(np.abs(det) > 1e-12, 1.0 / det, 0.0)
            s = O[:, None, :] - a
            u = np.einsum("ijk,ijk->ij", s, p) * inv
            q = np.cross(s, e1)
            v = np.einsum("ijk,ijk->ij", d, q) * inv
            t = np.einsum("ijk,ijk->ij", e2, q) * inv
        hit = (np.abs(det) > 1e-12) & (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0) \
            & (t > 1e-3) & (t <= reach)
        t = np.where(hit, t, np.inf)
        best = np.minimum(best, t.min(axis=1))
    return best


#: A sample of a shell's inner face within this of what it covers "hugs" it.
HUG_GAP_MM = 4.0


def _closest_on_triangles(P, T):
    """Closest points on each triangle to each point: (S, C, 3). Ericson 5.1.5."""

    import numpy as np

    a, b, c = T[:, 0][None], T[:, 1][None], T[:, 2][None]
    p = P[:, None, :]
    ab, ac, ap = b - a, c - a, p - a
    d1 = np.einsum("ijk,ijk->ij", ab, ap)
    d2 = np.einsum("ijk,ijk->ij", ac, ap)
    bp = p - b
    d3 = np.einsum("ijk,ijk->ij", ab, bp)
    d4 = np.einsum("ijk,ijk->ij", ac, bp)
    cp = p - c
    d5 = np.einsum("ijk,ijk->ij", ab, cp)
    d6 = np.einsum("ijk,ijk->ij", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v = np.where(np.abs(denom) > 1e-30, vb / denom, 0.0)
        w = np.where(np.abs(denom) > 1e-30, vc / denom, 0.0)
        result = a + ab * v[..., None] + ac * w[..., None]
        # Edge regions.
        t_ab = np.clip(np.where(np.abs(d1 - d3) > 1e-30, d1 / (d1 - d3), 0.0), 0, 1)
        t_ac = np.clip(np.where(np.abs(d2 - d6) > 1e-30, d2 / (d2 - d6), 0.0), 0, 1)
        t_bc = np.clip(np.where(np.abs((d4 - d3) + (d5 - d6)) > 1e-30,
                                (d4 - d3) / ((d4 - d3) + (d5 - d6)), 0.0), 0, 1)
    on_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    on_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    on_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    result = np.where(on_bc[..., None], b + (c - b) * t_bc[..., None], result)
    result = np.where(on_ac[..., None], a + ac * t_ac[..., None], result)
    result = np.where(on_ab[..., None], a + ab * t_ab[..., None], result)
    at_a = (d1 <= 0) & (d2 <= 0)
    at_b = (d3 >= 0) & (d4 <= d3)
    at_c = (d6 >= 0) & (d5 <= d6)
    result = np.where(at_c[..., None], np.broadcast_to(c, result.shape), result)
    result = np.where(at_b[..., None], np.broadcast_to(b, result.shape), result)
    result = np.where(at_a[..., None], np.broadcast_to(a, result.shape), result)
    return result
