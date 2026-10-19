"""Replay judged evaluation traces against the real part meshes (orun12 O9, P1, P2, Q1, Q2).

usage: PYTHONPATH=cli pixi run python docs/probes/orun12/trace_check.py PROJECT MODEL_XML EVALDIR [EVALDIR ...]
       [--paw-mm 8] [--heel-mm 8] [--pen-mm 5] [--settle-s 1] [--jobs 10]

PROJECT is the cadex project whose accepted attempt retained the meshes
(``film.retained_solids``); MODEL_XML is the run's compiled
``train/cat_model-model.xml``; each EVALDIR holds ``judge.py``'s
``seed-*-trace.json`` and ``evaluation.json``.

The traces carry every component's world placement per frame, and a
component's frame is its MuJoCo body's frame (checked: the rod gaps rebuilt
here equal the engine's ``closure`` rows). From those placements alone,
independent of the engine's contact readings, it reports per seed and as a
median over seeds, frames before ``--settle-s`` excluded:

1. **Heels, per hind leg.** A paw is in stance when the lowest point of its
   paw or claws mesh is under ``--paw-mm``; its heel is down when the heel
   mesh's lowest point is under ``--heel-mm``. The heel's stance share, its
   share at toe-off (the last stance frame of each contact), and its median
   stance height (mm), beside the engine's ``heel_down_share`` for the same
   seed.
2. **Rod loops.** For each ``equality/connect`` the distance between its two
   sites, median and worst (mm), against O9's 2 mm bar.
3. **Flight.** Strides run from one left-hind touchdown to the next; a
   stride's flight is its frames with no paw, claws or heel mesh under
   ``--paw-mm``. The share of strides with flight and the median flight
   time (s) at the trace's frame resolution.
4. **Interpenetration, real meshes.** Every component's mesh, as a convex
   hull on a free body (mocap bodies are static and never collide with
   each other), posed per frame, is only the broadphase: a hull overlap
   deeper than ``--pen-mm`` makes a candidate pair. Its depth is then read
   on the real triangles: each part's vertices and face centroids, put in
   the other's frame, are signed against its surface (a KD-tree of surface
   samples and their face normals), and the deepest few inside are
   confirmed by ray parity against every triangle (two rays, which must
   agree, as a tessellation can carry a cracked edge) and measured by exact
   point-to-triangle distance. Faces are first welded and wound
   consistently outward (``orient``). A pair counts when its real depth passes
   ``--pen-mm`` and its parts do not touch in the build pose (``qpos0``:
   real meshes overlapping or within ``TOUCH_MM``). The pair, its frames
   and its deepest mm are printed. The floor is a plane: each lower-leg
   part's deepest point below it (mm).
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")  # one thread a worker; the pool is the parallelism

import mujoco
import numpy as np
from scipy.spatial import cKDTree

from cadex_cli import film

HIND = (("LH", "hl"), ("RH", "hr"))
FEET = {"LH": ("c_paw_hl", "c_claws_hl"), "RH": ("c_paw_hr", "c_claws_hr"),
        "LF": ("c_paw_fl", "c_claws_fl"), "RF": ("c_paw_fr", "c_claws_fr")}
LOWER = ("c_shin_{s}", "c_qdd_hock_{s}", "c_meta_h{s}", "c_heel_h{s}", "c_paw_h{s}", "c_claws_h{s}",
         "c_spring_h{s}", "c_forearm_{s}", "c_paw_f{s}", "c_claws_f{s}")

TOUCH_MM = 2.0
POINT_MM = 1.5  # query-point spacing; far finer than the depth bar
CONFIRM = 24  # deepest estimated points confirmed exactly, per part and pair
RAYS = [np.asarray(r) / np.linalg.norm(r) for r in ([0.5773, 0.5774, 0.5775], [-0.3712, 0.8128, -0.4491])]  # off every axis

ARGS = None
STATE = {}


def orient(t):
    """Triangles ``t`` (n, 3, 3) wound consistently and outward.

    A tessellation's faces can come wound either way (a reversed CAD face),
    and the depth estimate signs by face normals. Vertices are welded by
    position, faces are flipped to agree across each shared edge
    (breadth-first over each connected shell), and a shell whose signed
    volume is negative is flipped whole.
    """

    _, ids = np.unique(np.round(t.reshape(-1, 3), 3), axis=0, return_inverse=True)
    f = ids.reshape(-1, 3)
    edges = collections.defaultdict(list)
    for i, (a, b, c) in enumerate(f.tolist()):
        for u, v in ((a, b), (b, c), (c, a)):
            edges[(min(u, v), max(u, v))].append((i, u < v))
    flip = np.zeros(len(f), bool)
    shell = np.full(len(f), -1)
    neighbours = collections.defaultdict(list)
    for faces in edges.values():
        if len(faces) == 2:
            (i, di), (j, dj) = faces
            neighbours[i].append((j, di == dj))  # same direction: one of the two must flip
            neighbours[j].append((i, di == dj))
    for start in range(len(f)):
        if shell[start] >= 0:
            continue
        shell[start] = start
        queue = collections.deque([start])
        while queue:
            i = queue.popleft()
            for j, differ in neighbours[i]:
                if shell[j] < 0:
                    shell[j] = start
                    flip[j] = flip[i] ^ differ
                    queue.append(j)
    t = np.where(flip[:, None, None], t[:, [0, 2, 1]], t)
    volume = (t[:, 0] * np.cross(t[:, 1], t[:, 2])).sum(axis=1)
    for root in np.unique(shell):
        mine = shell == root
        if volume[mine].sum() < 0:
            t[mine] = t[mine][:, [0, 2, 1]]
    return t


class Solid:
    """One part's triangles in its own frame, with what the depth test needs."""

    def __init__(self, flat):
        t = orient(np.asarray(flat, float).reshape(-1, 3, 3))
        self.a, self.b, self.c = t[:, 0], t[:, 1], t[:, 2]
        n = np.cross(self.b - self.a, self.c - self.a)
        norm = np.linalg.norm(n, axis=1)
        self.n = n / np.where(norm > 0, norm, 1.0)[:, None]
        centroid = t.mean(axis=1)
        samples = np.concatenate([centroid] + [(2 * t[:, i] + t[:, (i + 1) % 3] + t[:, (i + 2) % 3]) / 4 for i in range(3)])
        self.tree = cKDTree(samples)
        self.sample_n = np.tile(self.n, (4, 1))
        points = np.concatenate([t.reshape(-1, 3), centroid])
        _, keep = np.unique(np.floor(points / POINT_MM), axis=0, return_index=True)  # one point per POINT_MM cell
        self.points = points[keep]
        self.lo, self.hi = t.reshape(-1, 3).min(axis=0), t.reshape(-1, 3).max(axis=0)

    def inside(self, p):
        """Inside by ray parity against every triangle, on two rays that must agree.

        A tessellation can carry a few cracked edges; a ray through one
        miscounts, two independent rays rarely both do.
        """

        return self.parity(p, RAYS[0]) & self.parity(p, RAYS[1])

    def parity(self, p, RAY):
        e1, e2 = self.b - self.a, self.c - self.a
        h = np.cross(RAY, e2)
        det = (e1 * h).sum(axis=1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = p[:, None, :] - self.a[None]
        u = (s * h[None]).sum(axis=2) * inv
        q = np.cross(s, e1[None])
        v = (q * RAY).sum(axis=2) * inv
        t = (q * e2[None]).sum(axis=2) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        return hit.sum(axis=1) % 2 == 1

    def distance(self, p):
        """Exact distance from each point to the surface."""

        P = p[:, None, :]
        best = np.full(len(p), np.inf)
        d_plane = ((P - self.a[None]) * self.n[None]).sum(axis=2)
        proj = P - d_plane[..., None] * self.n[None]
        inside = np.ones(d_plane.shape, bool)
        for x, y in ((self.a, self.b), (self.b, self.c), (self.c, self.a)):
            inside &= (np.cross(y - x, proj - x[None]) * self.n[None]).sum(axis=2) >= 0
            e = y - x
            ee = np.maximum((e * e).sum(axis=1), 1e-18)
            t = np.clip(((P - x[None]) * e[None]).sum(axis=2) / ee, 0.0, 1.0)
            best = np.minimum(best, np.linalg.norm(P - (x[None] + t[..., None] * e[None]), axis=2).min(axis=1))
        plane = np.where(inside, np.abs(d_plane), np.inf).min(axis=1)
        return np.minimum(best, plane)

    def depth_of(self, points, depth_floor=0.0):
        """(deepest mm of ``points`` inside this solid, nearest gap mm), points in this frame.

        Points less than ``depth_floor`` from a surface sample are not
        confirmed; a depth at or under the floor reads as 0.
        """

        box = np.all((points >= self.lo - 1.0) & (points <= self.hi + 1.0), axis=1)
        p = points[box]
        if not len(p):
            return 0.0, np.inf
        d, i = self.tree.query(p)
        sign = ((p - self.tree.data[i]) * self.sample_n[i]).sum(axis=1)
        cand = np.where((sign < 0) & (d > depth_floor))[0]  # a sample's distance bounds the exact one from above
        if not len(cand):
            return 0.0, float(d.min())
        cand = cand[np.argsort(-d[cand])[:CONFIRM]]
        real = self.inside(p[cand])
        if not real.any():
            return 0.0, float(d.min())
        return float(self.distance(p[cand][real]).max()), 0.0


def to_frame(points, pa, pb):
    """Points in part a's frame, placed at ``pa``, into part b's frame at ``pb``."""

    Ra, Rb = quat_mat(pa["rotation_xyzw"]), quat_mat(pb["rotation_xyzw"])
    world = points @ Ra.T + np.asarray(pa["position_mm"])
    return (world - np.asarray(pb["position_mm"])) @ Rb


def real_depth(P, a, b, depth_floor=0.0):
    """(deepest real-mesh overlap mm, nearest gap mm) of parts a and b placed by ``P``.

    Memoised on the pair's relative pose to 0.25 mm and about 0.1 degrees:
    parts that hold still against each other are measured once.
    """

    Ra, Rb = quat_mat(P[a]["rotation_xyzw"]), quat_mat(P[b]["rotation_xyzw"])
    rel = np.concatenate([(np.asarray(P[a]["position_mm"]) - P[b]["position_mm"]) @ Rb / 0.25,
                          (Rb.T @ Ra).ravel() / 0.002])
    key = (a, b, depth_floor, tuple(np.round(rel).astype(int)))
    if key not in MEMO:
        MEMO[key] = _real_depth(P, a, b, depth_floor)
    return MEMO[key]


MEMO = {}


def _real_depth(P, a, b, depth_floor):
    sa, sb = STATE["solids"][a], STATE["solids"][b]
    d1, g1 = sb.depth_of(to_frame(sa.points, P[a], P[b]), depth_floor)
    d2, g2 = sa.depth_of(to_frame(sb.points, P[b], P[a]), depth_floor)
    return max(d1, d2), min(g1, g2)


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def setup(project, model_xml):
    """Per process: meshes, the hull scene, the build-pose contacts, the loops."""

    flats, _sources, world = film.retained_solids(Path(project), "cat_model")
    verts = {k: np.asarray(f, float).reshape(-1, 3) for k, f in flats.items() if k not in world}
    verts = {k: v for k, v in verts.items() if len(v) >= 4}
    spec = mujoco.MjSpec()
    spec.option.gravity = [0, 0, 0]
    for k, v in verts.items():
        mesh = spec.add_mesh()
        mesh.name = k
        mesh.uservert = (v / 1000.0).flatten().tolist()
        body = spec.worldbody.add_body()
        body.name = k
        body.add_freejoint()
        geom = body.add_geom()
        geom.type = mujoco.mjtGeom.mjGEOM_MESH
        geom.meshname = k
    hull = spec.compile()
    hdata = mujoco.MjData(hull)
    qadr = {k: hull.jnt_qposadr[hull.body_jntadr[mujoco.mj_name2id(hull, mujoco.mjtObj.mjOBJ_BODY, k)]] for k in verts}
    names = [mujoco.mj_id2name(hull, mujoco.mjtObj.mjOBJ_BODY, hull.geom_bodyid[g]) for g in range(hull.ngeom)]

    model = mujoco.MjModel.from_xml_path(str(model_xml))
    mdata = mujoco.MjData(model)
    mujoco.mj_forward(model, mdata)
    build = {}
    for k in verts:
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, k)
        if b >= 0:
            w, x, y, z = mdata.xquat[b]
            build[k] = {"position_mm": (mdata.xpos[b] * 1000.0).tolist(), "rotation_xyzw": [x, y, z, w]}
    loops = []
    for e in range(model.neq):
        if model.eq_type[e] != mujoco.mjtEq.mjEQ_CONNECT or model.eq_objtype[e] != mujoco.mjtObj.mjOBJ_SITE:
            continue
        ends = [(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.site_bodyid[s]), model.site_pos[s] * 1000.0)
                for s in (model.eq_obj1id[e], model.eq_obj2id[e])]
        loops.append((mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_EQUALITY, e), ends))
    STATE.update(verts=verts, hull=hull, hdata=hdata, qadr=qadr, names=names, loops=loops)
    STATE["solids"] = {k: Solid(flats[k]) for k in verts}
    touching = set()
    for (a, b), d in contacts(build, missing_ok=True).items():
        if a in build and b in build and d <= TOUCH_MM:
            depth, gap = real_depth(build, a, b)
            if depth > 0.0 or gap <= TOUCH_MM:
                touching.add((a, b))
    # components on one MuJoCo body never move apart: a pair clear in the build pose stays clear
    body = {k: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, k) for k in verts}
    weld = {k: model.body_weldid[b] if b >= 0 else -1 - i for i, (k, b) in enumerate(body.items())}
    touching |= {(a, b) for a in verts for b in verts if a < b and weld[a] == weld[b]}
    STATE["touching"] = touching


def contacts(placements, missing_ok=False):
    hull, hdata = STATE["hull"], STATE["hdata"]
    for n, (k, a) in enumerate(STATE["qadr"].items()):
        p = placements.get(k)
        if p is None:
            if not missing_ok:
                raise KeyError(k)
            hdata.qpos[a:a + 7] = [0.0, 0.0, -1000.0 - 10.0 * n, 1.0, 0.0, 0.0, 0.0]  # parked far apart
            continue
        x, y, z, w = p["rotation_xyzw"]
        hdata.qpos[a:a + 3] = np.asarray(p["position_mm"]) / 1000.0
        hdata.qpos[a + 3:a + 7] = [w, x, y, z]
    mujoco.mj_forward(hull, hdata)
    out = {}
    for c in hdata.contact[:hdata.ncon]:
        key = tuple(sorted((STATE["names"][c.geom1], STATE["names"][c.geom2])))
        out[key] = min(out.get(key, 1.0), c.dist * 1000.0)
    return out


def lowz(placements, k):
    p = placements[k]
    return float((STATE["verts"][k] @ quat_mat(p["rotation_xyzw"]).T)[:, 2].min() + p["position_mm"][2])


def runs(flags):
    """[(start, end)] index pairs of consecutive True."""

    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def seed(path):
    trace = json.loads(Path(path).read_text())
    frames = [f for f in trace["frames"] if f["frame_kind"] == "solver_output" and float(f["nominal_time_s"]) >= ARGS.settle_s]
    dt = 1.0 / float(trace["parameters"]["frames_per_second"])
    low = {k: [] for s in "lr" for k in (t.format(s=s) for t in LOWER) if k in STATE["verts"]}
    foot = {leg: [] for leg in FEET}
    heel = {leg: [] for leg, _ in HIND}
    gaps = collections.defaultdict(list)
    pen = collections.Counter()
    depth = collections.defaultdict(float)
    at = {}
    for f in frames:
        P = f["component_placements"]
        for k in low:
            low[k].append(lowz(P, k))
        for leg, parts in FEET.items():
            foot[leg].append(min(lowz(P, k) for k in parts))
        for leg, s in HIND:
            heel[leg].append(lowz(P, f"c_heel_{s}"))
        for name, ends in STATE["loops"]:
            a, b = (np.asarray(P[body]["position_mm"]) + quat_mat(P[body]["rotation_xyzw"]) @ pos for body, pos in ends)
            gaps[name].append(float(np.linalg.norm(a - b)))
        for key, d in contacts(P).items():
            if key in STATE["touching"] or d > -ARGS.pen_mm:
                continue
            real, _gap = real_depth(P, *key, depth_floor=ARGS.pen_mm)
            if real <= ARGS.pen_mm:
                continue
            pen[key] += 1
            if -real < depth[key]:
                depth[key], at[key] = -real, float(f["nominal_time_s"])
    out = {"seed": Path(path).name.split("-")[1], "frames": len(frames), "legs": {}, "loops": {}}
    for leg, _ in HIND:
        stance = [z < ARGS.paw_mm for z in foot[leg]]
        down = [h < ARGS.heel_mm for h in heel[leg]]
        idx = [i for i, s in enumerate(stance) if s]
        offs = [b for _, b in runs(stance)]
        out["legs"][leg] = {
            "stance_frames": len(idx),
            "heel_share": sum(down[i] for i in idx) / len(idx) if idx else None,
            "heel_at_toeoff": sum(down[i] for i in offs) / len(offs) if offs else None,
            "heel_height_mm": statistics.median(heel[leg][i] for i in idx) if idx else None,
            "touchdowns": len(offs),
        }
    for name, g in gaps.items():
        out["loops"][name] = {"median": statistics.median(g), "max": max(g)}
    airborne = [all(foot[leg][i] >= ARGS.paw_mm for leg in FEET) and all(heel[leg][i] >= ARGS.paw_mm for leg, _ in HIND)
                for i in range(len(frames))]
    lh = [a for a, _ in runs([z < ARGS.paw_mm for z in foot["LH"]])]
    flights = [sum(airborne[a:b]) * dt for a, b in zip(lh, lh[1:])]
    out["flight"] = {"strides": len(flights), "share": sum(1 for x in flights if x > 0) / len(flights) if flights else None,
                     "median_s": statistics.median(flights) if flights else None}
    out["sink_mm"] = {k: min(v) for k, v in low.items()}
    out["pen"] = {f"{a} x {b}": {"frames": n, "depth_mm": depth[(a, b)], "at_s": at[(a, b)]} for (a, b), n in pen.items()}
    return out


def init(project, model_xml, args):
    global ARGS
    ARGS = args
    setup(project, model_xml)


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(v, spec="%.2f"):
    return "–" if v is None else spec % v


def report(evaldir, seeds):
    engine = {str(s["seed"]): s for s in json.loads((evaldir / "evaluation.json").read_text())["seeds"]}
    print(f"\n### {evaldir.name}\n")
    print("| seed | heel share LH / RH | engine heel_down_share LH / RH | heel at toe-off LH / RH |"
          " heel stance height mm LH / RH | flight strides | flight s | worst loop mm | pen > bar | deepest floor mm |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for s in seeds:
        L, R = s["legs"]["LH"], s["legs"]["RH"]
        heels = engine.get(s["seed"], {}).get("detail", {}).get("heels", {})
        eng = [heels.get(p, {}).get("heel_down_share") for p in ("c_paw_hl", "c_paw_hr")]
        worst = max(s["loops"].items(), key=lambda kv: kv[1]["max"])
        sink = min(s["sink_mm"].items(), key=lambda kv: kv[1])
        print(f"| {s['seed']} | {fmt(L['heel_share'])} / {fmt(R['heel_share'])} | {fmt(eng[0])} / {fmt(eng[1])} |"
              f" {fmt(L['heel_at_toeoff'])} / {fmt(R['heel_at_toeoff'])} |"
              f" {fmt(L['heel_height_mm'], '%.0f')} / {fmt(R['heel_height_mm'], '%.0f')} |"
              f" {fmt(s['flight']['share'])} of {s['flight']['strides']} | {fmt(s['flight']['median_s'], '%.3f')} |"
              f" {worst[1]['max']:.2f} ({worst[0]}) | {len(s['pen'])} | {sink[1]:+.1f} ({sink[0]}) |")
    print("\nmedian over seeds, left / right:")
    for key, spec in (("heel_share", "%.2f"), ("heel_at_toeoff", "%.2f"), ("heel_height_mm", "%.0f"), ("touchdowns", "%.0f")):
        print(f"  {key}: {fmt(med(s['legs']['LH'][key] for s in seeds), spec)} / {fmt(med(s['legs']['RH'][key] for s in seeds), spec)}")
    print(f"  flight stride share {fmt(med(s['flight']['share'] for s in seeds))}, flight s {fmt(med(s['flight']['median_s'] for s in seeds), '%.3f')}")
    print("\nrod loops, mm (median of seed medians / worst over seeds; O9 bar 2 mm):")
    for name in sorted(seeds[0]["loops"]):
        worst = max(s["loops"][name]["max"] for s in seeds)
        print(f"  {name}: {med(s['loops'][name]['median'] for s in seeds):.2f} / {worst:.2f}"
              f"{'  OVER' if worst > 2.0 else ''}")
    print("\ndeepest point under the floor, mm (worst over seeds):")
    for k in sorted(seeds[0]["sink_mm"]):
        print(f"  {k}: {min(s['sink_mm'][k] for s in seeds):+.1f}")
    pairs = collections.defaultdict(lambda: [0, 0.0, 0, ""])
    for s in seeds:
        for k, v in s["pen"].items():
            pairs[k][0] += v["frames"]
            if v["depth_mm"] < pairs[k][1]:
                pairs[k][1], pairs[k][3] = v["depth_mm"], f"seed {s['seed']} at {v['at_s']:.2f} s"
            pairs[k][2] += 1
    print(f"\nreal-mesh interpenetration deeper than {ARGS.pen_mm:g} mm, pairs not touching in the build pose"
          f" ({len(pairs)} pairs; frames / deepest mm / seeds / deepest at):")
    for k, (n, d, ns, where) in sorted(pairs.items(), key=lambda kv: kv[1][1]):
        print(f"  {k}: {n} / {d:.1f} / {ns} / {where}")


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("project")
    p.add_argument("model_xml")
    p.add_argument("evaldirs", nargs="+")
    p.add_argument("--paw-mm", type=float, default=8.0)
    p.add_argument("--heel-mm", type=float, default=8.0)
    p.add_argument("--pen-mm", type=float, default=5.0)
    p.add_argument("--settle-s", type=float, default=1.0)
    p.add_argument("--jobs", type=int, default=10)
    args = p.parse_args(argv)
    global ARGS
    ARGS = args
    with ProcessPoolExecutor(args.jobs, initializer=init, initargs=(args.project, args.model_xml, args)) as pool:
        for d in map(Path, args.evaldirs):
            report(d, list(pool.map(seed, sorted(d.glob("seed-*-trace.json")))))


if __name__ == "__main__":
    main(sys.argv[1:])
