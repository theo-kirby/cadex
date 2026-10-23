"""orun17 SG: where in each hind stance a judged gallop_sg policy puts its heel down, and what heel_sched pays there.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/slow_heel.py \
           RUN/train/gallop-task.json EVALUATION_DIR [...]
       CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/slow_heel.py \
           RUN/train/gallop-task.json --clip MODEL_XML STRIDE.json [...]

SG's slow clause needs the hind heel down on at most 0.1 of stance; sgt-1-120
at 700 mm/s has it down on 0.12 / 0.19 (engine ``hock_down``) though the clip
holds no heel there (``b1-trim.md``). This reads every settled control frame:
a stance is a run of paw-down frames (sole within ``STANCE_MM``), split in
thirds (touchdown / mid / lift) by frame index. Per leg:

- stances, and the share with any heel-down frame;
- heel-down frames per third, as a share of that leg's heel-down frames;
- the longest heel-down run in frames (20 ms each);
- the metatarsus pitch (``orun14/heel_meta.py``'s ``_META``, calibrated on
  the first argument) median on heel-down and heel-up paw-down frames, and
  the task's heel_sched target T = 6 + 30 (2400 - cmd) / 1700 (the leo
  script's, low end 700, not ``heel_sched.py``'s 1000);
- heel_sched's pay a step (w 6, tent half-width 30, contact-gated as built)
  on heel-down and heel-up frames.

With ``--clip``, the same metatarsus pitch on the clip itself: each
``STRIDE.json`` is a task copy whose ``reference`` is one stride
(``docs/probes/orun16/sg_clip.py OUT_DIR`` writes them), and per hind leg it
prints the pitch's median and range over the clip's stance samples, split by
the held-heel flag, beside the T the stride's speed is trained towards.

Writes nothing.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

import mujoco

_spec = importlib.util.spec_from_file_location(
    "heel_sched", Path(__file__).resolve().parents[1] / "orun16" / "heel_sched.py")
HS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HS)
H, E = HS.H, HS.E

LOW, HIGH, FLAT, D, W, WT = 700.0, 2400.0, 6.0, 30.0, 30.0, 6.0


def target(cmd):
    return FLAT + D * (HIGH - min(HIGH, max(LOW, cmd))) / (HIGH - LOW)


def runs(flags):
    """(start, end) index pairs of each run of True in flags, end exclusive."""

    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    return out


def clip_meta(cal, model_xml, strides):
    model = mujoco.MjModel.from_xml_path(model_xml)
    data = mujoco.MjData(model)
    print("| stride | m/s | T | leg | stance samples; heel held | _META stance median (min..max) | heel-up samples median |")
    print("|---|---|---|---|---|---|---|")
    for arg in strides:
        clip = json.loads(Path(arg).read_text())["reference"]
        cmd = 1000.0 * clip["parameters"]["speed_m_s"] if "speed_m_s" in clip["parameters"] else float("nan")
        for side, leg in (("l", "LH"), ("r", "RH")):
            ms, up = [], []
            for k in range(clip["samples"]):
                if not clip["contact"][leg][k]:
                    continue
                data.qpos[:] = clip["qpos"][k]
                mujoco.mj_kinematics(model, data)
                m = H.pitch_from_x(data.xmat[model.body(f"c_meta_h{side}").id].reshape(3, 3)[:, 0]) + cal[side][0]
                ms.append(m)
                if not clip["heels"][leg]["down"][k]:
                    up.append(m)
            held = sum(1 for k in range(clip["samples"]) if clip["contact"][leg][k] and clip["heels"][leg]["down"][k])
            print(f"| {clip.get('label', Path(arg).name)} | {cmd / 1000:.2f} | {target(cmd):+.1f} | {leg} | {len(ms)}; {held} "
                  f"| {H.med(ms):+.1f} ({min(ms):+.1f}..{max(ms):+.1f}) | {H.med(up):+.1f} |")
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "--clip":
        return clip_meta(H.calibrate(Path(argv[0])), argv[2], argv[3:])
    if len(argv) < 2:
        print(__doc__)
        return 2
    cal = H.calibrate(Path(argv[0]))
    task = json.loads(Path(argv[0]).read_text())
    paw_geoms = H.paw_capsules(mujoco.MjModel.from_xml_path(
        str(Path(argv[0]).parent / Path(task["model"]["path"]).name)))
    print("| evaluation | leg | stances; with a heel-down frame | heel-down frames touchdown / mid / lift "
          "| longest heel-down run (frames) | _META heel down / heel up median; T | heel_sched a step heel down / up |")
    print("|---|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd, rig = float(ev["judged_command_mm_s"]), ev["rig"]
        t_meta = target(cmd)
        acc = {s: {"n": 0, "with": 0, "third": [0, 0, 0], "longest": 0, "m": {True: [], False: []}} for s in "lr"}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"])
                       for f in trace["frames"] if f.get("component_placements")]
            settled = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
            for side in "lr":
                paw = f"c_paw_h{side}"
                hb = rig["heels"][paw]
                heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
                sole = E.foot_series(samples, paw, paw_geoms[paw], rig["floor_mm"])["height"]
                a = acc[side]
                down = [sole[i] <= E.STANCE_MM for i in settled]
                for s0, s1 in runs(down):
                    idx = settled[s0:s1]
                    hd = [heel[i] <= E.STANCE_MM for i in idx]
                    a["n"] += 1
                    a["with"] += any(hd)
                    for k, h in enumerate(hd):
                        if h:
                            a["third"][min(2, 3 * k // len(idx))] += 1
                    a["longest"] = max([a["longest"]] + [e - b for b, e in runs(hd)])
                    for i, h in zip(idx, hd):
                        rot, _ = E._pose(samples[i][1], f"c_meta_h{side}")
                        a["m"][h].append(H.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0])
        for side, a in acc.items():
            nh = sum(a["third"])
            pay = {h: WT * statistics.fmean(HS.tent(m, t_meta, W) for m in a["m"][h]) / 2 if a["m"][h] else float("nan")
                   for h in (True, False)}
            print(f"| {out.name} | {side.upper()}H | {a['n']}; {a['with'] / max(a['n'], 1):.2f} | "
                  + " / ".join(f"{x / max(nh, 1):.2f}" for x in a["third"])
                  + f" | {a['longest']} | {H.med(a['m'][True]):+.1f} / {H.med(a['m'][False]):+.1f}; {t_meta:+.1f} "
                  f"| {pay[True]:.2f} / {pay[False]:.2f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
