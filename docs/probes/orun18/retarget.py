"""Retarget one stride of the AI4Animation dog capture to leo v05 as a gait clip (orun18 C2).

usage: pixi run python docs/probes/orun18/retarget.py MODEL_XML BVH FIRST END LABEL OUT_DIR [SAMPLES]

``MODEL_XML`` is leo v05's MJCF as a task bundle carries it (``cat_model-model.xml``),
``BVH`` one of the capture's takes (``~/mocap/ai4animation/``, CC BY-NC 4.0,
SOURCES.md), ``FIRST``/``END`` the stride's frames (``END`` exclusive, the left
hind's next touchdown), ``SAMPLES`` the phase grid the stride is read on (the
strides of one speed schedule share it; default, the capture's own frames). Writes ``OUT_DIR/LABEL.clip.json``, a ``cadex-gait-clip-v1``
dictionary of the fields ``CadexDynamics._tracking_records`` reads (and ``qpos``
for the resets), and ``OUT_DIR/LABEL.measure.json``. Neither is committed: the clip
is derived from the capture and stays beside it (D5); its sha256 is reported.

**The route.** The capture is a BVH skeleton (cm, y up, 60 fps): pelvis
(``Hips``), thorax (``Spine``), a scapula, three fore segments and a paw end, three
hind segments and a paw end. Leo's motion is set from it in four steps, every
length scaled by ``s`` (leo's girdle height at home over the dog's mean over the
stride, per girdle) and every time by ``sqrt(s)``, so the stride keeps the dog's
Froude number (Alexander & Jayes 1983):

1. **Spine.** The thorax's pitch (its frame's axis) and heading (its shoulder
   joints' lateral axis) against the pelvis's (hip joints), less their
   stride means, go to ``j_spine`` (its cable follower ``j_spine2`` follows, as
   the constraint will) and ``j_spine_yaw``, by each joint's measured gain on leo.
2. **Trunk.** Leo's base (the chest) is pitched and raised so its shoulder
   pivots and hip pivots stand at leo's home heights plus ``s`` times the dog's
   shoulder and hip height about their stride means; it moves forward with the
   girdles' midpoint, scaled. No roll, no yaw: the line is straight (D9).
3. **Feet.** Each paw's target is the dog's paw, scaled about the trunk's
   scale (the line's start), moved along the line by one offset per foot (the
   mean of leo's pivot less the dog's, scaled: leo's girdles sit elsewhere on its
   trunk) and sideways to leo's own stance width; its height over its stance
   level is scaled by its girdle's ``s``. Where the dog's paw is down (within
   ``CONTACT_M`` of its stance level and moving at under ``CONTACT_SPEED`` of the
   trunk's speed, gaps of up to ``CONTACT_GAP_S`` closed) the target is held still at its mean over
   that stance and on leo's ground: the raw target's travel there (the capture's
   own paw slip, scaled) is the retarget's **foot slip**, reported before it is
   removed.
4. **Legs.** Each leg's joints and its push-rod's passive pins are solved to its
   target by the engine's own rows (``CadexGait._leg_rows``: the foot, then each
   loop closure at ``CLOSURE_WEIGHT``) with its active-set clamp at every joint
   stop and its pull toward home in the null space: **no joint leaves its
   range**, and what a stop costs is a foot miss, reported per leg.

Measured and written: raw foot slip per stance, the solved foot's slip in
stance, foot miss, share of samples each joint sits at a stop, loop closure
error, the seam between the stride's last and first sample, and the clip's
speed, period, duty and footfall phases. Nothing here is rewarded.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402

import CadexGait as G  # noqa: E402

LEGS = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}
DOG_PAW = {"LF": "LeftHand_end", "RF": "RightHand_end", "LH": "LeftFoot_end", "RH": "RightFoot_end"}
DOG_PIVOT = {"LF": "LeftArm", "RF": "RightArm", "LH": "LeftUpLeg", "RH": "RightUpLeg"}
LEO_PIVOT = {"LF": "j_shoulder_l", "RF": "j_shoulder_r", "LH": "j_hip_l", "RH": "j_hip_r"}
GIRDLE = {"LF": "fore", "RF": "fore", "LH": "hind", "RH": "hind"}
CONTACT_M = 0.02          # a paw within 20 mm of its stance level,
CONTACT_SPEED = 0.4       # and moving at under 0.4 of the trunk speed, is down
CONTACT_GAP_S = 0.05      # capture seconds (three 60 fps frames) a stance may lift for
SPINE, SPINE_YAW = "j_spine", "j_spine_yaw"
SOURCES = [
    "Zhang H., Starke S., Komura T., Saito J. 2018. Mode-Adaptive Neural Networks for Quadruped "
    "Motion Control. ACM Trans. Graph. 37(4) (SIGGRAPH 2018); AI4Animation dog motion capture, "
    "CC BY-NC 4.0 (github.com/sebastianstarke/AI4Animation).",
    "Alexander R.McN., Jayes A.S. 1983. A dynamic similarity hypothesis for the gaits of "
    "quadrupedal mammals. J. Zool. 201:135-152 (equal Froude number: lengths by s, times by sqrt s).",
]


# ---------------------------------------------------------------- the capture

def _rot(axis: str, deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return {"X": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "Y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "Z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def read_bvh(path: Path) -> tuple[list[dict], np.ndarray, float]:
    """The skeleton (name, parent, offset, channels), the motion rows and the frame time."""

    lines = path.read_text().split("\n")
    joints: list[dict] = []
    stack: list[int] = []
    pending = -1
    i = 0
    while not lines[i].startswith("MOTION"):
        t = lines[i].split()
        if t and t[0] in ("ROOT", "JOINT", "End"):
            name = t[1] if t[0] != "End" else joints[stack[-1]]["name"] + "_end"
            joints.append({"name": name, "parent": stack[-1] if stack else -1, "channels": []})
            pending = len(joints) - 1
        elif t and t[0] == "{":
            stack.append(pending)
        elif t and t[0] == "}":
            stack.pop()
        elif t and t[0] == "OFFSET":
            joints[pending]["offset"] = np.array([float(v) for v in t[1:4]])
        elif t and t[0] == "CHANNELS":
            joints[pending]["channels"] = t[2:]
        i += 1
    frames = int(lines[i + 1].split()[1])
    dt = float(lines[i + 2].split()[2])
    motion = np.array([[float(v) for v in line.split()] for line in lines[i + 3:i + 3 + frames]])
    return joints, motion, dt


def forward_kinematics(joints: list[dict], motion: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """World positions (cm) and rotations of every joint, every frame; channels in file order."""

    n = len(motion)
    pos = np.zeros((n, len(joints), 3))
    rot = np.zeros((n, len(joints), 3, 3))
    for f in range(n):
        c = 0
        for j, joint in enumerate(joints):
            p, r = joint["offset"].copy(), np.eye(3)
            for ch in joint["channels"]:
                v = motion[f, c]
                c += 1
                if ch.endswith("position"):
                    p["XYZ".index(ch[0])] = v
                else:
                    r = r @ _rot(ch[0], v)
            parent = joint["parent"]
            if parent < 0:
                pos[f, j], rot[f, j] = p, r
            else:
                pos[f, j] = pos[f, parent] + rot[f, parent] @ p
                rot[f, j] = rot[f, parent] @ r
    return pos, rot


def dog_stride(path: Path, first: int, end: int, samples: int | None = None) -> dict:
    """The stride in a heading frame (m; x along the run, y left, z up, floor at 0).

    With ``samples`` the stride is read at that many even steps of its phase,
    each reading between its two frames linearly, so the strides of a speed
    schedule share one phase grid (ADR-773); without it, at its own frames.
    """

    joints, motion, dt = read_bvh(path)
    pos, rot = forward_kinematics(joints, motion)
    pos = pos / 100.0
    ix = {j["name"]: n for n, j in enumerate(joints)}
    floor = float(np.percentile(np.concatenate([pos[:, ix[n], 1] for n in DOG_PAW.values()]), 2))
    hips = pos[first:end + 1, ix["Hips"]]
    fwd = hips[-1, [0, 2]] - hips[0, [0, 2]]
    fwd = fwd / np.linalg.norm(fwd)
    # BVH (x, y up, z) -> heading frame (along, left, up): left = up x forward
    ex = np.array([fwd[0], 0.0, fwd[1]])
    ez = np.array([0.0, 1.0, 0.0])
    ey = np.cross(ez, ex)
    basis = np.stack([ex, ey, ez])
    origin = np.array([hips[0, 0], floor, hips[0, 2]])

    def at(name: str, f: int) -> np.ndarray:
        return basis @ (pos[f, ix[name]] - origin)

    def axis(name: str, local: np.ndarray, f: int) -> np.ndarray:
        return basis @ (rot[f, ix[name]] @ local)

    frames = list(range(first, end + 1))
    out = {"dt": dt, "frames": [first, end], "frame_count": len(motion),
           "paw": {k: np.array([at(n, f) for f in frames]) for k, n in DOG_PAW.items()},
           "pivot": {k: np.array([at(n, f) for f in frames]) for k, n in DOG_PIVOT.items()},
           "next_pivot_mid": 0.25 * sum(at(n, end) for n in DOG_PIVOT.values()),
           # the thorax's forward axis is Spine's +x (Spine1 sits there); the pelvis's is
           # Hips' -x (its tail and thighs sit behind it, at +x)
           "thorax": np.array([axis("Spine", np.array([1.0, 0, 0]), f) for f in frames]),
           "pelvis": np.array([axis("Hips", np.array([-1.0, 0, 0]), f) for f in frames]),
           # headings from the girdles' lateral axes (shoulder joints on the thorax, hip
           # joints on the pelvis): Spine's +x heading swings twice as far, with its roll
           "thorax_lateral": np.array([at("LeftShoulder", f) - at("RightShoulder", f) for f in frames]),
           "pelvis_lateral": np.array([at("LeftUpLeg", f) - at("RightUpLeg", f) for f in frames]),
           "skeleton": {"parents": [j["parent"] for j in joints], "names": [j["name"] for j in joints],
                        "points": np.array([[basis @ (pos[f, j] - origin) for j in range(len(joints))]
                                            for f in frames])}}
    count = end - first
    steps = int(samples) if samples else count
    at_t = np.arange(steps) * (count / steps)
    low = np.floor(at_t).astype(int)
    w = at_t - low

    def read(a: np.ndarray) -> np.ndarray:
        shape = (-1,) + (1,) * (a.ndim - 1)
        return a[low] + w.reshape(shape) * (a[low + 1] - a[low])

    for key in ("paw", "pivot"):
        out[key] = {k: read(v) for k, v in out[key].items()}
    for key in ("thorax", "pelvis", "thorax_lateral", "pelvis_lateral"):
        out[key] = read(out[key])
    out["skeleton"]["points"] = read(out["skeleton"]["points"])
    out["dt"] = dt * count / steps
    return out


def _pitch(v: np.ndarray) -> float:
    """Nose-up pitch of a forward axis (rad)."""

    return math.atan2(float(v[2]), math.hypot(float(v[0]), float(v[1])))


def _heading(v: np.ndarray) -> float:
    """Heading of a forward axis, left positive (rad)."""

    return math.atan2(float(v[1]), float(v[0]))


def _runs(flags: list[int]) -> list[list[int]]:
    """The cyclic runs of set samples, each as its sample indices in order."""

    n = len(flags)
    if all(flags):
        return [list(range(n))]
    start = next(k for k in range(n) if not flags[k])
    runs, cur = [], []
    for step in range(1, n + 1):
        k = (start + step) % n
        if flags[k]:
            cur.append(k)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


# ---------------------------------------------------------------- leo

def retarget(model_path: Path, bvh: Path, first: int, end: int, label: str,
             samples: int | None = None, stride: dict | None = None) -> tuple[dict, dict, dict]:
    """Retarget the BVH's stride, or ``stride`` when given: a ``dog_stride``-shaped
    dictionary from another capture, which also carries its ``source`` (``name``,
    ``sha256``, ``label``, ``sources``) and its ``contact`` rule (metres over the
    stance level, share of the trunk's speed, gap seconds)."""

    dog = stride if stride is not None else dog_stride(bvh, first, end, samples)
    source = dog.get("source") or {"name": bvh.name, "sha256": hashlib.sha256(bvh.read_bytes()).hexdigest(),
                                   "label": f"AI4Animation dog {bvh.name} frames {first}-{end}",
                                   "sources": SOURCES}
    contact_m, contact_speed, contact_gap_s = dog.get("contact") or (CONTACT_M, CONTACT_SPEED, CONTACT_GAP_S)
    n = len(dog["thorax"])
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mj = mujoco
    home = np.asarray(model.key_qpos[0], dtype=float).copy()
    structure = G.leg_chains(model, LEGS, mujoco=mj)
    chains, body_joints = structure["chains"], structure["body_joints"]
    closures = G.leg_closures(model, chains, body_joints, mujoco=mj)
    jid = {name: mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, name) for name in
           [SPINE, SPINE_YAW, *LEO_PIVOT.values()]}
    chest = int(model.jnt_bodyid[0])
    pelvis = int(model.jnt_bodyid[jid[SPINE_YAW]])
    foot_body = {f: mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, b) for f, b in LEGS.items()}

    def fk(q: np.ndarray) -> None:
        data.qpos[:] = q
        mj.mj_kinematics(model, data)
        mj.mj_comPos(model, data)

    fk(home)
    point_local = {f: G._foot_point(model, data, foot_body[f]) for f in LEGS}

    def foot_world(f: str) -> np.ndarray:
        b = foot_body[f]
        return data.xpos[b] + data.xmat[b].reshape(3, 3) @ point_local[f]

    def pivot_world(f: str) -> np.ndarray:
        return data.xanchor[jid[LEO_PIVOT[f]]].copy()

    home_foot = {f: foot_world(f) for f in LEGS}
    home_pivot = {f: pivot_world(f) for f in LEGS}
    girdle_z_home = {g: float(np.mean([home_pivot[f][2] for f in LEGS if GIRDLE[f] == g])) for g in ("fore", "hind")}
    # the scale per girdle: leo's pivot height at home over the dog's mean over the stride
    dog_girdle_z = {g: np.mean([dog["pivot"][f][:, 2] for f in LEGS if GIRDLE[f] == g], axis=0)
                    for g in ("fore", "hind")}
    scale = {g: girdle_z_home[g] / float(np.mean(dog_girdle_z[g])) for g in ("fore", "hind")}
    s_body = 0.5 * (scale["fore"] + scale["hind"])
    time_scale = math.sqrt(s_body)
    dt = dog["dt"] * time_scale
    period = n * dt

    # 1. the spine: the thorax against the pelvis, about the stride's mean, by leo's gains
    bend_p = np.array([_pitch(dog["thorax"][k]) - _pitch(dog["pelvis"][k]) for k in range(n)])
    bend_y = np.array([math.atan2(-dog["thorax_lateral"][k][0], dog["thorax_lateral"][k][1])
                       - math.atan2(-dog["pelvis_lateral"][k][0], dog["pelvis_lateral"][k][1]) for k in range(n)])
    bend_y = (bend_y + math.pi) % (2 * math.pi) - math.pi
    bend_p -= bend_p.mean()
    bend_y -= bend_y.mean()

    def leo_bend(q: np.ndarray) -> tuple[float, float]:
        fk(q)
        cx, px = data.xmat[chest].reshape(3, 3)[:, 0], data.xmat[pelvis].reshape(3, 3)[:, 0]
        return _pitch(cx) - _pitch(px), _heading(cx) - _heading(px)

    def with_spine(q: np.ndarray, sp: float, yaw: float) -> np.ndarray:
        q = q.copy()
        q[model.jnt_qposadr[jid[SPINE]]] = home[model.jnt_qposadr[jid[SPINE]]] + sp
        q[model.jnt_qposadr[jid[SPINE_YAW]]] = home[model.jnt_qposadr[jid[SPINE_YAW]]] + yaw
        G._follow_spine(model, mj, q, jid[SPINE], body_joints)
        return q

    b0 = leo_bend(with_spine(home, 0.0, 0.0))
    gain_p = (leo_bend(with_spine(home, 0.05, 0.0))[0] - b0[0]) / 0.05
    gain_y = (leo_bend(with_spine(home, 0.0, 0.05))[1] - b0[1]) / 0.05
    rng = {name: tuple(float(v) for v in model.jnt_range[jid[name]]) for name in (SPINE, SPINE_YAW)}
    q_sp = np.clip(bend_p / gain_p, *rng[SPINE])
    q_yaw = np.clip(bend_y / gain_y, *rng[SPINE_YAW])

    # 2. the trunk: pitch and height so each girdle's pivots stand where the dog's do, scaled
    want_z = {g: girdle_z_home[g] + scale[g] * (dog_girdle_z[g] - dog_girdle_z[g].mean()) for g in ("fore", "hind")}
    dog_mid_x = np.mean([dog["pivot"][f][:, 0] for f in LEGS], axis=0)
    dog_stride_m = float(dog["next_pivot_mid"][0] - dog_mid_x[0])
    home_mid_x = float(np.mean([home_pivot[f][0] for f in LEGS]))

    def trunk(k: int) -> np.ndarray:
        q = with_spine(home, float(q_sp[k]), float(q_yaw[k]))
        z, pitch = 0.0, 0.0
        for _ in range(20):
            def resid(zz: float, pp: float) -> np.ndarray:
                qq = q.copy()
                qq[2] = home[2] + zz
                qq[3:7] = G._pitch_quaternion(home[3:7], pp)
                fk(qq)
                got = {g: np.mean([pivot_world(f)[2] for f in LEGS if GIRDLE[f] == g]) for g in ("fore", "hind")}
                return np.array([got["fore"] - want_z["fore"][k], got["hind"] - want_z["hind"][k]])
            r = resid(z, pitch)
            if np.max(np.abs(r)) < 1e-7:
                break
            e = 1e-5
            J = np.stack([(resid(z + e, pitch) - r) / e, (resid(z, pitch + e) - r) / e], axis=1)
            dz, dp = np.linalg.solve(J, -r)
            z, pitch = z + dz, pitch + dp
        q[2] = home[2] + z
        q[3:7] = G._pitch_quaternion(home[3:7], pitch)
        fk(q)
        mid = float(np.mean([pivot_world(f)[0] for f in LEGS]))
        q[0] = home[0] + home_mid_x + s_body * (dog_mid_x[k] - dog_mid_x[0]) - mid
        return q

    trunks = [trunk(k) for k in range(n)]
    dog_speed = dog_stride_m / (n * dog["dt"])
    stride_m = s_body * dog_stride_m
    speed = stride_m / period

    # 3. the feet: the dog's paw, scaled, where leo's girdle stands; still and grounded
    # where the dog's paw is down
    contact, raw, targets, slip_raw = {}, {}, {}, {}
    leo_pivots = {f: [] for f in LEGS}
    for k in range(n):
        fk(trunks[k])
        for f in LEGS:
            leo_pivots[f].append(pivot_world(f))
    for f in LEGS:
        paw, piv = dog["paw"][f], dog["pivot"][f]
        level = float(np.percentile(paw[:, 2], 5))
        # the paw's speed along the ground, round the stride (its ends a stride apart)
        ahead = np.vstack([paw[1:], paw[:1] + [dog_stride_m, 0, 0]])
        behind = np.vstack([paw[-1:] - [dog_stride_m, 0, 0], paw[:-1]])
        crawl = np.linalg.norm((ahead - behind)[:, :2], axis=1) / (2.0 * dog["dt"])
        down = [int(paw[k, 2] - level < contact_m and crawl[k] < contact_speed * dog_speed)
                for k in range(n)]
        # a gap of up to contact_gap_s inside a stance is the paw rolling, not a step
        for run in _runs([1 - v for v in down]):
            if len(run) * dog["dt"] <= contact_gap_s + 1e-9 and len(run) < n - sum(down):
                for k in run:
                    down[k] = 1
        contact[f] = down
        # one offset along the line per foot (leo's girdle sits elsewhere on its trunk
        # than the dog's), so a paw still on the ground stays still on leo
        along = float(np.mean([leo_pivots[f][k][0] - s_body * piv[k, 0] for k in range(n)]))
        rows = [[s_body * paw[k, 0] + along,
                 home_foot[f][1] + s_body * (paw[k, 1] - paw[:, 1].mean()),
                 home_foot[f][2] + scale[GIRDLE[f]] * (paw[k, 2] - level)] for k in range(n)]
        raw[f] = np.array(rows)
        held = raw[f].copy()
        slips = []
        for run in _runs(contact[f]):
            # a stance across the stride's seam: its wrapped samples are one stride on
            pts = np.array([raw[f][k] + ([stride_m, 0, 0] if run[0] > k else 0.0) for k in run])
            slips.append(1000.0 * float(np.max(np.linalg.norm(pts[:, :2] - pts[0, :2], axis=1))))
            mean_xy = pts[:, :2].mean(axis=0)
            for k in run:
                held[k, :2] = mean_xy - ([stride_m, 0] if run[0] > k else 0.0)
                held[k, 2] = home_foot[f][2]
        targets[f], slip_raw[f] = held, slips

    # 4. the legs: the engine's rows, clamp and null-space pull
    limits = {}
    for f, joints in chains.items():
        for j in list(joints) + closures[f]["passive"]:
            lo, hi = model.jnt_range[j]
            limits[j] = (float(lo), float(hi)) if model.jnt_limited[j] else (-math.inf, math.inf)
    jacp = np.zeros((3, model.nv))
    damping, posture = 1e-6, 0.1
    qpos = np.zeros((n, model.nq))
    q_prev = home.copy()
    for sweep in range(2):  # the second sweep starts the stride from its own end
        for k in range(n):
            q = trunks[k].copy()
            for f in LEGS:
                for j in list(chains[f]) + closures[f]["passive"]:
                    a = int(model.jnt_qposadr[j])
                    q[a] = q_prev[a]
            for _ in range(G.IK_ITERATIONS):
                fk(q)
                worst = 0.0
                for f in LEGS:
                    errs, jacs = G._leg_rows(model, data, mj, f, targets[f][k], foot_world(f), foot_body[f],
                                             closures[f], jacp, None, 0.0, None)
                    err = np.concatenate(errs)
                    worst = max(worst, float(np.linalg.norm(err)))
                    if np.linalg.norm(err) < 1e-6:
                        continue
                    n_loops = len(closures[f]["connects"]) + len(closures[f]["couplings"])
                    joints = list(chains[f]) + closures[f]["passive"]
                    cols = [int(model.jnt_dofadr[j]) for j in joints]
                    adrs = [int(model.jnt_qposadr[j]) for j in joints]
                    weight = np.concatenate([np.full(len(e), G.CLOSURE_WEIGHT if m >= len(errs) - n_loops else 1.0)
                                             for m, e in enumerate(errs)])
                    err = err * weight
                    full = np.vstack(jacs) * weight[:, None]
                    free = list(range(len(joints)))
                    for _pass in range(len(joints)):
                        J = full[:, [cols[i] for i in free]]
                        pinv = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(len(err)))
                        pull = posture * (home[[adrs[i] for i in free]] - q[[adrs[i] for i in free]])
                        dq = pinv @ err + (np.eye(len(free)) - pinv @ J) @ pull
                        pinned = [i for m, i in enumerate(free)
                                  if (q[adrs[i]] <= limits[joints[i]][0] + 1e-9 and dq[m] < 0.0)
                                  or (q[adrs[i]] >= limits[joints[i]][1] - 1e-9 and dq[m] > 0.0)]
                        if not pinned or len(free) - len(pinned) < 1:
                            break
                        free = [i for i in free if i not in pinned]
                    biggest = float(np.max(np.abs(dq))) if len(dq) else 0.0
                    if biggest > G.MAX_STEP_RAD:
                        dq = dq * (G.MAX_STEP_RAD / biggest)
                    for m, i in enumerate(free):
                        lo, hi = limits[joints[i]]
                        q[adrs[i]] = min(hi, max(lo, q[adrs[i]] + dq[m]))
                if worst < 1e-5:
                    break
            qpos[k] = q
            q_prev = q

    # measures
    miss, loop, solved = {f: [] for f in LEGS}, {f: 0.0 for f in LEGS}, {f: [] for f in LEGS}
    pitch_deg: list[float] = []
    for k in range(n):
        fk(qpos[k])
        for f in LEGS:
            errs, _ = G._leg_rows(model, data, mj, f, targets[f][k], foot_world(f), foot_body[f],
                                  closures[f], None, None, 0.0, None)
            miss[f].append(1000.0 * float(np.linalg.norm(errs[0])))
            loop[f] = max(loop[f], max((1000.0 * float(np.max(np.abs(e))) for e in errs[1:]), default=0.0))
            solved[f].append(foot_world(f).copy())
        pitch_deg.append(math.degrees(_pitch(data.xmat[chest].reshape(3, 3)[:, 0])))
    solved = {f: np.array(v) for f, v in solved.items()}
    slip_solved = {}
    for f in LEGS:
        out = []
        for run in _runs(contact[f]):
            pts = np.array([solved[f][k] + ([stride_m, 0, 0] if run[0] > k else 0.0) for k in run])
            out.append(1000.0 * float(np.max(np.linalg.norm(pts[:, :2] - pts[0, :2], axis=1))))
        slip_solved[f] = out
    joint_ids = sorted({j for js in chains.values() for j in js} | set(body_joints))
    at_stop = {}
    for j in joint_ids:
        if not model.jnt_limited[j]:
            continue
        lo, hi = model.jnt_range[j]
        v = qpos[:, model.jnt_qposadr[j]]
        share = float(np.mean((v <= lo + 1e-6) | (v >= hi - 1e-6)))
        if share:
            at_stop[model.joint(j).name] = round(share, 3)
    hinge = [int(model.jnt_qposadr[j]) for j in joint_ids]
    steps = np.abs(np.diff(qpos[:, hinge], axis=0))
    seam = np.abs(qpos[0, hinge] - qpos[-1, hinge])
    touchdown = {f: next((k / n for k in range(n) if contact[f][k] and not contact[f][k - 1]), None) for f in LEGS}
    duty = {f: float(np.mean(contact[f])) for f in LEGS}
    flight = float(np.mean([not any(contact[f][k] for f in LEGS) for k in range(n)]))
    hip_height = float(np.mean([home_pivot[f][2] - home_foot[f][2] for f in LEGS if GIRDLE[f] == "hind"]))
    froude = speed ** 2 / (G.GRAVITY * hip_height)
    dog_hip = float(np.mean(dog_girdle_z["hind"]))

    clip = {
        "schema": G.SCHEMA,
        "gait": "capture",
        "label": f"{label}: {source['label']}, retargeted to leo v05",
        "parameters": {
            "speed_m_s": speed, "period_s": period, "stride_length_m": stride_m,
            "stride_frequency_hz": 1.0 / period, "hip_height_m": hip_height, "froude": froude,
            "duty_factor": float(np.mean(list(duty.values()))), "phase_offsets": touchdown,
            "spine_joint": SPINE, "length_scale": scale, "time_scale": time_scale,
        },
        "sources": source["sources"],
        "sample_dt_s": dt,
        "samples": n,
        "legs": {f: {"foot_body": LEGS[f], "joints": [model.joint(j).name for j in chains[f]]} for f in LEGS},
        "body_joints": [model.joint(j).name for j in body_joints],
        "joints": [model.joint(j).name for j in joint_ids],
        "joint_angles_rad": [[float(qpos[k][model.jnt_qposadr[j]]) for j in joint_ids] for k in range(n)],
        "joint_limits_rad": [[float(model.jnt_range[j][0]), float(model.jnt_range[j][1])]
                             if model.jnt_limited[j] else None for j in joint_ids],
        "qpos": qpos.tolist(),
        "foot_positions_m": {f: solved[f].tolist() for f in LEGS},
        "contact": contact,
        "body": {"x_m": [float(q[0]) for q in qpos], "z_m": [float(q[2]) for q in qpos],
                 "pitch_deg": pitch_deg},
        "ik": {"tolerance_m": G.TOLERANCE_M, "max_miss_m": {f: max(miss[f]) / 1000.0 for f in LEGS}},
        "start": "random",
    }
    measure = {
        "label": label, "bvh": source["name"], "bvh_sha256": source["sha256"],
        "frames": list(dog["frames"]), "dog_sample_s": dog["dt"], "samples": n,
        "dog": {"speed_m_s": dog_speed, "stride_m": dog_stride_m, "period_s": n * dog["dt"],
                "hip_pivot_height_m": dog_hip,
                "shoulder_pivot_height_m": float(np.mean(dog_girdle_z["fore"])),
                "froude": dog_speed ** 2 / (G.GRAVITY * dog_hip)},
        "leo": {"speed_m_s": speed, "stride_m": stride_m, "period_s": period, "froude": froude,
                "hip_height_m": hip_height},
        "length_scale": scale, "time_scale": time_scale,
        "duty": duty, "touchdown_phase": touchdown, "flight_share": flight,
        "spine": {"gain_pitch": gain_p, "gain_yaw": gain_y,
                  "dog_bend_pitch_deg_range": math.degrees(float(np.ptp(bend_p))),
                  "dog_bend_yaw_deg_range": math.degrees(float(np.ptp(bend_y))),
                  "j_spine_deg": [math.degrees(float(q_sp.min())), math.degrees(float(q_sp.max()))],
                  "j_spine_yaw_deg": [math.degrees(float(q_yaw.min())), math.degrees(float(q_yaw.max()))],
                  "clipped_share": float(np.mean((np.abs(bend_p / gain_p - q_sp) > 1e-9)
                                                 | (np.abs(bend_y / gain_y - q_yaw) > 1e-9)))},
        "foot_slip_raw_mm": {f: {"per_stance": [round(v, 1) for v in slip_raw[f]],
                                 "max": round(max(slip_raw[f], default=0.0), 1)} for f in LEGS},
        "foot_slip_solved_mm": {f: round(max(slip_solved[f], default=0.0), 2) for f in LEGS},
        "foot_miss_mm": {f: {"max": round(max(miss[f]), 2), "median": round(float(np.median(miss[f])), 2),
                             "over_5mm_share": round(float(np.mean(np.array(miss[f]) > 5.0)), 3),
                             "per_sample": [round(v, 1) for v in miss[f]]} for f in LEGS},
        "loop_error_mm": {f: round(v, 4) for f, v in loop.items()},
        "joints_at_stop_share": at_stop,
        "limit_violations": int(sum(
            int(np.sum((qpos[:, model.jnt_qposadr[j]] < model.jnt_range[j][0] - 1e-9)
                       | (qpos[:, model.jnt_qposadr[j]] > model.jnt_range[j][1] + 1e-9)))
            for j in limits if model.jnt_limited[j])),
        "seam_deg": {"max": math.degrees(float(seam.max())),
                     "largest_step_deg": math.degrees(float(steps.max())),
                     "joint": model.joint(joint_ids[int(np.argmax(seam))]).name},
    }
    return clip, measure, dog


def main(argv: list[str]) -> None:
    model_path, bvh, first, end, label, out_dir = argv[:6]
    samples = int(argv[6]) if len(argv) > 6 else None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    clip, measure, _dog = retarget(Path(model_path), Path(bvh), int(first), int(end), label, samples)
    text = json.dumps(clip)
    (out / f"{label}.clip.json").write_text(text)
    measure["clip_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (out / f"{label}.measure.json").write_text(json.dumps(measure, indent=1))
    print(json.dumps(measure, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
