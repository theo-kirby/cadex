"""orun14 P1 (ADR-785): the sole clip with trail_feet, and the hind paw pin through the stride.

usage: pixi run python docs/probes/orun14/clip_trail.py RUN/train/gallop-task.json RUN/train/cat_model-model.xml [CAP_DEG]

Regenerates a ``flat_feet="sole"`` bundle's clip offline with the engine's
generator on the bundle's MJCF: first at the bundle's own settings (checked
equal to the bundled clip, qpos exactly), then with ``trail_feet=True``. For
each hind leg prints the paw pin toes-up of the metatarsus (the right leg's
sign folded onto the left's) over the stance samples and over the swing
samples, its largest value, its largest step between samples, and whether
the swing keeps it under CAP_DEG (default 30). Writes nothing.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import CadexGait  # noqa: E402

LEGS = (("LH", "l", -1.0), ("RH", "r", 1.0))  # toes-up positive, as paw_floor.py


def clip(model, ref, trail):
    p = ref["parameters"]
    heels = ref["heels"]
    return CadexGait.generate(
        model, {k: v["foot_body"] for k, v in ref["legs"].items()},
        {"duty": p["duty_factor"], "offsets": p["phase_offsets"], "spine_deg": p["spine_amplitude_deg"]},
        p["speed_m_s"], stride_length_m=p["stride_length_m"], swing_height_m=p["swing_height_m"],
        pitch_amplitude_deg=p["pitch_amplitude_deg"], spine_joint=p["spine_joint"],
        spine_amplitude_deg=p["spine_amplitude_deg"], samples=ref["samples"],
        heels={k: v["body"] for k, v in heels.items()}, body_drop_m=p.get("body_drop_m", 0.0),
        body_pitch_deg=p.get("body_pitch_deg", 0.0), stance_shift_m=p.get("stance_shift_m"),
        heel_from=next(iter(heels.values()))["from_stance_share"], flat_feet="sole",
        trail_feet=trail, mujoco=mujoco)


def report(model, c, label, cap):
    ok = True
    for leg, side, sign in LEGS:
        j = c["joints"].index("j_pawpin_" + side)
        pin = [sign * math.degrees(row[j]) for row in c["joint_angles_rad"]]
        down = c["contact"][leg]
        stance = [v for v, d in zip(pin, down) if d]
        swing = [v for v, d in zip(pin, down) if not d]
        steps = [abs(pin[k] - pin[k - 1]) for k in range(len(pin))]
        ok &= max(swing) < cap
        print(f"{label} | {leg} | {min(stance):.1f}..{max(stance):.1f} | {min(swing):.1f}..{max(swing):.1f} "
              f"| {max(pin):.1f} | {max(steps):.1f} | {max(swing) < cap} | "
              f"{' '.join(f'{v:.0f}' for v in pin)}")
    return ok


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cap = float(argv[2]) if len(argv) > 2 else 30.0
    ref = json.loads(Path(argv[0]).read_text())["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    own = clip(model, ref, False)
    same = float(np.max(np.abs(np.array(own["qpos"]) - np.array(ref["qpos"])))) == 0.0
    print(f"regenerated clip equals the bundle's: {same}")
    trail = clip(model, ref, True)
    for leg, h in trail["heels"].items():
        print(f"{leg}: max IK miss {1000 * trail['ik']['max_miss_m'][leg]:.2f} mm; heel down on "
              f"{sum(h['down'])} samples; trails {h.get('trails', False)}")
    print(f"clip | leg | pin in stance deg | pin in swing deg | max | largest step | swing < {cap:.0f} | pin per sample")
    report(model, own, "sole", cap)
    under = report(model, trail, "sole + trail", cap)
    return 0 if same and under else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
