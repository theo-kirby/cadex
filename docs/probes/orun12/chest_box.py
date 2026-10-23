"""orun12 O9: would the chest frame's collision box have met the fore leg?

    PYTHONPATH=cli pixi run python docs/probes/orun12/chest_box.py MODEL_XML EVALDIR \
        [--box SX,SY,SZ,PX,PY,PZ] [--at SEED:TIME_S]

Replays a judged evaluation's traces (every component's world placement, which
is its MuJoCo body frame; ``trace_check.py`` matches the engine's loop gaps
to 0.01 mm that way) against MODEL_XML's collision geoms on free bodies, and
measures, frame by frame, the chest frame's box against every paw (group 1)
and limb (group 3) geom on another body. ``--box`` (mm, full sizes and the
centre in the chest frame's own frame) replaces the model's box, so a size
can be tried on old traces before a rebuild. It prints:

- whether the model's contact filter lets the box meet each geom at all
  (contype / conaffinity, either way);
- the build pose's clearance per pair (must be positive: a box that touches
  the leg standing is wrong);
- per pair over the traces after ``--settle-s``: frames the box overlaps the
  geom, the deepest overlap, and the share of frames within 5 mm;
- with ``--at``, every pair's distance at one frame (seed 1001 at 2.76 s is
  v07-g1-best's deepest wrist-in-chest frame, ``o9-baseline.md``).

The traces were made without the contact, so an overlap here is a frame where
the box would have pushed back; the real meshes' depths are ``trace_check.py``'s.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import mujoco
import numpy as np

CHEST = "c_chest_frame"
PAW, LIMB = 2, 8   # contact groups 1 and 3 as contype bits


def scene(model, box):
    """A free-body model: the chest box, and every paw and limb geom on its own body."""

    chest = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, CHEST)
    cbox = [g for g in range(model.ngeom) if model.geom_bodyid[g] == chest and model.geom_type[g] == mujoco.mjtGeom.mjGEOM_BOX]
    if len(cbox) != 1:
        raise SystemExit(f"{CHEST}: expected one collision box, found {len(cbox)}")
    cbox = cbox[0]
    spec = mujoco.MjSpec()
    spec.option.gravity = [0, 0, 0]
    bodies = collections.OrderedDict()

    def body(name):
        if name not in bodies:
            b = spec.worldbody.add_body()
            b.name = name
            b.add_freejoint()
            bodies[name] = b
        return bodies[name]

    g = body(CHEST).add_geom()
    g.name = "chest_box"
    g.type = mujoco.mjtGeom.mjGEOM_BOX
    if box is None:
        g.size = model.geom_size[cbox].tolist()
        g.pos = model.geom_pos[cbox].tolist()
    else:
        g.size = [v / 2000.0 for v in box[:3]]
        g.pos = [v / 1000.0 for v in box[3:]]
    pairs = []
    ct, ca = int(model.geom_contype[cbox]), int(model.geom_conaffinity[cbox])
    for k in range(model.ngeom):
        if model.geom_bodyid[k] == chest or not (int(model.geom_contype[k]) & (PAW | LIMB)):
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[k])
        gk = body(name).add_geom()
        gk.name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, k) or f"{name}/geom{k}"
        gk.type = mujoco.mjtGeom(int(model.geom_type[k]))
        gk.size = model.geom_size[k].tolist()
        gk.pos = model.geom_pos[k].tolist()
        gk.quat = model.geom_quat[k].tolist()
        filtered = bool((ct & int(model.geom_conaffinity[k])) or (int(model.geom_contype[k]) & ca))
        pairs.append((gk.name, name, filtered))
    for b in bodies.values():
        for gg in b.geoms:
            gg.contype = gg.conaffinity = 0
    m = spec.compile()
    gid = {n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n, _, _ in pairs}
    qadr = {n: m.jnt_qposadr[m.body_jntadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)]] for n in bodies}
    return m, mujoco.MjData(m), mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "chest_box"), pairs, gid, qadr


def place(m, d, qadr, placements):
    for name, a in qadr.items():
        p = placements[name]
        x, y, z, w = p["rotation_xyzw"]
        d.qpos[a:a + 3] = np.asarray(p["position_mm"]) / 1000.0
        d.qpos[a + 3:a + 7] = [w, x, y, z]
    mujoco.mj_kinematics(m, d)


def distances(m, d, box, pairs, gid):
    fromto = np.zeros(6)
    return {n: 1000.0 * mujoco.mj_geomDistance(m, d, box, gid[n], 0.2, fromto) for n, _, _ in pairs}


def live_contacts(model, placements):
    """The full model posed from one frame's placements, and its chest-box contacts.

    Every joint is a hinge but the root's free joint: its angle is the
    child body's rotation against its parent's, about the joint axis. This
    is MODEL_XML's own collision pass, filter and excludes included, so a
    pair the filter keeps apart is absent however deep it is.
    """

    d = mujoco.MjData(model)
    for j in range(model.njnt):
        b = model.jnt_bodyid[j]
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b)
        a = model.jnt_qposadr[j]
        if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE:
            x, y, z, w = placements[name]["rotation_xyzw"]
            d.qpos[a:a + 3] = np.asarray(placements[name]["position_mm"]) / 1000.0
            d.qpos[a + 3:a + 7] = [w, x, y, z]
            continue
        parent = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.body_parentid[b])
        rp = _mat(placements[parent]["rotation_xyzw"]) if parent in placements else np.eye(3)
        rel = _mat_wxyz(model.body_quat[b]).T @ rp.T @ _mat(placements[name]["rotation_xyzw"])
        q = np.zeros(4)
        mujoco.mju_mat2Quat(q, rel.flatten())
        d.qpos[a] = 2.0 * np.arctan2(float(np.dot(q[1:], model.jnt_axis[j])), q[0])
    mujoco.mj_forward(model, d)
    fit = max(float(np.linalg.norm(d.xpos[b] * 1000.0 - placements[n]["position_mm"]))
              for n in placements for b in [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)] if b >= 0)
    chest = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, CHEST)
    live = {}
    for c in d.contact[:d.ncon]:
        g = [c.geom1, c.geom2]
        if chest in (model.geom_bodyid[g[0]], model.geom_bodyid[g[1]]):
            other = g[1] if model.geom_bodyid[g[0]] == chest else g[0]
            n = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, other) or f"geom{other}"
            live[n] = min(live.get(n, 1e9), 1000.0 * c.dist)
    return fit, live


def _mat(xyzw):
    x, y, z, w = xyzw
    return _mat_wxyz([w, x, y, z])


def _mat_wxyz(q):
    out = np.zeros(9)
    mujoco.mju_quat2Mat(out, np.asarray(q, float))
    return out.reshape(3, 3)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("model_xml")
    ap.add_argument("evaldir")
    ap.add_argument("--box", help="SX,SY,SZ,PX,PY,PZ in mm")
    ap.add_argument("--at", help="SEED:TIME_S")
    ap.add_argument("--settle-s", type=float, default=1.0)
    args = ap.parse_args(argv)
    box = [float(v) for v in args.box.split(",")] if args.box else None
    model = mujoco.MjModel.from_xml_path(args.model_xml)
    m, d, cbox, pairs, gid, qadr = scene(model, box)
    print("chest box", "override " + args.box if box else "from the model",
          "size mm", (2000.0 * m.geom_size[cbox]).round(1).tolist(), "centre mm", (1000.0 * m.geom_pos[cbox]).round(1).tolist())

    md = mujoco.MjData(model)
    mujoco.mj_forward(model, md)
    build = {}
    for name in qadr:
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        w, x, y, z = md.xquat[b]
        build[name] = {"position_mm": (md.xpos[b] * 1000.0).tolist(), "rotation_xyzw": [x, y, z, w]}
    place(m, d, qadr, build)
    clear = distances(m, d, cbox, pairs, gid)

    over = collections.Counter()
    near = collections.Counter()
    deep = collections.defaultdict(float)
    where = {}
    frames = 0
    at = None
    if args.at:
        s, t = args.at.split(":")
        at = (s, float(t))
    at_d = None
    for path in sorted(Path(args.evaldir).glob("seed-*-trace.json")):
        sd = path.name.split("-")[1]
        trace = json.loads(path.read_text())
        for f in trace["frames"]:
            if f["frame_kind"] != "solver_output":
                continue
            t = float(f["nominal_time_s"])
            hit = at is not None and sd == at[0] and abs(t - at[1]) < 0.0101
            if t < args.settle_s and not hit:
                continue
            place(m, d, qadr, f["component_placements"])
            dist = distances(m, d, cbox, pairs, gid)
            if hit:
                at_d = (t, dist, live_contacts(model, f["component_placements"]))
            if t < args.settle_s:
                continue
            frames += 1
            for n, v in dist.items():
                if v < 0.0:
                    over[n] += 1
                    if -v > deep[n]:
                        deep[n], where[n] = -v, f"{sd} {t:.2f}s"
                if v < 5.0:
                    near[n] += 1

    print(f"{frames} frames after {args.settle_s:.1f} s")
    print(f"{'geom':34s} {'filter':>6s} {'build mm':>9s} {'overlap fr':>10s} {'deepest mm':>10s} {'at':>12s} {'<5mm %':>7s}"
          + (f" {'@' + args.at:>12s}" if at_d else ""))
    for n, _body, filt in sorted(pairs, key=lambda p: -deep.get(p[0], 0.0)):
        row = (f"{n:34s} {'yes' if filt else 'no':>6s} {clear[n]:9.1f} {over[n]:10d} {deep.get(n, 0.0):10.1f} "
               f"{where.get(n, '-'):>12s} {100.0 * near[n] / max(frames, 1):7.1f}")
        if at_d:
            row += f" {at_d[1][n]:12.1f}"
        print(row)
    if at and at_d is None:
        print(f"--at {args.at}: no such frame")
    elif at_d:
        fit, live = at_d[2]
        print(f"MODEL_XML itself at {args.at} (joint angles from the placements; worst body off its "
              f"placement {fit:.2f} mm): the chest box's live contacts, mm (negative = overlap)")
        for n, v in sorted(live.items(), key=lambda kv: kv[1]) or [("none", 0.0)]:
            print(f"  {n:34s} {v:8.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
