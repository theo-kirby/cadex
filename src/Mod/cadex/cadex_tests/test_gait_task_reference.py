# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A task carries its gait reference (ADR-703).

``assembly.gait`` declares a stride on the script surface and
``api.task(reference=...)`` attaches it. The worker resolves the feet and
the spine to output names, and the bundle's ``reference`` section is
``CadexGait.generate`` on the exported model plus every body's pose at each
sample, which is what the dashboard plays. Three claims are checked against
something other than the code that makes them: the poses put each foot on
the clip's own target (MuJoCo's forward kinematics, read back), the stride
starts from the episode's reset keyframe, and a stride the legs cannot reach
is a refusal with the generator's reason.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import CadexGait as gait
from cadex_assembly_api import _GAIT_NAMES, AssemblyDomainAPI
from cadex_assembly_worker import _gait_input
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

from test_gait_reference import LEGS, QUADRUPED  # noqa: E402


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _legged(api):
    """A body, four feet on revolute joints, and a spine joint."""

    names = ["torso", "pelvis", "lf", "rf", "lh", "rh"]
    parts = {n: api.component(_source(n)) for n in names}
    spine = api.joint("revolute", api.connector(parts["torso"]), api.connector(parts["pelvis"]))
    legs = [api.joint("revolute", api.connector(parts["torso" if n[1] == "f" else "pelvis"]),
                      api.connector(parts[n])) for n in ("lf", "rf", "lh", "rh")]
    motor = api.actuator(legs[0], kind="motor", control_nmm="0", torque_limit_nmm=500)
    assembly = api.assembly(list(parts.values()), [spine, *legs])
    model = api.mjcf(assembly, [api.body(c, density_kg_m3=1000) for c in parts.values()],
                     actuators=[motor],
                     observations=[api.observation(legs[0], "position", name="q")])
    return parts, spine, legs, motor, model


def _task(api, model, motor, **extra):
    return api.task(model, actions=[motor], reward=[api.reward("-q^2", weight=1.0)],
                    episode_seconds=2.0, control_hz=50, **extra)


def test_gait_is_an_intermediate_and_its_names_are_the_engines() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "gait" in pack.api_exports and "gait" not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["gait"] == "gait"
    assert list(_GAIT_NAMES) == list(gait.GAITS)
    assert "reference" in dyn.TASK_SEMANTIC_FIELDS


def test_a_task_carries_its_gait_and_the_worker_names_it() -> None:
    api = _api()
    parts, spine, legs, motor, model = _legged(api)
    feet = [parts[n] for n in ("lf", "rf", "lh", "rh")]
    trot = api.gait(feet, gait="trot", speed_mm_s=800, stride_length_mm=300,
                    spine=spine, spine_amplitude_deg=4, label="cruise")
    task = _task(api, model, motor, reference=trot)
    assert task.properties["reference"] is trot
    assert "reference" not in _task(api, model, motor).properties
    outputs = {id(c): n for n, c in parts.items()}
    resolved = _gait_input(trot, outputs, {id(spine): "j_spine"})
    assert resolved == {
        "label": "cruise", "gait": "trot", "speed_mm_s": 800.0,
        "feet": {"LF": "lf", "RF": "rf", "LH": "lh", "RH": "rh"},
        "stride_length_mm": 300.0, "spine_amplitude_deg": 4.0, "spine_joint": "j_spine"}
    explicit = api.gait(feet, offsets={"LF": 0.5, "RF": 0.0, "LH": 0.0, "RH": 0.5},
                        duty=0.5, speed_mm_s=600)
    assert _gait_input(explicit, outputs, {})["offsets"] == {
        "LF": 0.5, "RF": 0.0, "LH": 0.0, "RH": 0.5}


def test_the_script_surface_refuses_a_gait_it_cannot_honour() -> None:
    api = _api()
    parts, spine, legs, motor, model = _legged(api)
    feet = [parts[n] for n in ("lf", "rf", "lh", "rh")]
    with pytest.raises(ValueError, match="exactly four"):
        api.gait(feet[:3], gait="trot", speed_mm_s=800)
    with pytest.raises(ValueError, match="must be one of"):
        api.gait(feet, gait="amble", speed_mm_s=800)
    with pytest.raises(ValueError, match="name a gait"):
        api.gait(feet, speed_mm_s=800)
    with pytest.raises(ValueError, match="both offsets and duty"):
        api.gait(feet, offsets={"LF": 0, "RF": 0, "LH": 0, "RH": 0}, speed_mm_s=800)
    with pytest.raises(ValueError, match="expected"):
        api.gait(feet, offsets={"LF": 0, "RF": 0}, duty=0.5, speed_mm_s=800)
    with pytest.raises(ValueError, match="spine="):
        api.gait(feet, gait="trot", speed_mm_s=800, spine_amplitude_deg=5)
    with pytest.raises(ValueError, match="greater than 0"):
        api.gait(feet, gait="trot", speed_mm_s=0)
    stranger = api.component(_source("stranger"))
    lost = api.gait([stranger, *feet[1:]], gait="trot", speed_mm_s=800)
    with pytest.raises(ValueError, match="reference.feet"):
        _task(api, model, motor, reference=lost)


@pytest.fixture(scope="module")
def keyed():
    """The ADR-702 quadruped with its standing pose as the 'solved' keyframe."""

    model = mujoco.MjModel.from_xml_string(QUADRUPED)
    data = mujoco.MjData(model)
    home = model.qpos0.copy()
    for side in ("lf", "rf", "lh", "rh"):
        home[model.jnt_qposadr[model.joint(f"hip_{side}").id]] = np.radians(35)
        home[model.jnt_qposadr[model.joint(f"knee_{side}").id]] = np.radians(-70)
    data.qpos[:] = home
    mujoco.mj_kinematics(model, data)
    lowest = min(data.geom_xpos[model.geom(f"pad_{s}").id][2] for s in ("lf", "rf", "lh", "rh"))
    home[2] -= lowest - 0.02
    spec = mujoco.MjSpec.from_string(QUADRUPED)
    spec.add_key(name="solved", qpos=list(home))
    return spec.compile(), home


def _declared(**extra):
    return {"label": "trot", "gait": "trot", "speed_mm_s": 800.0, "feet": dict(LEGS), **extra}


def test_the_bundle_reference_is_the_stride_and_its_poses(keyed) -> None:
    model, home = keyed
    clip = dyn._reference_records(mujoco, model, _declared(stride_length_mm=300.0),
                                  {"reset_keyframe": "solved"}, context="t")
    assert clip["schema"] == gait.SCHEMA and clip["reset_keyframe"] == "solved"
    assert clip["parameters"]["stride_length_m"] == pytest.approx(0.3)
    assert len(clip["placements"]) == clip["samples"]
    # the stride is built about the keyframe: the first sample's trunk height is the key's
    assert clip["qpos"][0][2] == pytest.approx(home[2], abs=1e-9)
    # every body is posed, and the posed feet are on the clip's own targets
    named = {model.body(b).name for b in range(1, model.nbody)}
    data = mujoco.MjData(model)
    for k, frame in enumerate(clip["placements"]):
        assert set(frame) == named
        data.qpos[:] = clip["qpos"][k]
        mujoco.mj_kinematics(model, data)
        for foot, body in LEGS.items():
            pose = frame[body]
            assert np.allclose(pose["position_mm"], 1000 * data.xpos[model.body(body).id], atol=1e-3)
            pad = data.geom_xpos[model.geom(f"pad_{body[-2:]}").id]
            assert np.linalg.norm(pad - clip["foot_positions_m"][foot][k]) < gait.TOLERANCE_M
        w, x, y, z = data.xquat[model.body("torso").id]
        assert np.allclose(frame["torso"]["rotation_xyzw"], [x, y, z, w], atol=1e-6)


def test_an_unreachable_reference_refuses_the_task_with_the_reason(keyed) -> None:
    model, _home = keyed
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn._reference_records(mujoco, model, _declared(stride_length_mm=2000.0),
                               {"reset_keyframe": "solved"}, context="task output 't'")
    assert raised.value.reason == "gait_unreachable"
    assert "cannot be generated" in str(raised.value)
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn._reference_records(mujoco, model, _declared(feet={**LEGS, "LF": "nowhere"}),
                               {"reset_keyframe": "solved"}, context="t")
    assert raised.value.reason == "gait_unknown_body"


def test_placements_refuse_a_clip_from_another_model(keyed) -> None:
    model, _home = keyed
    with pytest.raises(gait.GaitError) as raised:
        gait.placements(model, {"qpos": [[0.0] * (model.nq - 1)]}, mujoco=mujoco)
    assert raised.value.reason == "clip_model_mismatch"
