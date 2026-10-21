"""orun14 O9/O1: how often the front wrist drive sits at peak, per stride and by phase, and what the rod loop does then.

usage: pixi run python docs/probes/orun14/wrist_peak.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

``rod_gap.py`` found the front rod loops (``j_frodbot_*``) open past O9's
2 mm only on frames with the wrist drive at peak. This asks whether that
peak is the clip's demand or the load: per fore leg, over every seed's frames
from the engine's settle (1 s), with each fore paw's stance read as the
engine reads it (``CadexEvaluation.foot_series`` on the paw's collision
geoms, down at ``STANCE_MM``):

- **at peak**: the share of frames where ``|effort| >= AT_PEAK`` of
  ``effort_high``, over all frames, over stance frames and over swing frames,
  and its median per stride (touchdown to touchdown);
- **strides with any peak frame**, as a share of strides;
- **at peak, where**: the median wrist angle and its tracking error
  (command minus position, degrees), and the sign of the effort, so a drive
  pinned against the paw's load in stance reads apart from one chasing a
  swing target it cannot reach;
- **the stop**: the share of frames past the wrist joint's range (the
  model's ``jnt_range``, a soft limit) and the deepest overrun, degrees;
- **the loop**: the rod gap's median on peak frames against other frames,
  and the share of > 2 mm frames that are peak frames.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from rod_gap import gaps  # noqa: E402

LEGS = (("LF", "c_paw_fl", "j_wrist_l", "j_frodbot_l"), ("RF", "c_paw_fr", "j_wrist_r", "j_frodbot_r"))
AT_PEAK = 0.95
SETTLE_S = 1.0


def capsules(model, body_name):
    b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    out = []
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) != b or not (model.geom_contype[g] or model.geom_conaffinity[g]):
            continue
        kind = {mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule", mujoco.mjtGeom.mjGEOM_SPHERE: "sphere",
                mujoco.mjtGeom.mjGEOM_BOX: "box"}.get(int(model.geom_type[g]))
        if kind is None:
            continue
        w, x, y, z = (float(v) for v in model.geom_quat[g])
        out.append({"kind": kind, "size_mm": [1000 * float(v) for v in model.geom_size[g]],
                    "pos_mm": [1000 * float(v) for v in model.geom_pos[g]], "quat_xyzw": [x, y, z, w]})
    return out


def med(values):
    values = [v for v in values if v is not None and not np.isnan(v)]
    return statistics.median(values) if values else float("nan")


def stop(model, joint):
    j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
    return tuple(np.degrees(model.jnt_range[j]))


def seed_rows(model, geoms, rig, trace):
    frames = [f for f in trace["frames"] if f.get("component_placements") and "actuator_efforts" in f]
    t = np.array([f.get("nominal_time_s") or 0.0 for f in frames])
    keep = t >= SETTLE_S
    samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
    channels = [c["joint"] for c in trace["actuator_channels"]]
    peaks = [c["effort_high"] for c in trace["actuator_channels"]]
    loop = gaps(model, trace, warmup_s=SETTLE_S)
    out = {}
    for leg, paw, drive, rod in LEGS:
        k = channels.index(drive)
        h = np.array(E.foot_series(samples, paw, geoms[paw], rig["floor_mm"])["height"])[keep]
        down = h <= E.STANCE_MM
        effort = np.array([f["actuator_efforts"][k] for f in frames])[keep]
        share = np.abs(effort) / peaks[k]
        pos = np.array([f["joint_positions"][k] for f in frames])[keep]
        cmd = np.array([f["actuator_commands"][k] for f in frames])[keep]
        at = share >= AT_PEAK
        lo, hi = stop(model, drive)
        past = np.maximum(lo - pos, pos - hi)
        gap = loop[rod][0]
        n = min(len(gap), len(at))
        touch = [i for i in range(1, len(down)) if down[i] and not down[i - 1]]
        strides = [at[a:b].mean() for a, b in zip(touch, touch[1:])]
        out[leg] = {
            "all": at.mean(), "stance": at[down].mean() if down.any() else float("nan"),
            "swing": at[~down].mean() if (~down).any() else float("nan"),
            "stride_med": med(strides), "strides_any": float(np.mean([s > 0 for s in strides])) if strides else float("nan"),
            "pos": med(list(pos[at])), "err": med(list((cmd - pos)[at])),
            "pos_sign": float(np.mean(effort[at] > 0)) if at.any() else float("nan"),
            "gap_peak": med(list(gap[:n][at[:n]])), "gap_other": med(list(gap[:n][~at[:n]])),
            "over": int((gap[:n] > 2.0).sum()),
            "over_at_peak": float(at[:n][gap[:n] > 2.0].mean()) if (gap[:n] > 2.0).any() else float("nan"),
            "stance_share": down.mean(), "past": float((past > 0).mean()), "past_max": float(max(past.max(), 0.0)),
            "past_at_peak": float((past[at] > 0).mean()) if at.any() else float("nan"),
        }
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = {paw: capsules(model, paw) for _, paw, _, _ in LEGS}
    for arg in argv[1:]:
        out = Path(arg)
        rig = json.loads((out / "evaluation.json").read_text())["rig"]
        rows = {leg: [] for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            r = seed_rows(model, geoms, rig, json.loads(path.read_text()))
            for leg in rows:
                rows[leg].append(r[leg])
        print(f"## {out.name}: the front wrist drive at >= {AT_PEAK:.2f} of peak (medians over {len(rows['LF'])} seeds)\n")
        print("| leg | paw stance share | at peak: all / stance / swing | per stride (median) | strides with a peak frame "
              "| wrist ° at peak | cmd − pos ° at peak | effort > 0 at peak | rod gap mm at peak / other "
              "| frames > 2 mm (sum) | of those at peak | past the stop: frames / at peak / deepest ° |")
        print("|---|" + "---|" * 11)
        for leg, rs in rows.items():
            m = {k: med([r[k] for r in rs]) for k in rs[0]}
            over = sum(r["over"] for r in rs)
            print(f"| {leg} | {m['stance_share']:.2f} | {m['all']:.3f} / {m['stance']:.3f} / {m['swing']:.3f} "
                  f"| {m['stride_med']:.3f} | {m['strides_any']:.2f} | {m['pos']:+.1f} | {m['err']:+.1f} "
                  f"| {m['pos_sign']:.2f} | {m['gap_peak']:.2f} / {m['gap_other']:.2f} | {over} | {m['over_at_peak']:.2f} "
                  f"| {m['past']:.3f} / {m['past_at_peak']:.2f} / {max(r['past_max'] for r in rs):.1f} |")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
