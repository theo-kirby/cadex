# SPDX-License-Identifier: LGPL-2.1-or-later

"""The joint a terminal implies: one revolved outline (ADR-063, ADR-064).

The geometry behind ``part.solder``.  ``part.cable`` and ``part.bundle``
sweep a conductor that stops flush on a face or in a bore, and nothing joins
it to the board: a wire that ends in mid-air is the last thing between the
harness operations and a model that looks like the object.

**Why the joint cannot be composed in the script.**  Everything a joint needs
— where the bore starts and ends, how wide it is, which way the lead leaves —
is known only *after* a terminal resolves, and terminals resolve in the
worker (ADR-062).  The script holds a name.  Building the same shape out of
``part.cylinder``/``part.cone``/``part.fuse`` at script level would mean
re-measuring by hand exactly the constants terminals exist to delete.  This is
the ADR-056 argument in a different key: not "the search is too expensive in
the sandbox" but "the numbers are not in the sandbox at all".

Like :mod:`CadexRouting`, :mod:`CadexBundle` and :mod:`CadexTerminals` this
module imports nothing from FreeCAD and touches no kernel object.  It takes a
terminal's ``metrics`` plus four numbers and returns a **profile**: a closed
loop of lines and one arc in the ``(r, z)`` half-plane, plus the frame that
places it.  The worker turns that into a wire, a face and one ``revolve``, and
nothing else.  The derivation rules and the refusals are what wants asserting
headless, and they are all here.

**The shape.**  Let ``a`` be the terminal's axis (unit, pointing out of the
board on the side the lead leaves), ``E`` the face the lead leaves from, and
``X`` the far face the lead ends flush on — a board's depth back along ``-a``,
and equal to ``E`` for a surface pad.  Work in ``(r, z)`` with ``z`` measured
from ``X`` along ``a``, so the entry face is ``z = depth`` and a pad has
``depth = 0``.

The **whole joint** is one solid of revolution.  A through-hole's outline runs
the cap cone under the lead's flush end, out to the pad rim, back in to the
bore, up the plating, out across the entry face, then up the **meniscus** — a
concave arc, tangent to the lead where it arrives — into a short straight
**collar** hugging the lead, and back down the lead's own radius to close.  A
pad is the same loop without the cap and the barrel, and it never touches the
axis.

**The meniscus is a concave arc, not a straight cone** (ADR-064, reversing
ADR-063).  A cone reads as a cone on a render; solder sweeps up from the pad
concavely, flattens as it meets the lead, and runs parallel to the wire for a
short distance before it ends.  That is one circular arc plus one line, and it
costs one refusal: an arc shorter than the annulus it spans would curl under
the board rather than sit on it.  This is still a *shape*, not a process
simulation: there is no wetting angle here and no solder volume budget.

**What the single revolve deletes.**  There is no fuse and no cut, so none of
the kernel hazards ADR-063 documented survive: no coincident faces to refine
away, no cut end-face tangent to a cone, and therefore no overshoot constant.
The knife edge goes too — a cone tapering to exactly the lead radius has zero
wall thickness at its tip, while the collar's wall is ``c - w`` all the way
up.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

__all__ = [
    "SolderError",
    "joint_volume",
    "lead_run_mm",
    "solder_specs",
]

#: The cap's height, as a fraction of the meniscus'.  Derived rather than
#: exposed: a joint has enough knobs.
_CAP_FRACTION = 0.5

#: The collar's height, as a fraction of the meniscus'.  The straight sleeve
#: of solder that runs parallel to the wire before the joint ends.
_COLLAR_FRACTION = 0.5

#: How far the collar stands off the lead, as a fraction of the lead's radius.
#: It used to be 0.10 — a sleeve 1.1x the wire — which is also the radius the
#: crown rounds over on, and a 0.025 mm round-over on a 0.5 mm lead reads as a
#: sharp ring rather than as solder (ADR-114). A quarter of the lead is still
#: a sleeve and not a blob, and it is bounded below by the annulus fraction on
#: a tight pad exactly as before.
_COLLAR_LEAD_FRACTION = 0.25

#: ...and as a fraction of the annulus between lead and pad, which is what
#: bounds it on a tight pad.  Taking the smaller of the two guarantees
#: ``w < c < q`` on every joint that builds at all, so the collar needs no
#: clamp and no refusal of its own.
_COLLAR_ANNULUS_FRACTION = 0.25

#: The narrowest annulus the meniscus arc can span.  Below it the arc's three
#: points collapse into one and the kernel throws; the existing ``pad > lead``
#: refusal is strict-greater only, so this is the floor that makes it mean
#: something.
_ARC_FLOOR_MM = 1.0e-6

#: Below this a direction has no direction.
_TINY = 1.0e-12


class SolderError(ValueError):
    """A joint that could not be built, with the reason named.

    ``reason`` is one of ``"metrics"``, ``"gauge"``, ``"bore"``, ``"pad"`` or
    ``"fillet"``; the host maps it to a model-facing correction that says what
    to change, the same contract :class:`CadexRouting.RoutingError` and
    :class:`CadexBundle.BundleError` have.
    """

    def __init__(
        self, message: str, *, reason: str, observed: Mapping[str, Any] | None = None
    ) -> None:
        self.reason = str(reason)
        self.observed = dict(observed or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# small vector arithmetic, on plain tuples


def _finite(value: Any, *, what: str, reason: str = "metrics") -> float:
    if isinstance(value, bool):
        raise SolderError(f"{what} must be a finite number; received {value!r}", reason=reason)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SolderError(
            f"{what} must be a finite number; received {value!r}", reason=reason
        ) from exc
    if not math.isfinite(result):
        raise SolderError(f"{what} must be a finite number; received {value!r}", reason=reason)
    return result


def _positive(value: Any, *, what: str, reason: str) -> float:
    result = _finite(value, what=what, reason=reason)
    if result <= 0.0:
        raise SolderError(
            f"{what} must be greater than zero; received {result:g}",
            reason=reason,
            observed={what: result},
        )
    return result


def _triple(value: Any, *, what: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SolderError(f"{what} must be [x, y, z]; received {value!r}", reason="metrics")
    return tuple(_finite(item, what=what) for item in value)  # type: ignore[return-value]


def _unit(vector: Sequence[float], *, what: str) -> tuple[float, float, float]:
    length = math.sqrt(sum(float(item) * float(item) for item in vector))
    if length <= _TINY:
        raise SolderError(
            f"{what} has no direction; received {list(vector)!r}", reason="metrics"
        )
    return (
        float(vector[0]) / length,
        float(vector[1]) / length,
        float(vector[2]) / length,
    )


def _zeroed(value: float) -> float:
    """``-0.0`` normalised to ``0.0``.

    The two terminal forms reach the same physical hole by opposite signs — a
    declared row states the drilling direction and negates it, a selector
    states the leaving direction directly — so one arrives carrying ``-0.0``
    where the other has ``0.0``.  They compare equal and serialise
    differently, and two joints that are the same joint should be the same
    specs.
    """

    return float(value) + 0.0


def _point_list(vector: Sequence[float]) -> list[float]:
    return [_zeroed(vector[0]), _zeroed(vector[1]), _zeroed(vector[2])]


def _pair(radius: float, height: float) -> list[float]:
    """One ``(r, z)`` point of the outline, through the same sign normaliser."""

    return [_zeroed(radius), _zeroed(height)]


def _radial(axis: Sequence[float]) -> tuple[float, float, float]:
    """Where ``r`` points, given where ``z`` does.

    A solid of revolution is rotationally symmetric, so *any* perpendicular
    gives the same shape — but it fixes where the BREP's seam edge lands, and
    the exported BREP is what ``compute_project_digest`` hashes.  So the
    choice has to be a pure function of the axis rather than whatever the
    kernel would have picked: Gram-Schmidt from the world axis least aligned
    with it, ties broken by the lowest index.  That is the rule
    :func:`CadexTerminals._order_frame` already uses, for the same reason.
    """

    seed_axis = min(range(3), key=lambda index: (abs(axis[index]), index))
    seed = [0.0, 0.0, 0.0]
    seed[seed_axis] = 1.0
    along = sum(seed[index] * axis[index] for index in range(3))
    projected = [seed[index] - along * axis[index] for index in range(3)]
    return _unit(projected, what="the terminal's axis")


# ---------------------------------------------------------------------------
# the joint


def _bore_radius(
    metrics: Mapping[str, Any], bore_dia_mm: Any, *, lead: float
) -> float:
    """How wide the plating is, and whether a lead fits down it.

    An explicit ``bore_dia_mm`` always wins.  Otherwise the terminal's own
    measurement is used — which a *declared* row only carries if it stated
    ``hole_dia``, so the one case with no number at all is named rather than
    guessed at.
    """

    if bore_dia_mm is not None:
        bore = _positive(bore_dia_mm, what="bore_dia_mm", reason="bore") / 2.0
    elif metrics.get("radius") is not None:
        bore = _positive(metrics.get("radius"), what="the terminal's bore radius", reason="bore")
    else:
        raise SolderError(
            "this terminal names a hole whose bore was never measured — a "
            "declared layout that stated a depth but no hole_dia — so there is "
            "no barrel to fill with solder. Pass bore_dia_mm, or declare "
            "hole_dia on the layout so every joint on that component takes it",
            reason="bore",
        )
    if bore <= lead:
        raise SolderError(
            f"the bore measures {bore * 2.0:.4g} mm across and the lead "
            f"{lead * 2.0:.4g} mm, so there is no annulus for solder to fill: "
            "the lead already fills the hole",
            reason="bore",
            observed={"bore_dia_mm": bore * 2.0, "gauge_mm": lead * 2.0},
        )
    return bore


def _pad_radius(
    metrics: Mapping[str, Any],
    pad_dia_mm: Any,
    *,
    kind: str,
    lead: float,
    bore: float | None,
) -> float:
    """How far the joint spreads across the face it sits on.

    An explicit ``pad_dia_mm`` always wins.  A hole derives it from the bore —
    twice the bore *diameter*, which is the annular ring a plated through-hole
    footprint carries.  A selected pad derives it from the face's measured
    area, as the diameter of the disc of that area; a *declared* pad has no
    area to take it from, and says so.
    """

    if pad_dia_mm is not None:
        pad = _positive(pad_dia_mm, what="pad_dia_mm", reason="pad") / 2.0
    elif kind == "hole":
        pad = 2.0 * float(bore)
    else:
        area = _finite(metrics.get("area") or 0.0, what="the terminal's pad area")
        if area <= 0.0:
            raise SolderError(
                "this terminal names a declared pad, which carries no measured "
                "area, so the joint has no width to take from it. Pass "
                "pad_dia_mm, or name the pad with a pads= selector so its area "
                "comes off the face",
                reason="pad",
            )
        pad = math.sqrt(area / math.pi)
    if pad <= lead:
        raise SolderError(
            f"the pad measures {pad * 2.0:.4g} mm across and the lead "
            f"{lead * 2.0:.4g} mm, so there is no annulus for a fillet to sit on",
            reason="pad",
            observed={"pad_dia_mm": pad * 2.0, "gauge_mm": lead * 2.0},
        )
    if bore is not None and pad <= bore:
        raise SolderError(
            f"the pad measures {pad * 2.0:.4g} mm across and the hole it rings "
            f"{bore * 2.0:.4g} mm, so the joint would be narrower than the bore "
            "it is meant to close",
            reason="pad",
            observed={"pad_dia_mm": pad * 2.0, "bore_dia_mm": bore * 2.0},
        )
    return pad


def _collar_radius(*, lead: float, pad: float) -> float:
    """Where the meniscus stops climbing and the sleeve begins.

    A tenth of the lead's radius clear of it — the subtle collar, close to the
    old cone's silhouette and merely softened — except on a pad so tight that
    a tenth of the lead would swallow the annulus, where a quarter of the
    annulus is taken instead.  The smaller of the two is always strictly
    between the lead and the pad, so this needs no clamp and refuses nothing.
    """

    return lead + min(
        _COLLAR_LEAD_FRACTION * lead, _COLLAR_ANNULUS_FRACTION * (pad - lead)
    )


def _meniscus_arc(
    *, collar: float, pad: float, fillet: float, z_face: float
) -> dict[str, Any]:
    """The one circular arc: up from the pad rim, tangent to the lead on top.

    Solved rather than fitted.  With ``d = q - c`` spanned and ``H`` climbed,
    the circle tangent to the line ``r = c`` at ``(c, z_face + H)`` and passing
    through ``(q, z_face)`` has radius ``R = (d**2 + H**2) / (2 d)`` and centre
    ``(c + R, z_face + H)``: tangency puts the centre level with the top, and
    the through-point fixes ``R``.  The arc runs from ``theta = pi + phi``
    (the rim) to ``theta = pi`` (the lead), where ``sin phi = H / R``.

    At the default ``H == d`` this is ``R == d`` and ``phi == 90 degrees``: an
    exact quarter circle, tangent to the board at the rim *and* to the lead at
    the top — the softest fillet that exists.  Shorter than that and ``phi``
    passes a right angle, which is the arc dipping below the board and curling
    under it; that is the one thing this shape refuses.
    """

    span = pad - collar
    radius = (span * span + fillet * fillet) / (2.0 * span)
    centre_r = collar + radius
    centre_z = z_face + fillet
    phi = math.atan2(fillet, radius - span)

    def at(theta: float) -> list[float]:
        return _pair(
            centre_r + radius * math.cos(theta), centre_z + radius * math.sin(theta)
        )

    start_angle = math.pi + phi
    end_angle = math.pi
    return {
        "role": "meniscus",
        "kind": "arc",
        # The two ends are written down rather than evaluated: they are shared
        # vertices with the lines either side, and `centre_r + R cos(pi)` is
        # only `collar` to within a rounding, which would leave the wire to be
        # sewn instead of merely ordered.
        "start": _pair(pad, z_face),
        "through": at(math.pi + 0.5 * phi),
        "end": _pair(collar, z_face + fillet),
        "centre": _pair(centre_r, centre_z),
        "radius": _zeroed(radius),
        "start_angle": _zeroed(start_angle),
        "end_angle": _zeroed(end_angle),
    }


def _crown_arc(*, collar: float, lead: float, z_top: float) -> dict[str, Any]:
    """The round-over that closes the joint onto the lead (ADR-114).

    The collar used to stop dead at ``z_top`` and cross to the lead along a
    flat annulus — a washer of solder, ``collar - lead`` wide, presenting a
    hard ring to every render and a square edge for a wire leaving at any
    angle to poke through. This turns that crossing into a quarter circle
    centred on ``(lead, z_top)``: tangent to the collar's own wall where it
    leaves, meeting the lead square at the top.

    It carries no new knob. The radius *is* the collar's stand-off, so a
    joint on a tight pad — where the annulus fraction bounds that stand-off —
    gets a proportionally smaller crown rather than a refusal, and the whole
    shape still scales with the lead.
    """

    radius = collar - lead

    def at(theta: float) -> list[float]:
        return _pair(lead + radius * math.cos(theta), z_top + radius * math.sin(theta))

    return {
        "role": "crown",
        "kind": "arc",
        # Written down rather than evaluated, for the reason the meniscus arc
        # states: these are shared vertices with the segments either side.
        "start": _pair(collar, z_top),
        "through": at(0.25 * math.pi),
        "end": _pair(lead, z_top + radius),
        "centre": _pair(lead, z_top),
        "radius": _zeroed(radius),
        "start_angle": 0.0,
        "end_angle": _zeroed(0.5 * math.pi),
    }


def _line(role: str, start: Sequence[float], end: Sequence[float]) -> dict[str, Any]:
    return {"role": role, "kind": "line", "start": list(start), "end": list(end)}


def solder_specs(
    metrics: Mapping[str, Any],
    *,
    gauge_mm: float,
    pad_dia_mm: Any = None,
    fillet_mm: Any = None,
    bore_dia_mm: Any = None,
) -> dict[str, Any]:
    """One joint, as the closed outline it is revolved from.

    ``metrics`` is what a resolved terminal carries (ADR-062): the kind, the
    outward axis, the bore radius and depth, and the two face points.  The
    four numbers are the lead's gauge and three overrides that default off the
    geometry.  Everything returned is in millimetres, in the placed frame the
    terminal already resolved into.

    The result carries ``"profile"`` — a closed loop of segments in the
    ``(r, z)`` half-plane, each ``{"role", "kind", "start", "end"}`` and the
    one arc additionally ``"through"`` — plus ``"origin"``, ``"direction"``
    and ``"radial"``, which are where that half-plane sits in space.  The
    ``role`` on each segment is diagnostic; the worker builds by ``kind``.
    """

    if not isinstance(metrics, Mapping) or not metrics:
        raise SolderError(
            "a joint is built from a terminal's measured geometry, and this "
            "port carried none. A literal (point, direction) pair has no "
            "radius, no depth and no face, so there is nothing to solder to; "
            "name the attachment with part.terminals or mesh.terminals",
            reason="metrics",
        )
    kind = str(metrics.get("kind") or "")
    if kind not in ("hole", "pad"):
        raise SolderError(
            f"a terminal solders as a hole or a pad; this one reports {kind!r}",
            reason="metrics",
            observed={"kind": kind},
        )

    axis = _unit(
        _triple(metrics.get("axis"), what="the terminal's axis"),
        what="the terminal's axis",
    )
    entry = _triple(metrics.get("entry_point"), what="the terminal's entry_point")
    exit_point = _triple(metrics.get("exit_point"), what="the terminal's exit_point")
    lead = _positive(gauge_mm, what="gauge_mm", reason="gauge") / 2.0

    depth = _finite(metrics.get("depth") or 0.0, what="the terminal's depth")
    bore: float | None = None
    if kind == "hole":
        if depth <= 0.0:
            raise SolderError(
                "this terminal names a hole of no depth, so there is no barrel "
                f"between its two faces to fill; received depth {depth:g} mm",
                reason="metrics",
                observed={"depth_mm": depth},
            )
        bore = _bore_radius(metrics, bore_dia_mm, lead=lead)
    else:
        depth = 0.0
    pad = _pad_radius(metrics, pad_dia_mm, kind=kind, lead=lead, bore=bore)

    collar = _collar_radius(lead=lead, pad=pad)
    span = pad - collar
    if span < _ARC_FLOOR_MM:
        # `pad > lead` is strict-greater only, so a pad a picometre wider than
        # its lead ships today and merely builds a cone that is a cylinder.
        # Under an arc the three points collapse into one, so the floor gets
        # named here rather than arriving as an OCC traceback.
        raise SolderError(
            f"the pad measures {pad * 2.0:.6g} mm across and the lead "
            f"{lead * 2.0:.6g} mm, which leaves {span:.3g} mm for the meniscus "
            f"to sweep across — less than the {_ARC_FLOOR_MM:g} mm floor an arc "
            "needs to be an arc at all",
            reason="pad",
            observed={
                "pad_dia_mm": pad * 2.0,
                "gauge_mm": lead * 2.0,
                "meniscus_span_mm": span,
                "minimum_span_mm": _ARC_FLOOR_MM,
            },
        )

    if fillet_mm is not None:
        fillet = _finite(fillet_mm, what="fillet_mm", reason="fillet")
    else:
        # An exact quarter circle: the meniscus climbs to the collar exactly as
        # far as it sweeps across to it, so the arc is tangent to the board at
        # the pad rim *and* tangent to the lead at the top.
        fillet = span
    if fillet <= 0.0:
        raise SolderError(
            f"fillet_mm must be greater than zero — it is how far the meniscus "
            f"climbs the lead — and this joint has {fillet:g} mm",
            reason="fillet",
            observed={"fillet_mm": fillet},
        )
    if fillet < span:
        raise SolderError(
            f"fillet_mm is {fillet:.4g} mm but the meniscus has {span:.4g} mm of "
            "pad to sweep across, and an arc that spreads further than it climbs "
            "meets the board from underneath — it would undercut the pad rather "
            f"than sit on it. Raise fillet_mm to {span:.4g} mm or more, or narrow "
            f"the joint with pad_dia_mm below {pad * 2.0:.4g} mm",
            reason="fillet",
            observed={
                "fillet_mm": fillet,
                "minimum_fillet_mm": span,
                "pad_dia_mm": pad * 2.0,
                "gauge_mm": lead * 2.0,
            },
        )
    collar_height = _COLLAR_FRACTION * fillet
    cap = _CAP_FRACTION * fillet if kind == "hole" else 0.0

    # z runs from the far face X, so the entry face is at z = depth and a pad
    # sits at z = 0.  The outline is traversed counter-clockwise in (r, z),
    # which is what makes the contour integral in joint_volume positive.
    top = depth + fillet + collar_height
    arc = _meniscus_arc(collar=collar, pad=pad, fillet=fillet, z_face=depth)
    crown = _crown_arc(collar=collar, lead=lead, z_top=top)
    # Where the joint actually ends on the lead, now that it rounds over onto
    # it rather than stopping square across it.
    crest = top + (collar - lead)
    profile: list[dict[str, Any]]
    if kind == "hole":
        profile = [
            _line("cap", _pair(0.0, -cap), _pair(pad, 0.0)),
            _line("cap_rim", _pair(pad, 0.0), _pair(bore, 0.0)),
            _line("bore", _pair(bore, 0.0), _pair(bore, depth)),
            _line("entry_annulus", _pair(bore, depth), _pair(pad, depth)),
            arc,
            _line("collar", _pair(collar, depth + fillet), _pair(collar, top)),
            crown,
            _line("lead", _pair(lead, crest), _pair(lead, 0.0)),
            _line("lead_end", _pair(lead, 0.0), _pair(0.0, 0.0)),
            _line("spine", _pair(0.0, 0.0), _pair(0.0, -cap)),
        ]
    else:
        profile = [
            _line("pad_face", _pair(lead, 0.0), _pair(pad, 0.0)),
            arc,
            _line("collar", _pair(collar, fillet), _pair(collar, top)),
            crown,
            _line("lead", _pair(lead, crest), _pair(lead, 0.0)),
        ]

    return {
        "kind": kind,
        "profile": profile,
        # Where the half-plane sits: the origin is (r, z) = (0, 0), the far
        # face for a hole and the pad's own face for a pad.
        "origin": _point_list(exit_point if kind == "hole" else entry),
        "direction": _point_list(axis),
        "radial": _point_list(_radial(axis)),
        "lead_radius": lead,
        "bore_radius": bore,
        "pad_radius": pad,
        "collar_radius": collar,
        "fillet_height": fillet,
        "collar_height": collar_height,
        "crown_height": _zeroed(collar - lead),
        "cap_height": cap,
        "arc_radius": arc["radius"],
        "depth": depth,
    }


def lead_run_mm(metrics: Mapping[str, Any], gauge_mm: float) -> float:
    """How much straight lead a joint on this terminal would need (ADR-074).

    The meniscus climbs the lead for ``fillet_height``, the collar hugs it for
    ``collar_height`` more and the crown rounds onto it over ``crown_height``,
    so a joint holds the lead straight for their sum above the entry face.  A
    wire that starts turning inside that run meets the joint at an angle and
    clips through one side of it.

    This is what lets ``part.cable`` leave room for a joint **without learning
    whether one exists**: the router floors its stand-off with this number, so
    the wire runs straight far enough that a joint *could* be there.  The two
    operations stay independent, which is the property that makes them
    composable at all.

    Zero when the terminal cannot carry a joint — a literal ``(point,
    direction)`` port with no metrics, or numbers :func:`solder_specs` refuses.
    A run that could never be soldered needs no room reserved for solder, and
    a caller asking this question is not the place to raise about it.
    """

    try:
        specs = solder_specs(metrics, gauge_mm=gauge_mm)
    except SolderError:
        return 0.0
    return (
        float(specs["fillet_height"])
        + float(specs["collar_height"])
        + float(specs["crown_height"])
    )


def _line_moment(start: Sequence[float], end: Sequence[float]) -> float:
    """``integral r**2 dz`` along a straight segment of the outline."""

    r1, z1 = float(start[0]), float(start[1])
    r2, z2 = float(end[0]), float(end[1])
    return (z2 - z1) * (r1 * r1 + r1 * r2 + r2 * r2) / 3.0


def _arc_moment(segment: Mapping[str, Any]) -> float:
    """``integral r**2 dz`` along the meniscus arc, in closed form.

    With ``r = rc + R cos t`` and ``dz = R cos t dt`` the integrand expands to
    three elementary terms, and the antiderivative below is their sum.
    """

    centre_r = float(segment["centre"][0])
    radius = float(segment["radius"])

    def antiderivative(theta: float) -> float:
        sin, cos = math.sin(theta), math.cos(theta)
        return radius * (
            centre_r * centre_r * sin
            + centre_r * radius * theta
            + centre_r * radius * sin * cos
            + radius * radius * sin
            - radius * radius * sin * sin * sin / 3.0
        )

    return antiderivative(float(segment["end_angle"])) - antiderivative(
        float(segment["start_angle"])
    )


def joint_volume(specs: Mapping[str, Any]) -> float:
    """The exact volume of the solid :func:`solder_specs` describes.

    ``V = pi * contour(r**2 dz)`` around the outline itself — Green's theorem
    on the half-section, which is exact for lines and for the one arc alike.
    It integrates the *same* segments the worker builds the face from, so the
    two cannot drift apart; what breaks the circularity is that this is
    asserted against the kernel's own ``Volume`` and, headless, against a fine
    polygonisation of the same loop.

    The lead's bore is the loop's inner boundary rather than a subtraction, so
    "less the lead" needs no separate term, and the plug of solder under the
    lead's flush end is included — which is correct, because the lead ends at
    the far face and there is nothing there to cut around.
    """

    total = 0.0
    for segment in specs["profile"]:
        if segment["kind"] == "arc":
            total += _arc_moment(segment)
        else:
            total += _line_moment(segment["start"], segment["end"])
    return math.pi * total
