"""orun16 SG (short-term step 3): a speed schedule's strides, generated offline and judged before a build.

usage: pixi run python docs/probes/orun16/sg_clip.py RUN/train/gallop-task.json RUN/train/cat_model-model.xml \
           STRIDES.json [OUT_DIR]

STRIDES.json is a list of strides, slowest first, each a dictionary of the
``assembly.gait`` arguments that differ from the bundle's own clip (in the
bundle's units: ``speed_m_s``, ``stride_length_m``, ``duty``, ``heel_from``,
``body_drop_m``, ``body_pitch_deg``, ``stance_shift_m``, ``swing_height_m``,
``hind_lag``, ``fore_lag``, ``spine_amplitude_deg``), plus a ``label``. The
offsets are the script's: LH 0, RH 1 - hind_lag, RF 0.5, LF 0.5 - fore_lag
(RH lead).

Each stride is generated with the engine's own generator
(``CadexGait.generate``) on the bundle's MJCF, with ``flat_feet="sole"`` and
``trail_feet`` as the bundle's clip, first at its own 50 Hz sample count and
then, as the worker's ``_reference_schedule_records`` does, at the largest
count any stride takes, so every stride is one phase grid. First the
bundle's own clip is regenerated and checked equal to it (qpos exactly).
Then per stride:

- the clock: speed, stride, rate, duty, samples;
- each pair's lag as a share of the stride and in ms, and whether its order
  crosses the stride before (the worker's ``schedule_footfall_order``);
- per hind leg, over the clip's stance samples: the share the heel is held
  (``heels.down``, what ``hock_down`` is trained towards), and the median
  height above the floor of the heel, the pad and the toe bulbs (each
  collision geom's lowest point, above the paw's lowest point in the home
  pose, which the generator takes as the ground), and the paw pin's
  range (toes-up of the metatarsus positive, both legs);
- the IK's largest miss per leg.

A refused stride is printed with the generator's reason. With OUT_DIR, each
stride is written into a copy of the task as its ``reference``
(``stride-K.json``), for ``docs/probes/orun15/clip_read.py``. Writes nothing
else.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import CadexGait  # noqa: E402

LEGS = (("LH", "l", "c_paw_hl", "c_heel_hl", 1.0), ("RH", "r", "c_paw_hr", "c_heel_hr", -1.0))


def offsets(hind_lag, fore_lag):
    return {"LH": 0.0, "RH": (1.0 - hind_lag) % 1.0, "RF": 0.5, "LF": 0.5 - fore_lag}


def generate(model, ref, stride, samples=None):
    p = ref["parameters"]
    off = p["phase_offsets"]
    hind = stride.get("hind_lag", (off["LH"] - off["RH"]) % 1.0)
    fore = stride.get("fore_lag", (off["RF"] - off["LF"]) % 1.0)
    heel_from = stride.get("heel_from", next(iter(ref["heels"].values()))["from_stance_share"])
    return CadexGait.generate(
        model, {k: v["foot_body"] for k, v in ref["legs"].items()},
        {"duty": stride.get("duty", p["duty_factor"]), "offsets": offsets(hind, fore),
         "spine_deg": stride.get("spine_amplitude_deg", p["spine_amplitude_deg"])},
        stride.get("speed_m_s", p["speed_m_s"]), stride_length_m=stride.get("stride_length_m", p["stride_length_m"]),
        swing_height_m=stride.get("swing_height_m", p["swing_height_m"]),
        pitch_amplitude_deg=p["pitch_amplitude_deg"], spine_joint=p["spine_joint"],
        spine_amplitude_deg=stride.get("spine_amplitude_deg", p["spine_amplitude_deg"]),
        heels={k: v["body"] for k, v in ref["heels"].items()},
        body_drop_m=stride.get("body_drop_m", p.get("body_drop_m", 0.0)),
        body_pitch_deg=stride.get("body_pitch_deg", p.get("body_pitch_deg", 0.0)),
        stance_shift_m=stride.get("stance_shift_m", p.get("stance_shift_m")), heel_from=heel_from,
        flat_feet="sole", trail_feet=True, samples=samples, mujoco=mujoco)


def lowest(model, data, geom):
    """The lowest world z of a capsule, sphere or box geom, in mm."""
    c, r, size = data.geom_xpos[geom], data.geom_xmat[geom].reshape(3, 3), model.geom_size[geom]
    kind = model.geom_type[geom]
    if kind == mujoco.mjtGeom.mjGEOM_SPHERE:
        return 1000.0 * (c[2] - size[0])
    if kind == mujoco.mjtGeom.mjGEOM_CAPSULE:
        return 1000.0 * (c[2] - abs(r[2, 2]) * size[1] - size[0])
    if kind == mujoco.mjtGeom.mjGEOM_BOX:
        return 1000.0 * (c[2] - sum(abs(r[2, k]) * size[k] for k in range(3)))
    return 1000.0 * c[2]


def body_geoms(model, body):
    b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
    return [g for g in range(model.ngeom) if model.geom_bodyid[g] == b and model.geom_contype[g] | model.geom_conaffinity[g]]


def judge(model, clip, before=None):
    p = clip["parameters"]
    period, off = p["period_s"], p["phase_offsets"]
    out = {"label": clip.get("label"), "speed_m_s": p["speed_m_s"], "hz": p["stride_frequency_hz"],
           "stride_m": p["stride_length_m"], "duty": p["duty_factor"], "samples": clip["samples"]}
    for pair, (a, b) in (("hind", ("RH", "LH")), ("fore", ("LF", "RF"))):
        lag = (off[b] - off[a]) % 1.0
        out[pair + "_lag"] = lag
        out[pair + "_lag_ms"] = 1000.0 * lag * period
    if before is not None:
        out["crossed"] = sorted((a, b) for a in before for b in before
                                if before[a] < before[b] and off[a] > off[b])
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_kinematics(model, data)
    floor = {paw: min(lowest(model, data, g) for g in body_geoms(model, paw)) for _, _, paw, _, _ in LEGS}
    for leg, side, paw, heel, sign in LEGS:
        geoms = body_geoms(model, paw)
        geoms.sort(key=lambda g: model.geom_size[g][0])  # toe bulbs are the smaller capsule
        toe, pad = geoms[0], geoms[-1]
        heel_g = body_geoms(model, heel)
        pin = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "j_pawpin_" + side)
        stance = [k for k, c in enumerate(clip["contact"][leg]) if c]
        held = sum(1 for k in stance if clip["heels"][leg]["down"][k])
        h, pd, tz, pins = [], [], [], []
        for k in stance:
            data.qpos[:] = clip["qpos"][k]
            mujoco.mj_kinematics(model, data)
            h.append(min(lowest(model, data, g) for g in heel_g) - floor[paw])
            pd.append(lowest(model, data, pad) - floor[paw])
            tz.append(lowest(model, data, toe) - floor[paw])
            pins.append(-sign * math.degrees(clip["qpos"][k][model.jnt_qposadr[pin]]))
        out[leg] = {"stance": len(stance), "heel_held": held / len(stance), "heel_mm": statistics.median(h),
                    "heel_mm_max": max(h), "pad_mm": statistics.median(pd), "toe_mm": statistics.median(tz),
                    "pin_deg": (min(pins), max(pins)),
                    "miss_mm": 1000.0 * clip["ik"]["max_miss_m"][leg]}
    return out


def show(j):
    print(f"### {j['label']}\n")
    print(f"- {j['stride_m']:.3f} m at {j['hz']:.2f} Hz = {j['speed_m_s']:.2f} m/s, duty {j['duty']}, "
          f"{j['samples']} samples")
    print(f"- hind lag {j['hind_lag']:.3f} = {j['hind_lag_ms']:.0f} ms; fore lag {j['fore_lag']:.3f} = "
          f"{j['fore_lag_ms']:.0f} ms" + (f"; order crossed: {j['crossed']}" if j.get("crossed") else ""))
    print("\n| leg | stance samples | heel held | heel mm (median / max) | pad mm | toe mm | pin deg toes-up | IK miss mm |")
    print("|---|---|---|---|---|---|---|---|")
    for leg in ("LH", "RH"):
        g = j[leg]
        print(f"| {leg} | {g['stance']} | {g['heel_held']:.2f} | {g['heel_mm']:.1f} / {g['heel_mm_max']:.1f} | "
              f"{g['pad_mm']:.1f} | {g['toe_mm']:.1f} | {g['pin_deg'][0]:+.1f}..{g['pin_deg'][1]:+.1f} | "
              f"{g['miss_mm']:.2f} |")
    print()


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    task = json.loads(Path(argv[0]).read_text())
    ref = task["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    strides = json.loads(Path(argv[2]).read_text())
    own = generate(model, ref, {})
    same = float(np.max(np.abs(np.array(own["qpos"]) - np.array(ref["qpos"])))) == 0.0
    print(f"regenerated bundle clip equals the bundle's: {same}\n")
    print("## The bundle's clip\n")
    show(judge(model, {**own, "label": ref["label"]}))
    clips = []
    for s in strides:
        try:
            c = generate(model, ref, s)
        except CadexGait.GaitError as exc:
            print(f"### {s.get('label')}: refused: {exc}\n")
            return 1
        c["label"] = s.get("label", c.get("label"))
        clips.append((s, c))
    rows = max(int(c["samples"]) for _, c in clips)
    print(f"## The schedule, on one grid of {rows} samples\n")
    before, ok = None, same
    for k, (s, c) in enumerate(clips):
        if int(c["samples"]) != rows:
            c = {**generate(model, ref, s, samples=rows), "label": c["label"]}
        j = judge(model, c, before)
        ok = ok and not j.get("crossed")
        before = c["parameters"]["phase_offsets"]
        show(j)
        if len(argv) > 3:
            out = Path(argv[3])
            out.mkdir(parents=True, exist_ok=True)
            (out / f"stride-{k}.json").write_text(json.dumps({**task, "reference": {**ref, **{
                key: v for key, v in c.items() if key in ref}}}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
