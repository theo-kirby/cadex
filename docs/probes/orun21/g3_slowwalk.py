# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun21 G3 step back on the slow walk (kind-ridge-3238): one play, step by step.

    ~/cadex-train-venv/bin/python docs/probes/orun21/g3_slowwalk.py POLICY TASK OUT --bands B
        [--seed 4] [--other-model] [--hold-vx V --hold-s S]

Plays ``cadex_goto play`` unchanged, but keeps what the judge reads per step
(index, arrived, bearing, forward, commanded) beside the layer's own vx, vy, wz,
the base's measured body-frame vx, vy and yaw rate, and the base height, and
writes ``OUT/trace.json`` and ``OUT/legs.json``: per straight stretch the judge
read, the mean commanded speed (its denominator), the mean vx and vy the layer
asked for, and the mean measured forward, lateral and yaw rate.

``--hold-vx V --hold-s S`` instead plays a bare joystick: the layer is replaced
by a constant ``(V, 0, 0)`` for S seconds, to read the policy's steady forward
speed at that command with no layer at all.
"""

import argparse
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "training"))
import cadex_goto  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy")
    parser.add_argument("task")
    parser.add_argument("out")
    parser.add_argument("--bands", required=True)
    parser.add_argument("--seed", type=int, default=4)
    parser.add_argument("--other-model", action="store_true")
    parser.add_argument("--hold-vx", type=float, default=None)
    parser.add_argument("--hold-s", type=float, default=30.0)
    options = parser.parse_args()
    out = Path(options.out)
    out.mkdir(parents=True, exist_ok=True)
    trace = {"layer": [], "measured": []}
    captured = {}

    layer_step = cadex_goto.layer_step

    def logged_step(xp, plan, state, x, y, yaw, dt, limits, gains=None):
        new, command = layer_step(xp, plan, state, x, y, yaw, dt, limits, gains)
        if options.hold_vx is not None:
            new = {**new, "index": new["index"] * 0, "arrived": new["arrived"] & False}
            command = {"vx": xp.array([options.hold_vx]), "vy": xp.array([0.0]), "wz": xp.array([0.0])}
        trace["layer"].append([round(float(command[a][0]), 5) for a in ("vx", "vy", "wz")])
        return new, command

    control = cadex_goto.Player.control

    def logged_control(self, data, command):
        R = data.xmat[self.base].reshape(3, 3)
        v = R.T @ data.qvel[:3]
        w = R.T @ data.qvel[3:6]
        trace["measured"].append([round(float(v[0]), 5), round(float(v[1]), 5), round(float(w[2]), 5),
                                  round(float(data.xipos[self.base][2]), 5)])
        return control(self, data, command)

    judge = cadex_goto.judge

    def logged_judge(samples, plan, dt, fell, walls=None):
        captured.update(samples=samples, plan=plan, dt=dt)
        return judge(samples, plan, dt, fell, walls)

    cadex_goto.layer_step = logged_step
    cadex_goto.Player.control = logged_control
    cadex_goto.judge = logged_judge
    argv = ["cadex_goto", "play", options.policy, "--task", options.task, "--seed", str(options.seed), "--split", "heldout",
            "--bands", options.bands, "--view-dir", str(out / "view"),
            *(["--other-model"] if options.other_model else []),
            *(["--seconds", str(options.hold_s)] if options.hold_vx is not None else [])]
    cadex_goto.main(argv)
    samples, dt = captured["samples"], captured["dt"]
    steps = len(samples["index"])
    rows = [{key: samples[key][i] for key in samples} for i in range(steps)]
    for i, row in enumerate(rows):
        row["layer_vxyz"] = trace["layer"][i]
        row["meas_vx_vy_wz_z"] = trace["measured"][i]
    (out / "trace.json").write_text(json.dumps({"dt": dt, "rows": rows}) + "\n")
    J = cadex_goto.JUDGE
    settle = int(round(J["straight_settle_s"] / dt))
    legs = []
    if options.hold_vx is not None:
        tail = rows[int(round(10.0 / dt)):]
        mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
        legs.append({"hold_vx": options.hold_vx, "after_s": 10.0,
                     "forward": round(mean([r["forward"] for r in tail]), 5),
                     "lateral": round(mean([r["meas_vx_vy_wz_z"][1] for r in tail]), 5),
                     "yaw_rate": round(mean([r["meas_vx_vy_wz_z"][2] for r in tail]), 5)})
    else:
        for k, point in enumerate(captured["plan"]["points"]):
            keep, run = [], 0
            for i, r in enumerate(rows):
                flag = r["index"] == k and not r["arrived"] and math.degrees(abs(r["bearing"])) < J["straight_deg"] \
                    and abs(r["commanded"] - point["speed_mps"]) <= 1e-3
                run = run + 1 if flag else 0
                if run > settle:
                    keep.append(r)
            if not keep:
                continue
            mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
            legs.append({"point": k, "band": point["band"], "speed_mps": point["speed_mps"],
                         "straight_s": round(len(keep) * dt, 2),
                         "commanded": round(mean([r["commanded"] for r in keep]), 5),
                         "layer_vx": round(mean([r["layer_vxyz"][0] for r in keep]), 5),
                         "layer_vy": round(mean([r["layer_vxyz"][1] for r in keep]), 5),
                         "layer_wz": round(mean([r["layer_vxyz"][2] for r in keep]), 5),
                         "bearing_deg": round(mean([math.degrees(r["bearing"]) for r in keep]), 3),
                         "forward": round(mean([r["forward"] for r in keep]), 5),
                         "lateral": round(mean([r["meas_vx_vy_wz_z"][1] for r in keep]), 5),
                         "yaw_rate": round(mean([r["meas_vx_vy_wz_z"][2] for r in keep]), 5),
                         "ratio": round(mean([r["forward"] for r in keep]) / point["speed_mps"], 4),
                         "deficit_mps": round(point["speed_mps"] - mean([r["forward"] for r in keep]), 5)})
    (out / "legs.json").write_text(json.dumps(legs, indent=1) + "\n")
    print(json.dumps(legs, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
