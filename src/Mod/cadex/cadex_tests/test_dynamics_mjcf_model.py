# SPDX-License-Identifier: LGPL-2.1-or-later

"""``export_mjcf``: the model as a file, and the proof that it is the model.

Phase 0 measured what ``MjSpec.to_xml()`` does; this is what M5 builds on
top of it. The three things the export adds beyond calling MuJoCo's writer
are the three things tested here:

* it writes the **solved keyframe**, on a *copy* of the spec, so a script
  that exports and simulates gets the same numbers from both;
* it **verifies its own output** -- reload, counts, fields, options, the
  OCCT inertia comparison re-run on the reloaded model, and the pose -- and
  raises ``DynamicsError`` rather than returning a file it has not checked;
* it **refuses a model without explicit inertia**, because that is the one
  failure that is silent and is also the one the slice exists to prevent.

The refusals are tested by breaking a real built model rather than by
constructing a plausible-looking mock: a refusal that only fires on a shape
nothing produces is a refusal that does not fire.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
import dynamics_mjcf_digest

mujoco = pytest.importorskip("mujoco")

DIGEST_MODULE = Path(dynamics_mjcf_digest.__file__).resolve()


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
    components, joints, placements = fx.pendulum()
    sizes = {"arm": [300.0, 40.0, 20.0], "base": [200.0, 200.0, 20.0]}
    for component in components:
        component["collision"] = {
            "shapes": [fx.collision_shape("box", size_mm=sizes[component["name"]])],
            "mesh": None,
        }
    return components, joints, placements


def _mesh_pendulum():
    components, joints, placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [fx.collision_shape("mesh")],
                "mesh": fx.box_mesh(300.0, 40.0, 20.0),
            }
    return components, joints, placements


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


# ---------------------------------------------------------------------------
# What comes back.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_export_is_bytes_and_evidence(name: str) -> None:
    exported = dyn.export_mjcf(_built(name))
    assert isinstance(exported["xml"], bytes)
    assert exported["xml"].startswith(b'<mujoco model="cadex-assembly">')
    assert exported["evidence"]["bytes"] == len(exported["xml"])
    assert exported["evidence"]["keyframe"] == "solved"
    assert exported["evidence"]["keyframe_count"] == 1
    assert exported["evidence"]["mujoco_version"] == mujoco.__version__


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_evidence_counts_the_model_that_was_exported(name: str) -> None:
    built = _built(name)
    evidence = dyn.export_mjcf(built)["evidence"]
    model = built["model"]
    assert evidence["body_count"] == int(model.nbody)
    assert evidence["joint_count"] == int(model.njnt)
    assert evidence["geom_count"] == int(model.ngeom)
    assert evidence["mesh_count"] == int(model.nmesh)
    assert evidence["equality_count"] == int(model.neq)
    assert evidence["actuator_count"] == int(model.nu)
    assert evidence["coordinate_count"] == int(model.nq)
    assert evidence["degree_of_freedom_count"] == int(model.nv)
    assert evidence["component_outputs"] == [
        str(body["name"]) for body in built["tree"]["bodies"]
    ]


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_reported_errors_are_inside_the_reported_tolerances(name: str) -> None:
    """The evidence says how much of each bound the export actually used.

    "Within tolerance" is not a fact anyone can act on without the number,
    which is why the export reports both halves and this asserts the
    relationship between them rather than restating the constants.
    """

    evidence = dyn.export_mjcf(_built(name))["evidence"]
    assert evidence["worst_mass_rel_error"] <= evidence["mass_tolerance"]
    assert evidence["worst_inertia_rel_error"] <= evidence["inertia_tolerance"]
    assert evidence["worst_field_rel_error"] <= evidence["field_tolerance"]
    assert evidence["worst_pose_error_mm"] <= evidence["pose_tolerance_mm"]
    # And the bounds are not so wide they would accept anything. The two
    # margins are honestly different: the inertia bound is *tight* -- the
    # four-bar spends a third of it and there is no precision knob to buy
    # more -- while the pose bound is a hundredth of a millimetre against
    # an error of a quarter of a micron.
    assert evidence["worst_inertia_rel_error"] < 0.5 * evidence["inertia_tolerance"]
    assert evidence["worst_pose_error_mm"] < 0.1 * evidence["pose_tolerance_mm"]


#: The worst error each fixture's export actually incurs, on mujoco 3.10.0,
#: as ``(inertia relative to OCCT, pose in mm)``. Pinned so the tolerances
#: stay honest: a bound is only meaningful beside the number it is bounding,
#: and a release that doubles one of these should be a decision rather than
#: a quiet consumption of headroom.
#:
#: The four-bar's inertia figure is 3.2e-6 where the plain model-to-model
#: diff in ``test_dynamics_mjcf_measured`` reads 2.4e-6, and that is not a
#: discrepancy: this one is the *file against OCCT*, which is the claim M5
#: sells, and it carries the compiler's own rounding as well as the
#: writer's.
MEASURED_EXPORT_ERROR = {
    "pendulum": (7.961783438614472e-07, 2.506888992503953e-04),
    "two_link_arm": (1.674653968558175e-06, 0.0),
    "four_bar": (3.1531815601755096e-06, 2.2920227084333167e-05),
    "actuated_pendulum": (7.961783438614472e-07, 2.506888992503953e-04),
    "contact_pendulum": (7.961783438614472e-07, 2.506888992503953e-04),
    "mesh_pendulum": (7.961783438614472e-07, 2.506888992503953e-04),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_worst_error_is_the_measured_one(name: str) -> None:
    evidence = dyn.export_mjcf(_built(name))["evidence"]
    inertia, pose_mm = MEASURED_EXPORT_ERROR[name]
    assert evidence["worst_inertia_rel_error"] == pytest.approx(inertia, rel=1.0e-6)
    assert evidence["worst_pose_error_mm"] == pytest.approx(
        pose_mm, rel=1.0e-6, abs=1.0e-15
    )


# ---------------------------------------------------------------------------
# The keyframe, and the copy that keeps it out of the caller's spec.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_exported_file_opens_at_the_solved_pose(name: str) -> None:
    built = _built(name)
    xml = dyn.export_mjcf(built)["xml"].decode("utf-8")
    reloaded = mujoco.MjModel.from_xml_string(xml)
    key = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_KEY, "solved")
    assert key >= 0
    there = mujoco.MjData(reloaded)
    mujoco.mj_resetDataKeyframe(reloaded, there, key)
    mujoco.mj_forward(reloaded, there)
    here = mujoco.MjData(built["model"])
    here.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(built["model"], here)
    worst = max(
        abs(a - b)
        for a, b in zip(
            here.xpos.ravel().tolist(), there.xpos.ravel().tolist(), strict=True
        )
    )
    assert dyn.length_mm(worst) < dyn.MJCF_POSE_TOLERANCE_MM


def test_exporting_does_not_move_the_callers_model() -> None:
    """A script may carry both ``api.dynamics`` and ``api.mjcf``.

    The export adds a keyframe, which is a change to the spec and would
    change the compiled model's ``nkey`` and its XML. Doing that on a copy
    is what makes "the export cannot move the simulation" structural rather
    than a thing to be careful about -- so this asserts the original is
    untouched, including the oracle other suites compare builds with.
    """

    built = _built("four_bar")
    before_xml = built["spec"].to_xml()
    before_nkey = int(built["model"].nkey)
    before_qpos = list(built["qpos_solved"])

    dyn.export_mjcf(built)
    dyn.export_mjcf(built)

    assert built["spec"].to_xml() == before_xml
    assert "<keyframe>" not in before_xml
    assert int(built["model"].nkey) == before_nkey == 0
    assert list(built["qpos_solved"]) == before_qpos


def test_the_same_build_exports_the_same_bytes_twice() -> None:
    """Exporting is a pure read of the built model, including the second time.

    The copy makes this true; without it the second export would add a
    second keyframe to a spec that already had one.
    """

    built = _built("four_bar")
    first = dyn.export_mjcf(built)["xml"]
    second = dyn.export_mjcf(built)["xml"]
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_two_builds_of_one_fixture_export_the_same_bytes() -> None:
    components, joints, _placements = fx.four_bar()
    first = dyn.export_mjcf(dyn.build_model(components, joints))["xml"]
    second = dyn.export_mjcf(dyn.build_model(components, joints))["xml"]
    assert first == second


# ---------------------------------------------------------------------------
# What it refuses.
# ---------------------------------------------------------------------------


def test_a_model_without_explicit_inertia_is_refused() -> None:
    """The exactness claim rides on the flag, so the export asserts it.

    Broken on a real built model rather than on a mock: this is exactly
    what a MuJoCo release changing the default, or a future edit to
    ``build_model``, would produce.
    """

    built = _built("contact_pendulum")
    for body in list(built["spec"].bodies)[1:]:
        body.explicitinertial = False
    with pytest.raises(dyn.DynamicsError, match="explicit inertial") as caught:
        dyn.export_mjcf(built)
    assert caught.value.reason == "mjcf_inertia_not_explicit"


def test_the_world_body_is_not_asked_for_an_explicit_inertial() -> None:
    """It has none and needs none; a check that refused it would refuse all."""

    built = _built("four_bar")
    world = list(built["spec"].bodies)[0]
    assert world.name == "world"
    assert not bool(world.explicitinertial)
    assert dyn.export_mjcf(built)["evidence"]["body_count"] == 5


def test_a_rewritten_inertia_is_refused() -> None:
    """The OCCT comparison is re-run on the *reloaded* model, not the built one.

    Faked by moving the number the file is compared against, which is the
    same thing a compiler default silently rewriting an inertia would do to
    the comparison.
    """

    built = _built("pendulum")
    poisoned = {
        name: dict(
            reading,
            principal_inertia_kg_m2=[
                value * 2.0 for value in reading["principal_inertia_kg_m2"]
            ],
        )
        for name, reading in built["inertials"].items()
    }
    built = dict(built, inertials=poisoned)
    with pytest.raises(dyn.DynamicsError, match="The exported MJCF rewrote") as caught:
        dyn.export_mjcf(built)
    assert caught.value.reason == "mjcf_lost_inertia"


def test_a_changed_mass_is_refused() -> None:
    built = _built("pendulum")
    poisoned = {
        name: dict(reading, mass_kg=float(reading["mass_kg"]) * 1.5)
        for name, reading in built["inertials"].items()
    }
    with pytest.raises(dyn.DynamicsError, match="changed body") as caught:
        dyn.export_mjcf(dict(built, inertials=poisoned))
    assert caught.value.reason == "mjcf_lost_inertia"


def test_a_model_of_a_different_shape_is_refused() -> None:
    """Counts are checked before fields, so the message names the shape."""

    built = _built("pendulum")
    other = _built("four_bar")
    with pytest.raises(dyn.DynamicsError, match="reloads as a different model"):
        dyn.export_mjcf(dict(built, spec=other["spec"], model=built["model"]))


def test_a_file_without_the_solved_keyframe_is_refused() -> None:
    """The pose check resets to the file's *own* keyframe, never to the input.

    Had it reset to ``qpos_solved`` instead, it would pass on a file that
    lost its keyframe entirely -- a file nobody could open in the right
    pose, whose defect is precisely that it looks fine. So the refusal is
    tested against a model built without one, which is exactly what
    ``build_model`` produces and what ``to_xml()`` writes unaided.
    """

    built = _built("four_bar")
    keyless = mujoco.MjModel.from_xml_string(built["spec"].to_xml())
    assert int(keyless.nkey) == 0
    with pytest.raises(dyn.DynamicsError, match="carries no 'solved' keyframe") as caught:
        dyn._verify_exported_pose(
            mujoco,
            keyless,
            built["model"],
            built["qpos_solved"],
            context="a four-bar",
        )
    assert caught.value.reason == "mjcf_keyframe_missing"

    # ...and the export itself always writes one, on every fixture.
    assert b'<key name="solved"' in dyn.export_mjcf(built)["xml"]


def test_an_oversized_model_is_refused(monkeypatch) -> None:
    """The byte cap is the export's own, because meshes are written inline."""

    built = _built("mesh_pendulum")
    monkeypatch.setattr(dyn, "MAXIMUM_MJCF_BYTES", 64)
    with pytest.raises(dyn.DynamicsError, match="accepted maximum is 64") as caught:
        dyn.export_mjcf(built)
    assert caught.value.reason == "mjcf_too_large"
    assert caught.value.observed["bytes"] > 64


def test_the_byte_cap_is_sized_for_the_largest_mesh_a_body_may_carry() -> None:
    assert dyn.MAXIMUM_MJCF_BYTES == 64 * 1024 * 1024
    # ~51 bytes a vertex, measured in test_dynamics_mjcf_measured.
    assert 5 * 51 * dyn.MAXIMUM_COLLISION_VERTICES < dyn.MAXIMUM_MJCF_BYTES


# ---------------------------------------------------------------------------
# What the file actually contains.
# ---------------------------------------------------------------------------


def test_a_component_with_no_collision_exports_no_geom() -> None:
    """Collision geometry only: the file is the model that was simulated.

    The consequence, stated where somebody will find it: a mechanism with
    no collision shapes opens *invisible* in MuJoCo's viewer, because there
    is nothing in it to draw. Visual meshes are a separate question and not
    this slice's.
    """

    built = _built("pendulum")
    xml = dyn.export_mjcf(built)["xml"].decode("utf-8")
    assert "<geom" not in xml
    assert int(built["model"].ngeom) == 0

    with_geoms = dyn.export_mjcf(_built("contact_pendulum"))["xml"].decode("utf-8")
    assert with_geoms.count("<geom") == 2


def test_a_collision_mesh_travels_inside_the_file() -> None:
    xml = dyn.export_mjcf(_built("mesh_pendulum"))["xml"].decode("utf-8")
    assert "<asset>" in xml
    assert 'vertex="' in xml
    assert "file=" not in xml


def test_the_loop_closure_survives_as_an_equality() -> None:
    exported = dyn.export_mjcf(_built("four_bar"))
    xml = exported["xml"].decode("utf-8")
    assert "<equality>" in xml
    assert "<connect " in xml
    assert exported["evidence"]["equality_count"] == 1


def test_an_actuator_survives_as_its_pd_loop() -> None:
    built = _built("actuated_pendulum")
    exported = dyn.export_mjcf(built)
    assert exported["evidence"]["actuator_count"] == 1
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    index = mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_ACTUATOR, "hinge/position"
    )
    assert index >= 0
    gain = dyn.stiffness_nm_per_rad(4000.0)
    damping = dyn.damping_nms_per_rad(120.0)
    assert float(reloaded.actuator_gainprm[index][0]) == pytest.approx(
        gain, rel=dyn.MJCF_FIELD_TOLERANCE
    )
    assert list(reloaded.actuator_biasprm[index][:3]) == pytest.approx(
        [0.0, -gain, -damping], rel=dyn.MJCF_FIELD_TOLERANCE
    )


def test_the_solver_flags_travel_with_the_model() -> None:
    """Islands off and sleep off, in the file, because M3 chose them."""

    reloaded = mujoco.MjModel.from_xml_string(
        dyn.export_mjcf(_built("four_bar"))["xml"].decode("utf-8")
    )
    assert int(reloaded.opt.disableflags) == int(
        mujoco.mjtDisableBit.mjDSBL_ISLAND
    )
    assert int(reloaded.opt.enableflags) == 0
    assert int(reloaded.opt.integrator) == int(
        mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    )


def test_gravity_and_the_solver_step_travel_with_the_model() -> None:
    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(
        components, joints, gravity_m_s2=[0.0, 0.0, -1.62], time_step_s=0.0005
    )
    reloaded = mujoco.MjModel.from_xml_string(
        dyn.export_mjcf(built)["xml"].decode("utf-8")
    )
    assert list(reloaded.opt.gravity) == pytest.approx([0.0, 0.0, -1.62])
    assert float(reloaded.opt.timestep) == pytest.approx(0.0005)


# ---------------------------------------------------------------------------
# The trajectory, which is the claim the exit criterion is made of.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_exported_model_integrates_to_the_same_trajectory(name: str) -> None:
    """500 steps, in millimetres of world position, at the pinned bound."""

    built = _built(name)
    reloaded = mujoco.MjModel.from_xml_string(
        dyn.export_mjcf(built)["xml"].decode("utf-8")
    )
    here = mujoco.MjData(built["model"])
    here.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(built["model"], here)
    there = mujoco.MjData(reloaded)
    mujoco.mj_resetDataKeyframe(
        reloaded,
        there,
        mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_KEY, "solved"),
    )
    mujoco.mj_forward(reloaded, there)
    worst = 0.0
    for _ in range(500):
        mujoco.mj_step(built["model"], here)
        mujoco.mj_step(reloaded, there)
        worst = max(
            worst,
            max(
                abs(a - b)
                for a, b in zip(
                    here.xpos.ravel().tolist(),
                    there.xpos.ravel().tolist(),
                    strict=True,
                )
            ),
        )
    assert dyn.length_mm(worst) < dyn.MJCF_POSE_TOLERANCE_MM, dyn.length_mm(worst)


def test_the_exported_pendulum_actually_swings() -> None:
    """A trajectory comparison over a mechanism that did nothing would pass.

    So the run being compared is checked for containing the thing it is
    supposed to contain, the same guard ``test_dynamics_restart_determinism``
    puts in front of its byte comparison.
    """

    built = _built("pendulum")
    reloaded = mujoco.MjModel.from_xml_string(
        dyn.export_mjcf(built)["xml"].decode("utf-8")
    )
    data = mujoco.MjData(reloaded)
    mujoco.mj_resetDataKeyframe(
        reloaded,
        data,
        mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_KEY, "solved"),
    )
    start = float(data.qpos[0])
    for _ in range(500):
        mujoco.mj_step(reloaded, data)
    # One second at the default step. Measured: 0.40 rad of swing, from
    # gravity alone and with nothing in the file prescribing it.
    assert abs(float(data.qpos[0]) - start) == pytest.approx(0.401, abs=0.01)


# ---------------------------------------------------------------------------
# Stock MuJoCo, and across processes -- which is the only honest reading of
# "loads in stock MuJoCo" and of "the same bytes".
# ---------------------------------------------------------------------------


def _run(arguments, *, stock: bool):
    """The digest module, in a fresh interpreter.

    ``stock`` runs it with ``-P`` and a scrubbed ``PYTHONPATH``, so the
    script's own directory is *not* prepended to ``sys.path`` and nothing
    Cadex is reachable. The subprocess reports whether it could import
    ``CadexDynamics``, and the tests below assert the negative rather than
    trusting the invocation -- an environment variable that leaked would
    otherwise make a stock-MuJoCo claim quietly untrue.
    """

    environment = dict(os.environ)
    environment.pop("PYTHONHASHSEED", None)
    if stock:
        environment.pop("PYTHONPATH", None)
    command = [sys.executable]
    if stock:
        command.append("-P")
    command += [str(DIGEST_MODULE), *arguments]
    finished = subprocess.run(
        command, capture_output=True, text=True, timeout=300, env=environment
    )
    assert finished.returncode == 0, finished.stderr
    return json.loads(finished.stdout)


@pytest.mark.parametrize("name", sorted(dynamics_mjcf_digest.FIXTURE_NAMES))
def test_the_same_fixture_exports_the_same_bytes_in_two_processes(
    name: str,
) -> None:
    """An exported file is compared between machines, not between iterations.

    ``to_xml()`` is trusted as a determinism oracle inside one interpreter
    today (``test_dynamics_model``), where a stable dict order and a warm
    allocator are doing part of the work. This re-takes the claim in two
    interpreters that have never seen each other.
    """

    first = _run(["digest", name], stock=False)
    second = _run(["digest", name], stock=False)
    assert first == second
    assert first["fixture"] == name
    assert len(first["digest"]) == 64
    assert first["keyframe_count"] == 1


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_stock_mujoco_loads_the_file_and_reaches_the_solved_pose(
    name: str, tmp_path: Path
) -> None:
    """The exit criterion's shape, at unit scale and on every fixture.

    No Cadex on the subprocess's path -- asserted by the subprocess, which
    tried to import it and failed -- and no help beyond the file itself: it
    finds the ``solved`` keyframe by name, resets to it, lands on the pose
    the engine solved, and integrates from there to the same trajectory.
    """

    built = _built(name)
    target = tmp_path / "model.xml"
    target.write_bytes(dyn.export_mjcf(built)["xml"])
    result = _run(["load", str(target), "500"], stock=True)

    assert result["cadex_importable"] is False, (
        "the subprocess could reach Cadex, so it proves nothing about a "
        "stock MuJoCo"
    )
    assert result["mujoco_version"] == mujoco.__version__
    assert result["keyframe_id"] == 0
    assert result["nkey"] == 1
    assert result["nbody"] == int(built["model"].nbody)
    assert result["nq"] == int(built["model"].nq)

    # It opened at the solved pose, before a single step.
    solved = mujoco.MjData(built["model"])
    solved.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(built["model"], solved)
    start = [float(value) for value in result["start_xpos"]]
    worst = max(
        abs(a - b)
        for a, b in zip(solved.xpos.ravel().tolist(), start, strict=True)
    )
    assert dyn.length_mm(worst) < dyn.MJCF_POSE_TOLERANCE_MM

    # ...and it integrated to the same trajectory the engine did.
    for _ in range(500):
        mujoco.mj_step(built["model"], solved)
    there = [float(value) for value in result["xpos"]]
    worst = max(
        abs(a - b)
        for a, b in zip(solved.xpos.ravel().tolist(), there, strict=True)
    )
    assert dyn.length_mm(worst) < dyn.MJCF_POSE_TOLERANCE_MM, dyn.length_mm(worst)

    # The masses in the file are the OCCT ones, read by a MuJoCo that has
    # never heard of OCCT.
    for body in built["tree"]["bodies"]:
        index = mujoco.mj_name2id(
            built["model"], mujoco.mjtObj.mjOBJ_BODY, str(body["name"])
        )
        expected = float(built["inertials"][str(body["name"])]["mass_kg"])
        assert float(result["body_mass"][index]) == pytest.approx(
            expected, rel=dyn.MJCF_MASS_TOLERANCE
        )


# ---------------------------------------------------------------------------
# The mass a short decimal was hiding (ADR-090).
# ---------------------------------------------------------------------------


def test_a_body_whose_mass_is_not_a_short_decimal_still_exports() -> None:
    """``MJCF_MASS_TOLERANCE`` was 1e-12 and the writer emits six figures.

    Every fixture above has a mass that is a short decimal -- box volumes at
    round densities -- and a short decimal round-trips six significant
    figures exactly, so a bound seven orders tighter than the formatter
    never fired. The first real body whose mass was not one, a shin with a
    fused spherical foot, was refused as ``mjcf_lost_inertia``.

    The density here is deliberately ugly. What it asserts is not merely
    that the export succeeds but that it succeeds *while actually losing
    precision* -- otherwise this passes for the same reason the fixtures
    did, and pins nothing.
    """

    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["inertial"] = fx.box_inertial(
                300.0, 40.0, 20.0, density=979.0783218
            )
    built = dyn.build_model(components, joints)

    source = float(built["inertials"]["arm"]["mass_kg"])
    assert len(f"{source:.12g}".split(".")[-1]) > 6, (
        f"{source} is a short decimal; this fixture no longer exercises the bug"
    )

    exported = dyn.export_mjcf(built)          # refused before ADR-090
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    index = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_BODY, "arm")
    written = float(reloaded.body_mass[index])

    drift = abs(written - source)
    assert drift > 1.0e-12, (
        "the writer round-tripped this mass exactly, so the fixture does not "
        "reach the code path ADR-090 fixed"
    )
    assert drift <= dyn.MJCF_MASS_TOLERANCE * max(1.0, abs(source))
    assert written == pytest.approx(source, rel=1.0e-5)
