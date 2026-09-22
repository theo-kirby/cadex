# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Did Robin stay up? One seed's trace, read against the ot9 bar.

The ot9 contract (``docs/probes/ot9/README.md``, ``contract.json``) passes a
policy only if every evaluation seed runs the full episode, never fires
``fallen``, and keeps the free base within 30 degrees of the attitude the
accepted solved pose gave it. Reward says none of that. This reads the
numbers the bar is written in, from the trace the engine exported, and
changes nothing: no rebuild, no rollout, no training.

Two trace dialects, one reading:

* **rollout** -- ``assembly-simulation-trace.json`` from ``cadex params`` on a
  policy revision: ``frames`` (an untimed ``input`` frame, then one
  ``solver_output`` frame per control step) with the episode, the policy and
  the digests in its ``policy`` block. This is what the ten seeds produce.
* **smoke** -- ``smoke-trace.json`` from ``cadex smoke``, a list of sampled
  poses with no policy, read beside the ``smoke.json`` receipt that carries
  its termination and digests. It is how the no-policy fall is re-measured,
  and it can never pass: there is no policy in it.

Tilt is the angle between the base's local +Z now and its local +Z in the
model's ``solved`` keyframe -- the reference ``cadex smoke``'s support check
uses (ADR-377), so a yaw is not a tilt and a base modelled lying down reads
zero while it lies there. The reference comes from the model, never from the
trace's first frame, because a rollout's first frame is the *reset* pose,
already tilted by the task's reset variation. Height is the base frame's
world Z, which is the quantity ``fallen`` reads (``chassis_pos_z``).

    pixi run python docs/probes/ot9/runner/balance_eval.py \\
        --model robin_model-model.xml TRACE.json [TRACE.json ...] \\
        [--expect-mjcf SHA] [--expect-task SHA] [--out report.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "ot9-balance-eval-v1"
CONTRACT = Path(__file__).resolve().parents[1] / "contract.json"


def _mujoco():
    import mujoco  # noqa: PLC0415 - deferred so the arithmetic tests need none

    return mujoco


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bar() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {**contract["bar"], "seeds": list(contract["evaluation_seeds"])}


# -- attitude ---------------------------------------------------------------

def up_vector_xyzw(quat_xyzw) -> tuple[float, float, float]:
    """A body's local +Z in world coordinates, from an ``[x, y, z, w]`` quaternion."""

    x, y, z, w = (float(v) for v in quat_xyzw)
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return (2.0 * (x * z + w * y), 2.0 * (y * z - w * x), 1.0 - 2.0 * (x * x + y * y))


def tilt_degrees(quat_xyzw, reference_xyzw) -> float:
    """How far a body's +Z has turned away from its reference +Z."""

    a, b = up_vector_xyzw(quat_xyzw), up_vector_xyzw(reference_xyzw)
    dot = sum(p * q for p, q in zip(a, b))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def reference_attitude(model_path: Path, keyframe: str = "solved") -> tuple[str, list[float]]:
    """The free base's name and its ``[x, y, z, w]`` attitude in ``keyframe``.

    An empty ``<key>`` means ``qpos0``, which MuJoCo fills in for us; that is
    why this asks MuJoCo rather than parsing the XML.
    """

    mujoco = _mujoco()
    model = mujoco.MjModel.from_xml_path(str(model_path))
    free = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
    if len(free) != 1:
        raise SystemExit(f"{model_path} has {len(free)} free joints; the bar reads exactly one base")
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, keyframe)
    if key < 0:
        raise SystemExit(f"{model_path} carries no {keyframe!r} keyframe")
    joint = free[0]
    adr = int(model.jnt_qposadr[joint])
    w, x, y, z = (float(v) for v in model.key_qpos[key][adr + 3:adr + 7])
    base = str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(model.jnt_bodyid[joint])))
    return base, [x, y, z, w]


# -- traces -----------------------------------------------------------------

def load_trace(path: Path) -> dict[str, Any]:
    """Normalise either dialect to ``{dialect, samples, episode, digests}``.

    ``samples`` is ``[(time_s, placements)]`` in time order. ``episode`` holds
    what the engine said about how the episode ended; the reader never infers
    a termination from the poses.
    """

    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "frames" in raw:
        policy = raw.get("policy") or {}
        dynamics = raw.get("dynamics") or {}
        samples = [
            (float(frame["nominal_time_s"]), frame["component_placements"])
            for frame in raw["frames"]
            if frame.get("frame_kind") == "solver_output"
        ]
        control_hz = dynamics.get("control_hz")
        steps = policy.get("step_count")
        return {
            "dialect": "rollout",
            "samples": samples,
            "episode": {
                "seed": policy.get("seed"),
                "steps": steps,
                "control_hz": control_hz,
                "steps_per_frame": dynamics.get("steps_per_frame"),
                "duration_s": (steps / control_hz) if steps is not None and control_hz else None,
                "termination": str(policy.get("termination") or ""),
                "terminated_step": policy.get("terminated_step"),
                "truncated": bool(policy.get("truncated")),
                "total_reward": policy.get("total_reward"),
            },
            "digests": {
                "policy_sha256": policy.get("policy_sha256"),
                "mjcf_sha256": policy.get("model_sha256"),
                "task_sha256": policy.get("task_sha256"),
            },
        }
    if isinstance(raw, list):
        receipt_path = path.with_name("smoke.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        fired = ((receipt.get("checks") or {}).get("termination") or {}).get("fired") or []
        first = min(fired, key=lambda row: float(row["at_s"])) if fired else None
        fps = int(receipt["frames_per_second"])
        samples = [(float(row["time_s"]), row["placements"]) for row in raw]
        return {
            "dialect": "smoke",
            "samples": samples,
            "episode": {
                "seed": None,
                "steps": len(samples) - 1,
                "control_hz": fps,
                "steps_per_frame": 1,
                "duration_s": float(receipt["simulated_seconds"]),
                "termination": str(first["label"]) if first else "",
                "terminated_at_s": float(first["at_s"]) if first else None,
                # A smoke runs its whole duration whatever fires; it is not a
                # truncated episode, and nothing reads it as one.
                "truncated": False,
                "total_reward": None,
            },
            "digests": {
                "policy_sha256": None,
                "mjcf_sha256": (receipt.get("model") or {}).get("sha256"),
                "task_sha256": (receipt.get("task") or {}).get("sha256"),
            },
        }
    raise SystemExit(f"{path} is neither a rollout trace nor a smoke trace")


def measure(samples, base: str, reference_xyzw) -> dict[str, Any]:
    """Peak tilt and minimum base height over every sample, with their times."""

    if not samples:
        raise SystemExit("the trace has no timed frames")
    peak = (-1.0, None)
    low = (math.inf, None)
    for time_s, placements in samples:
        if base not in placements:
            raise SystemExit(f"frame at {time_s} s carries no pose for {base!r}")
        pose = placements[base]
        tilt = tilt_degrees(pose["rotation_xyzw"], reference_xyzw)
        height = float(pose["position_mm"][2])
        if tilt > peak[0]:
            peak = (tilt, time_s)
        if height < low[0]:
            low = (height, time_s)
    last_time, last = samples[-1]
    return {
        "frames": len(samples),
        "first_time_s": samples[0][0],
        "last_time_s": last_time,
        "peak_tilt_degrees": peak[0],
        "peak_tilt_time_s": peak[1],
        "final_tilt_degrees": tilt_degrees(last[base]["rotation_xyzw"], reference_xyzw),
        "min_chassis_height_mm": low[0],
        "min_chassis_height_time_s": low[1],
    }


def evaluate(trace_path: Path, model_path: Path, *, expect_mjcf: str | None = None,
             expect_task: str | None = None, the_bar: dict[str, Any] | None = None,
             base: str | None = None, reference_xyzw=None) -> dict[str, Any]:
    """One seed's report, in the contract's ``per_seed_report`` shape, plus why.

    ``base`` and ``reference_xyzw`` default to the model's free base and its
    ``solved`` attitude; they are parameters so the arithmetic can be pinned
    without MuJoCo.
    """

    the_bar = the_bar or bar()
    if base is None or reference_xyzw is None:
        base, reference_xyzw = reference_attitude(Path(model_path))
    trace = load_trace(Path(trace_path))
    episode, digests = trace["episode"], trace["digests"]
    measured = measure(trace["samples"], base, reference_xyzw)
    model_sha = digest(Path(model_path))

    void: list[str] = []
    if digests["mjcf_sha256"] != model_sha:
        void.append(f"the trace ran model {digests['mjcf_sha256']}, not the model read ({model_sha})")
    if expect_mjcf and digests["mjcf_sha256"] != expect_mjcf:
        void.append(f"model {digests['mjcf_sha256']} is not the accepted pin {expect_mjcf}")
    if expect_task and digests["task_sha256"] != expect_task:
        void.append(f"task {digests['task_sha256']} is not the accepted pin {expect_task}")

    failing: list[str] = []
    if trace["dialect"] != "rollout" or not digests["policy_sha256"]:
        failing.append("no policy: only a policy rollout can pass")
    if episode["control_hz"] != the_bar["control_hz"]:
        failing.append(f"control rate {episode['control_hz']} Hz, bar {the_bar['control_hz']} Hz")
    if episode["steps_per_frame"] != 1:
        failing.append(f"one frame every {episode['steps_per_frame']} control steps; the bar reads every step")
    if episode["steps"] is not None and measured["frames"] != episode["steps"] + 1:
        failing.append(f"{measured['frames']} frames for {episode['steps']} steps; expected one per step plus reset")
    if episode["steps"] != the_bar["steps"]:
        failing.append(f"ran {episode['steps']} steps, bar {the_bar['steps']}")
    if episode["termination"] == the_bar["forbidden_termination"]:
        failing.append(f"{episode['termination']} fired")
    elif episode["termination"]:
        failing.append(f"terminated by {episode['termination']}")
    if trace["dialect"] == "rollout" and not episode["truncated"]:
        failing.append("did not end by truncation")
    if measured["peak_tilt_degrees"] > the_bar["max_tilt_degrees"]:
        failing.append(
            f"tilted {measured['peak_tilt_degrees']:.3f} deg at {measured['peak_tilt_time_s']:.3f} s "
            f"(limit {the_bar['max_tilt_degrees']:g} deg)")

    return {
        "schema": SCHEMA,
        "trace": str(trace_path),
        "dialect": trace["dialect"],
        "base": base,
        "reference_xyzw": list(reference_xyzw),
        "seed": episode["seed"],
        "steps": episode["steps"],
        "duration_s": episode["duration_s"],
        "termination": episode["termination"],
        "terminated_at_s": episode.get("terminated_at_s", (
            episode["terminated_step"] / episode["control_hz"]
            if episode.get("terminated_step") is not None and episode["control_hz"] else None)),
        "truncated": episode["truncated"],
        **measured,
        "total_reward": episode["total_reward"],
        **digests,
        "model_read_sha256": model_sha,
        "class": "void" if void else "completed",
        "void": void,
        "failing": failing,
        "pass": not void and not failing,
    }


def candidate_verdict(reports: list[dict[str, Any]], the_bar: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every contract seed, exactly once, each passing -- or it is not a pass."""

    the_bar = the_bar or bar()
    seeds = [r["seed"] for r in reports]
    wanted = list(the_bar["seeds"])
    missing = [s for s in wanted if s not in seeds]
    extra = [s for s in seeds if s not in wanted]
    duplicated = sorted({s for s in seeds if seeds.count(s) > 1})
    void = [r["seed"] for r in reports if r["class"] == "void"]
    failed = [r["seed"] for r in reports if r["class"] != "void" and not r["pass"]]
    if void or missing or extra or duplicated:
        verdict = "void" if void else "incomplete"
    else:
        verdict = "fail" if failed else "pass"
    return {"verdict": verdict, "seeds": seeds, "missing": missing, "extra": extra,
            "duplicated": duplicated, "void": void, "failed": failed,
            "passed": [r["seed"] for r in reports if r["pass"]]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--model", type=Path, required=True, help="the MJCF the traces ran")
    parser.add_argument("--expect-mjcf", help="the accepted MJCF sha256; any other is void")
    parser.add_argument("--expect-task", help="the accepted task sha256; any other is void")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    base, reference = reference_attitude(args.model)
    reports = [evaluate(t, args.model, expect_mjcf=args.expect_mjcf, expect_task=args.expect_task,
                        base=base, reference_xyzw=reference) for t in args.traces]
    result = {"schema": SCHEMA, "bar": bar(), "seeds": reports, "candidate": candidate_verdict(reports)}
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
