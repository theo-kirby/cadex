"""orun14 P1 (O7): heel_pitch's metatarsus angle on a judged policy's frames, and what a reshaped peak would pay there.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun14/heel_meta.py RUN/train/gallop-task.json EVALUATION_DIR [...]

heel_pitch (leo's ``script.py``) pays, in the clip's hind stance, a peak on
the metatarsus angle ``_META`` (chest pitch + 2 q_spine + hip - knee + hock
+ 63.9, the right leg's joints sign-flipped), centred at 4.5 deg, where
orun13 measured leo's rigid sole flat. On v03 the paw turns on its pin, so
``_META`` says where the metatarsus and its welded heel are, not the paw.

**Calibration.** On the bundle's clip samples (``reset_qpos``), ``_META``
from the trainer's own channels (``orun13/reward_terms.channel_vector``)
against ``c_meta_h*``'s world pitch from MuJoCo: the per-leg offset, and its
spread (a constant offset means the trace's metatarsus pitch stands in for
``_META`` exactly).

**On a judged policy.** Per frame from the settle (1 s) on, ``_META`` from
``c_meta_h*``'s placement plus the offset; the engine's ``foot_series`` says
whether the paw and the heel are down. Per leg, medians of ``_META`` on
heel-down frames (where the flat really is on v03) and on paw-down,
heel-up frames (what the policy holds), and for each peak shape in
``SHAPES`` its mean pay on paw-down frames and on heel-down frames, and its
slope towards flat at the heel-up median. Paw-down frames stand in for the
clip's stance flags (the trace has no clock), so the pay is the policy's
own stance, not the trainer's. Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "orun13"))
sys.path.insert(0, str(HERE.parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
import reward_terms as rt  # noqa: E402
from spine_foot import paw_capsules  # noqa: E402

def _gauss(centre, *pairs):
    return lambda m: sum(w * math.exp(-((m - centre) / s) ** 2) for w, s in pairs)


def _cubic(centre, half):
    return lambda m: max(0.0, 1.0 - abs(m - centre) / half) ** 3


# Each shape: (centre, pay(m)). The first is g4-peak's heel_pitch, centred where
# v02's welded sole was flat; the others are centred where v03's heel is down.
SHAPES = {
    "g4-peak (now): 0.3 g20 + 0.7 g3 @4.5": (4.5, _gauss(4.5, (0.3, 20.0), (0.7, 3.0))),
    "same @6": (6.0, _gauss(6.0, (0.3, 20.0), (0.7, 3.0))),
    "g6 @6": (6.0, _gauss(6.0, (1.0, 6.0))),
    "g8 @6": (6.0, _gauss(6.0, (1.0, 8.0))),
    "cubic 16 @6": (6.0, _cubic(6.0, 16.0)),
    "cubic 20 @6": (6.0, _cubic(6.0, 20.0)),
}


def pay(m, shape):
    return shape[1](m)


def slope(m, shape):
    """Pay gained per degree towards the shape's centre at m."""

    d = math.copysign(0.5, m - shape[0])
    return shape[1](m - d) - shape[1](m + d)


def meta_expr(v, side):
    body = 57.2958 * math.asin(2 * (v["imu_qw"] * v["imu_qy"] - v["imu_qx"] * v["imu_qz"]))
    if side == "l":
        return body + 2 * v["q_spine"] + v["q_hip_l"] - v["q_knee_l"] + v["q_hock_l"] + 63.9
    return body + 2 * v["q_spine"] - v["q_hip_r"] + v["q_knee_r"] - v["q_hock_r"] + 63.9


def pitch_from_x(x):
    return math.degrees(math.atan2(-x[2], x[0]))


def calibrate(bundle):
    task, model = rt.load(bundle)
    _, names, _, _ = rt.compiled(task)
    data = mujoco.MjData(model)
    tr = task["tracking"]
    offsets = {"l": [], "r": []}
    for s in range(int(tr["samples"])):
        data.qpos[:] = tr["reset_qpos"][s]
        data.qvel[:] = tr["reset_qvel"][s]
        mujoco.mj_forward(model, data)
        vec = rt.channel_vector(task, model, data, 0, s)
        v = {n: float(vec[i]) for i, n in enumerate(names)}
        for side in "lr":
            x = data.xmat[model.body(f"c_meta_h{side}").id].reshape(3, 3)[:, 0]
            offsets[side].append(meta_expr(v, side) - pitch_from_x(x))
    return {side: (statistics.median(o), max(o) - min(o)) for side, o in offsets.items()}


def med(values):
    return statistics.median(values) if values else float("nan")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cal = calibrate(Path(argv[0]))
    task = json.loads(Path(argv[0]).read_text())
    paw_geoms = paw_capsules(mujoco.MjModel.from_xml_path(
        str(Path(argv[0]).parent / Path(task["model"]["path"]).name)))
    print("## Calibration on the bundle's clip samples\n")
    for side, (off, spread) in cal.items():
        print(f"- {side.upper()}H: _META = c_meta world pitch {off:+.2f} deg (spread {spread:.2f} deg over the clip)")
    print()
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        acc = {side: {"heel": [], "up": [], "paw": []} for side in "lr"}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            frames = [f for f in trace["frames"] if f.get("component_placements")]
            samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
            for side in "lr":
                paw = f"c_paw_h{side}"
                hb = rig["heels"][paw]
                heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
                sole = E.foot_series(samples, paw, paw_geoms[paw], rig["floor_mm"])["height"]
                for i, (t, p) in enumerate(samples):
                    if t < E.SETTLE_S - 1e-9 or sole[i] > E.STANCE_MM:
                        continue
                    rot, _ = E._pose(p, f"c_meta_h{side}")
                    m = pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0]
                    acc[side]["paw"].append(m)
                    acc[side]["heel" if heel[i] <= E.STANCE_MM else "up"].append(m)
        print(f"## {out.name}: _META on paw-down frames\n")
        print("| leg | paw-down frames | heel-down share | _META median, heel down | _META median, heel up (p25–p75) |")
        print("|---|---|---|---|---|")
        for side, a in acc.items():
            up = sorted(a["up"])
            q = (up[len(up) // 4], up[3 * len(up) // 4]) if up else (float("nan"),) * 2
            print(f"| {side.upper()}H | {len(a['paw'])} | {len(a['heel']) / max(len(a['paw']), 1):.2f} "
                  f"| {med(a['heel']):+.1f} | {med(up):+.1f} ({q[0]:+.1f}–{q[1]:+.1f}) |")
        print()
        print("| shape | LH pay: paw-down / heel-down / heel-up median | LH slope /deg there "
              "| RH pay: paw-down / heel-down / heel-up median | RH slope /deg there |")
        print("|---|---|---|---|---|")
        for name, shape in SHAPES.items():
            cells = []
            for side in "lr":
                a = acc[side]
                mu = med(a["up"])
                cells.append(f"{med([pay(m, shape) for m in a['paw']]) if a['paw'] else float('nan'):.2f} mean "
                             f"{statistics.fmean(pay(m, shape) for m in a['paw']):.2f} / "
                             f"{statistics.fmean(pay(m, shape) for m in a['heel']) if a['heel'] else float('nan'):.2f} / "
                             f"{pay(mu, shape):.2f}")
                cells.append(f"{slope(mu, shape):.3f}")
            print(f"| {name} | " + " | ".join(cells) + " |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
