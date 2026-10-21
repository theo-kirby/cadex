"""orun15 P2 (O3, O7): score a hind-pair lag term per step on judged traces, before it is trained.

usage: pixi run python docs/probes/orun15/lag_term.py GALLOP_TASK_JSON MODEL_XML EVALUATION_DIR [...]

The clip asks RH to land 62.5 ms before LH (``clip-read.md``); the fast
policies land the hinds within 0-20 ms. Only ``track_contact`` (w10) pays
for the order. This reads, per seed, every control step from the engine's
settle (1 s) on:

- **the clip's clock:** the episode's random start sample (ADR-709) is
  recovered exactly from the first solver frame's joint angles against the
  bundle's ``tracking.reset_qpos`` rows; the reward at the frame landing at
  ``t`` reads the clip at phase ``t / period + origin / samples``
  (``cadex_train.tracking_vector`` one step on), ``ref_*_down`` thresholded
  at 0.5 as the trainer's ``held`` columns are;
- **the policy's contacts:** each paw body's collision geoms within
  ``CadexEvaluation.STANCE_MM`` of the floor (the evaluator's stance rule,
  standing in for the trainer's contact flags);
- **what the existing terms pay:** ``track_contact``'s hind half (w10 over
  four paws) and ``fore_sync`` (w2), per step;
- **the candidate** ``hind_lag``: ``|rl - rr| * (1 - |(cl - cr) - (rl - rr)|)``
  with ``r`` the clip's hind downs and ``c`` the policy's. It is 0 wherever
  the clip has both hinds in one state, +1 where the policy splits them the
  clip's way, 0 where it lands them together, -1 where it splits them the
  other way. The clip itself scores 6/21 = 0.286 a step.
- **its discrimination:** the per-seed mean against the seed's median
  RH-after-LH touchdown time, so a term that does not separate a lagged
  seed from a tied one shows it.

Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402

PAWS = {"lf": "c_paw_fl", "rf": "c_paw_fr", "lh": "c_paw_hl", "rh": "c_paw_hr"}
KINDS = {mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule", mujoco.mjtGeom.mjGEOM_SPHERE: "sphere",
         mujoco.mjtGeom.mjGEOM_BOX: "box"}


def capsules(model):
    out = {}
    for body in PAWS.values():
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
        geoms = []
        for g in range(model.ngeom):
            if int(model.geom_bodyid[g]) != b or not (model.geom_contype[g] or model.geom_conaffinity[g]):
                continue
            kind = KINDS.get(int(model.geom_type[g]))
            if kind is None:
                continue
            w, x, y, z = (float(v) for v in model.geom_quat[g])
            geoms.append({"kind": kind, "size_mm": [1000 * float(v) for v in model.geom_size[g]],
                          "pos_mm": [1000 * float(v) for v in model.geom_pos[g]], "quat_xyzw": [x, y, z, w]})
        out[body] = geoms
    return out


def origin(model, tracking, frame):
    """The clip sample the episode started at: the reset_qpos row the first frame's joints sit on."""

    best = None
    for s, row in enumerate(tracking["reset_qpos"]):
        err = 0.0
        for joint, q in frame:
            j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
            err += (math.degrees(row[model.jnt_qposadr[j]]) - q) ** 2
        if best is None or err < best[0]:
            best = (err, s)
    return best


def ref_down(tracking, phase):
    rows = int(tracking["samples"])
    at = (phase - math.floor(phase)) * rows
    low = int(math.floor(at)) % rows
    high = (low + 1) % rows
    w = at - math.floor(at)
    names = tracking["channels"][2:]
    out = {}
    for k in PAWS:
        i = names.index("ref_%s_down" % k)
        v = tracking["table"][low][i] + w * (tracking["table"][high][i] - tracking["table"][low][i])
        out[k] = 1.0 if v >= 0.5 else 0.0
    return out


def touchdowns(times, down):
    return [t for (t, d), (_, p) in zip(zip(times[1:], down[1:]), zip(times, down)) if d and not p]


def rh_after_lh(lh, rh, period):
    out = []
    for t in lh:
        near = [r - t for r in rh if abs(r - t) <= period / 2]
        if near:
            out.append(1000 * min(near, key=abs))
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    task = json.loads(Path(argv[0]).read_text())
    tracking = task["tracking"]
    period = float(tracking["period_s"])
    model = mujoco.MjModel.from_xml_path(argv[1])
    geoms = capsules(model)
    for arg in argv[2:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        floor = ev["rig"]["floor_mm"]
        print("\n## %s (policy %s)\n" % (out.name, ev["policy_sha256"][:8]))
        print("| seed | origin (fit err) | steps | hind_lag | clip | contact hind (w10) | fore_sync (w2) "
              "| RH after LH ms (median) | together |")
        print("|---|---|---|---|---|---|---|---|---|")
        every = {"lag": [], "clip": [], "hind": [], "fsync": []}
        per_seed = []
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            err, s = origin(model, tracking, list(zip(joints, solver[0]["joint_positions"])))
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            down = {k: [h <= E.STANCE_MM for h in E.foot_series(samples, body, geoms[body], floor)["height"]]
                    for k, body in PAWS.items()}
            acc = {"lag": [], "clip": [], "hind": [], "fsync": []}
            for i, t in enumerate(times):
                if t < E.SETTLE_S - 1e-9:
                    continue
                r = ref_down(tracking, t / period + s / float(tracking["samples"]))
                c = {k: 1.0 if down[k][i] else 0.0 for k in PAWS}
                dr, dc = r["lh"] - r["rh"], c["lh"] - c["rh"]
                acc["lag"].append(abs(dr) * (1 - abs(dc - dr)))
                acc["clip"].append(abs(dr))
                acc["hind"].append(10 * ((1 - abs(c["lh"] - r["lh"])) + (1 - abs(c["rh"] - r["rh"]))) / 4)
                acc["fsync"].append(2 * (1 - abs(c["lf"] - c["rf"])))
            lags = rh_after_lh(touchdowns(times, down["lh"]), touchdowns(times, down["rh"]), period)
            tied = sum(1 for v in lags if abs(v) < 20) / len(lags) if lags else float("nan")
            med = statistics.median(lags) if lags else float("nan")
            m = {k: statistics.fmean(v) for k, v in acc.items()}
            per_seed.append((m["lag"], med, tied))
            for k in every:
                every[k].extend(acc[k])
            print("| %s | %d (%.0f) | %d | %+.3f | %.3f | %.2f | %.2f | %+.0f | %.2f |" % (
                path.name.split("-")[1], s, err, len(acc["lag"]), m["lag"], m["clip"], m["hind"], m["fsync"],
                med, tied))
        m = {k: statistics.fmean(v) for k, v in every.items()}
        print("\nAll seeds: hind_lag %+.3f a step (clip %.3f), track_contact's hind half %.2f, fore_sync %.2f."
              % (m["lag"], m["clip"], m["hind"], m["fsync"]))
        if len(per_seed) > 2:
            xs, ys = [p[0] for p in per_seed], [p[2] for p in per_seed]
            print("Per seed, hind_lag against the tied share: r = %+.2f." % statistics.correlation(xs, ys))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
