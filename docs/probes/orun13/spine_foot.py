"""orun13 O2/O4/O9: leo's two spine joints and rigid hind feet, read from a judged evaluation's traces.

usage: pixi run python docs/probes/orun13/spine_foot.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

MODEL_XML is the run's ``train/cat_model-model.xml``; each EVALUATION_DIR
holds ``docs/probes/orun11/judge.py``'s ``evaluation.json`` and
``seed-*-trace.json``. Every reading is over frames from the engine's settle
(1 s) on.

**Spine (O4).** ``j_spine`` (chest, driven) and ``j_spine2`` (lumbar, on the
cable) are read per frame as the child body's rotation against its parent
about the joint axis, from the model's rest pose (judge.py's closure
reading). Per seed: the range of each joint and of their sum per left-hind
stride (touchdown to touchdown), the share of frames either joint sits
within ``STOP_DEG`` of a stop, the cable's largest gap ``|j_spine2 -
j_spine|`` (O9: within 1 deg), and the phase of the sum's peak flexion
(most negative, nose-down bend... read off the sign of the model's axis) and
peak extension within the stride, as a share of the stride from the
left-hind touchdown.

**Rigid foot (O2).** The paw's and the heel's lowest collision points
(``CadexEvaluation.foot_series``, the engine's own reading). A frame is in
stance when the paw is within ``STANCE_MM`` (the engine's stance); the heel
is down when it is too. In leo's rigid foot the heel and toes are one
piece, so the foot is **flat** when both are down; **toes-up** is the
orun12 fault (heel down, paw off the floor); **heel-up** is a toe stance.
Per leg: the shares of heel-down frames that are flat and toes-up, the
heel's share of stance (checked against the engine's ``heel_down_share``),
and the median sole tilt in stance, the paw's lowest point minus the
heel's (mm; 0 is flat, positive is toes up).

Writes nothing; prints markdown tables. Left and right are given apart (O5).
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402

STOP_DEG = 1.0
SPINE = ("j_spine", "j_spine2")
LEGS = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))


def rot(xyzw):
    x, y, z, w = xyzw
    m = np.zeros(9)
    mujoco.mju_quat2Mat(m, np.array([w, x, y, z], dtype=float))
    return m.reshape(3, 3)


def joint_reader(model, name):
    j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    child = int(model.jnt_bodyid[j])
    parent = int(model.body_parentid[child])
    cname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, child)
    pname = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, parent)
    q0 = np.zeros(9)
    mujoco.mju_quat2Mat(q0, model.body_quat[child])
    q0 = q0.reshape(3, 3)
    axis = np.asarray(model.jnt_axis[j], float)
    lo, hi = (math.degrees(v) for v in model.jnt_range[j])

    def read(placements):
        rel = rot(placements[pname]["rotation_xyzw"]).T @ rot(placements[cname]["rotation_xyzw"])
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, (q0.T @ rel).reshape(9))
        return math.degrees(2.0 * math.atan2(float(np.dot(quat[1:], axis)), float(quat[0])))

    return read, (lo, hi)


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(v, spec="%.2f"):
    return "–" if v is None else spec % v


def seed_rows(model, out: Path):
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    floor = rig["floor_mm"]
    readers = {n: joint_reader(model, n) for n in SPINE}
    paw_geoms = paw_capsules(model)
    engine = {s["seed"]: s["detail"] for s in evaluation["seeds"]}
    rows = []
    for path in sorted(out.glob("seed-*-trace.json")):
        seed = int(path.name.split("-")[1])
        trace = json.loads(path.read_text())
        frames = [f for f in trace["frames"] if f.get("joint_positions")]
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
        late = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
        q = {n: [readers[n][0](samples[i][1]) for i in late] for n in SPINE}
        t = [samples[i][0] for i in late]
        total = [a + b for a, b in zip(q["j_spine"], q["j_spine2"])]
        at_stop = sum(1 for k in range(len(late)) if any(
            min(q[n][k] - readers[n][1][0], readers[n][1][1] - q[n][k]) <= STOP_DEG for n in SPINE))
        row = {"seed": seed, "frames": len(late), "stop": at_stop / max(len(late), 1),
               "cable": max(abs(a - b) for a, b in zip(q["j_spine"], q["j_spine2"])) if late else None,
               "q1": (min(q["j_spine"]), max(q["j_spine"])), "q2": (min(q["j_spine2"]), max(q["j_spine2"]))}
        downs = [x for x in engine[seed]["feet"]["c_paw_hl"]["touchdowns_s"] if x >= E.SETTLE_S]
        ranges = {n: [] for n in SPINE + ("sum",)}
        flex, ext = [], []
        for a, b in zip(downs, downs[1:]):
            idx = [k for k, x in enumerate(t) if a <= x < b]
            if len(idx) < 3:
                continue
            for n, series in (("j_spine", q["j_spine"]), ("j_spine2", q["j_spine2"]), ("sum", total)):
                ranges[n].append(max(series[k] for k in idx) - min(series[k] for k in idx))
            kmin = min(idx, key=lambda k: total[k])
            kmax = max(idx, key=lambda k: total[k])
            flex.append((t[kmin] - a) / (b - a))
            ext.append((t[kmax] - a) / (b - a))
        row.update({"range_" + n: med(v) for n, v in ranges.items()})
        row["strides"] = len(ranges["sum"])
        row["min_phase"], row["max_phase"] = med(flex), med(ext)
        for leg, paw in LEGS:
            sole = E.foot_series(samples, paw, paw_geoms[paw], floor)["height"]
            heel_body = rig["heels"][paw]
            heel = E.foot_series(samples, heel_body["body"], heel_body["geoms"], floor)["height"]
            stance = [i for i in late if sole[i] <= E.STANCE_MM]
            heel_down = [i for i in late if heel[i] <= E.STANCE_MM]
            flat = [i for i in heel_down if sole[i] <= E.STANCE_MM]
            row[leg] = {
                "heel_share": len(flat) / max(len(stance), 1),
                "engine_share": engine[seed]["heels"][paw]["heel_down_share"],
                "flat": len(flat) / max(len(heel_down), 1) if heel_down else None,
                "toes_up": (len(heel_down) - len(flat)) / max(len(heel_down), 1) if heel_down else None,
                "tilt": med([sole[i] - heel[i] for i in stance]),
                "heel_mm": med([heel[i] for i in stance]),
            }
        rows.append(row)
    return rows, evaluation


def paw_capsules(model):
    """Each hind paw body's collision geoms, in the engine's rig form (mm, local, xyzw)."""

    out = {}
    for _, paw in LEGS:
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, paw)
        geoms = []
        for g in range(model.ngeom):
            if int(model.geom_bodyid[g]) != b or not (model.geom_contype[g] or model.geom_conaffinity[g]):
                continue
            kind = {mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule", mujoco.mjtGeom.mjGEOM_SPHERE: "sphere",
                    mujoco.mjtGeom.mjGEOM_BOX: "box"}.get(int(model.geom_type[g]))
            if kind is None:
                continue
            w, x, y, z = (float(v) for v in model.geom_quat[g])
            geoms.append({"kind": kind, "size_mm": [1000 * float(v) for v in model.geom_size[g]],
                          "pos_mm": [1000 * float(v) for v in model.geom_pos[g]], "quat_xyzw": [x, y, z, w]})
        out[paw] = geoms
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    for arg in argv[1:]:
        out = Path(arg)
        rows, evaluation = seed_rows(model, out)
        cable = next((r for r in evaluation.get("closure", {}).get("rows", []) if r["name"] == "coupling/cable_spine"),
                     None)
        print(f"## {out.name}\n")
        print("| seed | strides | j_spine min / max deg | j_spine2 min / max deg | range per stride j_spine / j_spine2 / sum deg "
              "| at a stop | cable gap max deg | peak flex / ext phase |")
        print("|---|" + "---|" * 7)
        for r in rows:
            print(f"| {r['seed']} | {r['strides']} | {r['q1'][0]:+.1f} / {r['q1'][1]:+.1f} | {r['q2'][0]:+.1f} / {r['q2'][1]:+.1f} "
                  f"| {fmt(r['range_j_spine'], '%.1f')} / {fmt(r['range_j_spine2'], '%.1f')} / {fmt(r['range_sum'], '%.1f')} "
                  f"| {r['stop']:.2f} | {fmt(r['cable'], '%.2f')} | {fmt(r['min_phase'])} / {fmt(r['max_phase'])} |")
        print(f"\nmedians: range per stride sum {fmt(med([r['range_sum'] for r in rows]), '%.1f')} deg, "
              f"at a stop {fmt(med([r['stop'] for r in rows]))}, cable gap max {fmt(max(r['cable'] for r in rows), '%.2f')} deg"
              + (f" (judge.py closure: median {cable['median']:.3f}, max {cable['max']:.2f} {cable['unit']})" if cable else "")
              + "\n")
        print("| leg | heel share of stance (engine) | heel-down frames flat | toes-up | sole tilt mm (toes minus heel) "
              "| heel mm in stance |")
        print("|---|---|---|---|---|---|")
        for leg, _ in LEGS:
            m = {k: med([r[leg][k] for r in rows]) for k in ("heel_share", "engine_share", "flat", "toes_up", "tilt",
                                                             "heel_mm")}
            print(f"| {leg} | {fmt(m['heel_share'])} ({fmt(m['engine_share'])}) | {fmt(m['flat'])} | {fmt(m['toes_up'])} "
                  f"| {fmt(m['tilt'], '%+.1f')} | {fmt(m['heel_mm'], '%.1f')} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
