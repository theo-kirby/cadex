# SPDX-License-Identifier: LGPL-2.1-or-later

"""What MJX, numpy and Python actually do (docs/MUJOCO.md M7, phase 0).

Nothing here imports the M7 surface, so a failure names MuJoCo, MJX or the
standard library rather than anything we wrote. The M2--M6 shape: the phase
that measures comes before the phase that builds, and every finding that
contradicted the plan is recorded here rather than quietly absorbed.

**Two environments, on purpose.** Training is offboard by design (ADR-075),
so ``jax`` and ``mujoco.mjx`` are deliberately *not* in the engine's pixi
environment and never enter ``pixi.toml`` -- ``test_engine_purity_guardrails``
asserts they reach no payload. The measurements that need them are therefore
gated on an import and skip in the engine environment; they were run for real
in a venv built from ``training/requirements.txt``, and the numbers they
assert are the numbers that run produced. The measurements that need only
numpy or the standard library run everywhere and always.

Four findings changed the design before it was written, which is what a
phase 0 is for. They are called out at their tests.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


def _mjx():
    """MJX, or a skip that says why it is legitimately absent."""

    return pytest.importorskip(
        "mujoco.mjx",
        reason=(
            "MJX is the offboard trainer's dependency and is deliberately "
            "absent from the engine environment (ADR-075, ADR-084). Run this "
            "file from a venv built from training/requirements.txt to "
            "re-measure."
        ),
    )


# ---------------------------------------------------------------------------
# 1. Does MJX load our exported models at all?
#
# THE GO/NO-GO OF THE SLICE. If MJX could not carry an equality constraint or
# a mesh geom, the trainer would fall back to batched CPU `mujoco.rollout`
# and the plan would have changed here, before code. It can carry both.
# ---------------------------------------------------------------------------


def _exported(built, observations=()):
    exported = dyn.export_mjcf(built, observations=list(observations))
    return mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))


def _cpu_qpos(model, steps):
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    if key >= 0:
        mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    for _ in range(steps):
        mujoco.mj_step(model, data)
    return [float(value) for value in data.qpos], int(data.ncon)


def _mjx_qpos(model, steps):
    mjx = _mjx()
    import jax
    import jax.numpy as jnp

    handle = mjx.put_model(model)
    data = mjx.make_data(handle)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    if key >= 0:
        data = data.replace(qpos=jnp.asarray(model.key_qpos[key]))
    data = mjx.forward(handle, data)
    step = jax.jit(mjx.step)
    for _ in range(steps):
        data = step(handle, data)
    return [float(value) for value in data.qpos]


def test_mjx_carries_the_equality_constraint_that_closes_a_four_bar() -> None:
    """The first of two candidates that could have sunk MJX for us.

    A four-bar is a kinematic *loop*, and MuJoCo is a tree plus equality
    constraints -- so M2 closes it with ``equality/connect``. Measured: MJX
    accepts the model and its five steps land within 4e-8 of stock CPU
    MuJoCo's.
    """

    model = _exported(dyn.build_model(*fx.four_bar()[:2]))
    assert model.neq == 1
    assert int(model.eq_type[0]) == int(mujoco.mjtEq.mjEQ_CONNECT)

    cpu, _ = _cpu_qpos(model, 5)
    accelerated = _mjx_qpos(model, 5)
    assert len(accelerated) == len(cpu) == 3
    drift = max(abs(a - b) for a, b in zip(accelerated, cpu))
    assert drift < 1.0e-6, f"MJX and CPU MuJoCo disagree by {drift:g}"


def test_mjx_carries_a_mesh_geom_and_the_contact_it_makes() -> None:
    """The second candidate, and the one that needed real contact to measure.

    A model that merely *holds* a mesh geom proves nothing about mesh
    collision -- the first run of this measurement stepped 20 times, made
    zero contacts, and would have reported success. So this drops a free box
    onto a slab and asserts contacts actually happened.

    Measured, 400 steps: box-box agrees with CPU to 1.3e-5 m, mesh-box to
    3.4e-4 m -- 0.34 mm, and the block settles 0.12 mm lower under MJX.
    **Recorded rather than treated as a defect**: MJX is float32 with its own
    contact path, training happens there and evaluation happens on CPU, and a
    policy that could not survive 0.1 mm of contact difference is not a
    policy. It is a fidelity note for M8, not a blocker for M7.
    """

    _mjx()
    components, joints, _ = fx.build(
        [
            {"name": "slab", "grounded": True, "size": (600.0, 600.0, 40.0),
             "collision": {"shapes": [fx.collision_shape(
                 "box", size_mm=[600.0, 600.0, 40.0])], "mesh": None}},
            {"name": "block", "size": (100.0, 100.0, 40.0),
             "world": [1.0, 0.0, 0.0, 3.0, 0.0, 1.0, 0.0, 2.0,
                       0.0, 0.0, 1.0, 120.0, 0.0, 0.0, 0.0, 1.0],
             "collision": {"shapes": [fx.collision_shape(
                 "mesh", deflection_mm=0.25)],
                 "mesh": fx.box_mesh(100.0, 100.0, 40.0)}},
        ],
        [],
    )
    model = _exported(dyn.build_model(components, joints))
    assert model.nmesh == 1
    assert int(mujoco.mjtGeom.mjGEOM_MESH) in [int(t) for t in model.geom_type]

    cpu, contacts = _cpu_qpos(model, 400)
    assert contacts > 0, "the fixture never touched the slab, so nothing was measured"
    accelerated = _mjx_qpos(model, 400)
    settled = abs(accelerated[2] - cpu[2]) * dyn.MM_PER_METRE
    assert settled < 1.0, f"MJX settled {settled:g} mm from CPU MuJoCo"


def test_mjx_carries_position_actuators_and_joint_limits() -> None:
    """The third fixture: the two-link arm M4 and M6 both measured against."""

    _mjx()
    components, joints, _ = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components, joints,
        actuators=[
            {"joint": "elbow", "motion_type": "angular", "kind": "motor",
             "control_nmm": "0", "torque_limit_nmm": 800.0},
            {"joint": "shoulder", "motion_type": "angular", "kind": "position",
             "control_deg": "10", "stiffness_nmm_per_deg": 4000.0,
             "damping_nmms_per_deg": 120.0},
        ],
    )
    model = _exported(built)
    assert model.nu == 2
    assert any(bool(value) for value in model.jnt_limited)

    cpu, _ = _cpu_qpos(model, 5)
    accelerated = _mjx_qpos(model, 5)
    drift = max(abs(a - b) for a, b in zip(accelerated, cpu))
    assert drift < 1.0e-6, f"MJX and CPU MuJoCo disagree by {drift:g}"


# ---------------------------------------------------------------------------
# 2. Does MJX produce sensordata for every observation kind we offer?
#
# ADR-083's central decision was that *MuJoCo computes the observation
# vector*, so that nothing on the path needs shipping. If MJX evaluated no
# sensors, the trainer would need a fourth implementation of every channel
# -- the exact thing M6 exists to avoid. It evaluates all of them.
#
# The list below is checked against `OBSERVATION_KINDS` rather than counted,
# and that is a repair rather than a flourish: it was written as eight rows
# and ADR-112 added a ninth kind without adding a row, so a test named
# "every observation kind the task surface offers" quietly stopped covering
# them all. It is MJX-gated, so `pixi run test-engine` could not have said
# so. ADR-116 adds a tenth and makes the omission impossible instead.
# ---------------------------------------------------------------------------

_EVERY_KIND = [
    {"kind": "position", "joint": "elbow", "motion_type": "angular", "name": "a"},
    {"kind": "velocity", "joint": "elbow", "motion_type": "angular", "name": "b"},
    {"kind": "actuator_force", "joint": "elbow", "motion_type": "angular",
     "actuator_kind": "motor", "name": "c"},
    {"kind": "component_position", "component": "fore", "name": "d"},
    {"kind": "component_orientation", "component": "fore", "name": "e"},
    {"kind": "component_linear_velocity", "component": "fore", "name": "f"},
    {"kind": "component_angular_velocity", "component": "fore", "name": "g"},
    {"kind": "centre_of_mass", "component": "upper", "name": "h"},
    {"kind": "centre_of_mass_velocity", "component": "upper", "name": "i"},
    {"kind": "centroidal_angular_momentum", "component": "upper", "name": "j"},
]


def _arm_with_every_kind():
    components, joints, _ = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components, joints,
        actuators=[{"joint": "elbow", "motion_type": "angular", "kind": "motor",
                    "control_nmm": "0", "torque_limit_nmm": 800.0}],
    )
    records = dyn.observation_records(
        list(_EVERY_KIND), built["tree"], built["joint_records"], built["actuators"]
    )
    return _exported(built, records), records


def test_mjx_evaluates_every_observation_kind_the_task_surface_offers() -> None:
    """Every kind, per channel, against stock CPU MuJoCo.

    Asserted **per channel** rather than on the whole array: an all-zero
    sensordata would pass a norm comparison against a mechanism at rest, and
    the failure this guards against is precisely one kind silently reading
    zero under MJX. Measured worst disagreement across the eight kinds this
    started with: 3.5e-7.

    The set comparison is the guard on the guard. A kind added to
    `OBSERVATION_KINDS` with no row here fails this immediately, rather than
    leaving a test whose *name* claims coverage it lost -- which is what
    happened between ADR-112 and ADR-116.
    """

    mjx = _mjx()
    import jax
    import jax.numpy as jnp

    model, records = _arm_with_every_kind()
    assert {str(record["kind"]) for record in records} == set(dyn.OBSERVATION_KINDS)

    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, key)
    data.ctrl[:] = 0.3
    for _ in range(20):
        mujoco.mj_step(model, data)
    cpu = [float(value) for value in data.sensordata]

    handle = mjx.put_model(model)
    accelerated = mjx.make_data(handle).replace(
        qpos=jnp.asarray(model.key_qpos[key]),
        ctrl=jnp.full((model.nu,), 0.3),
    )
    accelerated = mjx.forward(handle, accelerated)
    step = jax.jit(mjx.step)
    for _ in range(20):
        accelerated = step(handle, accelerated)
    produced = [float(value) for value in accelerated.sensordata]

    assert len(produced) == len(cpu) == int(model.nsensordata)
    for record in records:
        # `adr` is resolved by task_records against the *reloaded* file; this
        # measurement predates a task, so the address comes from the model
        # directly, by the sensor name the record already names.
        sensor = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_SENSOR, str(record["mujoco_sensor"])
        )
        assert sensor >= 0, (
            f"the exported file carries no {record['mujoco_sensor']!r}"
        )
        adr, dim = int(model.sensor_adr[sensor]), int(record["dim"])
        theirs = cpu[adr:adr + dim]
        ours = produced[adr:adr + dim]
        worst = max(abs(a - b) for a, b in zip(ours, theirs))
        assert worst < 1.0e-5, f"{record['kind']} disagrees by {worst:g}"
        if any(abs(value) > 1.0e-9 for value in theirs):
            assert any(abs(value) > 1.0e-9 for value in ours), (
                f"{record['kind']} reads zero under MJX where CPU MuJoCo "
                "reads a value"
            )


def test_mjx_sensordata_vectorises_and_the_first_environment_matches_one() -> None:
    """Eight environments at once, and element zero equal to the lone run.

    ``vmap`` over ``mjx.step`` is the whole reason to train on MJX, and a
    batch whose first member disagrees with an unbatched run would make every
    number this file measured meaningless. Measured: **exactly 0.0** apart.
    """

    mjx = _mjx()
    import jax
    import jax.numpy as jnp

    model, _records = _arm_with_every_kind()
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    handle = mjx.put_model(model)

    def run(data):
        data = mjx.forward(handle, data)
        for _ in range(20):
            data = mjx.step(handle, data)
        return data

    lone = jax.jit(run)(mjx.make_data(handle).replace(
        qpos=jnp.asarray(model.key_qpos[key]),
        ctrl=jnp.full((model.nu,), 0.3),
    ))
    batch = jax.vmap(lambda q: mjx.make_data(handle).replace(
        qpos=q, ctrl=jnp.full((model.nu,), 0.3)))(
            jnp.tile(jnp.asarray(model.key_qpos[key]), (8, 1)))
    batch = jax.jit(jax.vmap(run))(batch)

    assert tuple(batch.sensordata.shape) == (8, int(model.nsensordata))
    worst = max(
        abs(float(a) - float(b))
        for a, b in zip(batch.sensordata[0], lone.sensordata)
    )
    assert worst == 0.0, f"the batch's first environment differs by {worst:g}"


# ---------------------------------------------------------------------------
# 3. Does a reward expression evaluate under jnp globals?
# ---------------------------------------------------------------------------


def test_every_whitelisted_function_exists_in_jax_numpy() -> None:
    """The bundle's ``functions`` array, resolved against ``jax.numpy``.

    This one needs no MJX and no GPU -- it is a fact about names -- so it
    runs in the engine environment too, by checking the spellings rather than
    the module. ``asin`` is the interesting row: ``jax.numpy`` spells it
    ``arcsin`` only, so the trainer maps both of the engine's spellings onto
    it and a task written with either works.
    """

    assert set(dyn.REWARD_FUNCTIONS) == {
        "abs", "arcsin", "arctan", "asin", "cos", "exp", "sin", "sqrt", "tanh",
    }
    jnp = pytest.importorskip("jax.numpy", reason="offboard trainer dependency")
    for name in dyn.REWARD_FUNCTIONS:
        spelling = "arcsin" if name == "asin" else name
        assert hasattr(jnp, spelling), f"jax.numpy has no {spelling}"


def test_a_reward_expression_traces_under_jit_and_vectorises_under_vmap() -> None:
    """Compiled once, evaluated under two globals dicts.

    The whole trainer rests on this: the bundle ships expressions as text,
    and PPO needs them differentiable-adjacent and batched. Measured against
    the engine's own float64 evaluator: **9.5e-8** relative.
    """

    pytest.importorskip("jax", reason="offboard trainer dependency")
    import jax
    import jax.numpy as jnp

    formula = (
        "-(hand_x - 300)**2 + tanh(rate/100) + exp(-abs(effort)) "
        "+ sqrt(abs(hand_x)) + sin(angle*pi/180)"
    )
    names = ["hand_x", "rate", "effort", "angle"]
    values = {"hand_x": 310.0, "rate": 50.0, "effort": 2.0, "angle": 30.0}

    engine = dyn.evaluate_reward(
        dyn.compile_reward(formula, names=names, context="probe"),
        values, context="probe",
    )

    table = {
        "__builtins__": {}, "pi": math.pi, "abs": jnp.abs, "sin": jnp.sin,
        "cos": jnp.cos, "asin": jnp.arcsin, "arcsin": jnp.arcsin,
        "arctan": jnp.arctan, "exp": jnp.exp, "sqrt": jnp.sqrt, "tanh": jnp.tanh,
    }
    code = compile(formula, "<reward>", "eval")

    def evaluate(hand_x, rate, effort, angle):
        return eval(code, table, {"hand_x": hand_x, "rate": rate,
                                  "effort": effort, "angle": angle})

    arguments = [jnp.float32(values[name]) for name in names]
    traced = float(jax.jit(evaluate)(*arguments))
    batched = jax.vmap(evaluate)(*[jnp.full((8,), value) for value in arguments])

    assert tuple(batched.shape) == (8,)
    assert abs(traced - engine) / abs(engine) < 1.0e-6
    assert abs(float(batched[0]) - traced) < 1.0e-4


# ---------------------------------------------------------------------------
# 4. Is np.savez byte-deterministic?
#
# FINDING THAT CONTRADICTS THE PLAN. The plan that scoped M7 said "No zip
# container, because np.savez stamps zip entries with an mtime and a project
# digest cannot depend on when a file was written (phase 0 measures this
# rather than asserting it)." Measured: it IS deterministic -- numpy writes a
# fixed date_time. The hand-rolled container is still right, for reasons that
# survive the measurement; the reason the plan gave does not, and is recorded
# as wrong rather than dropped.
# ---------------------------------------------------------------------------


def test_np_savez_is_byte_deterministic_which_the_plan_expected_it_not_to_be() -> None:
    numpy = pytest.importorskip("numpy")

    array = numpy.arange(16, dtype=numpy.float32).reshape(4, 4)
    first = io.BytesIO()
    numpy.savez(first, w=array)
    time.sleep(1.1)  # past any one-second zip timestamp granularity
    second = io.BytesIO()
    numpy.savez(second, w=array)

    assert first.getvalue() == second.getvalue(), (
        "np.savez is non-deterministic after all -- which would make the "
        "plan's stated reason for the hand-rolled container correct again"
    )


def test_the_container_is_deterministic_for_the_reasons_that_do_survive() -> None:
    """What actually decides the format, measured rather than argued.

    The engine reads this file inside a ``--safe-mode`` sandbox from a module
    that imports no numpy at all. A length-prefixed header and a flat float32
    blob need no zip parser and no ``allow_pickle`` flag that has to stay
    false, and they carry the schema, the task digest and the witness in one
    file rather than in a naming convention over several arrays.
    """

    header = {"schema": dyn.POLICY_SCHEMA, "network": {"kind": "mlp"}}
    weights = [0.5, -0.25, 1.0e-7]
    first = dyn.encode_policy(header, weights)
    time.sleep(1.1)
    second = dyn.encode_policy(dict(header), list(weights))

    assert first == second
    assert first.startswith(b"CXPOLICY1\n")
    assert dyn.decode_policy(first)["weights"] == pytest.approx(weights, rel=1e-6)
    # ...and no numpy anywhere in the module that reads it.
    source = Path(dyn.__file__).read_text(encoding="utf-8")
    assert "import numpy" not in source


# ---------------------------------------------------------------------------
# 5. What is a PPO policy actually made of, and how big?
#
# docs/MUJOCO.md 3.1 guessed "tens of megabytes". Measured, an MLP with its
# observation normaliser is three orders of magnitude smaller, and that
# number is what sizes MAXIMUM_POLICY_BYTES.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "observations,actions,hidden,parameters",
    [
        (2, 1, (32, 32), 1189),          # one hinge, swing-up: the CI gate
        (16, 2, (64, 64), 5410),         # a two-link arm
        (48, 12, (32, 32, 32, 32), 5228),  # brax PPO's own default
        (123, 23, (512, 256, 128), 230925),  # a humanoid gait
    ],
)
def test_a_policy_is_kilobytes_rather_than_the_megabytes_the_plan_guessed(
    observations: int, actions: int, hidden: tuple[int, ...], parameters: int
) -> None:
    widths = [observations, *hidden, actions]
    total = sum(a * b + b for a, b in zip(widths[:-1], widths[1:]))
    total += 2 * observations  # the normaliser: one mean and one std each
    assert total == parameters
    assert total * 4 < 1024 * 1024, "an MLP policy fits in a mebibyte"
    assert total <= dyn.MAXIMUM_POLICY_PARAMETERS
    assert total * 4 <= dyn.MAXIMUM_POLICY_BYTES


# ---------------------------------------------------------------------------
# 6. Does a numpy float64 forward pass reproduce the JAX float32 one?
#
# The number that became POLICY_WITNESS_TOLERANCE, measured rather than
# chosen -- the way M5's 1e-5 inertia bound was.
# ---------------------------------------------------------------------------


def _random_network(seed: int, observations: int, actions: int, hidden):
    rng = random.Random(seed)
    widths = [observations, *hidden, actions]
    shapes = list(zip(widths[:-1], widths[1:]))
    weights = [rng.uniform(-0.5, 0.5)
               for a, b in shapes for _ in range(a * b + b)]
    return shapes, weights


def test_the_witness_tolerance_is_above_what_two_implementations_actually_differ_by() -> None:
    """float32 JAX against float64 pure Python, over random observations.

    Measured: max **1.46e-5** relative, 2.16e-7 absolute on tanh-bounded
    outputs. Separately, JAX's own jitted and un-jitted evaluations of the
    same weights in the same process differ by ~1e-7 -- so no tolerance
    tighter than that is meaningful about anything. The pinned tolerance is
    seven times the worst of these.
    """

    assert dyn.POLICY_WITNESS_TOLERANCE == 1.0e-4
    assert dyn.POLICY_WITNESS_TOLERANCE > 1.46e-5

    pytest.importorskip("jax", reason="offboard trainer dependency")
    import jax
    import jax.numpy as jnp
    import numpy

    observations, actions, hidden = 16, 2, (64, 64)
    shapes, weights = _random_network(11, observations, actions, hidden)
    header = {
        "schema": dyn.POLICY_SCHEMA,
        "observations": [f"c{i}" for i in range(observations)],
        "network": {"kind": "mlp", "layers": [list(s) for s in shapes],
                    "activation": "tanh", "output": "tanh",
                    "output_scale": [1.0] * actions,
                    "output_bias": [0.0] * actions},
        "normaliser": {"mean": [0.0] * observations, "std": [1.0] * observations},
    }
    # Round to float32 first: that is what the container stores, so a witness
    # taken against unrounded weights would be about numbers that never land.
    weights = [float(numpy.float32(value)) for value in weights]

    layers = []
    cursor = 0
    for inputs, outputs in shapes:
        matrix = numpy.asarray(weights[cursor:cursor + inputs * outputs],
                               dtype=numpy.float32).reshape(inputs, outputs)
        cursor += inputs * outputs
        bias = numpy.asarray(weights[cursor:cursor + outputs],
                             dtype=numpy.float32)
        cursor += outputs
        layers.append((matrix, bias))

    def accelerated(vector):
        value = vector
        for index, (matrix, bias) in enumerate(layers):
            value = value @ jnp.asarray(matrix) + jnp.asarray(bias)
            if index < len(layers) - 1:
                value = jnp.tanh(value)
        return jnp.tanh(value)

    rng = random.Random(5)
    worst = 0.0
    for _ in range(64):
        sample = [rng.uniform(-4.0, 4.0) for _ in range(observations)]
        theirs = numpy.asarray(jax.jit(accelerated)(
            jnp.asarray(sample, dtype=jnp.float32)))
        ours = dyn.policy_forward(header, weights, sample)
        worst = max(worst, max(abs(float(a) - b) for a, b in zip(theirs, ours)))
    assert worst < dyn.POLICY_WITNESS_TOLERANCE, (
        f"the two implementations differ by {worst:g}, at or above the pinned "
        "tolerance"
    )


# ---------------------------------------------------------------------------
# 7. How slow is a pure-Python forward pass?
#
# CadexDynamics deliberately imports no numpy. The plan said numpy would
# enter the module deferred -- as scipy.spatial does -- *if* pure Python
# could not evaluate a policy at the control rate. Measured, it can, so it
# does not, and the module stays what its docstring says it is.
# ---------------------------------------------------------------------------


def test_pure_python_evaluates_a_policy_far_above_the_control_rate() -> None:
    """Measured: 219 us for an arm-sized network, 5.29 ms for a humanoid one.

    That is 4 564 Hz and 189 Hz against the 50 Hz the task surface
    encourages. The engine therefore needs no numpy to roll a policy out,
    which is the measurement that kept ``CadexDynamics`` numpy-free.
    """

    observations, actions, hidden = 16, 2, (64, 64)
    shapes, weights = _random_network(3, observations, actions, hidden)
    header = {
        "schema": dyn.POLICY_SCHEMA,
        "observations": [f"c{i}" for i in range(observations)],
        "network": {"kind": "mlp", "layers": [list(s) for s in shapes],
                    "activation": "tanh", "output": "tanh",
                    "output_scale": [1.0] * actions,
                    "output_bias": [0.0] * actions},
        "normaliser": {"mean": [0.0] * observations, "std": [1.0] * observations},
    }
    sample = [0.1 * index for index in range(observations)]

    dyn.policy_forward(header, weights, sample)  # warm the compile caches
    started = time.perf_counter()
    for _ in range(200):
        dyn.policy_forward(header, weights, sample)
    per_call = (time.perf_counter() - started) / 200

    assert per_call < 0.005, (
        f"a pure-Python forward pass costs {per_call * 1e6:.0f} us, which is "
        "too slow to evaluate at a 50 Hz control rate with margin -- numpy "
        "would have to enter CadexDynamics deferred, as scipy.spatial does"
    )


# ---------------------------------------------------------------------------
# 8. Is JAX-on-CPU reproducible across two processes at a fixed seed?
#
# Recorded either way, because the *rollout* determinism claim M8 depends on
# is a different claim -- it is MuJoCo's, and it must not inherit this one's
# answer by accident.
# ---------------------------------------------------------------------------


_JAX_REPRO_PROBE = """
import json, sys
import jax, jax.numpy as jnp
print(json.dumps({
    "prng": [repr(float(v)) for v in jax.random.normal(jax.random.PRNGKey(0), (4,))],
    "jitted": repr(float(jax.jit(lambda x: jnp.tanh(x @ x))(jnp.arange(8, dtype=jnp.float32)))),
    "backend": jax.default_backend(),
}, sort_keys=True))
"""


def test_jax_on_cpu_is_reproducible_across_two_processes_at_a_fixed_seed() -> None:
    """Measured: bit-identical, on CPU, for both the PRNG and a jitted pass.

    The honest expectation was yes on CPU and no on GPU, and that is why
    docs/MUJOCO.md 3.1 already says a policy is an *asset* rather than a
    derivation. This measurement does not change that: a GPU run is still not
    reproducible, and the policy still arrives as bytes with a digest.
    """

    pytest.importorskip("jax", reason="offboard trainer dependency")
    runs = [
        subprocess.run([sys.executable, "-c", _JAX_REPRO_PROBE],
                       capture_output=True, text=True, check=True).stdout.strip()
        for _ in range(2)
    ]
    assert runs[0] == runs[1], "JAX-on-CPU differed between two processes"
    assert json.loads(runs[0])["backend"] == "cpu"


# ---------------------------------------------------------------------------
# 9. How does per-episode randomisation vectorise?
# ---------------------------------------------------------------------------


def test_the_bundles_one_algorithm_extends_to_thousands_of_independent_draws() -> None:
    """``seed = base + index``, and the base reproduces the bundle exactly.

    The bundle states one algorithm -- ``random.Random(seed)`` drawing
    ``uniform(low, high)`` in bundle order -- which is one parameter set.
    Training needs thousands. The extension the trainer uses has to be
    *stated* in the container or a "reproducible" run is not, so this pins
    both halves: the draws are distinct, and index zero is the bundle's own.
    """

    entries = [{"label": "mass", "low": 0.8, "high": 1.2},
               {"label": "damping", "low": 0.5, "high": 1.5}]

    def draw(seed: int) -> tuple[float, ...]:
        rng = random.Random(int(seed))
        return tuple(rng.uniform(float(e["low"]), float(e["high"])) for e in entries)

    assert len({draw(seed) for seed in range(1000)}) == 1000
    assert draw(0) == draw(0)

    # ...and index zero is exactly what apply_randomisation would have done.
    model = _exported(dyn.build_model(*fx.four_bar()[:2]))
    task = {"randomisation": [
        {"label": "mass", "low": 0.8, "high": 1.2,
         "fields": [{"field": "body_mass", "index": 1}]},
        {"label": "damping", "low": 0.5, "high": 1.5,
         "fields": [{"field": "dof_damping", "index": 0}]},
    ]}
    drawn = dyn.apply_randomisation(mujoco, model, mujoco.MjData(model), task, seed=0)
    assert tuple(entry["factor"] for entry in drawn) == draw(0)


# ---------------------------------------------------------------------------
# Risk 4: how expensive is _asset_entry's full re-hash?
#
# Not M7's to fix -- but M8 adds rollouts on top of it, so the number is
# recorded now rather than discovered then.
# ---------------------------------------------------------------------------


def test_rehashing_the_whole_asset_budget_is_measured_rather_than_assumed() -> None:
    """``_asset_entry`` digests every asset in full on every ``put_asset``.

    Measured: sha256 runs at roughly 2.8 GB/s here, so the full 128 MB
    staging budget re-hashes in about 46 ms and a 21 KiB policy adds about
    0.01 ms. Visible but not a problem, and it does not grow with M7 -- a
    policy is three orders of magnitude smaller than the scan mesh it would
    sit beside.
    """

    blob = b"\x5a" * (16 * 1024 * 1024)
    started = time.perf_counter()
    hashlib.sha256(blob).hexdigest()
    elapsed = time.perf_counter() - started

    budget_ms = elapsed * (128 / 16) * 1000.0
    assert budget_ms < 1000.0, (
        f"re-hashing the 128 MB asset budget costs {budget_ms:.0f} ms, which "
        "is no longer invisible on every put_asset and every inspect "
        "scope=assets"
    )
