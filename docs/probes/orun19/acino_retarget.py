"""Retarget one AcinoSet cheetah stride to leo v06 as a gait clip (orun19 M1, charter O4).

usage: pixi run python -I docs/probes/orun19/acino_retarget.py MODEL_XML FTE_PICKLE FIRST END LABEL OUT_DIR [SAMPLES]

``MODEL_XML`` is leo v06's MJCF as a task bundle carries it (``runs/s1-v06/train/
cat_model-model.xml``, sha256 ``f9b8ab82…``). The rest is orun18's
``acino_retarget.py`` unchanged: the stride is read by its ``cheetah_stride`` (12 Hz
low-pass, the wrist and hock as the paw, stance as the wrist or hock stopped) and
solved by ``retarget.retarget`` (same trunk, spine, foot-hold and clamped leg
solve). The clip and its measure go to ``OUT_DIR`` beside the capture, never to
the repository (D5a); their sha256 is reported.

**What O4 asks, and why orun18's solve already does it on v06.** The solve reads
each leg's chain from the model (``CadexGait.leg_chains`` from the foot body to the
trunk) and places the foot body's lowest collision geom on the target. On v06:

- the hind foot body ``c_paw_h*`` holds only the ball (r 30 mm), so the hind
  target is the ball, through hip, knee and hock (``j_hhaa``, ``j_hip``,
  ``j_knee``, ``j_ankle`` and the parallelogram's passive pins);
- the fore foot body ``c_paw_f*`` holds only the ball (r 22 mm) on the forearm,
  so the fore chain is abduction, scapula, shoulder and elbow, with no wrist.
  The capture's fore point is the wrist itself (the FTE has no carpus or digits),
  so nothing below it is dropped: the ball is fitted at the wrist's track;
- the spine maps to ``j_spine`` / ``j_spine_yaw`` as before;
- **the tail** (``map_tail``): the capture's tail chord (tail base to tip) against
  its pelvis, in pitch and heading, about the stride's mean as the spine is, goes
  to ``j_tail1`` (pitch) and ``j_tail2`` (yaw) by leo's own gains on its tail chord
  (``j_tail1``'s anchor to ``c_tail_tip``'s centre of mass, against ``c_pelvis_frame``), measured with the
  cable followers (the model's joint couplings) applied; clamped to the drives'
  ranges. The followers are written into ``qpos`` as the couplings hold them;
- **the head** is measured, not posed: its chord (neck base to nose) against the
  thorax, in pitch and heading. leo's speed task holds ``j_neck1``, ``j_neckyaw``
  and ``j_headpitch`` (they are not actions), so a posed head could not be
  tracked and would only make the reset start off its hold.

**What this adds for v06**, measured on the solved clip, nothing rewarded:

- foot miss split into stance and swing per leg (v06 has no wrist, so the fore
  leg's misses are the new risk);
- the heel pad's height over the ground through each hind stance (its lowest
  point, r 16 mm, ``c_heel_h*``), and the share of hind stance samples with the
  pad within 5 mm of the ground: whether the clip asks for a toe or a
  plantigrade stance;
- the hock's angle (``j_ankle``, the right leg's negated to read as the left's)
  through hind stance, against the owner's "both touch near hock −40°".
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ORUN18 = Path(__file__).resolve().parents[1] / "orun18"
sys.path.insert(0, str(ORUN18))

import acino_retarget as AR  # noqa: E402
import retarget as R  # noqa: E402

import mujoco  # noqa: E402

HEEL = {"LH": "c_heel_hl", "RH": "c_heel_hr"}
HOCK = {"LH": "j_ankle_l", "RH": "j_ankle_r"}
PAD_TOUCH_M = 0.005  # a heel pad within 5 mm of the ground counts as touching


def heel_and_miss(model_path: Path, clip: dict, measure: dict) -> dict:
    """Stance/swing miss per leg; heel pad height and hock angle through hind stance."""

    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    # the ball's centre in stance is held at its home height, so the ground is the
    # median of its stance heights less its radius
    ground = {f: float(np.median([p[2] for p, c in zip(clip["foot_positions_m"][f], clip["contact"][f]) if c]))
              for f in R.LEGS}
    out: dict = {"foot_miss_mm": {}, "heel_pad": {}}
    for f in R.LEGS:
        miss = np.array(measure["foot_miss_mm"][f]["per_sample"])
        down = np.array(clip["contact"][f], dtype=bool)
        out["foot_miss_mm"][f] = {
            "stance_max": round(float(miss[down].max()) if down.any() else 0.0, 1),
            "swing_max": round(float(miss[~down].max()) if (~down).any() else 0.0, 1)}
    for f, body in HEEL.items():
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
        g = int(model.body_geomadr[b])
        radius = float(model.geom_size[g][0])
        hock = int(model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, HOCK[f])])
        foot_r = float(model.geom_size[int(model.body_geomadr[
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, R.LEGS[f])])][0])
        floor = ground[f] - foot_r
        heights, angles = [], []
        for k, q in enumerate(clip["qpos"]):
            if not clip["contact"][f][k]:
                continue
            data.qpos[:] = q
            mujoco.mj_kinematics(model, data)
            heights.append(1000.0 * (float(data.geom_xpos[g][2]) - radius - floor))
            # the right leg's joints are mirrored: its angles are negated to read as the left's
            angles.append(math.degrees(float(q[hock])) * (1.0 if f == "LH" else -1.0))
        h = np.array(heights)
        out["heel_pad"][f] = {
            "stance_samples": len(h),
            "height_mm": [round(float(h.min()), 1), round(float(h.max()), 1)] if len(h) else None,
            "touch_share": round(float(np.mean(h < 1000.0 * PAD_TOUCH_M)), 3) if len(h) else None,
            "hock_deg": [round(min(angles), 1), round(max(angles), 1)] if angles else None}
    return out


def _couple(model, q: np.ndarray) -> None:
    """Apply the model's joint couplings (the tail's cables) to ``q`` in place."""

    for _ in range(int(model.neq)):
        for e in range(int(model.neq)):
            if int(model.eq_type[e]) != int(mujoco.mjtEq.mjEQ_JOINT) or int(model.eq_obj2id[e]) < 0:
                continue
            c = model.eq_data[e][:5]
            x = float(q[model.jnt_qposadr[model.eq_obj2id[e]]])
            q[model.jnt_qposadr[model.eq_obj1id[e]]] = sum(float(c[i]) * x ** i for i in range(5))


def _bend(base_minus_tip: np.ndarray, frame_x: np.ndarray, frame_heading: float) -> tuple[float, float]:
    return (R._pitch(base_minus_tip) - R._pitch(frame_x),
            (R._heading(base_minus_tip) - frame_heading + math.pi) % (2 * math.pi) - math.pi)


def map_tail(model_path: Path, stride: dict, clip: dict) -> dict:
    """Pose j_tail1/j_tail2 from the capture's tail (see the docstring); return the measure."""

    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    body = {n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n) for n in ("c_tail_tip", "c_pelvis_frame")}
    jt = {n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in ("j_tail1", "j_tail2")}
    adr = {n: int(model.jnt_qposadr[j]) for n, j in jt.items()}
    home = np.asarray(model.key_qpos[0], dtype=float)

    def leo(q0: np.ndarray, t1: float, t2: float) -> tuple[float, float]:
        q = q0.copy()
        q[adr["j_tail1"]], q[adr["j_tail2"]] = t1, t2
        _couple(model, q)
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        px = data.xmat[body["c_pelvis_frame"]].reshape(3, 3)[:, 0]
        # the body frames sit at the origin, so the chord runs from j_tail1's anchor to
        # the tip body's centre of mass
        return _bend(data.xanchor[jt["j_tail1"]] - data.xipos[body["c_tail_tip"]], px, R._heading(px))

    b0 = leo(home, 0.0, 0.0)
    gain_p = (leo(home, 0.05, 0.0)[0] - b0[0]) / 0.05
    gain_y = (leo(home, 0.0, 0.05)[1] - b0[1]) / 0.05
    names = stride["skeleton"]["names"]
    pts = np.asarray(stride["skeleton"]["points"])
    ix = {n: names.index(n) for n in ("tail_base", "tail_tip")}
    n = int(clip["samples"])
    cap = np.array([_bend(pts[k, ix["tail_base"]] - pts[k, ix["tail_tip"]], stride["pelvis"][k],
                          math.atan2(-stride["pelvis_lateral"][k][0], stride["pelvis_lateral"][k][1]))
                    for k in range(n)])
    want = np.column_stack([(cap[:, 0] - cap[:, 0].mean()) / gain_p, (cap[:, 1] - cap[:, 1].mean()) / gain_y])
    rng = [tuple(float(v) for v in model.jnt_range[jt[j]]) for j in ("j_tail1", "j_tail2")]
    got = np.column_stack([np.clip(want[:, i], *rng[i]) for i in range(2)])
    qpos = np.asarray(clip["qpos"], dtype=float)
    for k in range(n):
        qpos[k, adr["j_tail1"]], qpos[k, adr["j_tail2"]] = got[k]
        _couple(model, qpos[k])
    clip["qpos"] = qpos.tolist()
    for j in ("j_tail1", "j_tail2"):
        clip["joints"].append(j)
        clip["joint_limits_rad"].append(list(rng[0 if j == "j_tail1" else 1]))
    for k in range(n):
        clip["joint_angles_rad"][k] += [float(got[k, 0]), float(got[k, 1])]
    deg = np.degrees
    return {"gain_pitch": gain_p, "gain_yaw": gain_y,
            "capture_pitch_deg": [round(float(deg(cap[:, 0].min())), 1), round(float(deg(cap[:, 0].max())), 1)],
            "capture_heading_deg": [round(float(deg(cap[:, 1].min())), 1), round(float(deg(cap[:, 1].max())), 1)],
            "j_tail1_deg": [round(float(deg(got[:, 0].min())), 1), round(float(deg(got[:, 0].max())), 1)],
            "j_tail2_deg": [round(float(deg(got[:, 1].min())), 1), round(float(deg(got[:, 1].max())), 1)],
            "clipped_share": round(float(np.mean(np.any(np.abs(want - got) > 1e-9, axis=1))), 3)}


def measure_head(stride: dict, n: int) -> dict:
    """The capture's head chord (neck base to nose) against its thorax, in pitch and heading (deg)."""

    names = stride["skeleton"]["names"]
    pts = np.asarray(stride["skeleton"]["points"])
    nose, neck = names.index("nose"), names.index("neck_base")
    # the head points sit over the hind floor and the thorax is read the same way, so the
    # chord's direction is exact; the head is forward of the neck, so nose minus neck
    cap = np.array([_bend(pts[k, nose] - pts[k, neck], stride["thorax"][k],
                          math.atan2(-stride["thorax_lateral"][k][0], stride["thorax_lateral"][k][1]))
                    for k in range(n)])
    d = np.degrees(cap)
    return {"pitch_deg": [round(float(d[:, 0].min()), 1), round(float(d[:, 0].max()), 1)],
            "heading_deg": [round(float(d[:, 1].min()), 1), round(float(d[:, 1].max()), 1)],
            "posed": False, "why": "j_neck1/j_neckyaw/j_headpitch are held, not actions, in leo's speed task"}


def main(argv: list[str]) -> None:
    model_path, pickle_path, first, end, label, out_dir = argv[:6]
    samples = int(argv[6]) if len(argv) > 6 else None
    stride = AR.cheetah_stride(Path(pickle_path), int(first), int(end), samples)
    clip, measure, _ = R.retarget(Path(model_path), Path(pickle_path), int(first), int(end), label,
                                  samples, stride=stride)
    clip["label"] = clip["label"].replace("retargeted to leo v05", "retargeted to leo v06")
    measure["model_sha256"] = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    measure["cheetah"] = {"fps": stride["fps"], "cutoff_hz": AR.CUTOFF_HZ,
                          "pivot_over_distal_floor_m": {g: float(np.mean([stride["pivot"][f][:, 2] for f in feet]))
                                                        for g, feet in AR.GIRDLE_FEET.items()},
                          "paw": "wrist/hock (FTE has no paw): duty short, flight long, raw slip is the roll"}
    measure["v06"] = heel_and_miss(Path(model_path), clip, measure)
    measure["v06"]["tail"] = map_tail(Path(model_path), stride, clip)
    measure["v06"]["head"] = measure_head(stride, int(clip["samples"]))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(clip)
    (out / f"{label}.clip.json").write_text(text)
    measure["clip_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (out / f"{label}.measure.json").write_text(json.dumps(measure, indent=1))
    print(json.dumps({k: measure[k] for k in ("label", "leo", "v06", "clip_sha256")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
