"""orun12 Q1 / O3: a policy's mirror image, left for right, as a new .cxpolicy.

    pixi run python docs/probes/orun12/mirror_policy.py MODEL.xml IN.cxpolicy OUT.cxpolicy

The mirrored policy is pi'(o) = M_a pi(M_o o): it reads the world through
the sagittal plane (y -> -y) and acts mirrored. On a model that mirrors
(``mirror.py``) its gait is the original's mirror image, so judging both on
the same seeds says where a left/right difference lives:

- it **swaps sides** under the mirror: the policy learned a handed gait;
- it **stays on the same side**: the simulation or the evaluation is handed.

The maps are signed permutations, folded into the network so the engine
runs the result unchanged:

- a joint's angle, velocity and action go to its partner (``_l``/``_r``) or
  stay (the spine and tail), with the sign its world axis gives: an axis a
  mirrors as a pseudo-vector to (-ax, ay, -az), and the sign is that of its
  dot product with the partner's axis, read in the model's keyframe; every
  sign is checked against the action ranges (the partner's range is the
  same, or its negation);
- the IMU quaternion goes to (w, -x, y, -z), the gyro to (-x, y, -z);
- a height-scan point goes to the point at (x, -y); the clip phase and a
  forward speed command (``cmd``, orun17) stay.

The first layer and the normaliser absorb M_o (mean_j' = s mean_i), the last
layer M_a (a tanh output negates when the sign is -1, which the range check
makes exact). The witness is recomputed with the engine's own forward pass
on the new weights. numpy, mujoco and the engine's CadexDynamics.
"""

import math
import re
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexDynamics as D  # noqa: E402

SIDE = (("_l", "_r"), ("_r", "_l"))


def partner(name):
    for a, b in SIDE:
        if name.endswith(a):
            return name[: -len(a)] + b
    return name


def joint_signs(model_path):
    """Each joint's mirror sign, by name: +1 or -1 against its partner (or itself)."""
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_forward(model, data)
    names = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i): i for i in range(model.njnt)}
    signs = {}
    for name, i in names.items():
        if not name:
            continue
        j = names.get(partner(name))
        if j is None:
            continue
        a = data.xaxis[i] * np.array([-1.0, 1.0, -1.0])
        dot = float(np.dot(a, data.xaxis[j]))
        if abs(dot) < 0.99:
            raise SystemExit(f"{name}: mirrored axis is {math.degrees(math.acos(min(1, abs(dot)))):.1f} deg off its partner's")
        signs[name] = 1.0 if dot > 0 else -1.0
    return signs


def channel_map(channels, signs, scan_offsets):
    """For each channel i, (p(i), s_i): the mirrored observation is s_i * o[p(i)]."""
    index = {c: k for k, c in enumerate(channels)}
    out = []
    for c in channels:
        m = re.fullmatch(r"(d?q)_(.+)", c)
        if m:
            joint = "j_" + m.group(2)
            out.append((index[f"{m.group(1)}_{partner(m.group(2))}"], signs[joint]))
        elif c in ("imu_qx", "imu_qz", "gyro_x", "gyro_z"):
            out.append((index[c], -1.0))
        elif c in ("imu_qw", "imu_qy", "gyro_y", "ref_sin", "ref_cos", "cmd"):
            out.append((index[c], 1.0))
        elif c in scan_offsets:
            x, y = scan_offsets[c]
            other = [k for k, (u, v) in scan_offsets.items() if u == x and v == -y]
            out.append((index[other[0]], 1.0))
        else:
            raise SystemExit(f"no mirror rule for observation channel {c!r}")
    return out


def main(argv):
    model_path, src, dst = argv[1:4]
    policy = D.decode_policy(Path(src).read_bytes())
    header, weights = policy["header"], np.asarray(policy["weights"], dtype=np.float64)
    signs = joint_signs(model_path)

    scan_offsets = {}
    if "scan_0" in header["observations"]:
        bundle = next(p for p in (Path(src).parent / n for n in ("gallop-task.json", "gallop_sg-task.json")) if p.exists())
        task = __import__("json").loads(bundle.read_text())
        for scan in task.get("scans") or ():
            for c, (x, y) in zip(scan["channels"], scan["offsets_mm"]):
                scan_offsets[c] = (x, y)
    obs = channel_map(header["observations"], signs, scan_offsets)

    actions = header["actions"]
    by_joint = {a["joint"]: k for k, a in enumerate(actions)}
    act = []
    for a in actions:
        p = by_joint[partner(a["joint"])]
        s = signs[a["joint"]]
        lo, hi = actions[p]["low"], actions[p]["high"]
        want = (lo, hi) if s > 0 else (-hi, -lo)
        if not np.allclose(want, (a["low"], a["high"])):
            raise SystemExit(f"{a['joint']}: range {a['low'], a['high']} is not sign {s:+.0f} of {actions[p]['joint']}'s {lo, hi}")
        act.append((p, s))

    shapes = [tuple(x) for x in header["network"]["layers"]]
    layers, cursor = [], 0
    for n_in, n_out in shapes:
        w = weights[cursor : cursor + n_in * n_out].reshape(n_in, n_out)
        cursor += n_in * n_out
        b = weights[cursor : cursor + n_out]
        cursor += n_out
        layers.append([w.copy(), b.copy()])

    # input: n_i = s_i * n'_{p(i)}, n'_j = (o_j - mean'_j) / std'_j
    mean, std = np.asarray(header["normaliser"]["mean"]), np.asarray(header["normaliser"]["std"])
    w0 = layers[0][0]
    w0n, mean_n, std_n = np.zeros_like(w0), np.zeros_like(mean), np.zeros_like(std)
    for i, (p, s) in enumerate(obs):
        w0n[p] = s * w0[i]
        mean_n[p] = s * mean[i]
        std_n[p] = std[i]
    layers[0][0] = w0n
    # output: z'_i = s_i * z_{p(i)}
    w_last, b_last = layers[-1]
    layers[-1] = [np.stack([s * w_last[:, p] for p, s in act], axis=1), np.array([s * b_last[p] for p, s in act])]

    log_std = header["exploration"]["log_std"]
    header = dict(header)
    header["normaliser"] = dict(header["normaliser"], mean=mean_n.tolist(), std=std_n.tolist())
    header["exploration"] = dict(header["exploration"], log_std=[log_std[p] for p, _ in act])
    header["label"] = "mirror of " + str(header.get("label") or "")
    flat = np.concatenate([np.concatenate([w.reshape(-1), b]) for w, b in layers]).astype(np.float32).tolist()
    witness = header["evaluation"]["observations"]
    header["evaluation"] = dict(header["evaluation"], actions=[D.policy_forward(header, flat, o) for o in witness])

    # check: pi'(o) == M_a pi(M_o o) on the witness, through the engine's forward pass
    worst = 0.0
    for o in witness:
        mo = [s * o[p] for p, s in obs]
        a = D.policy_forward(policy["header"], policy["weights"], mo)
        want = [s * a[p] for p, s in act]
        worst = max(worst, max(abs(x - y) for x, y in zip(D.policy_forward(header, flat, o), want)))
    Path(dst).write_bytes(D.encode_policy(header, flat))
    flips = sorted(j for j, s in signs.items() if s < 0)
    print(f"{dst}: {len(obs)} channels, {len(act)} actions; joints with sign -1: {', '.join(flips)}")
    print(f"witness: {len(witness)} samples, largest |pi'(o) - M_a pi(M_o o)| = {worst:.2e} (action units)")
    return 0 if worst < 1e-3 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
