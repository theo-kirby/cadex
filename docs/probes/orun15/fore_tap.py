"""orun15 P2: which paw fails ``no_tap``, and what its extra landings are, from a judged evaluation's traces.

usage: pixi run python docs/probes/orun15/fore_tap.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

``no_tap`` bounds ``touchdown_rate_ratio_max``: each paw's landings per
settled second over LH's stride rate (ADR-774). A **landing** is any
return to within ``STANCE_MM`` of the floor after a lift; a **step** is a
landing after a swing of at least ``SWING_MIN_S`` that advanced at least
``STEP_ADVANCE_HIP_HEIGHTS``. A **tap** is a landing that is not a step.

Per paw, over the 10 seeds after the settle: landings and steps per
stride (the predicate's ratio is the first), and for each tap its lift in
frames, its peak height over the floor, its plan advance, its phase in the
paw's own step cycle (0 the step's landing), and the paw's drive angles
(the shoulder, elbow and wrist position channels) at the tap's lift
against at the step's landing. The paw's geoms are its body's collision
geoms in ``MODEL_XML``, read as the engine reads them
(``CadexEvaluation.foot_series``).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402

PAWS = {"LF": ("c_paw_fl", "l"), "RF": ("c_paw_fr", "r"), "LH": ("c_paw_hl", "l"), "RH": ("c_paw_hr", "r")}
FORE_JOINTS = ("j_shoulder", "j_elbow", "j_wrist")


def geoms_of(model, body):
    b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
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


def med(v):
    return statistics.median(v) if v else float("nan")


def seed_taps(trace, rig, geoms, hip_mm):
    frames = [f for f in trace["frames"] if f.get("component_placements")]
    time = [f.get("nominal_time_s") or 0.0 for f in frames]
    samples = [(t, f["component_placements"]) for t, f in zip(time, frames)]
    channels = [c["joint"] for c in trace["actuator_channels"]]
    dt = E._frame_interval(time)
    out = {}
    for label, (paw, side) in PAWS.items():
        series = E.foot_series(samples, paw, geoms[paw], rig["floor_mm"])
        stance = [h <= E.STANCE_MM for h in series["height"]]
        lifts = []  # (start, end) frame indices of each whole lift
        i, n = 0, len(stance)
        while i < n:
            if stance[i]:
                i += 1
                continue
            start = i
            while i < n and not stance[i]:
                i += 1
            if start and i < n:
                lifts.append((start, i - 1))
        rows = []
        for start, end in lifts:
            land = time[end + 1]
            if land < E.SETTLE_S - 1e-9:
                continue
            p0, p1 = series["point"][start - 1], series["point"][end + 1]
            advance = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
            airborne = (end - start + 1) * dt
            step = airborne >= E.SWING_MIN_S - 1e-9 and advance >= E.STEP_ADVANCE_HIP_HEIGHTS * hip_mm
            angles = {}
            if label in ("LF", "RF"):
                for j in FORE_JOINTS:
                    name = f"{j}_{side}"
                    if name in channels:
                        k = channels.index(name)
                        angles[j] = frames[start]["joint_positions"][k]
            rows.append({"land": land, "lift": time[start], "frames": end - start + 1,
                         "peak": max(series["height"][start:end + 1]), "advance": advance,
                         "step": step, "angles": angles})
        steps = [r["land"] for r in rows if r["step"]]
        for r in rows:
            if r["step"]:
                continue
            before = [s for s in steps if s < r["land"]]
            after = [s for s in steps if s > r["land"]]
            r["phase"] = ((r["land"] - before[-1]) / (after[0] - before[-1])) if before and after else None
        out[label] = rows
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = {paw: geoms_of(model, paw) for paw, _ in PAWS.values()}
    for arg in argv[1:]:
        out = Path(arg).expanduser()
        ev = json.loads((out / "evaluation.json").read_text())
        rig, hip = ev["rig"], ev["rig"]["hip_height_mm"]
        engine = {s["seed"]: s["detail"]["footfall"] for s in ev["seeds"]}
        rows = {k: [] for k in PAWS}
        ratio = {k: [] for k in PAWS}
        per_stride = {k: [] for k in PAWS}
        for path in sorted(out.glob("seed-*-trace.json")):
            seed = int(path.name.split("-")[1])
            taps = seed_taps(json.loads(path.read_text()), rig, geoms, hip)
            hz = engine[seed].get("stride_hz")
            for k in PAWS:
                rows[k] += taps[k]
                r = (engine[seed].get("touchdown_rate_ratio") or {}).get(k)
                if r is not None:
                    ratio[k].append(r)
                n_steps = sum(1 for t in taps[k] if t["step"])
                if hz and n_steps:
                    per_stride[k].append(sum(1 for t in taps[k] if not t["step"]) / n_steps)
        print(f"## {out.name}: landings that are not steps (taps), {len(ratio['LH'])} seeds\n")
        print("| paw | engine ratio median (max) | taps per step, median seed | taps | lift frames median | "
              "peak mm median (q3) | advance mm median | phase in own step cycle q1 / med / q3 | "
              "shoulder / elbow / wrist ° at tap lift | at the steps' lift |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for k, rs in rows.items():
            taps = [r for r in rs if not r["step"]]
            steps = [r for r in rs if r["step"]]
            ph = [r["phase"] for r in taps if r.get("phase") is not None]
            q = statistics.quantiles(ph, n=4) if len(ph) > 1 else [float("nan")] * 3
            pk = statistics.quantiles([r["peak"] for r in taps], n=4) if len(taps) > 1 else [float("nan")] * 3

            def ang(group):
                if not group or not group[0]["angles"]:
                    return "–"
                return " / ".join(f"{med([r['angles'][j] for r in group if j in r['angles']]):+.0f}"
                                  for j in FORE_JOINTS)

            print(f"| {k} | {med(ratio[k]):.2f} ({max(ratio[k], default=float('nan')):.2f}) | "
                  f"{med(per_stride[k]):.2f} | {len(taps)} | {med([r['frames'] for r in taps]):.0f} | "
                  f"{med([r['peak'] for r in taps]):.1f} ({pk[2]:.1f}) | {med([r['advance'] for r in taps]):.0f} | "
                  f"{q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f} | {ang(taps)} | {ang(steps)} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
