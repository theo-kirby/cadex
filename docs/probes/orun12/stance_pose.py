"""The hind leg's pose in the engine's own stance frames, beside the clip's heel-down pose (orun12 P1, O2a).

usage: python3 docs/probes/orun12/stance_pose.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

MODEL_XML is the run's compiled ``train/cat_model-model.xml``; each
EVALUATION_DIR holds ``docs/probes/orun11/judge.py``'s ``seed-*-trace.json``,
``evaluation.json`` and ``judged-task.json``.

Stance is the engine's (``CadexEvaluation.heel_metrics``): a frame after
the first second where the lowest point of the paw body's collision
capsules is within ``STANCE_MM`` of the floor, and the heel is down when
the heel's capsules are too. The engine's own helpers (``foot_series``)
pose the capsules, so the frame count and heel share are checked against
the engine's ``detail.heels`` for every seed (``engine n / share``).

Over those frames, per hind leg, it prints the median of:

- the hip, knee and hock drive angles (deg; the right leg's sign folded onto
  the left's, as its axes are mirrored);
- each segment's pitch in the world's x-z plane (deg from horizontal, positive
  rising toward the rear of the cat): the thigh (hip pin to knee pin), the
  shin (knee pin to ankle pin), the metatarsus (ankle pin to paw pin) and the
  paw (paw pin to its front capsule);
- the pelvis's pitch (deg, nose down positive), and the heel's height (mm).

Two more tables, both legs' stance frames together: the heel's down share
by metatarsus pitch, in 5 deg bins; and, per leg, the closed form
heel5-s1's ``heel_pitch`` term computes the metatarsus pitch with from
observed channels (``metatarsus_pitch``: chest pitch from the imu
quaternion, plus spine, hip, knee and hock, the right mirrored), as its
mean and largest error against the geometric pitch, with the mean the
term pays in stance (``(45 - pitch) / 35`` clipped to 0..1).

The clip's row is the same reading on its own placements over the samples
where it holds that heel down. The last column is the share of
``hock_stance.py``'s lowest-quarter proxy frames that are engine stance
frames. Standard library only.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402

LEGS = (("LH", "l", "hl", 1.0), ("RH", "r", "hr", -1.0))


def model(xml: Path) -> tuple[dict, dict]:
    """Paw capsules per leg (in the engine's rig form) and joint pins (mm, build frame)."""

    root = ET.parse(xml).getroot()
    pins, paws = {}, {}
    for joint in root.iter("joint"):
        if joint.get("pos"):
            pins[joint.get("name")] = tuple(1000 * float(v) for v in joint.get("pos").split())
    for body in root.iter("body"):
        name = body.get("name", "")
        if name.startswith("c_paw_h"):
            geoms = []
            for g in body.findall("geom"):
                w, x, y, z = (float(v) for v in g.get("quat", "1 0 0 0").split())
                size = [1000 * float(v) for v in g.get("size").split()] + [0.0]
                geoms.append({"kind": g.get("type", "sphere"), "size_mm": size[:3],
                              "pos_mm": [1000 * float(v) for v in g.get("pos").split()],
                              "quat_xyzw": [x, y, z, w]})
            paws[name] = geoms
    return paws, pins


def world(placements, body, point):
    rotation, origin = E._pose(placements, body)
    return E._add(E._apply(rotation, point), origin)


def pitch(a, b):
    """Pitch of a -> b in x-z, deg from horizontal, positive when b is lower and ahead... read as rise to the rear."""

    return math.degrees(math.atan2(a[2] - b[2], b[0] - a[0]))


def metatarsus_pitch(placements, q, side):
    """heel_pitch's closed form (deg): q maps a drive's joint name to its angle (deg)."""

    x, y, z, w = placements["c_imu"]["rotation_xyzw"]
    chest = math.degrees(math.asin(2 * (w * y - x * z)))
    if side == "l":
        return chest + q["j_spine"] + q["j_hip_l"] - q["j_knee_l"] + q["j_hock_l"] + 63.9
    return chest + q["j_spine"] - q["j_hip_r"] + q["j_knee_r"] - q["j_hock_r"] + 63.9


def pose(placements, side, foot, pins, paw_geoms):
    hip = world(placements, "c_thigh_" + side, pins["j_hip_" + side])
    knee_t = world(placements, "c_thigh_" + side, pins["j_knee_" + side])
    knee = world(placements, "c_shin_" + side, pins["j_knee_" + side])
    ankle_s = world(placements, "c_shin_" + side, pins["j_ankle_" + side])
    ankle = world(placements, "c_meta_" + foot, pins["j_ankle_" + side])
    pawpin_m = world(placements, "c_meta_" + foot, pins["j_pawpin_" + side])
    pawpin = world(placements, "c_paw_" + foot, pins["j_pawpin_" + side])
    toe = world(placements, "c_paw_" + foot, paw_geoms[-1]["pos_mm"])
    rotation, _ = E._pose(placements, "c_pelvis_frame")
    nose = E._column(rotation, 0)
    return {"thigh": pitch(hip, knee_t), "shin": pitch(knee, ankle_s), "meta": pitch(ankle, pawpin_m),
            "paw": pitch(pawpin, toe), "pelvis": -math.degrees(math.atan2(nose[2], nose[0]))}


def stance_rows(out: Path, paws, pins):
    evaluation = json.loads((out / "evaluation.json").read_text())
    heels = evaluation["rig"]["heels"]
    floor = evaluation["rig"]["floor_mm"]
    engine = {s["seed"]: s["detail"]["heels"] for s in evaluation["seeds"]}
    rows = {leg: {"n": 0, "engine_n": 0, "down": 0, "engine_down": 0.0, "proxy": [0, 0],
                  "q": {"hip": [], "knee": [], "hock": []}, "seg": {}, "heel": [], "form": [], "pay": [],
                  "bins": {}} for leg, *_ in LEGS}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        seed = int(path.name.split("-")[1])
        names = [c["joint"] if isinstance(c, dict) else c for c in trace["actuator_channels"]]
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        for leg, side, foot, sign in LEGS:
            paw = "c_paw_" + foot
            sole = E.foot_series(samples, paw, paws[paw], floor)["height"]
            heel = E.foot_series(samples, heels[paw]["body"], heels[paw]["geoms"], floor)["height"]
            late = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
            stance = [i for i in late if sole[i] <= E.STANCE_MM]
            row = rows[leg]
            row["n"] += len(stance)
            row["down"] += sum(1 for i in stance if heel[i] <= E.STANCE_MM)
            row["engine_n"] += engine[seed][paw]["stance_frames"]
            row["engine_down"] += (engine[seed][paw]["heel_down_share"] or 0.0) * engine[seed][paw]["stance_frames"]
            z = [samples[i][1][paw]["position_mm"][2] for i in late]
            low = sorted(z)[len(z) // 4]
            proxy = [i for i, zi in zip(late, z) if zi <= low]
            row["proxy"][0] += sum(1 for i in proxy if sole[i] <= E.STANCE_MM)
            row["proxy"][1] += len(proxy)
            for i in stance:
                for joint in ("hip", "knee", "hock"):
                    row["q"][joint].append(sign * frames[i]["joint_positions"][names.index(f"j_{joint}_{side}")])
                for k, v in pose(samples[i][1], side, foot, pins, paws[paw]).items():
                    row["seg"].setdefault(k, []).append(v)
                row["heel"].append(heel[i])
                q = dict(zip(names, frames[i]["joint_positions"]))
                form = metatarsus_pitch(samples[i][1], q, side)
                row["form"].append(form - row["seg"]["meta"][-1])
                row["pay"].append(min(max((45 - form) / 35, 0.0), 1.0))
                b = row["bins"].setdefault(5 * math.floor(row["seg"]["meta"][-1] / 5), [0, 0])
                b[0] += heel[i] <= E.STANCE_MM
                b[1] += 1
    return rows


def clip_rows(out: Path, paws, pins):
    task = json.loads((out / "judged-task.json").read_text())
    ref = task["reference"]
    rows = {}
    for leg, side, foot, sign in LEGS:
        down = ref["heels"][leg]["down"]
        joints = ref["joints"]
        idx = [i for i, d in enumerate(down) if d]
        q = {"hip": [], "knee": [], "hock": []}
        seg = {}
        for i in idx:
            angles = ref["joint_angles_rad"][i]
            for joint, name in (("hip", "j_hip_"), ("knee", "j_knee_"), ("hock", "j_ankle_")):
                q[joint].append(sign * math.degrees(angles[joints.index(name + side)]))
            for k, v in pose(ref["placements"][i], side, foot, pins, paws["c_paw_" + foot]).items():
                seg.setdefault(k, []).append(v)
        rows[leg] = {"q": q, "seg": seg, "n": len(idx)}
    return rows


def med(values):
    return statistics.median(values) if values else float("nan")


def main(argv: list[str]) -> None:
    paws, pins = model(Path(argv[0]))
    print("| evaluation | leg | stance n (engine n) | heel down share (engine) | heel mm | hip / knee / hock deg "
          "| pelvis / thigh / shin / meta / paw pitch deg | proxy frames in stance |")
    print("|---|---|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg)
        rows, clip = stance_rows(out, paws, pins), clip_rows(out, paws, pins)
        for leg, *_ in LEGS:
            r, c = rows[leg], clip[leg]
            seg = " / ".join(f"{med(r['seg'][k]):.0f}" for k in ("pelvis", "thigh", "shin", "meta", "paw"))
            q = " / ".join(f"{med(r['q'][k]):.0f}" for k in ("hip", "knee", "hock"))
            print(f"| {out.name} | {leg} | {r['n']} ({r['engine_n']}) | {r['down'] / max(r['n'], 1):.2f} "
                  f"({r['engine_down'] / max(r['engine_n'], 1):.2f}) | {med(r['heel']):.0f} | {q} | {seg} "
                  f"| {r['proxy'][0] / max(r['proxy'][1], 1):.2f} |")
            cseg = " / ".join(f"{med(c['seg'][k]):.0f}" for k in ("pelvis", "thigh", "shin", "meta", "paw"))
            cq = " / ".join(f"{med(c['q'][k]):.0f}" for k in ("hip", "knee", "hock"))
            print(f"| clip, heel down | {leg} | {c['n']} samples | 1 | – | {cq} | {cseg} | – |")
        bins = {}
        for r in rows.values():
            for k, (d, n) in r["bins"].items():
                bins.setdefault(k, [0, 0])
                bins[k][0] += d
                bins[k][1] += n
        print(f"\n{out.name}: heel down share by metatarsus pitch (both legs' stance frames)\n")
        print("| pitch deg | frames | heel down |\n|---|---|---|")
        for k in sorted(bins):
            print(f"| {k}..{k + 5} | {bins[k][1]} | {bins[k][0] / bins[k][1]:.2f} |")
        print(f"\n| {out.name} | leg | closed form error mean / max abs deg | heel_pitch pay in stance |\n|---|---|---|---|")
        for leg, *_ in LEGS:
            r = rows[leg]
            if r["form"]:
                print(f"| | {leg} | {statistics.mean(r['form']):+.2f} / {max(map(abs, r['form'])):.2f} "
                      f"| {statistics.mean(r['pay']):.2f} |")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
