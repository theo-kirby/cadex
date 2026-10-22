"""orun15 P1/Q1 (O7): score a hind swing-contact term and the yaw term per step on judged traces, before training.

usage: pixi run python docs/probes/orun15/hind_step.py GALLOP_TASK_JSON MODEL_XML EVALUATION_DIR [...]

hk12-sole-50's first hind to land (RH) steps at 3.89 Hz against LH's 2.67
and the clip's 2.40, 505 mm a stride against 789, and the cat yaws 21-28°
(``hk12-mirror.md``: the mirrored policy swaps both, so they are the
policy's). This reads, per seed, every control step from the engine's
settle on, with the clip's clock recovered as ``lag_term.py`` does
(``origin``, ``ref_down``) and each paw's contact by the evaluator's stance
rule:

- **per hind leg:** the share of steps the paw is down while the clip has
  it in swing (``off``), and up while the clip has it in stance (``miss``);
  ``track_contact`` pays both the same, so its per-leg pay (w10 over four
  paws) is printed beside them;
- **the candidate** ``hind_tap``: ``((1 - ref_lh_down) * chl_down +
  (1 - ref_rh_down) * chr_down) / 2``, ``fore_tap``'s form on the hinds;
- **the yaw:** ``straight``'s ``4 * |imu_qz|`` from the chest frame's
  rotation, and the chest's heading, per step.

Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from lag_term import PAWS, capsules, origin, ref_down  # noqa: E402

CHEST = "c_chest_frame"


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
        out = Path(arg).expanduser()
        ev = json.loads((out / "evaluation.json").read_text())
        floor = ev["rig"]["floor_mm"]
        print("\n## %s (policy %s)\n" % (out.name, ev["policy_sha256"][:8]))
        print("| seed | off LH / RH | miss LH / RH | contact pay LH / RH (w10) | hind_tap | 4·abs(qz) | heading ° end |")
        print("|---|---|---|---|---|---|---|")
        every = {k: [] for k in ("offl", "offr", "missl", "missr", "payl", "payr", "tap", "qz")}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, s = origin(model, tracking, list(zip(joints, solver[0]["joint_positions"])))
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            down = {k: [h <= E.STANCE_MM for h in E.foot_series(samples, body, geoms[body], floor)["height"]]
                    for k, body in PAWS.items() if k in ("lh", "rh")}
            acc = {k: [] for k in every}
            heading = 0.0
            for i, t in enumerate(times):
                if t < E.SETTLE_S - 1e-9:
                    continue
                r = ref_down(tracking, t / period + s / float(tracking["samples"]))
                cl, cr = (1.0 if down["lh"][i] else 0.0), (1.0 if down["rh"][i] else 0.0)
                acc["offl"].append((1 - r["lh"]) * cl)
                acc["offr"].append((1 - r["rh"]) * cr)
                acc["missl"].append(r["lh"] * (1 - cl))
                acc["missr"].append(r["rh"] * (1 - cr))
                acc["payl"].append(10 * (1 - abs(cl - r["lh"])) / 4)
                acc["payr"].append(10 * (1 - abs(cr - r["rh"])) / 4)
                acc["tap"].append(((1 - r["lh"]) * cl + (1 - r["rh"]) * cr) / 2)
                x, y, z, w = samples[i][1][CHEST]["rotation_xyzw"]
                acc["qz"].append(4 * abs(z))
                heading = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
            m = {k: statistics.fmean(v) for k, v in acc.items()}
            for k in every:
                every[k].extend(acc[k])
            print("| %s | %.2f / %.2f | %.2f / %.2f | %.2f / %.2f | %.3f | %.2f | %+.1f |" % (
                path.name.split("-")[1], m["offl"], m["offr"], m["missl"], m["missr"], m["payl"], m["payr"],
                m["tap"], m["qz"], heading))
        m = {k: statistics.fmean(v) for k, v in every.items()}
        print("\nAll seeds: off %.2f / %.2f, miss %.2f / %.2f, contact pay %.2f / %.2f, hind_tap %.3f a step "
              "(x8 = %.2f), straight's 4·abs(qz) %.2f a step." % (
                  m["offl"], m["offr"], m["missl"], m["missr"], m["payl"], m["payr"], m["tap"], 8 * m["tap"],
                  m["qz"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
