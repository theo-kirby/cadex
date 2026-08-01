# SPDX-License-Identifier: LGPL-2.1-or-later

"""Contact parameters (docs/MUJOCO.md M3, phase 2).

Five knobs and two findings, and the findings are why the file is long.

**Restitution is a translation, not a pass-through, and the textbook
formula for it is wrong.** MuJoCo has no restitution coefficient: a contact
is a spring-damper and bounce is a consequence of its damping ratio. The
relation every reference gives, ``e = exp(−ζπ/√(1−ζ²))``, is derived for a
*bilateral* spring that holds the mass for a full half period. A contact is
unilateral -- it lets go the instant the normal force would turn tensile,
which is earlier -- and solving for that instant gives
``e = exp(−ζ(π − 2 arcsin ζ)/√(1−ζ²))`` instead. At ζ = 0.5 the two differ
by nearly a factor of two, and the measurement agrees with the second one
to 1%.

**And even the right formula needs the solver to keep up.** At the default
solver step -- ten steps per contact time constant, which is what 60 fps
and ``DEFAULT_TIME_STEP_S`` produce -- a requested restitution of 0.9 comes
back as **3.45**: a ball bouncing higher than it was dropped from, forever,
every frame of it looking like physics. So a bouncing contact *requires* a
finer step, and asking for one without the other is refused with the number
it would take.

**Parent/child filtering does not do what its name suggests**, which was
the phase 2 question the plan asked. Measured: MuJoCo excludes a body from
its parent only when that parent is not itself welded to the world -- and
in a model built the way M2 builds one, every grounded component *is* a
static world child. So the first link of every mechanism collides with the
base it is hinged to, and a four-bar overlaps at its pins by construction.
The translator therefore writes an explicit exclusion for every pair of
components a joint connects, which is what the script meant all along.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _one(shape: dict) -> dict:
    return dyn.collision_geoms(
        [shape], None, exact_volume_mm3=1.0, context="component 'part'"
    )[0]


# ---------------------------------------------------------------------------
# Restitution: the formula, its inverse, and what MuJoCo actually does.
# ---------------------------------------------------------------------------


def test_the_unilateral_formula_is_the_one_that_matches_the_measurement() -> None:
    """Both formulas, side by side, against a dropped ball.

    This is the test that chose between them. The bilateral formula is not
    merely less accurate -- at ζ = 0.5 it is out by 44%, which on a
    requested restitution is the difference between a part that settles and
    one that hops off the table.
    """

    for zeta, measured in ((0.1, 0.7456), (0.2, 0.5699), (0.3, 0.4404)):
        bilateral = math.exp(-zeta * math.pi / math.sqrt(1.0 - zeta * zeta))
        unilateral = dyn.restitution_for_dampratio(zeta)
        assert abs(unilateral - measured) < 0.012, (zeta, unilateral, measured)
        assert abs(bilateral - measured) > abs(unilateral - measured)


def test_restitution_falls_from_one_to_its_floor_as_damping_rises() -> None:
    assert dyn.restitution_for_dampratio(0.0) == 1.0
    assert dyn.restitution_for_dampratio(1.0) == pytest.approx(math.exp(-2.0))
    assert dyn.restitution_for_dampratio(5.0) == pytest.approx(math.exp(-2.0))
    previous = 1.0
    for step in range(1, 20):
        value = dyn.restitution_for_dampratio(step / 20.0)
        assert value < previous
        previous = value


@pytest.mark.parametrize("target", [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
def test_the_damping_ratio_inverts_the_formula_exactly(target: float) -> None:
    ratio = dyn.dampratio_for_restitution(target, context="c")
    assert dyn.restitution_for_dampratio(ratio) == pytest.approx(target, abs=1e-12)


def test_a_restitution_of_zero_is_critical_damping_and_is_the_default() -> None:
    """Exact, unlike every other value, and therefore worth stating."""

    assert dyn.dampratio_for_restitution(0.0, context="c") == 1.0
    assert _one(fx.collision_shape("sphere", radius_mm=5.0))["solref"] == [
        dyn.CONTACT_TIMECONST_S,
        1.0,
    ]


@pytest.mark.parametrize("value", [0.05, 0.2, 0.29, 0.95, 0.99])
def test_a_restitution_outside_the_honest_band_is_refused(value: float) -> None:
    """Measured at both ends: 0.15 returns 0.00 and 0.95 returns 0.71.

    A knob that silently does nothing is the failure this slice exists to
    stop, so the refusal names the band and points at zero.
    """

    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.dampratio_for_restitution(value, context="component 'ball'")
    assert excinfo.value.reason == "restitution_out_of_range"
    assert "0.3" in excinfo.value.correction and "0.9" in excinfo.value.correction
    with pytest.raises(ValueError, match="restitution"):
        _api().collision("sphere", radius_mm=5.0, restitution=value)


def test_a_bouncing_contact_at_the_default_step_is_refused_with_the_step_it_needs() -> None:
    """The measurement that turned an inaccuracy into a refusal."""

    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [
                    fx.collision_shape("sphere", radius_mm=5.0, restitution=0.9)
                ],
                "mesh": None,
            }
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints, time_step_s=dyn.DEFAULT_TIME_STEP_S)
    error = excinfo.value
    assert error.reason == "restitution_needs_a_finer_step"
    assert error.observed["required_step_s"] == pytest.approx(0.001)
    assert error.observed["component"] == "arm"
    assert "3.45" in error.correction
    # And it compiles at the step the refusal named.
    built = dyn.build_model(components, joints, time_step_s=0.001)
    assert built["model"].ngeom == 1


def test_nothing_is_refused_when_nothing_bounces() -> None:
    """The default costs an ordinary contact model nothing."""

    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [fx.collision_shape("sphere", radius_mm=5.0)],
                "mesh": None,
            }
    assert dyn.build_model(
        components, joints, time_step_s=dyn.DEFAULT_TIME_STEP_S
    )["model"].ngeom == 1


@pytest.mark.parametrize("requested", [0.4, 0.6, 0.8])
def test_a_ball_really_bounces_to_the_restitution_it_asked_for(requested) -> None:
    """End to end, in MuJoCo, at the step the refusal above insists on.

    This is the only test here that runs the physics rather than the
    arithmetic, and it is the one that would notice a MuJoCo release
    changing what ``solref`` means. The tolerance is 15% because that is
    what the translation is worth -- stated, rather than discovered later.
    """

    dampratio = dyn.dampratio_for_restitution(requested, context="c")
    step = dyn.CONTACT_TIMECONST_S / dyn.RESTITUTION_STEPS_PER_TIMECONST
    model = mujoco.MjModel.from_xml_string(
        f"""
        <mujoco>
          <option timestep="{step}"/>
          <worldbody>
            <geom name="floor" type="plane" size="9 9 0.1"
                  solref="{dyn.CONTACT_TIMECONST_S} {dampratio}"/>
            <body name="b" pos="0 0 0.5"><freejoint/>
              <geom type="sphere" size="0.05"
                    solref="{dyn.CONTACT_TIMECONST_S} {dampratio}"/>
            </body>
          </worldbody>
        </mujoco>
        """
    )
    data = mujoco.MjData(model)
    heights = []
    for _step in range(int(3.0 / step)):
        mujoco.mj_step(model, data)
        heights.append(float(data.qpos[2]))
    apex = None
    rising = False
    for index in range(1, len(heights)):
        if heights[index] > heights[index - 1]:
            rising = True
        elif rising:
            apex = heights[index - 1]
            break
    assert apex is not None
    measured = math.sqrt(max(0.0, apex - 0.05) / (0.5 - 0.05))
    assert measured == pytest.approx(requested, rel=0.15)


def test_mujoco_averages_the_two_springs_so_one_sided_bounce_is_half() -> None:
    """Which is why the docstring tells authors to declare it on both sides.

    Measured rather than assumed: a solref of (0.02, 1.0) against
    (0.05, 0.3) produces (0.035, 0.65), the arithmetic mean of each term.
    """

    model = mujoco.MjModel.from_xml_string(
        """
        <mujoco><worldbody>
         <body name="a"><freejoint/><geom name="ga" type="sphere" size="0.05"
           solref="0.02 1"/></body>
         <body name="b" pos="1 0 0"><freejoint/><geom name="gb" type="sphere"
           size="0.05" solref="0.05 0.3"/></body>
        </worldbody></mujoco>
        """
    )
    data = mujoco.MjData(model)
    data.qpos[0:3] = [0.0, 0.0, 0.0]
    data.qpos[7:10] = [0.099, 0.0, 0.0]
    mujoco.mj_forward(model, data)
    assert data.ncon == 1
    assert list(data.contact[0].solref) == pytest.approx([0.035, 0.65])


# ---------------------------------------------------------------------------
# Friction, condim, margin, groups.
# ---------------------------------------------------------------------------


def test_one_friction_number_replaces_sliding_and_keeps_the_other_two() -> None:
    """Torsional and rolling friction are in different units, so a sliding
    coefficient cannot imply them without inventing numbers."""

    record = _one(fx.collision_shape("sphere", radius_mm=5.0, friction=0.4))
    assert record["friction"] == [0.4, dyn.DEFAULT_FRICTION[1], dyn.DEFAULT_FRICTION[2]]
    triple = _one(
        fx.collision_shape("sphere", radius_mm=5.0, friction=[0.4, 0.01, 0.002])
    )
    assert triple["friction"] == [0.4, 0.01, 0.002]
    assert _one(fx.collision_shape("sphere", radius_mm=5.0))["friction"] == list(
        dyn.DEFAULT_FRICTION
    )


def test_friction_on_a_frictionless_contact_is_refused_rather_than_ignored() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _one(fx.collision_shape("sphere", radius_mm=5.0, condim=1, friction=0.8))
    assert excinfo.value.reason == "friction_on_frictionless_contact"
    # Either half alone is fine.
    assert _one(fx.collision_shape("sphere", radius_mm=5.0, condim=1))["condim"] == 1


def test_condim_takes_only_the_four_mujoco_has() -> None:
    for value in (1, 3, 4, 6):
        assert _one(fx.collision_shape("sphere", radius_mm=5.0, condim=value))[
            "condim"
        ] == value
    with pytest.raises(dyn.DynamicsError, match="condim"):
        _one(fx.collision_shape("sphere", radius_mm=5.0, condim=2))
    with pytest.raises(ValueError, match="condim"):
        _api().collision("sphere", radius_mm=5.0, condim=2)


def test_the_margin_converts_to_metres_here_and_nowhere_else() -> None:
    record = _one(fx.collision_shape("sphere", radius_mm=5.0, margin_mm=2.5))
    assert record["margin_m"] == pytest.approx(0.0025)
    assert record["margin_mm"] == 2.5


def test_mujoco_sums_the_two_margins_rather_than_taking_the_larger() -> None:
    """Measured, and it is not what "max" in the documentation implied.

    20 mm on one geom and 30 mm on the other is a 50 mm margin, not 30.
    Worth pinning: a script that gives every part a margin gets twice the
    margin it thinks it does at every contact.
    """

    model = mujoco.MjModel.from_xml_string(
        """
        <mujoco><worldbody>
         <body name="a"><freejoint/><geom name="ga" type="sphere" size="0.05"
           margin="0.02"/></body>
         <body name="b" pos="1 0 0"><freejoint/><geom name="gb" type="sphere"
           size="0.05" margin="0.03"/></body>
        </worldbody></mujoco>
        """
    )
    data = mujoco.MjData(model)
    data.qpos[0:3] = [0.0, 0.0, 0.0]
    data.qpos[7:10] = [0.099, 0.0, 0.0]
    mujoco.mj_forward(model, data)
    assert data.contact[0].includemargin == pytest.approx(0.05)


def test_a_group_becomes_a_bit_and_an_unlisted_partner_set_becomes_all() -> None:
    assert dyn.contact_masks(0, None, context="c") == (1, (1 << 31) - 1)
    assert dyn.contact_masks(3, None, context="c") == (8, (1 << 31) - 1)
    assert dyn.contact_masks(1, [0, 2], context="c") == (2, 0b101)
    assert dyn.contact_masks(2, [], context="c") == (4, 0)


def test_the_group_count_is_thirty_one_because_the_binding_says_so() -> None:
    """Found by a compiler error, which is the cheap end of the flag lesson.

    contype/conaffinity are documented as 32-bit masks and are signed
    int32 in the binding: an all-ones 0xFFFFFFFF is refused outright by
    ``add_geom``, so the top bit is unusable.
    """

    assert dyn.CONTACT_GROUP_COUNT == 31
    with pytest.raises(dyn.DynamicsError, match="collision group"):
        dyn.contact_masks(31, None, context="c")
    with pytest.raises(dyn.DynamicsError, match="collides with group"):
        dyn.contact_masks(0, [31], context="c")
    with pytest.raises(ValueError, match="contact_group"):
        _api().collision("sphere", radius_mm=5.0, contact_group=31)


def test_two_groups_that_do_not_list_each_other_do_not_touch() -> None:
    """The bitmask protocol, exercised through the model rather than the maths."""

    components, joints, _placements = fx.build(
        [
            {"name": "floor", "grounded": True, "size": (400.0, 400.0, 20.0)},
            {"name": "left", "size": (40.0, 40.0, 40.0)},
            {"name": "right", "size": (40.0, 40.0, 40.0)},
        ],
        [],
    )
    for component in components:
        if component["name"] == "left":
            component["collision"] = {
                "shapes": [
                    fx.collision_shape(
                        "box",
                        size_mm=[40.0, 40.0, 40.0],
                        contact_group=1,
                        collides_with=[1],
                    )
                ],
                "mesh": None,
            }
        elif component["name"] == "right":
            component["collision"] = {
                "shapes": [
                    fx.collision_shape(
                        "box",
                        size_mm=[40.0, 40.0, 40.0],
                        contact_group=2,
                        collides_with=[2],
                    )
                ],
                "mesh": None,
            }
    model = dyn.build_model(components, joints)["model"]
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    # The two boxes are at the same place and would collide on any shared
    # group; declaring disjoint groups is what stops them.
    assert data.ncon == 0
    assert list(model.geom_contype) == [2, 4]
    assert list(model.geom_conaffinity) == [2, 4]


# ---------------------------------------------------------------------------
# What MuJoCo's own parent filter does, and what the translator adds.
# ---------------------------------------------------------------------------


def test_mujocos_parent_filter_does_not_cover_a_body_hinged_to_a_static_one() -> None:
    """The phase 2 question, answered by measurement rather than by name.

    Three bodies: ``p`` welded to the world, ``c`` hinged to ``p``, ``g``
    hinged to ``c``, all overlapping. With the filter in its default state
    the ``c``-``g`` pair is excluded and the ``c``-``p`` pair is **not** --
    because ``c``'s parent weld is the world, which is the case the filter
    exempts. Every mechanism M2 can build has exactly that shape.
    """

    xml = """
    <mujoco><worldbody>
      <body name="p"><geom name="gp" type="box" size="0.1 0.1 0.1"/>
        <body name="c"><joint name="j" type="hinge" axis="0 0 1"/>
          <geom name="gc" type="box" size="0.1 0.1 0.1"/>
          <body name="g"><joint name="j2" type="hinge" axis="0 0 1"/>
            <geom name="gg" type="box" size="0.1 0.1 0.1"/></body>
        </body></body>
    </worldbody></mujoco>
    """

    def pairs(disable_filter: bool) -> set[tuple[str, str]]:
        model = mujoco.MjModel.from_xml_string(xml)
        if disable_filter:
            model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_FILTERPARENT)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        return {
            tuple(
                sorted(
                    (
                        mujoco.mj_id2name(
                            model, mujoco.mjtObj.mjOBJ_GEOM, data.contact[index].geom1
                        ),
                        mujoco.mj_id2name(
                            model, mujoco.mjtObj.mjOBJ_GEOM, data.contact[index].geom2
                        ),
                    )
                )
            )
            for index in range(data.ncon)
        }

    assert pairs(False) == {("gc", "gp"), ("gg", "gp")}
    assert pairs(True) == {("gc", "gp"), ("gc", "gg"), ("gg", "gp")}


def test_components_a_joint_connects_are_excluded_from_each_other() -> None:
    """A four-bar's crank overlaps its ground at the pin by construction."""

    components, joints, _placements = fx.four_bar()
    for component in components:
        component["collision"] = {
            "shapes": [fx.collision_shape("box", size_mm=[220.0, 20.0, 10.0])],
            "mesh": None,
        }
    built = dyn.build_model(components, joints)
    pairs = {tuple(pair) for pair in built["excluded_pairs"]}
    assert pairs == {
        ("crank", "ground"),
        ("coupler", "crank"),
        ("coupler", "rocker"),
        ("ground", "rocker"),
    }
    assert built["model"].nexclude == 4
    data = mujoco.MjData(built["model"])
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(built["model"], data)
    for index in range(data.ncon):
        first = mujoco.mj_id2name(
            built["model"], mujoco.mjtObj.mjOBJ_GEOM, data.contact[index].geom1
        ).split("/")[0]
        second = mujoco.mj_id2name(
            built["model"], mujoco.mjtObj.mjOBJ_GEOM, data.contact[index].geom2
        ).split("/")[0]
        assert tuple(sorted((first, second))) not in pairs


def test_a_suppressed_joint_excludes_nothing() -> None:
    """It is not an edge, so the two parts are simply two parts."""

    components, joints, _placements = fx.pendulum()
    joints[0]["suppressed"] = True
    for component in components:
        component["collision"] = {
            "shapes": [fx.collision_shape("box", size_mm=[100.0, 40.0, 20.0])],
            "mesh": None,
        }
    built = dyn.build_model(components, joints)
    assert built["excluded_pairs"] == []


def test_the_evidence_names_the_exclusions_and_the_contact_parameters() -> None:
    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [
                    fx.collision_shape(
                        "box",
                        size_mm=[300.0, 40.0, 20.0],
                        friction=0.4,
                        condim=4,
                        margin_mm=1.0,
                        contact_group=2,
                        collides_with=[0, 2],
                    )
                ],
                "mesh": None,
            }
    built = dyn.build_model(components, joints)
    evidence = dyn.model_evidence(built, components)
    assert evidence["contact_exclusions"] == [["arm", "base"]]
    shape = evidence["collisions"][0]["shapes"][0]
    assert shape["friction"] == [0.4, dyn.DEFAULT_FRICTION[1], dyn.DEFAULT_FRICTION[2]]
    assert shape["condim"] == 4
    assert shape["margin_mm"] == 1.0
    assert shape["contact_group"] == 2
    assert shape["collides_with"] == [0, 2]
    assert shape["contype"] == 4
    assert shape["conaffinity"] == 0b101
    assert shape["restitution"] == 0.0


def test_two_bodies_slide_to_a_stop_at_the_friction_they_were_given() -> None:
    """Friction as a measured deceleration rather than a number in a dict.

    A block pushed across a floor at µ decelerates at µg, so where it stops
    is arithmetic anybody can check: v²/(2µg). Two coefficients, two
    distances, and the ratio between them is the ratio of the coefficients.
    """

    def slide(coefficient: float) -> float:
        components, joints, _placements = fx.build(
            [
                {"name": "floor", "grounded": True, "size": (4000.0, 400.0, 20.0)},
                {"name": "block", "size": (40.0, 40.0, 40.0)},
            ],
            [],
        )
        for component in components:
            shape = (
                fx.collision_shape(
                    "box", size_mm=[4000.0, 400.0, 20.0], friction=coefficient,
                    offset={"position": (0.0, 0.0, -10.0)},
                )
                if component["name"] == "floor"
                else fx.collision_shape(
                    "box", size_mm=[40.0, 40.0, 40.0], friction=coefficient
                )
            )
            component["collision"] = {"shapes": [shape], "mesh": None}
            if component["name"] == "block":
                component["solved_matrix"] = dyn.matrix_from_rotation_translation(
                    [1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 0.0, 20.0)
                )
        built = dyn.build_model(components, joints, time_step_s=0.001)
        model = built["model"]
        data = mujoco.MjData(model)
        data.qpos[:] = built["qpos_solved"]
        mujoco.mj_forward(model, data)
        data.qvel[0] = 2.0  # 2 m/s along +X
        start = float(data.qpos[0])
        for _step in range(3000):
            mujoco.mj_step(model, data)
        return float(data.qpos[0]) - start

    rough = slide(0.8)
    smooth = slide(0.2)
    assert smooth > rough > 0.0
    # v²/(2µg): 2²/(2·0.8·9.81) = 0.255 m and 2²/(2·0.2·9.81) = 1.019 m.
    assert rough == pytest.approx(0.255, rel=0.15)
    assert smooth == pytest.approx(1.019, rel=0.15)


# --- Initial contact: the collision/solid frame mismatch (ADR-087) ----------
#
# The bug this pair of tests exists for shipped a working one-leg hopper
# whose foot never touched the floor it was drawn on. Every gate was green
# twice; a viewport caught it and nothing else did.
#
# `part.box(4000, 600, 40, origin=[-2000, -300, -40])` puts the floor solid
# at z = -40..0, so its visible top is z = 0. `collision("box",
# size_mm=[4000, 600, 40])` with no offset puts the collision box in the
# COMPONENT frame -- centred on the origin, z = -20..+20. The collision top
# stands 20 mm above the visible one and the foot rests on an invisible
# shelf from frame 0.
#
# No bounding-box rule finds it. The two boxes OVERLAP across z = -20..0, so
# an overlap test passes; a containment test would fail the foot sphere,
# which protrudes 25 mm below the shin on purpose; and the collision box's
# centre sits exactly on the solid's boundary, which is marginal either way.
# The observable that does discriminate is what is touching at t = 0.


def _hopper(floor_offset_mm: float):
    """The hopper's chain, with the floor's collision box where it was.

    ground -rail- torso -hip- thigh -knee- shin, foot sphere bottom at
    world z = 20 mm. ``floor_offset_mm`` of 0 is the shipped bug; -20 is
    the correction that puts the collision top back on the visible top.

    The chain length is load-bearing rather than incidental: ``shin`` and
    ``ground`` are three joints apart, so they are not an excluded pair and
    their geoms are free to meet. A one-joint fixture would report nothing
    however wrong the floor was.
    """

    components = [
        {
            "name": "ground",
            "grounded": True,
            "size": (4000.0, 600.0, 40.0),
            "collision": {
                "shapes": [
                    fx.collision_shape(
                        "box",
                        size_mm=[4000.0, 600.0, 40.0],
                        friction=1.0,
                        offset={"position": (0.0, 0.0, floor_offset_mm)},
                    )
                ],
                "mesh": None,
            },
        },
        {"name": "torso", "size": (140.0, 100.0, 120.0)},
        {"name": "thigh", "size": (40.0, 40.0, 200.0)},
        {
            "name": "shin",
            "size": (30.0, 30.0, 200.0),
            "collision": {
                "shapes": [
                    fx.collision_shape(
                        "sphere",
                        radius_mm=25.0,
                        friction=1.2,
                        offset={"position": (0.0, 0.0, -100.0)},
                    )
                ],
                "mesh": None,
            },
        },
    ]
    joints = [
        {
            "name": "rail",
            "kind": "slider",
            "parent": "ground",
            "child": "torso",
            "parent_frame": fx.frame(position=(0.0, 0.0, 505.0)),
            "child_frame": fx.frame(),
            "values": [0.0],
            "length_limits_mm": [-260.0, 400.0],
        },
        {
            "name": "hip",
            "kind": "revolute",
            "parent": "torso",
            "child": "thigh",
            "parent_frame": fx.frame(
                position=(0.0, 0.0, -60.0), axis=(1.0, 0.0, 0.0), angle_degrees=-90.0
            ),
            "child_frame": fx.frame(
                position=(0.0, 0.0, 100.0), axis=(1.0, 0.0, 0.0), angle_degrees=-90.0
            ),
            "values": [0.0],
            "angle_limits_degrees": [-70.0, 70.0],
        },
        {
            "name": "knee",
            "kind": "revolute",
            "parent": "thigh",
            "child": "shin",
            "parent_frame": fx.frame(
                position=(0.0, 0.0, -100.0), axis=(1.0, 0.0, 0.0), angle_degrees=-90.0
            ),
            "child_frame": fx.frame(
                position=(0.0, 0.0, 100.0), axis=(1.0, 0.0, 0.0), angle_degrees=-90.0
            ),
            "values": [0.0],
            "angle_limits_degrees": [-5.0, 130.0],
        },
    ]
    return fx.build(components, joints)


def test_a_collision_shape_left_in_the_component_frame_starts_in_contact() -> None:
    components, joints, _placements = _hopper(0.0)
    evidence = dyn.model_evidence(dyn.build_model(components, joints), components)

    assert evidence["initial_contact_count"] == 1
    contact = evidence["initial_contacts"][0]
    assert sorted(contact["component_outputs"]) == ["ground", "shin"]
    assert sorted(contact["geoms"]) == ["ground/collision0", "shin/collision0"]
    # The number that says where the invisible shelf is: the foot meets the
    # floor 20 mm above the floor's own top surface.
    assert contact["position_mm"][2] == pytest.approx(20.0, abs=1.0e-6)
    assert contact["distance_mm"] == pytest.approx(0.0, abs=1.0e-6)
    # Resting, not overlapping -- and the tolerance is why. The residue out
    # of the placement chain is about 5e-17 m; a bare `dist < 0` would call
    # that interpenetration and put a true flag on every model that starts
    # on its feet by design.
    assert contact["penetrating"] is False
    assert evidence["initial_contacts_omitted"] == 0


def test_the_same_hopper_with_the_floor_offset_starts_clear_of_the_ground() -> None:
    components, joints, _placements = _hopper(-20.0)
    evidence = dyn.model_evidence(dyn.build_model(components, joints), components)

    assert evidence["initial_contact_count"] == 0
    assert evidence["initial_contacts"] == []
    # Nothing else moved: the same shapes are still declared on the same two
    # bodies, so this is the offset and not a collision that went missing.
    assert {entry["component_output"] for entry in evidence["collisions"]} == {
        "ground",
        "shin",
    }


def test_interpenetration_is_reported_as_penetrating() -> None:
    """The case a refusal would be argued about, with the data to argue from.

    Evidence rather than a refusal is a decision ADR-087 takes deliberately
    -- a mechanism designed to start on its feet is ordinary -- but the
    signal that would drive an escalation has to exist first, and be
    distinguishable from resting contact. 5 mm of overlap is not float
    residue.

    ``+5`` rather than ``-5``: a positive offset raises the collision box,
    so its top goes to z = +25 against a foot whose bottom is at z = 20.
    """

    components, joints, _placements = _hopper(5.0)
    evidence = dyn.model_evidence(dyn.build_model(components, joints), components)

    assert evidence["initial_contact_count"] == 1
    contact = evidence["initial_contacts"][0]
    assert contact["penetrating"] is True
    assert contact["distance_mm"] == pytest.approx(-5.0, abs=1.0e-6)
