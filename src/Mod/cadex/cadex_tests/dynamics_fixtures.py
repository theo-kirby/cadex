# SPDX-License-Identifier: LGPL-2.1-or-later

"""Assemblies built forwards, so the translator can be checked backwards.

Every dynamics fixture here is constructed from *known* joint coordinates:
pick the connector frames and the joint values, then compose the solved
component placements from them. The translator's job is the inverse -- take
the placements and the connector frames and recover the joint coordinates --
so a fixture built this way lets a test assert against a number nothing in
the code under test produced.

That is the difference between the exit criterion and a tautology. A fixture
built at the model's own reference configuration would pass on a model whose
joint axes are entirely wrong; these fixtures put every joint at a non-zero,
non-round coordinate, so recovering it means the axis, the anchor and the
frame composition are all right.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import CadexDynamics as dyn

STEEL = 7850.0
ALUMINIUM = 2700.0


def box_inertial(
    length: float,
    width: float,
    height: float,
    *,
    density: float = STEEL,
    centre: Sequence[float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    """What ``body_inertial`` returns for one box solid, in mm."""

    volume = length * width * height
    reading = {
        "volume_mm3": volume,
        "center_of_mass_mm": list(centre),
        "inertia_mm5_about_com": [
            volume * (width * width + height * height) / 12.0, 0.0, 0.0,
            0.0, volume * (length * length + height * height) / 12.0, 0.0,
            0.0, 0.0, volume * (length * length + width * width) / 12.0,
        ],
    }
    return dyn.body_inertial([reading], density, context="fixture body")


def collision_shape(kind: str, **parameters: Any) -> dict[str, Any]:
    """One ``api.collision`` value, as the worker hands it over.

    The API's own validation is tested against the API; this is the shape
    of the mapping that crosses the seam, so a fixture that drifts from it
    is a test passing against a payload nothing produces.
    """

    offset = parameters.pop("offset", None) or {}
    return {
        "kind": kind,
        "offset": {
            "position": list(offset.get("position", (0.0, 0.0, 0.0))),
            "rotation": list(offset.get("rotation", (0.0, 0.0, 0.0, 1.0))),
        },
        **parameters,
    }


def _prism_mesh(
    polygon: Sequence[Sequence[float]],
    height: float,
    caps: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """A closed, outward-wound prism over one XY polygon.

    ``polygon`` is counter-clockwise seen from +Z; ``caps`` is the polygon's
    triangulation by vertex index, which is supplied rather than derived
    because a fan does the wrong thing on a non-convex outline and the whole
    point of these fixtures is the non-convex one.

    The winding matches what ``tessellate_shape`` produces -- outward -- so
    ``mesh_volume_mm3`` reads a positive volume, which is the precondition
    every convexity measurement rests on.
    """

    count = len(polygon)
    vertices: list[float] = []
    for point in polygon:
        vertices.extend((float(point[0]), float(point[1]), 0.0))
    for point in polygon:
        vertices.extend((float(point[0]), float(point[1]), float(height)))
    triangles: list[int] = []
    for a, b, c in caps:
        triangles.extend((a, c, b))  # bottom cap faces -Z
        triangles.extend((a + count, b + count, c + count))  # top faces +Z
    for index in range(count):
        following = (index + 1) % count
        triangles.extend((index, following, following + count))
        triangles.extend((index, following + count, index + count))
    return {"vertices_mm": vertices, "triangles": triangles}


def box_mesh(
    length: float, width: float, height: float, *, deflection_mm: float = 0.25
) -> dict[str, Any]:
    """A box, tessellated exactly -- so fidelity error is exactly zero."""

    polygon = [
        (-length / 2.0, -width / 2.0),
        (length / 2.0, -width / 2.0),
        (length / 2.0, width / 2.0),
        (-length / 2.0, width / 2.0),
    ]
    mesh = _prism_mesh(polygon, height, [(0, 1, 2), (0, 2, 3)])
    shifted = list(mesh["vertices_mm"])
    for index in range(2, len(shifted), 3):
        shifted[index] -= height / 2.0
    return {
        "deflection_mm": deflection_mm,
        "vertices_mm": shifted,
        "triangles": mesh["triangles"],
    }


def l_bracket_mesh(
    long_arm: float = 60.0,
    thickness: float = 20.0,
    short_arm: float = 60.0,
    height: float = 10.0,
    *,
    deflection_mm: float = 0.25,
) -> dict[str, Any]:
    """The hazard, as geometry: an L whose hull is 40% bigger than it is.

    This is the bracket-with-a-slot of docs/MUJOCO.md hazard 2 in its
    smallest honest form. MuJoCo would collide with the full triangle
    across the inside corner and every contact would look plausible.
    """

    polygon = [
        (0.0, 0.0),
        (long_arm, 0.0),
        (long_arm, thickness),
        (thickness, thickness),
        (thickness, short_arm),
        (0.0, short_arm),
    ]
    mesh = _prism_mesh(polygon, height, [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)])
    return {
        "deflection_mm": deflection_mm,
        "vertices_mm": mesh["vertices_mm"],
        "triangles": mesh["triangles"],
    }


def l_bracket_volume_mm3(
    long_arm: float = 60.0,
    thickness: float = 20.0,
    short_arm: float = 60.0,
    height: float = 10.0,
) -> float:
    return height * (long_arm * thickness + thickness * (short_arm - thickness))


def faceted_cylinder_mesh(
    radius: float, height: float, sides: int, *, deflection_mm: float = 0.25
) -> dict[str, Any]:
    """An inscribed n-gon prism: a cylinder as a tessellator really makes one.

    Convex, so it says nothing about concavity -- what it exercises is the
    *other* measurement, the one that asks whether the mesh is still the
    part. An inscribed polygon always encloses less than the circle it
    approximates, and at a coarse deflection it encloses visibly less.
    """

    polygon = [
        (
            radius * math.cos(2.0 * math.pi * index / sides),
            radius * math.sin(2.0 * math.pi * index / sides),
        )
        for index in range(sides)
    ]
    caps = [(0, index, index + 1) for index in range(1, sides - 1)]
    mesh = _prism_mesh(polygon, height, caps)
    return {
        "deflection_mm": deflection_mm,
        "vertices_mm": mesh["vertices_mm"],
        "triangles": mesh["triangles"],
    }


def frame(
    position: Sequence[float] = (0.0, 0.0, 0.0),
    axis: Sequence[float] = (0.0, 0.0, 1.0),
    angle_degrees: float = 0.0,
) -> list[float]:
    """A connector frame: a rotation about ``axis`` at ``position`` in mm."""

    quaternion = dyn.quaternion_from_axis_angle_wxyz(
        axis, math.radians(angle_degrees)
    )
    return dyn.matrix_from_quaternion_wxyz(quaternion, position)


def joint_motion(kind: str, values: Sequence[float]) -> list[float]:
    """``J(q)`` in the connector frame: what the joint is free to do.

    The one definition the whole construction rests on --
    ``T_parent_child = L_p ∘ J(q) ∘ inv(L_c)``.
    """

    if kind in {"revolute", "screw", "rack_pinion"}:
        return dyn.matrix_from_quaternion_wxyz(
            dyn.quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), values[0])
        )
    if kind == "slider":
        return dyn.matrix_from_rotation_translation(
            [1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 0.0, dyn.length_mm(values[0]))
        )
    if kind == "cylindrical":
        return dyn.matrix_multiply(
            dyn.matrix_from_rotation_translation(
                [1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 0.0, dyn.length_mm(values[0]))
            ),
            dyn.matrix_from_quaternion_wxyz(
                dyn.quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), values[1])
            ),
        )
    if kind == "ball":
        return dyn.matrix_from_quaternion_wxyz(values)
    if kind == "fixed":
        return list(dyn.IDENTITY_MATRIX)
    raise AssertionError(f"no fixture motion for {kind!r}")


def build(
    components: Sequence[Mapping[str, Any]],
    joints: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[float]]]:
    """Compose solved placements from declared joint coordinates.

    ``components`` entries carry ``name``, optional ``grounded``, an
    optional ``world`` placement for roots, and their box size. ``joints``
    entries carry ``name``, ``kind``, ``parent``, ``child``, the two
    connector frames and the joint's ``values``. Joints are walked in order,
    so a parent must be placed before its child -- which is also the order a
    script would naturally declare them in.
    """

    placements: dict[str, list[float]] = {}
    component_records: list[dict[str, Any]] = []
    for component in components:
        name = str(component["name"])
        if component.get("world") is not None or component.get("grounded"):
            placements[name] = list(component.get("world") or dyn.IDENTITY_MATRIX)
        component_records.append(
            {
                "name": name,
                "grounded": bool(component.get("grounded")),
                "flexible": False,
                "inertial": component.get("inertial")
                or box_inertial(*component.get("size", (100.0, 40.0, 20.0))),
                "solved_matrix": None,
                "collision": component.get(
                    "collision", {"shapes": [], "mesh": None}
                ),
            }
        )
    joint_records: list[dict[str, Any]] = []
    for joint in joints:
        parent = str(joint["parent"])
        child = str(joint["child"])
        parent_frame = list(joint["parent_frame"])
        child_frame = list(joint["child_frame"])
        if parent in placements and child not in placements:
            placements[child] = dyn.matrix_multiply(
                placements[parent],
                dyn.matrix_multiply(
                    parent_frame,
                    dyn.matrix_multiply(
                        joint_motion(str(joint["kind"]), list(joint.get("values") or [])),
                        dyn.matrix_inverse(child_frame),
                    ),
                ),
            )
        joint_records.append(
            {
                "name": str(joint["name"]),
                "kind": str(joint["kind"]),
                "suppressed": bool(joint.get("suppressed")),
                "parameters": dict(joint.get("parameters") or {}),
                "length_limits_mm": joint.get("length_limits_mm"),
                "angle_limits_degrees": joint.get("angle_limits_degrees"),
                "connectors": [
                    {"component": parent, "local_matrix": parent_frame},
                    {"component": child, "local_matrix": child_frame},
                ],
            }
        )
    for record in component_records:
        record["solved_matrix"] = placements.get(
            record["name"], list(dyn.IDENTITY_MATRIX)
        )
    return component_records, joint_records, placements


def closing_frame(
    placements: Mapping[str, Sequence[float]],
    parent: str,
    parent_local: Sequence[float],
    child: str,
) -> list[float]:
    """The child-side connector frame that makes a closing joint coincide.

    A loop closure is only meaningful on a consistent assembly: FreeCAD's
    solver produces one, and a fixture has to earn it. Rather than guessing
    a frame and hoping, this composes the one that puts the child's
    connector exactly where the parent's already is.
    """

    return dyn.matrix_multiply(
        dyn.matrix_inverse(placements[child]),
        dyn.matrix_multiply(placements[parent], parent_local),
    )


def closing_joint(
    name: str,
    kind: str,
    parent: str,
    child: str,
    parent_local: Sequence[float],
    placements: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    """One loop-closing joint whose two connector frames coincide."""

    return {
        "name": name,
        "kind": kind,
        "suppressed": False,
        "parameters": {},
        "length_limits_mm": None,
        "angle_limits_degrees": None,
        "connectors": [
            {"component": parent, "local_matrix": list(parent_local)},
            {
                "component": child,
                "local_matrix": closing_frame(placements, parent, parent_local, child),
            },
        ],
    }


def pendulum(*, angle: float = 0.7) -> tuple[list[dict], list[dict], dict]:
    """A grounded base and one arm on a revolute joint, off both axes.

    The joint is neither at the origin nor aligned with the world axes, so a
    translator that dropped the anchor, dropped the rotation, or used the
    parent's frame where it needed the child's would produce a different
    pose.
    """

    return build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {"name": "arm", "size": (300.0, 40.0, 20.0)},
        ],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": frame((40.0, -15.0, 60.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": frame((-120.0, 5.0, 0.0), (0.0, 1.0, 0.0), -35.0),
                "values": [angle],
            }
        ],
    )


def four_bar() -> tuple[list[dict], list[dict], dict]:
    """A planar four-bar: three tree edges and one loop closure.

    Built from a real crank angle so the closure is consistent rather than
    approximately so -- the coupler and rocker positions are computed from
    the loop's own geometry.
    """

    ground_length = 200.0
    crank_length = 80.0
    rocker_length = 120.0
    crank_angle = math.radians(50.0)

    # Solve the four-bar for the coupler/rocker angles at this crank angle.
    pin_a = (0.0, 0.0)
    pin_d = (ground_length, 0.0)
    pin_b = (
        crank_length * math.cos(crank_angle),
        crank_length * math.sin(crank_angle),
    )
    span = math.hypot(pin_d[0] - pin_b[0], pin_d[1] - pin_b[1])
    coupler_length = 220.0
    # Circle intersection: coupler from B, rocker from D.
    base_angle = math.atan2(pin_d[1] - pin_b[1], pin_d[0] - pin_b[0])
    cosine = (coupler_length**2 + span**2 - rocker_length**2) / (
        2.0 * coupler_length * span
    )
    interior = math.acos(max(-1.0, min(1.0, cosine)))
    coupler_angle = base_angle + interior
    pin_c = (
        pin_b[0] + coupler_length * math.cos(coupler_angle),
        pin_b[1] + coupler_length * math.sin(coupler_angle),
    )

    def link(name: str, start, end, *, grounded: bool = False) -> dict:
        return {
            "name": name,
            "grounded": grounded,
            "size": (max(1.0, math.dist(start, end)), 20.0, 10.0),
        }

    components = [
        link("ground", pin_a, pin_d, grounded=True),
        link("crank", pin_a, pin_b),
        link("coupler", pin_b, pin_c),
        link("rocker", pin_d, pin_c),
    ]
    # Each link's own frame has its first pin at the origin and its second
    # pin along +X, so the connector frames are simple and the placements
    # are not.
    joints = [
        {
            "name": "a",
            "kind": "revolute",
            "parent": "ground",
            "child": "crank",
            "parent_frame": frame((pin_a[0], pin_a[1], 0.0)),
            "child_frame": frame((0.0, 0.0, 0.0)),
            "values": [crank_angle],
        },
        {
            "name": "d",
            "kind": "revolute",
            "parent": "ground",
            "child": "rocker",
            "parent_frame": frame((pin_d[0], pin_d[1], 0.0)),
            "child_frame": frame((0.0, 0.0, 0.0)),
            "values": [
                math.atan2(pin_c[1] - pin_d[1], pin_c[0] - pin_d[0])
            ],
        },
        {
            "name": "b",
            "kind": "revolute",
            "parent": "crank",
            "child": "coupler",
            "parent_frame": frame((crank_length, 0.0, 0.0)),
            "child_frame": frame((0.0, 0.0, 0.0)),
            "values": [coupler_angle - crank_angle],
        },
        {
            "name": "c",
            "kind": "revolute",
            "parent": "coupler",
            "child": "rocker",
            "parent_frame": frame((coupler_length, 0.0, 0.0)),
            "child_frame": frame((rocker_length, 0.0, 0.0)),
            "values": [0.0],
        },
    ]
    return build(components, joints)
