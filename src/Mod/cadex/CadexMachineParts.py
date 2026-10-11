# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One generator per interface, for the machine parts in ``CadexParts.json`` (ADR-646).

A part number is a row of data; what turns a row into geometry is the
*interface* its family is built by -- a rail, a carriage, a pulley, a belt,
a screw and its nut, a motor face, an extrusion profile, slot hardware, a
cylinder, a spindle, a caster, a wheel on a hub, a spring. Each builder
here takes the part API, the row and the call's options, and returns the
canonical body (axis +Z, datum at the origin, as every ``lib`` part), any
member bodies a mechanism needs apart (a cylinder's barrel and rod, a
caster's yoke and wheel), and the numbers it adds to the spec: datums, the
derived quantities a joint or an actuator takes, and the density the stated
mass implies over the modelled volume.

Like the rest of the library this imports nothing from FreeCAD; the
volumes are the builders' own primitive sums, so the density is exact for
the body as modelled.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping

__all__ = ["BUILDERS", "PartBuildError", "build"]


class PartBuildError(ValueError):
    """A ``lib.part`` call's options do not fit its interface."""


def _cyl(r: float, h: float) -> float:
    return math.pi * r * r * h


def _need(options: Mapping[str, Any], name: str, interface: str) -> float:
    value = options.get(name)
    if value is None:
        raise PartBuildError(f"a {interface} part needs {name}=")
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value <= 0.0:
        raise PartBuildError(f"{name} must be a positive number of millimetres")
    return float(value)


def _unused(options: Mapping[str, Any], interface: str, allowed: tuple[str, ...] = ()) -> None:
    extra = sorted(name for name, value in options.items()
                   if value is not None and name not in allowed)
    if extra:
        raise PartBuildError(f"a {interface} part does not take {extra[0]}=")


def _thread_dia(thread: str) -> float:
    """``'m3'`` -> 3.0: the nominal diameter a tapped hole is modelled at."""

    return float(str(thread).strip().lower().lstrip("m"))


def _hole(origin, axis, *, thread: str | None = None, hole_dia: float | None = None,
          output: bool = False) -> dict[str, Any]:
    """One mounting hole in the part's own frame (ADR-660).

    ``origin`` is where a screw's head seats (or, for a tapped hole, the
    hole's mouth) and ``axis`` is the ``direction`` a ``lib.bolt`` placed
    at ``origin`` takes, its shank running back along ``-axis``; a tapped
    hole names its thread, a clearance hole its diameter. ``lib.part``
    carries these through the placement into the mounting check, which
    credits a screw on the axis either way round.
    """

    row: dict[str, Any] = {"origin": [float(v) for v in origin], "axis": [float(v) for v in axis]}
    if thread is not None:
        row["thread_dia_mm"] = _thread_dia(thread)
    elif hole_dia is not None:
        row["hole_dia_mm"] = float(hole_dia)
    if output:
        row["output"] = True
    return row


def _density(spec: dict[str, Any], volume_mm3: float, mass_kg: float | None) -> None:
    if mass_kg is not None and volume_mm3 > 0.0:
        spec["density_kg_m3"] = mass_kg / (volume_mm3 * 1.0e-9)
    spec["modelled_volume_mm3"] = volume_mm3


def rail(part, spec, options):
    """Rail along +Z from the datum end, base centred in X at Y = 0, height +Y."""

    _unused(options, "rail", ("length",))
    length = _need(options, "length", "rail")
    w, h = spec["width_mm"], spec["height_mm"]
    pitch, least = spec["hole_pitch_mm"], spec["end_distance_mm"]
    body = part.box(w, h, length, origin=(-w / 2.0, 0.0, 0.0))
    # The pattern is centred, as the catalogue's standard lengths are
    # (L = (n - 1) P + 2E): as many holes as keep each end at least the
    # catalogue's end distance, and the two ends equal (ADR-660).
    count = int(math.floor((length - 2.0 * least) / pitch + 1e-9)) + 1 if length >= 2.0 * least else 0
    end = (length - (count - 1) * pitch) / 2.0 if count else 0.0
    seat = h - spec["counterbore_depth_mm"]
    holes, points = [], []
    for index in range(count):
        z = end + index * pitch
        holes.append(part.cylinder(spec["hole_dia_mm"] / 2.0, h + 2.0, origin=(0.0, -1.0, z),
                                   direction=(0.0, 1.0, 0.0)))
        holes.append(part.cylinder(spec["counterbore_dia_mm"] / 2.0, spec["counterbore_depth_mm"] + 1.0,
                                   origin=(0.0, seat, z), direction=(0.0, 1.0, 0.0)))
        points.append(_hole((0.0, seat, z), (0.0, 1.0, 0.0), hole_dia=spec["hole_dia_mm"]))
    if holes:
        body = part.cut(body, holes)
    volume = w * h * length - count * (_cyl(spec["hole_dia_mm"] / 2, h - spec["counterbore_depth_mm"])
                                       + _cyl(spec["counterbore_dia_mm"] / 2, spec["counterbore_depth_mm"]))
    spec.update(length_mm=length, mounting_holes=count, end_offset_mm=end, mount_points=points,
                datums={"rail": "+Z along the rail from its datum end; base on Y = 0, centred in X; "
                                "mounting face +Y",
                        "holes": f"{count} counterbored M3 clearance holes on X = 0, {pitch:g} apart "
                                 f"from Z = {end:g}; each mount_points origin is a counterbore floor "
                                 f"(Y = {seat:g}), where a screw head seats, axis +Y",
                        "carriage": "a carriage placed with the rail's origin and direction, moved "
                                    "along +Z, rides it: a slider joint on +Z"})
    _density(spec, volume, spec["mass_kg_per_m"] * length / 1000.0)
    return body, {}


def carriage(part, spec, options):
    """Carriage in the rail's frame: centred on Z = 0, from Y = H1 to Y = H, channel over the rail."""

    _unused(options, "carriage")
    import CadexCatalog
    rail_row = CadexCatalog.part_spec(spec["rail"])
    w, l = spec["width_mm"], spec["length_mm"]
    top, low = spec["assembly_height_mm"], spec["clearance_mm"]
    block = part.box(w, top - low, l, origin=(-w / 2.0, low, -l / 2.0))
    channel_w = rail_row["width_mm"] + 0.6
    channel_h = rail_row["height_mm"] + 0.3 - low
    channel = part.box(channel_w, channel_h, l + 2.0, origin=(-channel_w / 2.0, low - 0.01, -l / 2.0 - 1.0))
    # A tapped hole is an open bore at the thread's nominal diameter, as a
    # catalog part's always is (ADR-660): a screw that reaches it is in its
    # thread and shares no volume with the block. HIWIN's thread depth is
    # 3.5 mm on MGN12 and 3 on MGN9, what the block over the rail allows.
    radius = _thread_dia(spec["thread"]) / 2.0
    depth = min(3.5, top - rail_row["height_mm"] - 0.5)
    centres = [(sx * spec["hole_spacing_width_mm"] / 2.0, sz * spec["hole_spacing_length_mm"] / 2.0)
               for sx in (-1, 1) for sz in (-1, 1)]
    holes = [part.cylinder(radius, depth + 1.0, origin=(x, top - depth, z), direction=(0.0, 1.0, 0.0))
             for x, z in centres]
    body = part.cut(block, [channel, *holes])
    volume = w * (top - low) * l - channel_w * channel_h * l - 4.0 * _cyl(radius, depth)
    spec.update(datums={"carriage": "the rail's frame: centred on Z = 0, mounting face at Y = "
                                    f"{top:g}, four {spec['thread']} holes {depth:g} deep on "
                                    f"{spec['hole_spacing_width_mm']:g} (X) x "
                                    f"{spec['hole_spacing_length_mm']:g} (Z); each mount_points "
                                    "origin is a hole's mouth, axis +Y"},
                mount_face_y_mm=top, mount_thread=spec["thread"], thread_depth_mm=depth,
                mount_points=[_hole((x, top, z), (0.0, 1.0, 0.0), thread=spec["thread"])
                              for x, z in centres])
    _density(spec, volume, spec["mass_kg"])
    return body, {}


def _gt2_pitch_radius(spec) -> float:
    return spec["teeth"] * spec["pitch_mm"] / math.pi / 2.0


def pulley(part, spec, options):
    """Pulley on +Z: hub from Z = 0, then flange, belt band, flange; bore through."""

    _unused(options, "pulley")
    r_pitch = _gt2_pitch_radius(spec)
    r_band = r_pitch - 0.254
    flange_t = 1.0
    hub = spec["hub_length_mm"]
    band = spec["belt_width_mm"] + 0.8
    solids, volume, z = [], 0.0, 0.0
    if hub > 0.0 and spec["hub_dia_mm"] > 0.0:
        solids.append(part.cylinder(spec["hub_dia_mm"] / 2.0, hub))
        volume += _cyl(spec["hub_dia_mm"] / 2.0, hub)
        z = hub
    for radius, height in ((spec["flange_dia_mm"] / 2.0, flange_t), (r_band, band),
                           (spec["flange_dia_mm"] / 2.0, flange_t)):
        solids.append(part.cylinder(radius, height, origin=(0.0, 0.0, z)))
        volume += _cyl(radius, height)
        z += height
    bore = part.cylinder(spec["bore_mm"] / 2.0, z + 2.0, origin=(0.0, 0.0, -1.0))
    body = part.cut(part.fuse(solids), bore)
    volume -= _cyl(spec["bore_mm"] / 2.0, z)
    belt_z = (hub if hub > 0.0 and spec["hub_dia_mm"] > 0.0 else 0.0) + flange_t + band / 2.0
    spec.update(pitch_radius_mm=r_pitch, pitch_dia_mm=2.0 * r_pitch, outside_dia_mm=2.0 * r_band,
                belt_mm_per_degree=spec["teeth"] * spec["pitch_mm"] / 360.0,
                belt_centre_z_mm=belt_z, length_mm=z,
                # The bore is the pulley's one axis (ADR-660): a drive's
                # shaft on it, or an axle screw through an idler.
                mount_points=[_hole((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), hole_dia=spec["bore_mm"])],
                datums={"pulley": "+Z along the shaft, base face (hub end) on Z = 0; the belt runs "
                                  f"centred on Z = {belt_z:g} at the pitch radius {r_pitch:.4g}; "
                                  "the bore is its mount_points axis"},
                drive_note=("A belt carrying a carriage is assembly.joint('rack_pinion', "
                            "pitch_radius_mm=spec['pitch_radius_mm']); an n-joint belt (CoreXY) "
                            "is assembly.coupling with spec['belt_mm_per_degree']."))
    _density(spec, volume, None)
    return body, {}


def belt(part, spec, options):
    """Closed belt in the XY plane round two equal pitch circles at X = 0 and X = span."""

    _unused(options, "belt", ("span", "pitch_radius"))
    span = _need(options, "span", "belt")
    radius = _need(options, "pitch_radius", "belt")
    inner = radius - spec["pitch_line_offset_mm"]
    outer = inner + spec["thickness_mm"]
    width = spec["width_mm"]

    def stadium(r):
        return part.fuse([part.cylinder(r, width), part.cylinder(r, width, origin=(span, 0.0, 0.0)),
                          part.box(span, 2.0 * r, width, origin=(0.0, -r, 0.0))])

    hole = part.fuse([part.cylinder(inner, width + 2.0, origin=(0.0, 0.0, -1.0)),
                      part.cylinder(inner, width + 2.0, origin=(span, 0.0, -1.0)),
                      part.box(span, 2.0 * inner, width + 2.0, origin=(0.0, -inner, -1.0))])
    body = part.cut(stadium(outer), hole)
    length = 2.0 * span + 2.0 * math.pi * radius
    volume = (2.0 * span * (outer - inner) + math.pi * (outer ** 2 - inner ** 2)) * width
    spec.update(span_mm=span, pitch_radius_mm=radius, pitch_length_mm=length,
                teeth=length / spec["pitch_mm"],
                datums={"belt": "in the XY plane, width along +Z from Z = 0, round pitch circles "
                                f"centred at X = 0 and X = {span:g}"})
    _density(spec, volume, None)
    return body, {}


def screw(part, spec, options):
    """Screw shaft on +Z from Z = 0 to length; threads not modelled."""

    _unused(options, "screw", ("length",))
    length = _need(options, "length", "screw")
    r = spec["nominal_dia_mm"] / 2.0
    body = part.cylinder(r, length)
    spec.update(length_mm=length, thread_pitch_mm=spec["lead_mm"],
                travel_per_degree_mm=spec["lead_mm"] / 360.0,
                datums={"screw": "+Z along the screw axis, Z = 0 at its datum end"},
                drive_note=("assembly.joint('screw', nut_connector, screw_connector, "
                            "thread_pitch_mm=spec['lead_mm']) with the nut on a slider and the "
                            "screw on a revolute, both coaxial."))
    _density(spec, _cyl(r, length), None)
    return body, {}


def screw_nut(part, spec, options):
    """Nut on +Z: flange from Z = 0, body after it, bore the screw's diameter."""

    _unused(options, "screw_nut")
    import CadexCatalog
    bore = CadexCatalog.part_spec(spec["screw"])["nominal_dia_mm"]
    t, length = spec["flange_thickness_mm"], spec["body_length_mm"]
    flange = part.cylinder(spec["flange_dia_mm"] / 2.0, t)
    volume = _cyl(spec["flange_dia_mm"] / 2.0, t)
    if spec["flat_width_mm"] > 0.0:
        keep = part.box(spec["flange_dia_mm"] + 2.0, spec["flat_width_mm"], t + 2.0,
                        origin=(-spec["flange_dia_mm"] / 2.0 - 1.0, -spec["flat_width_mm"] / 2.0, -1.0))
        flange = part.common([flange, keep])
        volume *= min(1.0, spec["flat_width_mm"] / spec["flange_dia_mm"] * 1.15)
    nut = part.fuse([flange, part.cylinder(spec["body_dia_mm"] / 2.0, length)])
    volume += _cyl(spec["body_dia_mm"] / 2.0, length - t)
    holes = [part.cylinder(bore / 2.0, length + 2.0, origin=(0.0, 0.0, -1.0))]
    count, r = int(spec["bolt_holes"]), spec["bolt_circle_mm"] / 2.0
    if spec["flat_width_mm"] > 0.0 and count % 2 == 0:
        # A flatted flange (DIN 69051 form B) keeps its holes off the flats:
        # half each side of the axis across them, 360 / (count + 2) apart
        # (six at 0 and +-45 degrees, each side).
        step = 2.0 * math.pi / (count + 2)
        side = [(k - (count // 2 - 1) / 2.0) * step for k in range(count // 2)]
        angles = side + [math.pi + a for a in side]
    else:
        angles = [2.0 * math.pi * index / count + math.pi / 4.0 for index in range(count)]
    centres = [(r * math.cos(a), r * math.sin(a)) for a in angles]
    for x, y in centres:
        holes.append(part.cylinder(spec["bolt_hole_dia_mm"] / 2.0, t + 2.0, origin=(x, y, -1.0)))
    body = part.cut(nut, holes)
    volume -= _cyl(bore / 2.0, length) + len(centres) * _cyl(spec["bolt_hole_dia_mm"] / 2.0, t)
    spec.update(bore_mm=bore,
                mount_points=[_hole((x, y, 0.0), (0.0, 0.0, -1.0), hole_dia=spec["bolt_hole_dia_mm"])
                              for x, y in centres],
                datums={"nut": "+Z along the screw axis; flange face on Z = 0, body towards +Z",
                        "holes": f"{len(centres)} {spec['bolt_hole_dia_mm']:g} mm clearance holes "
                                 f"through the flange on a {spec['bolt_circle_mm']:g} circle; each "
                                 "mount_points origin is on the Z = 0 face, axis -Z (a screw head "
                                 "there, its shank through the flange along +Z)"})
    _density(spec, volume, None)
    return body, {}


def motor_face(part, spec, options):
    """Stepper: front face on Z = 0, shaft and pilot along +Z, case to Z = -length."""

    _unused(options, "motor_face")
    f, length = spec["frame_mm"], spec["body_length_mm"]
    case = part.box(f, f, length, origin=(-f / 2.0, -f / 2.0, -length))
    pilot = part.cylinder(spec["pilot_dia_mm"] / 2.0, spec["pilot_height_mm"])
    shaft = part.cylinder(spec["shaft_dia_mm"] / 2.0, spec["shaft_length_mm"])
    # Tapped holes are open bores at the thread's nominal diameter (ADR-660).
    radius = _thread_dia(spec["thread"]) / 2.0
    depth = spec["thread_depth_mm"]
    s = spec["hole_spacing_mm"] / 2.0
    centres = [(sx * s, sy * s) for sx in (-1, 1) for sy in (-1, 1)]
    holes = [part.cylinder(radius, depth + 1.0, origin=(x, y, -depth)) for x, y in centres]
    body = part.cut(part.fuse([case, pilot, shaft]), holes)
    volume = f * f * length + _cyl(spec["pilot_dia_mm"] / 2.0, spec["pilot_height_mm"]) \
        + _cyl(spec["shaft_dia_mm"] / 2.0, spec["shaft_length_mm"]) - 4.0 * _cyl(radius, depth)
    spec.update(mount_thread=spec["thread"],
                mount_holes_mm=[[x, y, 0.0] for x, y in centres],
                mount_points=[_hole((x, y, 0.0), (0.0, 0.0, 1.0), thread=spec["thread"])
                              for x, y in centres],
                datums={"motor": "front face on Z = 0, shaft along +Z, case to Z = "
                                 f"{-length:g}; four {spec['thread']} holes {depth:g} deep on a "
                                 f"{spec['hole_spacing_mm']:g} square, mouths on Z = 0 (mount_points); "
                                 "the shaft is the drive's output axis (+Z through the origin), so a "
                                 "pulley on it is on the output"},
                drive_note=("assembly.actuator(joint, torque_limit_nmm=<well under "
                            f"{spec['holding_torque_nmm']:g}>) and assembly.joint_dynamics(joint, "
                            f"armature_kgmm2={spec['rotor_inertia_kgmm2']:g}): a coupled motor "
                            "needs its rotor inertia (ADR-642)."))
    _density(spec, volume, spec["mass_kg"])
    return body, {}


def profile(part, spec, options):
    """Extrusion along +Z from Z = 0, section centred on the axis (width X, height Y), T-slots."""

    _unused(options, "profile", ("length",))
    length = _need(options, "length", "profile")
    w, h = spec["width_mm"], spec["height_mm"]
    o, d, iw, lip, wall = (spec[k] for k in ("slot_opening_mm", "slot_depth_mm", "slot_inner_width_mm",
                                             "lip_mm", "slot_wall_mm"))
    bottom = iw / 2.0 - (d - lip - wall)
    if bottom <= 0.0:
        raise PartBuildError("the slot's 45-degree undercut closes before its depth")
    body = part.box(w, h, length, origin=(-w / 2.0, -h / 2.0, 0.0))
    module = 20.0
    centres_x = [-w / 2.0 + module / 2.0 + module * i for i in range(int(round(w / module)))]
    centres_y = [-h / 2.0 + module / 2.0 + module * i for i in range(int(round(h / module)))]
    # The B-type slot as (across, depth in from the face) (ADR-661): the
    # opening through the lip, the undercut's straight wall, then 45-degree
    # flanks down to the bottom -- the flanks keep the diagonal webs that
    # tie the corners to the core, which a rectangular undercut this wide
    # would cut through.
    outline = [(-o / 2.0, -0.02), (o / 2.0, -0.02), (o / 2.0, lip), (iw / 2.0, lip),
               (iw / 2.0, lip + wall), (bottom, d), (-bottom, d), (-iw / 2.0, lip + wall),
               (-iw / 2.0, lip), (-o / 2.0, lip)]
    slot_area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1])) / 2.0
    faces = [("+y", (0.0, 1.0), (1.0, 0.0), h / 2.0, centres_x),
             ("-y", (0.0, -1.0), (1.0, 0.0), h / 2.0, centres_x),
             ("+x", (1.0, 0.0), (0.0, 1.0), w / 2.0, centres_y),
             ("-x", (-1.0, 0.0), (0.0, 1.0), w / 2.0, centres_y)]
    cuts, removed, datums = [], 0.0, []
    for name, n, t, edge, centres in faces:
        for index, c in enumerate(centres):
            def at(u, s, z):
                return (n[0] * (edge - s) + t[0] * (c + u), n[1] * (edge - s) + t[1] * (c + u), z)
            wire = part.wire([at(u, s, -1.0) for u, s in outline], closed=True)
            cuts.append(part.extrude(part.face(wire), (0.0, 0.0, length + 2.0)))
            removed += abs(slot_area)
            datums.append({"face": name, "index": index, "origin": list(at(0.0, lip, 0.0)),
                           "normal": [n[0], n[1], 0.0]})
    for x in centres_x:
        for y in centres_y:
            cuts.append(part.cylinder(spec["bore_dia_mm"] / 2.0, length + 2.0, origin=(x, y, -1.0)))
            removed += math.pi * (spec["bore_dia_mm"] / 2.0) ** 2
    body = part.cut(body, cuts)
    volume = (w * h - removed) * length
    spec.update(length_mm=length,
                slot_centres_mm={"x": centres_x, "y": centres_y},
                slot_datums=datums,
                datums={"profile": "+Z along the profile from Z = 0; section centred on the axis, "
                                   f"{w:g} along X and {h:g} along Y; slots at the 20 mm module, "
                                   f"end bores tapped {spec['tap']}",
                        "slot": "each slot's datum (slot_datums: face '+x', '-x', '+y' or '-y', its "
                                "index along that face, origin at Z = 0, outward normal) is the "
                                f"underside of its lip ({lip:g} mm in from the face) on the slot's "
                                "centreline; .slot(face, along, index) places a T-nut there: "
                                "lib.part('2020-tnut-m5', **beam.slot('+y', 40.0))"})
    _density(spec, volume, spec["mass_kg_per_m"] * length / 1000.0)
    return body, {}


def slot_hardware(part, spec, options):
    """A T-nut (clamp face on Z = 0, thread along +Z) or an L corner bracket (corner at the origin)."""

    _unused(options, "slot_hardware")
    l, w, h = spec["length_mm"], spec["width_mm"], spec["height_mm"]
    if spec["kind"] == "tnut":
        # The slide-in nut's section (ADR-661): a neck that enters the slot
        # opening above the clamp face, the body under the lip, its lower
        # edges chamfered at 45 degrees to clear the undercut's flanks. Its
        # thread is the tap drill, so a screw in it cuts a thread's volume.
        nw, nh, c = spec["neck_width_mm"], spec["neck_height_mm"], spec["chamfer_mm"]
        section = [(-nw / 2.0, nh), (nw / 2.0, nh), (nw / 2.0, 0.0), (w / 2.0, 0.0),
                   (w / 2.0, -(h - c)), (w / 2.0 - c, -h), (-(w / 2.0 - c), -h),
                   (-w / 2.0, -(h - c)), (-w / 2.0, 0.0), (-nw / 2.0, 0.0)]
        wire = part.wire([(-l / 2.0, y, z) for y, z in section], closed=True)
        block = part.extrude(part.face(wire), (l, 0.0, 0.0))
        r = spec["hole_dia_mm"] / 2.0
        body = part.cut(block, part.cylinder(r, h + nh + 2.0, origin=(0.0, 0.0, -h - 1.0)))
        volume = (nw * nh + w * h - c * c) * l - _cyl(r, h + nh)
        datum = ("clamp face (against the underside of the slot's lip) on Z = 0, the neck up to Z = "
                 f"{nh:g} into the opening, the body down to Z = {-h:g}; length along X (the slot), "
                 "the screw along +Z out of the slot; place it with a profile's .slot(...)")
        points = [_hole((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), thread=spec["thread"])]
    else:
        t = spec["thickness_mm"]
        legs = part.fuse([part.box(l, w, t, origin=(0.0, -w / 2.0, 0.0)),
                          part.box(t, w, h, origin=(0.0, -w / 2.0, 0.0))])
        r = spec["hole_dia_mm"] / 2.0
        at = l / 2.0 + t / 2.0
        body = part.cut(legs, [part.cylinder(r, t + 2.0, origin=(at, 0.0, -1.0)),
                               part.cylinder(r, t + 2.0, origin=(-1.0, 0.0, at),
                                             direction=(1.0, 0.0, 0.0))])
        volume = (l * w + (h - t) * w) * t - 2.0 * _cyl(r, t)
        datum = ("outer corner at the origin: one leg's outer face on Z = 0 along +X, the other's on "
                 f"X = 0 up +Z, {t:g} thick; one {spec['hole_dia_mm']:g} mm hole in each, {at:g} from "
                 "the corner, its mount_points origin on the leg's inner face (where a screw head seats)")
        points = [_hole((at, 0.0, t), (0.0, 0.0, 1.0), hole_dia=spec["hole_dia_mm"]),
                  _hole((t, 0.0, at), (1.0, 0.0, 0.0), hole_dia=spec["hole_dia_mm"])]
    spec.update(datums={spec["kind"]: datum}, mount_points=points)
    _density(spec, volume, None)
    return body, {}


def cylinder(part, spec, options):
    """Cylinder: rear pin at the origin with its axis along X, rod out along +Z by extension."""

    _unused(options, "cylinder", ("extension",))
    extension = options.get("extension") or 0.0
    if isinstance(extension, bool) or not isinstance(extension, (int, float)) \
            or not 0.0 <= float(extension) <= spec["stroke_mm"]:
        raise PartBuildError(f"extension must be in [0, {spec['stroke_mm']:g}] mm")
    extension = float(extension)
    stroke, dead = spec["stroke_mm"], spec["dead_length_mm"]
    pin = spec["pin_dia_mm"]
    eye_r = pin
    retracted = stroke + dead
    barrel_r = spec["barrel_od_mm"] / 2.0
    barrel_start = 0.5 * eye_r  # overlapping the eye, so barrel and eye are one solid
    barrel_length = stroke + 0.5 * dead
    rod_r = spec["rod_mm"] / 2.0
    clevis = spec["clevis_width_mm"]

    def eye(z):
        return part.cylinder(eye_r, clevis, origin=(-clevis / 2.0, 0.0, z), direction=(1.0, 0.0, 0.0))

    def pin_hole(z):
        return part.cylinder(pin / 2.0, clevis + 2.0, origin=(-clevis / 2.0 - 1.0, 0.0, z),
                             direction=(1.0, 0.0, 0.0))

    barrel = part.cut(part.fuse([eye(0.0), part.cylinder(barrel_r, barrel_length, origin=(0.0, 0.0, barrel_start))]),
                      pin_hole(0.0))
    front = retracted + extension
    rod_start = barrel_start + barrel_length - stroke + extension
    rod = part.cut(part.fuse([part.cylinder(rod_r, front - rod_start, origin=(0.0, 0.0, rod_start)), eye(front)]),
                   pin_hole(front))
    body = part.compound([barrel, rod])
    barrel_volume = _cyl(barrel_r, barrel_length) + _cyl(eye_r, clevis)
    rod_volume = _cyl(rod_r, front - rod_start) + _cyl(eye_r, clevis)
    pascal = spec["working_pressure_bar"] * 1.0e5
    area = math.pi * (spec["bore_mm"] / 1000.0) ** 2 / 4.0
    annulus = math.pi * ((spec["bore_mm"] / 1000.0) ** 2 - (spec["rod_mm"] / 1000.0) ** 2) / 4.0
    spec.update(extension_mm=extension, retracted_centres_mm=retracted,
                extended_centres_mm=retracted + stroke,
                mount_centres_mm=[[0.0, 0.0, 0.0], [0.0, 0.0, front]],
                extend_force_n=pascal * area, retract_force_n=pascal * annulus,
                datums={"cylinder": "rear pin centre at the origin, pin axes along X, the rod "
                                    f"extending along +Z; the rod pin at Z = {front:g}"},
                drive_note=("Barrel and rod are .members['barrel'] and .members['rod']: a slider "
                            "joint on +Z between them, a revolute at each pin, and "
                            "assembly.actuator(slider, kind='cylinder', "
                            f"bore_mm={spec['bore_mm']:g}, rod_mm={spec['rod_mm']:g}, "
                            f"pressure_bar={spec['working_pressure_bar']:g}, ...)."))
    _density(spec, barrel_volume + rod_volume, spec["mass_kg"])
    return body, {"barrel": barrel, "rod": rod}


def spindle(part, spec, options):
    """Spindle: collet nose tip at the origin, body up +Z, so the tool points -Z."""

    _unused(options, "spindle")
    nose_r, nose = spec["nose_dia_mm"] / 2.0, spec["nose_length_mm"]
    body = part.fuse([part.cone(nose_r * 0.8, nose_r, nose),
                      part.cylinder(spec["body_dia_mm"] / 2.0, spec["body_length_mm"], origin=(0.0, 0.0, nose))])
    volume = _cyl(nose_r, nose) + _cyl(spec["body_dia_mm"] / 2.0, spec["body_length_mm"])
    spec.update(clamp_dia_mm=spec["body_dia_mm"],
                tool_point_mm=[0.0, 0.0, 0.0], tool_axis=[0.0, 0.0, -1.0],
                clamp_from_mm=nose, clamp_to_mm=nose + spec["body_length_mm"],
                datums={"spindle": "collet nose at the origin, body up +Z; the cutter points -Z "
                                   "(assembly.tool(component, origin_mm=[0, 0, -stick_out], axis=[0, 0, -1]))",
                        "clamp": f"held round its {spec['body_dia_mm']:g} mm body between Z = {nose:g} "
                                 f"and {nose + spec['body_length_mm']:g} by a clamp (a printed or "
                                 "bought ring that touches it and encloses its axis there); it has "
                                 "no screw holes, and its axis is the drive's output"})
    _density(spec, volume, spec["mass_kg"])
    return body, {}


def caster(part, spec, options):
    """Swivel caster: top plate face at the origin, +Z down to the floor; yoke and wheel members."""

    _unused(options, "caster")
    pl, pw, pt = spec["plate_length_mm"], spec["plate_width_mm"], spec["plate_thickness_mm"]
    r, width = spec["wheel_dia_mm"] / 2.0, spec["wheel_width_mm"]
    height = spec["overall_height_mm"]
    axle_z = height - r
    offset = spec["swivel_offset_mm"]
    plate = part.box(pl, pw, pt, origin=(-pl / 2.0, -pw / 2.0, 0.0))
    centres = [(sx * spec["hole_spacing_length_mm"] / 2.0, sy * spec["hole_spacing_width_mm"] / 2.0)
               for sx in (-1, 1) for sy in (-1, 1)]
    holes = [part.cylinder(spec["hole_dia_mm"] / 2.0, pt + 2.0, origin=(x, y, -1.0)) for x, y in centres]
    # The plate's four holes; a screw head seated under the plate (Z = pt)
    # drives its shank up -Z into the chassis (ADR-660).
    spec["mount_points"] = [_hole((x, y, pt), (0.0, 0.0, 1.0), hole_dia=spec["hole_dia_mm"])
                            for x, y in centres]
    spec["mount_member"] = "yoke"
    cheek = 2.5
    yoke = part.fuse([part.cut(plate, holes)] + [
        part.box(offset + r * 0.6, cheek, axle_z - pt + 4.0,
                 origin=(-r * 0.3, side * (width / 2.0 + 1.0) - (cheek if side < 0 else 0.0), pt))
        for side in (-1, 1)])
    wheel = part.cylinder(r, width, origin=(offset, -width / 2.0, axle_z), direction=(0.0, 1.0, 0.0))
    body = part.compound([yoke, wheel])
    volume_wheel = _cyl(r, width)
    volume_yoke = pl * pw * pt + 2.0 * (offset + r * 0.6) * cheek * (axle_z - pt + 4.0)
    spec.update(axle_mm=[offset, 0.0, axle_z], swivel_axis=[0.0, 0.0, 1.0],
                datums={"caster": "top-plate face at the origin, +Z down to the floor; swivel about "
                                  f"Z, the axle along Y at X = {offset:g} (trailing), Z = {axle_z:g}"},
                drive_note=("A swivel caster is .members['yoke'] on a revolute about Z and "
                            ".members['wheel'] on a revolute about Y at spec['axle_mm']."))
    _density(spec, volume_wheel + volume_yoke, spec["mass_kg"])
    return body, {"yoke": yoke, "wheel": wheel}


def wheel_hub(part, spec, options):
    """Wheel and tyre on +Z: the hub from Z = 0, the tyre centred on the hub's middle."""

    _unused(options, "wheel_hub")
    ro, width = spec["outer_dia_mm"] / 2.0, spec["section_width_mm"]
    rim = spec["rim_dia_mm"] / 2.0
    hub_l = spec["hub_length_mm"]
    mid = hub_l / 2.0
    shoulder = min((ro - rim) * 0.45, width * 0.45)
    tyre_core = part.cylinder(ro - shoulder, width, origin=(0.0, 0.0, mid - width / 2.0))
    tread = part.cylinder(ro, width - 2.0 * shoulder, origin=(0.0, 0.0, mid - width / 2.0 + shoulder))
    rings = [part.torus(ro - shoulder, shoulder, center=(0.0, 0.0, z))
             for z in (mid - width / 2.0 + shoulder, mid + width / 2.0 - shoulder)]
    tyre = part.cut(part.fuse([tyre_core, tread, *rings]),
                    part.cylinder(rim, width + 2.0, origin=(0.0, 0.0, mid - width / 2.0 - 1.0)))
    wheel = part.cut(part.fuse([part.cylinder(rim, width * 0.8, origin=(0.0, 0.0, mid - width * 0.4)),
                                part.cylinder(spec["hub_dia_mm"] / 2.0, hub_l)]),
                     part.cylinder(spec["bore_mm"] / 2.0, hub_l + 2.0, origin=(0.0, 0.0, -1.0)))
    body = part.compound([wheel, tyre])
    volume = _cyl(ro, width) - _cyl(rim, width) + _cyl(rim, width * 0.8) + _cyl(spec["hub_dia_mm"] / 2.0, hub_l)
    spec.update(rolling_radius_mm=ro, axle_centre_z_mm=mid,
                datums={"wheel": f"axle along +Z, hub from Z = 0 to {hub_l:g}, the tyre centred on "
                                 f"Z = {mid:g}; bore {spec['bore_mm']:g}"})
    _density(spec, volume, spec["mass_kg"])
    return body, {"rim": wheel, "tyre": tyre}


def spring(part, spec, options):
    """Compression spring on +Z from Z = 0 at free length, as a tube."""

    _unused(options, "spring")
    d, od, free = spec["wire_dia_mm"], spec["outer_dia_mm"], spec["free_length_mm"]
    mean = od - d
    rate = spec["shear_modulus_mpa"] * d ** 4 / (8.0 * mean ** 3 * spec["active_coils"])
    solid = spec["total_coils"] * d
    body = part.cut(part.cylinder(od / 2.0, free),
                    part.cylinder(od / 2.0 - d, free + 2.0, origin=(0.0, 0.0, -1.0)))
    wire_volume = math.pi * mean * spec["total_coils"] * math.pi * d * d / 4.0
    tube = _cyl(od / 2.0, free) - _cyl(od / 2.0 - d, free)
    spec.update(rate_n_per_mm=rate, solid_length_mm=solid, max_deflection_mm=free - solid,
                inner_dia_mm=od - 2.0 * d, mean_dia_mm=mean,
                datums={"spring": "+Z along the spring axis, seated on Z = 0 at free length"},
                drive_note=("A sprung slider is assembly.joint_dynamics(slider, ...) with "
                            "stiffness_n_per_mm=spec['rate_n_per_mm']."))
    # The tube's density is the wire's mass spread over the tube.
    spec["density_kg_m3"] = spec["density_kg_m3"] * wire_volume / tube
    spec["modelled_volume_mm3"] = tube
    return body, {}


BUILDERS: Mapping[str, Callable[..., tuple[Any, dict[str, Any]]]] = {
    "rail": rail, "carriage": carriage, "pulley": pulley, "belt": belt, "screw": screw,
    "screw_nut": screw_nut, "motor_face": motor_face, "profile": profile,
    "slot_hardware": slot_hardware, "cylinder": cylinder, "spindle": spindle,
    "caster": caster, "wheel_hub": wheel_hub, "spring": spring,
}


def build(part, spec: dict[str, Any], options: Mapping[str, Any]):
    """The canonical body, its members and the spec it adds, for one row's interface."""

    return BUILDERS[str(spec["interface"])](part, spec, dict(options))
