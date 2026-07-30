# SPDX-License-Identifier: LGPL-2.1-or-later

"""What ``MjSpec.to_xml()`` actually does, before M5 builds anything on it.

The phase that measures comes before the phase that builds -- M2, M3 and M4
each paid for skipping that once, and this is M5's instalment. Nothing here
imports the export path: every assertion is about ``mujoco`` 3.10.0 and the
spec ``build_model`` already produces, so a failure names MuJoCo rather than
the translator, and the numbers pinned here are what ``export_mjcf`` is later
allowed to verify itself against.

Six findings, each with a test rather than a comment:

1. ``to_xml()`` produces a valid, self-contained file -- collision meshes go
   in as ``<mesh vertex= face=>`` inside ``<asset>``, so an export is one
   file and never an asset directory.
2. It writes about six significant figures, and that is **not free**. Mass
   survives to 1e-16 relative; inertia does not, and lands at 2.4e-6. So
   "matches the in-engine model" is a *tolerance*, and it is measured here
   per mechanism rather than asserted once. There is no precision knob on
   ``MjSpec``.
3. ``explicitinertial`` is load-bearing for export and not merely for the
   compile: turn it off and the ``<inertial>`` element vanishes from the
   file entirely, taking M5's whole differentiator with it silently.
4. Four compiler flags ``build_model`` sets deliberately do **not** appear
   in the emitted XML, because ``to_xml()`` omits anything equal to an MJCF
   default. The reloaded model is unaffected -- but that is a measurement,
   not a guarantee, and it is this file's job to keep re-taking it.
5. A stock load starts in the **wrong pose**: MuJoCo's reference
   configuration is the one where each joint's connector frames coincide,
   which is deliberately not the solved one, and ``to_xml()`` emits no
   keyframe. 61 mm of wrong, on the four-bar.
6. The XML grows with triangle count at about 50 bytes a vertex, so a
   collision mesh at ``MAXIMUM_COLLISION_VERTICES`` costs roughly 11 MB and
   the export needs a byte cap of its own.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")

MODULE_DIR = Path(dyn.__file__).resolve().parent


# ---------------------------------------------------------------------------
# The fixtures, including the variants the plain three do not cover.
# ---------------------------------------------------------------------------


def _servo(**overrides):
    entry = {
        "joint": "hinge",
        "motion_type": "angular",
        "kind": "position",
        "control_deg": "30",
        "stiffness_nmm_per_deg": 4000.0,
        "damping_nmms_per_deg": 120.0,
    }
    entry.update(overrides)
    return entry


def _contact_pendulum():
    """The pendulum with primitive geoms on both bodies."""

    components, joints, placements = fx.pendulum()
    sizes = {"arm": [300.0, 40.0, 20.0], "base": [200.0, 200.0, 20.0]}
    for component in components:
        component["collision"] = {
            "shapes": [
                fx.collision_shape("box", size_mm=sizes[component["name"]])
            ],
            "mesh": None,
        }
    return components, joints, placements


def _mesh_pendulum():
    """The pendulum with a tessellated collision mesh, which lands inline."""

    components, joints, placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [fx.collision_shape("mesh")],
                "mesh": fx.box_mesh(300.0, 40.0, 20.0),
            }
    return components, joints, placements


#: Every fixture the reload diff is taken over, and the arguments that make
#: it the variant it is. Named rather than parametrised over a tuple so a
#: failure says which mechanism moved.
CASES = {
    "pendulum": (fx.pendulum, {}),
    "two_link_arm": (fx.two_link_arm, {}),
    "four_bar": (fx.four_bar, {}),
    "actuated_pendulum": (fx.pendulum, {"actuators": [_servo()]}),
    "contact_pendulum": (_contact_pendulum, {}),
    "mesh_pendulum": (_mesh_pendulum, {}),
}


def _built(name):
    maker, keywords = CASES[name]
    components, joints, _placements = maker()
    return dyn.build_model(components, joints, **keywords)


def _flat(value):
    """One model field as a flat list of floats, without importing numpy."""

    listed = value.tolist() if hasattr(value, "tolist") else value
    out: list[float] = []
    stack = [listed]
    while stack:
        item = stack.pop()
        if isinstance(item, (list, tuple)):
            stack.extend(reversed(item))
        else:
            out.append(float(item))
    return out


def _relative(first, second):
    """The worst absolute difference, over the field's own largest value."""

    left = _flat(first)
    right = _flat(second)
    assert len(left) == len(right), (len(left), len(right))
    if not left:
        return 0.0
    scale = max(max(abs(value) for value in left), 1.0e-30)
    return max(abs(a - b) for a, b in zip(left, right, strict=True)) / scale


#: Every integer count a reload must reproduce exactly. A field diff over a
#: model of a different shape is meaningless, so these are checked first.
COUNTS = (
    "nbody", "njnt", "nq", "nv", "neq", "ngeom", "nsite", "nmesh", "nu",
    "nkey", "nmeshvert", "nmeshface",
)

#: Every numeric field the reload is diffed on. Written out rather than
#: derived from ``dir(model)`` on purpose: a MuJoCo release adding a field
#: should be a decision to extend this list, not a silent widening of what
#: "matches" means.
FIELDS = (
    "body_mass", "body_inertia", "body_ipos", "body_iquat", "body_pos",
    "body_quat", "jnt_type", "jnt_bodyid", "jnt_pos", "jnt_axis", "jnt_range",
    "jnt_limited", "jnt_qposadr", "jnt_dofadr", "eq_type", "eq_obj1id",
    "eq_obj2id", "eq_data", "eq_active0", "eq_solref", "eq_solimp",
    "geom_type", "geom_size", "geom_pos", "geom_quat", "geom_friction",
    "geom_solref", "geom_solimp", "geom_condim", "geom_margin", "geom_gap",
    "geom_contype", "geom_conaffinity", "actuator_gainprm", "actuator_biasprm",
    "actuator_ctrlrange", "actuator_forcerange", "actuator_gear",
    "actuator_trnid", "actuator_ctrllimited", "actuator_forcelimited",
    "dof_damping", "dof_armature", "dof_frictionloss", "site_pos", "site_quat",
    "mesh_vert", "mesh_face", "qpos0",
)

#: Every ``mjOption`` field a reload must reproduce, bit for bit. These are
#: the flags M3 chose deliberately -- islands off, sleep off, implicitfast --
#: and an export that lost one would run a different solver from the engine.
OPTIONS = (
    "timestep", "gravity", "integrator", "disableflags", "enableflags",
    "iterations", "tolerance", "solver", "impratio", "cone", "jacobian",
    "noslip_iterations", "o_margin", "o_solref", "o_solimp", "wind",
    "density", "viscosity", "ls_iterations", "ls_tolerance",
)


# ---------------------------------------------------------------------------
# Finding 1: one file, self-contained.
# ---------------------------------------------------------------------------


def test_to_xml_produces_a_self_contained_file_phase_zero_measured() -> None:
    """A four-bar is 1.7 kB of ordinary MJCF with no sidecars."""

    xml = _built("four_bar")["spec"].to_xml()
    assert xml.startswith('<mujoco model="cadex-assembly">')
    assert '<compiler angle="radian" autolimits="false"/>' in xml
    assert '<option integrator="implicitfast">' in xml
    assert '<flag island="disable"/>' in xml
    # The loop closure, as the equality constraint the tree could not carry.
    assert "<equality>" in xml
    assert "<connect " in xml
    # And the joint exclusions, which are what keep a hinged pair from
    # colliding with itself the instant geoms exist.
    assert "<contact>" in xml
    assert "<exclude " in xml


def test_a_collision_mesh_is_written_inline_phase_zero_measured() -> None:
    """No STL sidecar, no ``to_zip()``, no asset directory: one file.

    This is why the export needs a byte cap of its own rather than
    inheriting the trace's reasoning: the vertices are *in* the XML.
    """

    built = _built("mesh_pendulum")
    xml = built["spec"].to_xml()
    assert "<asset>" in xml
    assert '<mesh name="arm/collision0/mesh"' in xml
    assert 'vertex="' in xml and 'face="' in xml
    assert int(built["model"].nmesh) == 1
    # Nothing outside the file is referenced.
    assert ".stl" not in xml and ".obj" not in xml and "file=" not in xml


# ---------------------------------------------------------------------------
# Finding 2: what a reload costs, field by field.
# ---------------------------------------------------------------------------


#: The reload diff, as measured on mujoco 3.10.0. Every entry is a field
#: that moved, with the number it moved by; a field absent from a case's
#: mapping came back bit-identical and is asserted to have done so. These
#: are what set ``export_mjcf``'s tolerances, and a MuJoCo release that
#: widens one should fail here first and loudly.
MEASURED_RELOAD_DRIFT: dict[str, dict[str, float]] = {
    "pendulum": {
        "body_inertia": 7.961783438614472e-07,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 3.535742116640626e-17,
        "body_pos": 1.7738090493084087e-06,
        "body_quat": 1.7940855184805926e-07,
        "jnt_axis": 3.320348632467828e-07,
    },
    "two_link_arm": {
        "body_inertia": 1.674653968558175e-06,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 1.1049194114501957e-17,
        "jnt_axis": 2.220446049250313e-16,
    },
    "four_bar": {
        "body_inertia": 2.3731098180158446e-06,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 3.214311015127841e-16,
    },
    "actuated_pendulum": {
        "actuator_biasprm": 5.151004589778716e-07,
        "actuator_gainprm": 5.151004589778716e-07,
        "body_inertia": 7.961783438614472e-07,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 3.535742116640626e-17,
        "body_pos": 1.7738090493084087e-06,
        "body_quat": 1.7940855184805926e-07,
        "jnt_axis": 3.320348632467828e-07,
    },
    "contact_pendulum": {
        "body_inertia": 7.961783438614472e-07,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 3.535742116640626e-17,
        "body_pos": 1.7738090493084087e-06,
        "body_quat": 1.7940855184805926e-07,
        "jnt_axis": 3.320348632467828e-07,
    },
    "mesh_pendulum": {
        "body_inertia": 7.961783438614472e-07,
        "body_iquat": 1.4432899320127035e-15,
        "body_mass": 3.535742116640626e-17,
        "body_pos": 1.7738090493084087e-06,
        "body_quat": 1.7940855184805926e-07,
        "jnt_axis": 3.320348632467828e-07,
    },
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_reload_reproduces_the_model_shape_exactly(name: str) -> None:
    """Every count survives the file, on every fixture."""

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    observed = {field: int(getattr(reloaded, field)) for field in COUNTS}
    expected = {field: int(getattr(built["model"], field)) for field in COUNTS}
    assert observed == expected


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_reload_field_diff_is_the_measured_one(name: str) -> None:
    """Field by field, with a recorded number for everything that moves.

    The assertion is two-sided on purpose. A field that drifted *more* than
    measured is the failure everyone expects; a field that came back exact
    when it used to drift is also a change, and one that would otherwise let
    a tolerance stay wide long after the reason for it went away.
    """

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    expected = MEASURED_RELOAD_DRIFT[name]
    observed = {}
    for field in FIELDS:
        drift = _relative(getattr(built["model"], field), getattr(reloaded, field))
        if drift > 0.0:
            observed[field] = drift
    assert sorted(observed) == sorted(expected), (
        f"{name}: fields that drift changed; observed {sorted(observed)}"
    )
    for field, measured in expected.items():
        assert observed[field] == pytest.approx(measured, rel=1.0e-6), (
            f"{name}.{field}: measured {measured:.6g}, observed "
            f"{observed[field]:.6g}"
        )


@pytest.mark.parametrize("name", sorted(CASES))
def test_solver_options_survive_the_file_bit_for_bit(name: str) -> None:
    """M3 chose these; a file that lost one would run a different solver."""

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    for field in OPTIONS:
        assert _flat(getattr(reloaded.opt, field)) == _flat(
            getattr(built["model"].opt, field)
        ), field
    assert int(reloaded.opt.disableflags) == int(
        mujoco.mjtDisableBit.mjDSBL_ISLAND
    )
    assert int(reloaded.opt.enableflags) == 0


def test_mass_survives_far_better_than_inertia_phase_zero_measured() -> None:
    """The asymmetry that makes one tolerance wrong for both.

    ``to_xml()`` writes ~6 significant figures. A mass is one number and
    round-trips to 1e-16; a ``diaginertia`` triple is three numbers whose
    smallest is 1e-5 of the largest, and the *relative-to-largest* error
    that leaves is 2.4e-6 -- ten orders of magnitude apart, from the same
    formatter.
    """

    worst_mass = 0.0
    worst_inertia = 0.0
    for name in CASES:
        built = _built(name)
        reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
        worst_mass = max(
            worst_mass, _relative(built["model"].body_mass, reloaded.body_mass)
        )
        worst_inertia = max(
            worst_inertia,
            _relative(built["model"].body_inertia, reloaded.body_inertia),
        )
    assert worst_mass < 1.0e-12, worst_mass
    assert 1.0e-7 < worst_inertia < 1.0e-5, worst_inertia
    # The bound M5 pins, with the headroom it was chosen for.
    assert worst_inertia == pytest.approx(2.3731098180158446e-06, rel=1.0e-6)


#: What the export is allowed to cost, in millimetres of world position,
#: over a fixed number of solver steps. The worst fixture measured 4.1e-4;
#: the bound is 1e-2, which is a hundredth of a millimetre and two orders
#: of headroom on a number that comes from a formatter, not from physics.
DIVERGENCE_STEPS = 500
MEASURED_DIVERGENCE_MM = {
    "pendulum": 4.1014568810671115e-04,
    "two_link_arm": 9.71445146547012e-13,
    "four_bar": 0.0,
    "actuated_pendulum": 2.515488557314205e-04,
    "contact_pendulum": 4.1014568810671115e-04,
    "mesh_pendulum": 4.1014568810671115e-04,
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_trajectory_divergence_is_the_measured_one(name: str) -> None:
    """500 steps from the solved pose, in millimetres of world position.

    This is the number the exit criterion is stated against, and it is
    measured per mechanism because it is not predictable from the field
    diff: the four-bar has the *worst* inertia drift and diverges by
    nothing at all, because its loop closure keeps pulling the two runs back
    onto the same constraint manifold.
    """

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    here = mujoco.MjData(built["model"])
    there = mujoco.MjData(reloaded)
    here.qpos[:] = list(built["qpos_solved"])
    there.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(built["model"], here)
    mujoco.mj_forward(reloaded, there)
    worst = 0.0
    for _ in range(DIVERGENCE_STEPS):
        mujoco.mj_step(built["model"], here)
        mujoco.mj_step(reloaded, there)
        worst = max(
            worst,
            max(
                abs(a - b)
                for a, b in zip(_flat(here.xpos), _flat(there.xpos), strict=True)
            ),
        )
    worst_mm = dyn.length_mm(worst)
    assert worst_mm == pytest.approx(
        MEASURED_DIVERGENCE_MM[name], rel=1.0e-3, abs=1.0e-12
    ), worst_mm
    assert worst_mm < 1.0e-2, worst_mm


# ---------------------------------------------------------------------------
# Finding 3: explicitinertial is what makes the exactness claim survive.
# ---------------------------------------------------------------------------


def test_every_body_carries_explicitinertial_phase_zero_measured() -> None:
    built = _built("four_bar")
    bodies = list(built["spec"].bodies)
    assert [body.name for body in bodies][0] == "world"
    assert [bool(body.explicitinertial) for body in bodies[1:]] == [True] * 4


def test_without_explicitinertial_the_inertial_element_vanishes() -> None:
    """A flag is only a promise about a default; this is its effect.

    ``build_model`` sets ``explicitinertial`` for reasons that predate M5
    -- and M5's differentiator rides entirely on it, because without it
    MuJoCo omits ``<inertial>`` from the file and the exact OCCT tensor
    simply is not in the exported model. Nothing warns. This is the test
    that makes the reason a fact rather than a comment.
    """

    built = _built("four_bar")
    with_flag = built["spec"].to_xml()
    assert with_flag.count("<inertial ") == int(built["model"].nbody) - 1

    stripped = built["spec"].copy()
    for body in list(stripped.bodies)[1:]:
        body.explicitinertial = False
    stripped.compile()
    without = stripped.to_xml()
    assert "<inertial" not in without

    # Measured, and louder than expected: on a mechanism with no collision
    # geoms the file does not merely lose its masses, it stops loading at
    # all -- ``inertiafromgeom`` defaulting to ``auto`` has nothing to infer
    # from, so every moving body compiles to zero mass and MuJoCo refuses
    # it. Loud is the good failure mode; it is the *silent* half of this
    # that M5 could not have survived, and a body that does carry a geom
    # would have got exactly that.
    with pytest.raises(ValueError, match="must be larger than mjMINVAL"):
        mujoco.MjModel.from_xml_string(without)
    assert max(_flat(built["model"].body_mass)) > 0.0


def test_a_body_with_a_geom_loses_its_inertia_silently_instead() -> None:
    """The same flag off, on a body MuJoCo *can* infer a mass for.

    This is the failure the assertion above exists to prevent: with a
    collision geom present there is something to infer from, so the file
    loads, runs, and carries an inertia that has nothing to do with OCCT --
    a mechanism that is wrong and says nothing.
    """

    built = _built("contact_pendulum")
    stripped = built["spec"].copy()
    for body in list(stripped.bodies)[1:]:
        body.explicitinertial = False
    stripped.compile()
    reloaded = mujoco.MjModel.from_xml_string(stripped.to_xml())
    assert int(reloaded.nbody) == int(built["model"].nbody)
    # It loaded. And the masses are the geoms' own, not the part's.
    drift = _relative(built["model"].body_mass, reloaded.body_mass)
    assert drift > 0.5, drift


# ---------------------------------------------------------------------------
# Finding 4: the four flags that do not round-trip.
# ---------------------------------------------------------------------------


#: Set deliberately by ``build_model``, load-bearing for exact inertia, and
#: absent from the emitted XML because each equals an MJCF default.
OMITTED_COMPILER_FLAGS = (
    "inertiafromgeom",
    "balanceinertia",
    "boundmass",
    "boundinertia",
)


@pytest.mark.parametrize("flag", OMITTED_COMPILER_FLAGS)
def test_the_deliberate_compiler_flags_are_absent_from_the_xml(flag: str) -> None:
    """``to_xml()`` omits any attribute equal to an MJCF default."""

    assert flag not in _built("four_bar")["spec"].to_xml()


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_omitted_flags_change_nothing_on_reload(name: str) -> None:
    """Measured, not assumed -- and re-measured on every fixture.

    Every body carries an explicit ``<inertial>``, so ``inertiafromgeom``
    defaulting to ``auto`` behaves as false; ``balanceinertia`` and the two
    bounds have nothing left to act on. That is why the file survives their
    absence, and the assertion is the compiled inertia rather than the
    absence itself: if a MuJoCo release changes what those defaults do, the
    numbers move and this fails, which is the point.
    """

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    assert _relative(built["model"].body_mass, reloaded.body_mass) < 1.0e-12
    assert _relative(built["model"].body_inertia, reloaded.body_inertia) < 1.0e-5
    # boundmass/boundinertia off means a body may legitimately be light;
    # a bound silently applied would show up as a floor under the smallest.
    assert min(_flat(reloaded.body_inertia)[3:]) == pytest.approx(
        min(_flat(built["model"].body_inertia)[3:]), rel=1.0e-5
    )


# ---------------------------------------------------------------------------
# Finding 5: no keyframe means the wrong pose.
# ---------------------------------------------------------------------------


def test_a_stock_load_starts_folded_up_without_a_keyframe() -> None:
    """61 mm of wrong, and it looks like a model rather than an error.

    ``build_model`` deliberately builds at the configuration where each
    joint's connector frames coincide, not at the solved pose -- ADR-062's
    exit criterion depends on the solved pose being *derived* rather than
    built in. ``to_xml()`` emits no ``<keyframe>``, so anyone opening the
    exported file gets that reference configuration.
    """

    built = _built("four_bar")
    xml = built["spec"].to_xml()
    assert "<keyframe>" not in xml
    assert int(built["model"].nkey) == 0

    reloaded = mujoco.MjModel.from_xml_string(xml)
    fresh = mujoco.MjData(reloaded)
    mujoco.mj_forward(reloaded, fresh)
    solved = mujoco.MjData(built["model"])
    solved.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(built["model"], solved)
    off_by = dyn.length_mm(
        max(
            abs(a - b)
            for a, b in zip(_flat(fresh.xpos), _flat(solved.xpos), strict=True)
        )
    )
    assert off_by == pytest.approx(61.28355544951825, rel=1.0e-6), off_by


@pytest.mark.parametrize("name", sorted(CASES))
def test_add_key_puts_the_solved_pose_in_the_file(name: str) -> None:
    """``spec.add_key()`` + ``compile()`` is the fix, and it round-trips.

    The assertion is the *pose after a reset*, never the attribute text.
    Measured on ``two_link_arm``, whose solved pose happens to be all
    zeros: ``to_xml()`` omits an attribute equal to its default, so the
    element comes out as a bare ``<key name="solved"/>`` and a test written
    on ``qpos=`` would fail on a keyframe that is perfectly correct.
    """

    built = _built(name)
    copied = built["spec"].copy()
    copied.add_key(name="solved", qpos=list(built["qpos_solved"]))
    copied.compile()
    xml = copied.to_xml()
    assert "<keyframe>" in xml
    assert '<key name="solved"' in xml
    assert ('qpos=' in xml) == any(
        float(value) != 0.0 for value in built["qpos_solved"]
    )

    reloaded = mujoco.MjModel.from_xml_string(xml)
    assert int(reloaded.nkey) == 1
    key = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_KEY, "solved")
    assert key == 0
    data = mujoco.MjData(reloaded)
    mujoco.mj_resetDataKeyframe(reloaded, data, key)
    drift = max(
        abs(a - b)
        for a, b in zip(
            _flat(data.qpos), [float(v) for v in built["qpos_solved"]], strict=True
        )
    )
    assert drift < 1.0e-6, drift


def test_copying_the_spec_leaves_the_original_alone() -> None:
    """The reason the export copies rather than mutates.

    A script carrying both ``api.dynamics`` and ``api.mjcf`` must not have
    its simulation's numbers moved by an export, and this is what makes that
    structural rather than careful.
    """

    built = _built("four_bar")
    before = built["spec"].to_xml()
    copied = built["spec"].copy()
    copied.add_key(name="solved", qpos=list(built["qpos_solved"]))
    copied.compile()
    assert "<keyframe>" in copied.to_xml()
    assert built["spec"].to_xml() == before
    assert "<keyframe>" not in before
    assert int(built["model"].nkey) == 0


# ---------------------------------------------------------------------------
# Finding 6: what a mesh costs, in bytes.
# ---------------------------------------------------------------------------


def _cylinder_pendulum(sides: int):
    """A pendulum whose arm collides as an ``n``-gon prism of ``n`` vertices.

    The component's exact volume is set to the mesh's own, because the
    mesh-against-exact check is a different question from the one being
    asked here and would refuse every faceted cylinder before a single byte
    was counted.
    """

    components, joints, _placements = fx.pendulum()
    mesh = fx.faceted_cylinder_mesh(20.0, 300.0, sides)
    volume = dyn.mesh_volume_mm3(mesh["vertices_mm"], mesh["triangles"])
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [fx.collision_shape("hull", deflection_mm=5.0)],
                "mesh": mesh,
            }
            component["inertial"] = dict(
                component["inertial"], volume_mm3=volume
            )
    return components, joints, mesh


@pytest.mark.parametrize(
    ("sides", "vertices", "measured_bytes"),
    [(64, 128, 6330), (256, 512, 24548), (1024, 2048, 103893)],
)
def test_xml_size_grows_with_vertex_count(
    sides: int, vertices: int, measured_bytes: int
) -> None:
    """About 50 bytes a vertex, which is what sets the export's byte cap."""

    components, joints, mesh = _cylinder_pendulum(sides)
    assert len(mesh["vertices_mm"]) // 3 == vertices
    xml = dyn.build_model(components, joints)["spec"].to_xml()
    assert len(xml.encode("utf-8")) == pytest.approx(measured_bytes, rel=0.02)


def test_a_mesh_at_the_vertex_cap_is_bounded_by_the_byte_cap() -> None:
    """The arithmetic the export's cap is sized from, stated as a test.

    ``MAXIMUM_COLLISION_VERTICES`` is 200 000 per mesh at about 51 bytes a
    vertex, so one maximal mesh is roughly 11 MB of XML. A 64 MiB export cap
    -- the same number the trace carries -- admits five of them, and refuses
    a file no reasonable mechanism produces.
    """

    components, joints, _mesh = _cylinder_pendulum(1024)
    xml = dyn.build_model(components, joints)["spec"].to_xml()
    per_vertex = len(xml.encode("utf-8")) / 2048.0
    assert 45.0 < per_vertex < 60.0, per_vertex
    largest = per_vertex * dyn.MAXIMUM_COLLISION_VERTICES
    assert largest < 16 * 1024 * 1024, largest
    assert largest * 5 < 64 * 1024 * 1024, largest


# ---------------------------------------------------------------------------
# Byte determinism, across processes rather than across loop iterations.
# ---------------------------------------------------------------------------


_ACROSS_PROCESSES = """
import hashlib, sys
sys.path[:0] = sys.argv[1:3]
import CadexDynamics as dyn
import dynamics_fixtures as fx
components, joints, _placements = getattr(fx, sys.argv[3])()
xml = dyn.build_model(components, joints)["spec"].to_xml().encode("utf-8")
print(hashlib.sha256(xml).hexdigest(), len(xml))
"""


@pytest.mark.parametrize("name", ["pendulum", "two_link_arm", "four_bar"])
def test_to_xml_is_byte_identical_across_processes(name: str) -> None:
    """``to_xml()`` is trusted inside one process today; M5 needs it across.

    ``test_dynamics_model`` already compares two builds with
    ``to_xml() == to_xml()`` as a determinism oracle -- inside one
    interpreter, where a stable dict order and a warm allocator are doing
    part of the work. An exported *file* is compared between machines, so
    the claim has to be re-taken in an interpreter that has never seen the
    first one.
    """

    environment = dict(os.environ)
    environment.pop("PYTHONHASHSEED", None)
    digests = set()
    for _ in range(2):
        finished = subprocess.run(
            [
                sys.executable,
                "-c",
                _ACROSS_PROCESSES,
                str(MODULE_DIR),
                str(Path(__file__).resolve().parent),
                name,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env=environment,
        )
        assert finished.returncode == 0, finished.stderr
        digests.add(finished.stdout.strip())
    assert len(digests) == 1, digests
