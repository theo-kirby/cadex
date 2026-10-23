"""orun13 (O7): each reward term per step on a gallop bundle, standing against the clip.

    CUDA_VISIBLE_DEVICES= ~/cadex-train-venv/bin/python docs/probes/orun13/reward_terms.py \
        RUN/train/gallop-task.json [--seconds 3]

Scores the bundle's own reward and terminations with the trainer's own
expression compiler, channel order, contact flags, tracking clock and height
scan (``training/cadex_train.py``), on stock MuJoCo on the CPU, in three
scenarios, each started from every clip sample (the bundle's random start):

- ``hold``: reset to the clip sample, every position drive held at the
  angle it starts at, simulated for ``--seconds`` with the clock running.
  What a policy earns by standing still in the pose it was dropped in.
- ``keyframe``: the same from the reset keyframe's pose (``solved``).
- ``clip``: the clip replayed kinematically (``reset_qpos`` and
  ``reset_qvel`` per sample, read linearly between samples, the root
  advanced at the clip's speed), contacts from ``mj_forward``. What perfect
  tracking would earn, as far as a kinematic pose can say.

Prints each term's mean weighted value per step, the total, and the share
of steps a termination fires.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))
import cadex_train as ct  # noqa: E402


def load(bundle_path: Path):
    task = json.loads(bundle_path.read_text())
    xml = (bundle_path.parent / Path(task["model"]["path"]).name).read_bytes()
    model = mujoco.MjModel.from_xml_string(xml.decode())
    return task, model


def compiled(task):
    table = ct.globals_for(np)
    names = ct.channels(task)
    rewards = [(str(t["label"]), float(t["weight"]),
                ct.compile_expression(str(t["expression"]), names, table)) for t in task["reward"]]
    terms = [(str(t["label"]), t.get("above"), t.get("below"),
              ct.compile_expression(str(t["expression"]), names, table)) for t in task["termination"]]
    return table, names, rewards, terms


def channel_vector(task, model, data, steps, origin):
    gather = np.concatenate([np.arange(int(r["adr"]), int(r["adr"]) + int(r["dim"]))
                             for r in task["observations"]])
    scale = np.asarray([float(r["scale"]) for r in task["observations"] for _ in range(int(r["dim"]))])
    raw = data.sensordata[gather] * scale
    parts, cursor = [], 0
    for record in task["observations"]:
        dim = int(record["dim"])
        seg = raw[cursor:cursor + dim]
        cursor += dim
        parts.append(ct.contact_reading(np, seg, record["contact"]) if record.get("contact") else seg)
    vec = [np.concatenate(parts)]
    vec.append(ct.tracking_vector(np, task, np.asarray(float(steps)), np.asarray(float(origin))))
    if task.get("scans"):
        vec.append(ct.height_scan_vector(np, task, data.xpos, data.xmat))
    return np.concatenate(vec)


def score(task, compiled_, vector):
    table, names, rewards, terms = compiled_
    values = {n: vector[i] for i, n in enumerate(names)}
    out = {label: w * float(eval(code, table, dict(values))) for label, w, code in rewards}
    fired = {}
    for label, above, below, code in terms:
        v = float(eval(code, table, dict(values)))
        fired[label] = bool((above is not None and v > float(above)) or (below is not None and v < float(below)))
    return out, fired, values


def clip_state(task, step, origin):
    tr = task["tracking"]
    rows = int(tr["samples"])
    turned = step * float(tr["turn_per_step"]) + origin / rows
    at = (turned - math.floor(turned)) * rows
    lo = int(math.floor(at)) % rows
    hi = (lo + 1) % rows
    w = at - math.floor(at)
    qp = (1 - w) * np.asarray(tr["reset_qpos"][lo]) + w * np.asarray(tr["reset_qpos"][hi])
    qv = (1 - w) * np.asarray(tr["reset_qvel"][lo]) + w * np.asarray(tr["reset_qvel"][hi])
    return qp, qv, math.floor(turned)


def run(task, model, comp, scenario, origin, seconds):
    ep = task["episode"]
    data = mujoco.MjData(model)
    tr = task["tracking"]
    key = model.keyframe(ep["reset_keyframe"]).id if model.nkey else None
    if scenario == "keyframe" and key is not None:
        mujoco.mj_resetDataKeyframe(model, data, key)
    else:
        data.qpos[:] = tr["reset_qpos"][origin]
        data.qvel[:] = tr["reset_qvel"][origin]
    mujoco.mj_forward(model, data)
    for a in task["actions"]:
        jid = model.joint(a["joint"]).id
        data.ctrl[int(a["index"])] = data.qpos[model.jnt_qposadr[jid]]
    held = data.ctrl.copy()
    speed = None
    if scenario == "clip":
        q0, _, _ = clip_state(task, 0, origin)
        # The clip's forward speed: its stride over its period.
        speed = float(np.mean(np.asarray(tr["reset_qvel"])[:, 0]))
    steps = int(round(seconds / float(ep["control_interval_s"])))
    rows, fires = [], []
    for k in range(1, steps + 1):
        if scenario == "clip":
            qp, qv, _ = clip_state(task, k, origin)
            qp = qp.copy()
            qp[0] = speed * k * float(ep["control_interval_s"])
            data.qpos[:] = qp
            data.qvel[:] = qv
            mujoco.mj_forward(model, data)
        else:
            data.ctrl[:] = held
            for _ in range(int(ep["solver_steps_per_action"])):
                mujoco.mj_step(model, data)
        out, fired, _ = score(task, comp, channel_vector(task, model, data, k, origin))
        rows.append(out)
        fires.append(fired)
    return rows, fires


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--skip-s", type=float, default=0.5,
                    help="steps before this are left out of the means (the drop on reset)")
    args = ap.parse_args(argv)
    task, model = load(Path(args.bundle).expanduser())
    comp = compiled(task)
    labels = [str(t["label"]) for t in task["reward"]]
    skip = int(round(args.skip_s / float(task["episode"]["control_interval_s"])))
    samples = int(task["tracking"]["samples"])
    table = {}
    for scenario in ("hold", "keyframe", "clip"):
        origins = [0] if scenario == "keyframe" else range(samples)
        allrows, allfires, firstfire = [], [], []
        for o in origins:
            rows, fires = run(task, model, comp, scenario, o, args.seconds)
            allrows += rows[skip:]
            allfires += fires[skip:]
            first = next((i for i, f in enumerate(fires) if any(f.values())), None)
            firstfire.append(first)
        mean = {l: float(np.mean([r[l] for r in allrows])) for l in labels}
        mean["TOTAL"] = float(sum(mean[l] for l in labels))
        share = {l: float(np.mean([f[l] for f in allfires])) for l in allfires[0]}
        ended = sum(1 for f in firstfire if f is not None)
        table[scenario] = (mean, share, ended, len(firstfire))
    width = max(len(l) for l in labels + ["TOTAL"])
    print(f"{'term':<{width}}  " + "  ".join(f"{s:>9}" for s in table))
    for l in labels + ["TOTAL"]:
        print(f"{l:<{width}}  " + "  ".join(f"{table[s][0][l]:9.3f}" for s in table))
    for s, (_, share, ended, n) in table.items():
        print(f"{s}: termination share {share}; episodes ending within {args.seconds:g} s: {ended}/{n}")


if __name__ == "__main__":
    main(sys.argv[1:])
