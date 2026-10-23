"""orun12 P1 (O2a, ADR-780): the plantigrade clip's hind pose with and without flat_feet.

Regenerates a training bundle's gait clip offline with the engine's own
generator (CadexGait.generate) on the bundle's exported MJCF, first at the
bundle's own settings (checked equal to the bundle's clip, qpos exactly), then
with ``flat_feet`` on, and for each hind leg prints, over the samples where the
clip holds the heel down: the metatarsus's world pitch (ankle pin to paw pin,
degrees from horizontal, rising to the rear), the paw pin's angle (the right
leg's sign folded onto the left's), and the largest step of each hind joint
between samples over the stride.

    pixi run python docs/probes/orun12/clip_flat.py \
        RUN/train/gallop-task.json RUN/train/cat_model-model.xml
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import CadexGait  # noqa: E402

LEGS = (("LH", "l", 1.0), ("RH", "r", -1.0))


def clip(model, ref, flat_feet):
    p = ref["parameters"]
    return CadexGait.generate(
        model, {k: v["foot_body"] for k, v in ref["legs"].items()},
        {"duty": p["duty_factor"], "offsets": p["phase_offsets"], "spine_deg": p["spine_amplitude_deg"]},
        p["speed_m_s"], stride_length_m=p["stride_length_m"], swing_height_m=p["swing_height_m"],
        pitch_amplitude_deg=p["pitch_amplitude_deg"], spine_joint=p["spine_joint"],
        spine_amplitude_deg=p["spine_amplitude_deg"],
        heels={k: v["body"] for k, v in ref["heels"].items()}, body_drop_m=p.get("body_drop_m", 0.0),
        body_pitch_deg=p.get("body_pitch_deg", 0.0), stance_shift_m=p.get("stance_shift_m"),
        heel_from=next(iter(ref["heels"].values()))["from_stance_share"], flat_feet=flat_feet, mujoco=mujoco)


def report(model, c, label):
    data = mujoco.MjData(model)

    def jid(name):
        return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)

    angles = np.degrees(np.array(c["joint_angles_rad"]))
    steps = np.abs(np.diff(np.vstack([angles, angles[:1]]), axis=0)).max(axis=0)
    for leg, side, sign in LEGS:
        pitch, pin = [], []
        for k, down in enumerate(c["heels"][leg]["down"]):
            if not down:
                continue
            data.qpos[:] = c["qpos"][k]
            mujoco.mj_kinematics(model, data)
            a, b = data.xanchor[jid("j_ankle_" + side)], data.xanchor[jid("j_pawpin_" + side)]
            pitch.append(math.degrees(math.atan2(a[2] - b[2], b[0] - a[0])))
            pin.append(sign * math.degrees(c["qpos"][k][model.jnt_qposadr[jid("j_pawpin_" + side)]]))
        step = ", ".join(f"{n[2:-2]} {steps[c['joints'].index(n)]:.1f}"
                         for n in ("j_hip_" + side, "j_knee_" + side, "j_ankle_" + side, "j_pawpin_" + side))
        print(f"{label} | {leg} | {len(pitch)} | {min(pitch):.1f}..{max(pitch):.1f} | "
              f"{min(pin):.1f}..{max(pin):.1f} | {step}")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    ref = json.loads(Path(argv[0]).read_text())["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    bundled_flat = "flat_pitch_deg" in next(iter(ref["heels"].values()))
    own = clip(model, ref, bundled_flat)
    same = float(np.max(np.abs(np.array(own["qpos"]) - np.array(ref["qpos"])))) == 0.0
    print(f"regenerated clip equals the bundle's: {same}")
    print("clip | leg | heel-down samples | metatarsus pitch deg | paw pin deg | largest step deg")
    report(model, clip(model, ref, False), "without flat_feet")
    report(model, clip(model, ref, True), "flat_feet")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
