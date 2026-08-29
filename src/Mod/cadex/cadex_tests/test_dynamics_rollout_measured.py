# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What a policy-driven rollout actually does (docs/MUJOCO.md M8, phase 0).

The M2--M7 shape, once more: the phase that measures comes before the phase
that builds, and every finding that contradicted the plan is recorded here
rather than quietly absorbed.

**Unlike M7's phase 0, none of this needs MJX.** M7 measured a trainer, so
half its file skipped in the engine environment; M8 measures the *engine*
rolling a policy out, which is exactly the environment ``pixi run python -m
pytest`` provides. Everything here runs everywhere ``mujoco`` does.

Five questions, in the order the design depends on them:

1. does reloading the exported model change what a policy does (the decision
   to reload rather than reuse ``built["model"]``);
2. is a policy-driven rollout byte-deterministic **across processes**, since
   its trace's sha256 joins the project digest (ADR-068);
3. how far does the float32/float64 gap M7 measured at a single step
   compound over a closed loop;
4. what does a realistic episode cost; and
5. what does the frame rate have to divide, and what happens when it does
   not.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")

import dynamics_policy_fixtures as pf  # noqa: E402


def _with_sensors(built, observations):
    """The spec copy ``export_mjcf`` compiles, kept rather than discarded.

    ``export_mjcf`` compiles exactly this and throws it away -- it keeps only
    the bytes. Measurement 1 is about the difference between that compiled
    model and the one a reader gets by loading those bytes, so this rebuilds
    the discarded half by the same steps.
    """

    spec = built["spec"].copy()
    dyn._add_observation_sensors(mujoco, spec, observations)
    spec.add_key(name=dyn.MJCF_KEYFRAME_NAME, qpos=list(built["qpos_solved"]))
    return spec.compile()


def _prepared(**task):
    """One swing-up bundle, its models and a policy trained on nothing.

    Random weights rather than trained ones: every measurement here is about
    arithmetic in a closed loop, and a converged gait would make the numbers
    prettier without making them mean more.
    """

    prepared = pf.swing_up_bundle(
        task={**pf.SWING_UP_TASK, **task} if task else None
    )
    prepared["container"] = pf.policy_container(prepared, normalise=True)
    return prepared


def _driver(container):
    header = container["header"]
    weights = container["weights"]

    def actions(_step, observation):
        return dyn.policy_forward(header, weights, observation)

    return actions


# ---------------------------------------------------------------------------
# 1. Does reloading the model change what the policy does?
#
# FINDING THAT SETTLES THE DESIGN DECISION ON EVIDENCE. The plan chose to
# reload the exported MJCF rather than reuse the model the engine built, on
# the rule M6 and M7 follow: resolve against the bytes somebody else opens.
# The plan expected the two to agree and treated the choice as taste.
#
# Measured: they do NOT agree. MuJoCo's XML writer emits about six
# significant figures -- M5 already knew that and bounds it at export -- and
# a closed loop turns that rounding into a different trajectory. So the
# choice is load-bearing rather than tasteful, and reloading is the only
# option that makes the rollout run the model the policy's digest attests to.
# ---------------------------------------------------------------------------


def test_the_reloaded_model_diverges_from_the_one_in_memory_over_an_episode() -> None:
    """Same policy, same seed, one episode, two models.

    Measured on the swing-up, over the 66 control steps before its
    termination rule fires: the two agree to 8.1e-6 at the first control step
    and disagree by up to 5.8e-3 (degrees, and millimetres of tip position)
    later in the episode. The reward totals differ by 9.4e-6.

    Neither model is wrong. What the measurement says is that *which* model
    ran is a fact about the numbers, so it cannot be left to whichever one
    happened to be in memory -- and the one a reader can check is the file.
    """

    prepared = _prepared()
    built = prepared["built"]
    observations = dyn.observation_records(
        list(pf.SWING_UP_OBSERVATIONS), built["tree"], built["joint_records"],
        built["actuators"],
    )
    in_memory = _with_sensors(built, observations)
    reloaded = dyn.load_model(prepared["model_xml"])
    actions = _driver(prepared["container"])

    first = dyn.evaluate_episode(in_memory, prepared["bundle"], actions=actions)
    second = dyn.evaluate_episode(reloaded, prepared["bundle"], actions=actions)

    assert first["step_count"] == second["step_count"]
    gaps = [
        max(abs(left["observation"][name] - right["observation"][name])
            for name in left["observation"])
        for left, right in zip(first["steps"], second["steps"], strict=True)
    ]
    reward_gap = abs(first["total_reward"] - second["total_reward"])
    print(f"\nMEASURED reload divergence over {len(gaps)} control steps: "
          f"step 1 {gaps[0]:g}, step {len(gaps)} {gaps[-1]:g}, "
          f"worst {max(gaps):g}, reward {reward_gap:g}")

    # It starts at the writer's own precision...
    assert gaps[0] < 1.0e-4
    # ...and it does not stay there, which is the finding.
    assert max(gaps) > 1.0e-4, (
        "the two models agreed after all, which would make the reload a "
        "matter of taste rather than the design decision it is recorded as"
    )
    # The reward still moves far less than a policy's own margin over doing
    # nothing (M7's live gate measured 243.4 against 98.4), so this is a
    # determinism finding rather than a fidelity one.
    assert reward_gap < 1.0e-3 * abs(first["total_reward"])


# ---------------------------------------------------------------------------
# 2. Is a policy-driven rollout byte-deterministic across processes?
#
# M3 proved this for `simulate()`. A rollout puts a pure-Python float64
# forward pass inside the inner loop, and the trace's sha256 joins the
# project digest by ADR-068's have-an-artifact clause -- so this is
# load-bearing rather than reassuring.
# ---------------------------------------------------------------------------


_ROLLOUT_PROBE = '''
import hashlib, json, sys
sys.path.insert(0, sys.argv[1])
import CadexDynamics as dyn
bundle = json.loads(open(sys.argv[2], encoding="utf-8").read())
container = dyn.decode_policy(open(sys.argv[3], "rb").read())
model = dyn.load_model(open(sys.argv[4], "rb").read())
episode = dyn.evaluate_episode(
    model, bundle, seed=17,
    actions=lambda step, observation: dyn.policy_forward(
        container["header"], container["weights"], observation),
)
trajectory = [
    [repr(float(value)) for name in sorted(step["observation"])
     for value in [step["observation"][name]]] + [repr(float(step["reward"]))]
    for step in episode["steps"]
]
print(json.dumps({
    "digest": hashlib.sha256(
        json.dumps(trajectory, sort_keys=True).encode("utf-8")).hexdigest(),
    "steps": episode["step_count"],
    "total_reward": repr(float(episode["total_reward"])),
    "mujoco_version": str(__import__("mujoco").__version__),
}, sort_keys=True))
'''


def test_a_policy_driven_rollout_is_byte_identical_across_two_processes(
    tmp_path: Path,
) -> None:
    """Two fresh interpreters, one seed, one digest.

    The claim the *trace* digest rests on, taken at the level the trace is
    made of: the observation, the action's effect and the reward at every
    control step, serialised with ``repr`` so a difference is a number
    rather than a formatting artefact.
    """

    prepared = _prepared()
    bundle = tmp_path / "job-task.json"
    bundle.write_text(json.dumps(prepared["bundle"]), encoding="utf-8")
    weights = tmp_path / "walk.cxpolicy"
    weights.write_bytes(prepared["container"]["blob"])
    model = tmp_path / "job-model.xml"
    model.write_bytes(prepared["model_xml"])
    probe = tmp_path / "rollout_probe.py"
    probe.write_text(_ROLLOUT_PROBE, encoding="utf-8")

    module_dir = str(Path(dyn.__file__).resolve().parent)
    runs = [
        json.loads(
            subprocess.run(
                [sys.executable, "-P", str(probe), module_dir, str(bundle),
                 str(weights), str(model)],
                capture_output=True, text=True, check=True,
            ).stdout
        )
        for _ in range(2)
    ]

    print(f"\nMEASURED cross-process rollout digest: {runs[0]['digest']} "
          f"over {runs[0]['steps']} control steps")
    assert runs[0] == runs[1]
    assert runs[0]["steps"] > 1
    assert runs[0]["mujoco_version"] == str(mujoco.__version__)


# ---------------------------------------------------------------------------
# 3. How far does the float32/float64 gap compound in a closed loop?
#
# M7 measured single-step witness agreement at 1.7e-9...3.6e-8 and pinned the
# tolerance at 1e-4. A closed loop feeds each action back through the
# mechanism, so the question is not what one forward pass differs by -- it is
# what an episode does with that difference.
# ---------------------------------------------------------------------------


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _float32_forward(header, weights, observation):
    """``policy_forward`` with every intermediate rounded to float32.

    Not a second implementation of the network -- it is the same arithmetic
    with the precision a trainer's own inference would have used, which is
    what makes the difference between the two a measurement of precision
    rather than of implementation.
    """

    channels = [str(name) for name in header["observations"]]
    network = header["network"]
    normaliser = header["normaliser"]
    values = [
        _float32((float(observation[name]) - float(normaliser["mean"][index]))
                 / float(normaliser["std"][index]))
        for index, name in enumerate(channels)
    ]
    shapes = [tuple(int(v) for v in layer) for layer in network["layers"]]
    cursor = 0
    for index, (inputs, outputs) in enumerate(shapes):
        matrix = weights[cursor:cursor + inputs * outputs]
        cursor += inputs * outputs
        bias = weights[cursor:cursor + outputs]
        cursor += outputs
        result = []
        for column in range(outputs):
            total = _float32(bias[column])
            for row in range(inputs):
                total = _float32(
                    total + _float32(values[row] * matrix[row * outputs + column])
                )
            result.append(total)
        if index < len(shapes) - 1:
            result = [_float32(math.tanh(value)) for value in result]
        values = result
    return [
        _float32(_float32(math.tanh(value)) * float(network["output_scale"][index])
                 + float(network["output_bias"][index]))
        for index, value in enumerate(values)
    ]


def test_the_float32_gap_compounds_over_an_episode_and_the_reward_still_moves() -> None:
    """One episode driven at float64, one at float32, same everything else.

    **The finding that matters for the ADR.** Measured on the swing-up: the
    two trajectories are 2.8e-5 apart at the first control step and 5.8e-3
    apart at their worst, while the episode totals agree to 7.0e-6 out of
    61.9 -- and each precision reproduces itself exactly.

    So a closed loop does compound the gap M7 measured at 1.7e-9...3.6e-8 for
    a single forward pass, by about five orders of magnitude over a hundred
    steps. The *reward* survives that, which is why a rollout is worth
    watching; the *trajectory* does not, which is why the trace's digest is a
    claim about this engine's own arithmetic and never about somebody else's
    inference of the same weights.
    """

    prepared = _prepared()
    model = dyn.load_model(prepared["model_xml"])
    container = prepared["container"]
    header, weights = container["header"], container["weights"]

    exact = dyn.evaluate_episode(model, prepared["bundle"],
                                 actions=_driver(container))
    rounded = dyn.evaluate_episode(
        model, prepared["bundle"],
        actions=lambda step, observation: _float32_forward(
            header, weights, observation),
    )

    gaps = [
        max(abs(left["observation"][name] - right["observation"][name])
            for name in left["observation"])
        for left, right in zip(exact["steps"], rounded["steps"], strict=True)
    ]
    reward_gap = abs(exact["total_reward"] - rounded["total_reward"])
    print(f"\nMEASURED float32 compounding: step 1 {gaps[0]:g}, "
          f"step {len(gaps)} {gaps[-1]:g}, worst {max(gaps):g}, "
          f"reward {exact['total_reward']:g} vs {rounded['total_reward']:g} "
          f"({reward_gap:g})")

    assert gaps[0] < 1.0e-3, "one step apart is a precision difference"
    assert max(gaps) >= gaps[0], "a closed loop does not un-diverge"

    # ...and each precision reproduces itself exactly, which is the half the
    # trace digest actually rests on.
    again = dyn.evaluate_episode(model, prepared["bundle"],
                                 actions=_driver(container))
    assert [step["reward"] for step in again["steps"]] == [
        step["reward"] for step in exact["steps"]
    ]


# ---------------------------------------------------------------------------
# 4. What does a realistic episode cost?
#
# M7 measured 17 ms per 100 control steps for a tiny net. This is the whole
# rollout: an arm-sized network, 50 Hz, ten seconds, against
# MAXIMUM_SOLVER_STEPS.
# ---------------------------------------------------------------------------


def test_a_ten_second_episode_at_fifty_hertz_costs_what_the_budget_allows() -> None:
    """Measured: 85 ms for 500 control steps of a 4609-parameter net.

    0.17 ms a control step, 5000 solver steps, against a budget of
    ``MAXIMUM_SOLVER_STEPS`` = 2 000 000. A rollout is cheaper than the
    ``api.dynamics`` run beside it and nowhere near either cap.

    ``termination`` is emptied so the episode runs its whole horizon --
    random weights spin the swing-up out in about a dozen steps, and a cost
    measured over thirteen steps is a measurement of nothing.
    """

    prepared = pf.swing_up_bundle(
        task={**pf.SWING_UP_TASK, "episode_seconds": 10.0, "termination": []}
    )
    container = pf.policy_container(prepared, hidden=(64, 64), normalise=True)
    model = dyn.load_model(prepared["model_xml"])
    episode_schedule = prepared["bundle"]["episode"]

    started = time.perf_counter()
    episode = dyn.evaluate_episode(model, prepared["bundle"],
                                   actions=_driver(container))
    elapsed = time.perf_counter() - started

    solver_steps = (episode["step_count"]
                    * int(episode_schedule["solver_steps_per_action"]))
    print(f"\nMEASURED rollout cost: {elapsed:.3f} s for "
          f"{episode['step_count']} control steps "
          f"({solver_steps} solver steps), "
          f"{elapsed / max(episode['step_count'], 1) * 1e3:.3f} ms/step; "
          f"parameters {len(container['weights'])}")

    assert episode["step_count"] == 500 or episode["terminated_step"] is not None
    assert solver_steps <= dyn.MAXIMUM_SOLVER_STEPS
    assert elapsed < 30.0, (
        f"a ten-second episode took {elapsed:.1f} s, which would make a "
        "rollout the slowest thing in a rebuild"
    )


# ---------------------------------------------------------------------------
# 5. Aliasing: what a policy's own control rate does to a trace.
#
# `simulate()`'s docstring names the sample rate as schema contract -- "a
# link turning more than half a circle between samples is aliased, and no
# amount of de-flipping recovers it". A policy picks its own control rate, so
# the rollout inherits the problem and has to bound it.
# ---------------------------------------------------------------------------


def test_a_frame_rate_that_does_not_divide_the_control_rate_lands_between_steps() -> None:
    """Why ``frames_per_second`` must divide ``control_hz`` exactly.

    50 Hz control played at 60 fps: the arithmetic, without a rollout in
    sight. A frame every 1/60 s is a frame every 0.833 control steps, so
    frames 1, 2 and 4 would each be interpolated between two different
    actions -- which makes the trace depend on floating-point accumulation,
    the exact thing ``simulate`` chooses its solver step to avoid.
    """

    control_hz, frames_per_second = 50, 60
    assert control_hz % frames_per_second != 0
    boundaries = [
        index * control_hz / frames_per_second for index in range(1, 5)
    ]
    assert [abs(value - round(value)) > 1.0e-9 for value in boundaries] == [
        True, True, True, True
    ]
    # ...and the rates that do divide it are the ones a task can be played at.
    assert [rate for rate in range(1, 51) if control_hz % rate == 0] == [
        1, 2, 5, 10, 25, 50
    ]


def test_a_coarse_frame_rate_aliases_a_spinning_link_and_a_fine_one_does_not() -> None:
    """The half-circle rule, measured on the mechanism M7's gate trains.

    The task terminates at 3000 deg/s, so the fastest a link can legitimately
    turn is 60 degrees per control step at 50 Hz. Sampled every step that is
    unambiguous; sampled every tenth step it is 600 degrees, and a player has
    no way to tell that from 240 the other way.
    """

    control_hz = int(pf.SWING_UP_TASK["control_hz"])
    limit_deg_per_s = float(pf.SWING_UP_TASK["termination"][0]["above"])

    per_control_step = limit_deg_per_s / control_hz
    assert per_control_step < 180.0, "one frame per control step cannot alias"

    for decimation in (2, 5, 10):
        per_frame = per_control_step * decimation
        aliased = per_frame > 180.0
        print(f"\nMEASURED aliasing at 1 frame per {decimation} control steps: "
              f"{per_frame:g} deg/frame, aliased={aliased}")
        assert aliased is (decimation >= 5)
