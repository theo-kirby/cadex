# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.reset_variation`` and ``assembly.disturbance`` on the script
surface (docs/MUJOCO.md M9, ADR-097).

Two new intermediates and two new keyword arguments on ``api.task``, modelled
line for line on ``api.randomise`` -- and the division of labour is the point
this file asserts, exactly as ``test_dynamics_task_api`` asserts M6's.

**The API refuses what a reader of the script could see**: a negative
magnitude, a range the wrong way round, an entry that varies nothing, a
sustained push that also declares a window. **The engine refuses what only
the compiled model and the rounded schedule know**: whether a tilt clears
the floor, whether the target body actually floats, whether a shove is
longer than a control interval and lands inside the horizon. Duplicating
either half here would make one of them untested and the other twice-tested.

None of this touches ``CadexdProtocol.OP_ARG_SPECS``. ``assembly.*`` is the
xscript authoring surface, not the cadexd op table, so ``docs/INTEGRATION.md``
is unmoved and the shell's client needs no change at all.
"""

from __future__ import annotations

import pytest

from cadex_assembly_api import AssemblyDomainAPI, _DISTURBANCE_DIRECTIONS
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _scene(api):
    components = [
        api.component(_source("solid0"), grounded=True),
        api.component(_source("solid1")),
    ]
    joint = api.joint(
        "revolute",
        api.connector(components[0], "origin"),
        api.connector(components[1], "origin"),
    )
    assembly = api.assembly(components, [joint])
    motor = api.actuator(joint, kind="motor", control_nmm="100",
                         torque_limit_nmm=500)
    model = api.mjcf(
        assembly,
        [api.body(component, density_kg_m3=7850) for component in components],
        actuators=[motor],
        observations=[api.observation(joint, "position", name="angle")],
    )
    return {"components": components, "motor": motor, "model": model}


def _task(api, scene, **overrides):
    arguments = {
        "actions": [scene["motor"]],
        "reward": [api.reward("angle", weight=1.0e-3, label="up")],
        "episode_seconds": 4.0,
        "control_hz": 50,
    }
    arguments.update(overrides)
    return api.task(scene["model"], **arguments)


# ---------------------------------------------------------------------------
# Registration.
# ---------------------------------------------------------------------------


def test_both_intermediates_are_registered_and_neither_is_publishable() -> None:
    """The same shape ``randomise`` has, for the same reason.

    A reset variation and a disturbance are *arguments to a task*, not
    things a script publishes: nothing bakes them, nothing renders them, and
    an output type for either would be an artifact with no reader.
    """

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    for name in ("reset_variation", "disturbance"):
        assert name in pack.api_exports
        assert name not in pack.output_types
        assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"][name] == name
    # And the constructor is what enforces it: it refuses to build if the
    # pack and the class disagree, so this constructing at all is half the
    # assertion.
    api = _api()
    assert "reset_variation" in api.exported_names
    assert "disturbance" in api.exported_names


def test_the_two_ops_produce_intermediates_of_their_own_type() -> None:
    api = _api()
    scene = _scene(api)
    start = api.reset_variation(scene["components"][1], tilt_degrees=[0.0, 5.0])
    shove = api.disturbance(scene["components"][1], newtons=[0.1, 0.5],
                            at_seconds=[1.0, 2.0], duration_s=0.2)
    assert start.output_type == "reset_variation"
    assert shove.output_type == "disturbance"
    assert start.domain == shove.domain == "assembly"


def test_a_task_carries_both_lists_through_to_its_properties() -> None:
    """Passed to ``api.task`` exactly as a randomisation is."""

    api = _api()
    scene = _scene(api)
    start = api.reset_variation(scene["components"][1], tilt_degrees=[0.0, 5.0])
    shove = api.disturbance(scene["components"][1], newtons=[0.1, 0.5],
                            at_seconds=[1.0, 2.0], duration_s=0.2)
    task = _task(api, scene, reset_variation=[start], disturbance=[shove])
    assert list(task.properties["reset_variation"]) == [start]
    assert list(task.properties["disturbance"]) == [shove]

    # Absent means empty, not missing: a task with neither is the M6 task,
    # unchanged, and every script written before M9 stays one.
    plain = _task(api, scene)
    assert list(plain.properties["reset_variation"]) == []
    assert list(plain.properties["disturbance"]) == []


# ---------------------------------------------------------------------------
# Units and defaults on the reset variation.
# ---------------------------------------------------------------------------


def test_the_reset_variation_keeps_the_scripts_own_units() -> None:
    """Degrees, millimetres and degrees-per-second cross the seam unchanged.

    Converted once, in ``CadexDynamics``, at bundle-build time -- which is
    the split every other surface on this boundary has. A conversion here
    would be a second place for a factor of 1000.
    """

    api = _api()
    scene = _scene(api)
    start = api.reset_variation(
        scene["components"][1],
        tilt_degrees=[1.0, 6.0],
        height_mm=[0.0, 3.0],
        angular_velocity_dps=[-20.0, 20.0],
        label="start",
    )
    assert start.properties["tilt_degrees_low"] == 1.0
    assert start.properties["tilt_degrees_high"] == 6.0
    assert start.properties["height_mm_low"] == 0.0
    assert start.properties["height_mm_high"] == 3.0
    assert start.properties["angular_velocity_dps_low"] == -20.0
    assert start.properties["angular_velocity_dps_high"] == 20.0
    assert start.properties["label"] == "start"


def test_an_omitted_range_is_a_declared_zero_rather_than_absent() -> None:
    """Every field is present, so nothing downstream reads a default.

    A range the script did not write is ``[0, 0]``, which draws zero. The
    alternative -- a missing key -- would put "what does absent mean" in
    three evaluators instead of in one constructor.
    """

    api = _api()
    scene = _scene(api)
    start = api.reset_variation(scene["components"][1], tilt_degrees=[0.0, 4.0])
    assert start.properties["height_mm_low"] == 0.0
    assert start.properties["height_mm_high"] == 0.0
    assert start.properties["angular_velocity_dps_low"] == 0.0
    assert start.properties["angular_velocity_dps_high"] == 0.0


def test_a_reset_variation_that_varies_nothing_is_refused() -> None:
    """It costs an episode's arithmetic and changes no episode."""

    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.reset_variation(scene["components"][1])
    assert "varies nothing" in str(excinfo.value)


@pytest.mark.parametrize(
    "parameter", ["tilt_degrees", "height_mm"]
)
def test_a_negative_magnitude_is_refused_with_the_reason(parameter: str) -> None:
    """A tilt's direction is drawn, not signed; a downward lift is a sole
    through the floor."""

    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.reset_variation(scene["components"][1], **{parameter: [-1.0, 4.0]})
    assert "cannot be negative" in str(excinfo.value)


def test_an_unordered_range_is_refused() -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.reset_variation(scene["components"][1], tilt_degrees=[6.0, 1.0])
    assert "[low, high]" in str(excinfo.value)


def test_a_stumble_is_declared_as_a_speed_and_the_direction_is_drawn() -> None:
    """``linear_velocity_mm_s``, in the script's own units like the rest.

    The point of it, stated where it can be read: a machine that begins
    every episode at rest has nothing to recover from until something pushes
    it, so an initial speed is the cheapest way to make a batch be *about*
    recovering. It is a magnitude with its azimuth drawn, exactly as the
    tilt is, and so it cannot be negative for exactly the same reason.
    """

    api = _api()
    scene = _scene(api)
    start = api.reset_variation(
        scene["components"][1], linear_velocity_mm_s=[0.0, 250.0]
    )
    assert start.properties["linear_velocity_mm_s_low"] == 0.0
    assert start.properties["linear_velocity_mm_s_high"] == 250.0
    # ...and it is enough on its own: an entry that declares only a stumble
    # varies something, so the "varies nothing" refusal must not fire.
    assert start.properties["tilt_degrees_high"] == 0.0

    with pytest.raises(ValueError) as excinfo:
        api.reset_variation(
            scene["components"][1], linear_velocity_mm_s=[-10.0, 250.0]
        )
    assert "cannot be negative" in str(excinfo.value)


def test_a_signed_angular_velocity_range_is_allowed() -> None:
    """...and is the only one of the three that may go negative, because a
    spin has a direction the mechanism can tell apart and a tilt magnitude
    does not."""

    api = _api()
    scene = _scene(api)
    start = api.reset_variation(
        scene["components"][1], angular_velocity_dps=[-30.0, -10.0]
    )
    assert start.properties["angular_velocity_dps_low"] == -30.0


# ---------------------------------------------------------------------------
# The disturbance.
# ---------------------------------------------------------------------------


def test_a_shove_declares_a_window_and_wind_declares_none() -> None:
    """One mechanism, two shapes. Wind is a push whose window is the whole
    episode, which is why there is no second surface for it."""

    api = _api()
    scene = _scene(api)
    shove = api.disturbance(scene["components"][1], newtons=[0.05, 0.35],
                            at_seconds=[1.0, 5.0], duration_s=0.12,
                            label="shove")
    wind = api.disturbance(scene["components"][1], newtons=[0.0, 0.08],
                           sustained=True, label="wind")

    assert shove.properties["sustained"] is False
    assert shove.properties["at_seconds_low"] == 1.0
    assert shove.properties["duration_s"] == 0.12
    assert wind.properties["sustained"] is True
    assert wind.properties["duration_s"] == 0.0
    assert shove.properties["direction"] == wind.properties["direction"] == (
        "horizontal"
    )


def test_a_sustained_disturbance_that_also_declares_a_window_is_refused() -> None:
    """The two readings would contradict, and quietly picking one is how a
    script comes to mean something nobody wrote."""

    api = _api()
    scene = _scene(api)
    for extra in ({"at_seconds": [1.0, 2.0]}, {"duration_s": 0.2}):
        with pytest.raises(ValueError) as excinfo:
            api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                            sustained=True, **extra)
        assert "sustained=True" in str(excinfo.value)


def test_a_windowed_disturbance_needs_both_halves_of_its_window() -> None:
    api = _api()
    scene = _scene(api)
    for extra in ({"at_seconds": [1.0, 2.0]}, {"duration_s": 0.2}, {}):
        with pytest.raises(ValueError) as excinfo:
            api.disturbance(scene["components"][1], newtons=[0.1, 0.2], **extra)
        assert "when it happens and how long it lasts" in str(excinfo.value)


def test_only_the_two_declared_directions_are_accepted() -> None:
    """Both are one drawn scalar, which is what keeps the stated stream the
    same length whichever a script picks."""

    api = _api()
    scene = _scene(api)
    assert _DISTURBANCE_DIRECTIONS == frozenset({"horizontal", "vertical"})
    for direction in sorted(_DISTURBANCE_DIRECTIONS):
        entry = api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                                direction=direction, sustained=True)
        assert entry.properties["direction"] == direction
    with pytest.raises(ValueError) as excinfo:
        api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                        direction="sideways", sustained=True)
    assert "horizontal" in str(excinfo.value) and "vertical" in str(excinfo.value)


def test_an_undeclared_arc_is_the_whole_circle_and_says_so() -> None:
    """Absent is not missing: the entry carries ``[0, 360]``.

    Every field present is the same decision ``height_mm`` took -- "what
    does absent mean" belongs in one constructor rather than in the three
    evaluators that read the bundle.
    """

    api = _api()
    scene = _scene(api)
    entry = api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                            sustained=True)
    assert entry.properties["azimuth_degrees_low"] == 0.0
    assert entry.properties["azimuth_degrees_high"] == 360.0


def test_an_arc_aims_a_horizontal_push_and_is_refused_on_a_vertical_one() -> None:
    """The one refusal B1a exists to make.

    A vertical push reads the same uniform draw as a *sign*, so an arc there
    would silently mean something else. A parameter that means one thing on
    one direction and another on the other is one that gets read wrong, so
    it is refused rather than ignored.
    """

    api = _api()
    scene = _scene(api)
    aimed = api.disturbance(scene["components"][1], newtons=[0.15, 0.9],
                            azimuth_degrees=[-60.0, 60.0],
                            at_seconds=[0.3, 1.5], duration_s=0.12)
    assert aimed.properties["azimuth_degrees_low"] == -60.0
    assert aimed.properties["azimuth_degrees_high"] == 60.0

    with pytest.raises(ValueError) as excinfo:
        api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                        direction="vertical", azimuth_degrees=[-60.0, 60.0],
                        sustained=True)
    assert "reads its draw as a sign" in str(excinfo.value)


@pytest.mark.parametrize(
    "arc, expected",
    [
        ([60.0, -60.0], "[low, high]"),
        ([-180.0, 240.0], "more than one full circle"),
    ],
)
def test_a_malformed_arc_is_refused(arc, expected: str) -> None:
    """An arc the wrong way round, and one that overlaps itself.

    The second is the one worth a message: a span past 360 degrees draws
    part of the circle twice as often as the rest, which is a distribution
    nobody wrote and nobody would notice.
    """

    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                        azimuth_degrees=arc, sustained=True)
    assert expected in str(excinfo.value)


def test_a_negative_force_is_refused_because_the_direction_is_drawn() -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.disturbance(scene["components"][1], newtons=[-0.1, 0.2],
                        sustained=True)
    assert "which way the push goes is drawn" in str(excinfo.value)


def test_a_push_that_starts_before_the_episode_does_is_refused() -> None:
    api = _api()
    scene = _scene(api)
    with pytest.raises(ValueError) as excinfo:
        api.disturbance(scene["components"][1], newtons=[0.1, 0.2],
                        at_seconds=[-1.0, 2.0], duration_s=0.2)
    assert "before the episode does" in str(excinfo.value)


# ---------------------------------------------------------------------------
# What ``api.task`` checks, and what it deliberately leaves to the engine.
# ---------------------------------------------------------------------------


def test_a_variation_naming_a_component_outside_the_assembly_is_refused() -> None:
    """The one check this surface *can* make: it has the component list.

    Whether that component floats is the engine's, because the answer is a
    property of the tree the model was built from rather than of the script.
    """

    api = _api()
    scene = _scene(api)
    stranger = api.component(_source("elsewhere"))
    for parameter, entry in (
        ("reset_variation", api.reset_variation(stranger, tilt_degrees=[0.0, 4.0])),
        ("disturbance", api.disturbance(stranger, newtons=[0.1, 0.2],
                                        sustained=True)),
    ):
        with pytest.raises(ValueError) as excinfo:
            _task(api, scene, **{parameter: [entry]})
        assert "not listed in this assembly" in str(excinfo.value)


def test_the_wrong_intermediate_in_the_wrong_list_is_refused() -> None:
    """A randomisation is not a disturbance, and the list says which."""

    api = _api()
    scene = _scene(api)
    varied = api.randomise(scene["components"][1], "mass", scale=[0.9, 1.1])
    with pytest.raises(ValueError) as excinfo:
        _task(api, scene, disturbance=[varied])
    assert "disturbance" in str(excinfo.value)
