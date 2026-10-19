"""orun11 rung 6: can the gait generator reach a plantigrade hind stance on this cat? (ADR-776)

Usage: pixi run python docs/probes/orun11/plantigrade_reach.py MODEL.xml

On the exported model (a training bundle's ``*-model.xml``), with
``CadexGait.generate``:

1. **The coupled paw in a clip.** The gallop clip orun11-cat trains on
   (rotary, 0.7 m at 2.4 Hz, duty 0.25, lags 0.05, swing 60 mm, spine 10
   deg), now generated with the rod's loop held: the paw pin against the
   hock over the hind stance, and the worst closure error.
2. **A plantigrade clip, inside the joint limits.** The same footfall with
   the hock cases as heels (``heels``), held down from ``heel_from`` of the
   stance to toe-off, over a grid of stride lengths, duties, trunk drops,
   nose-up pitches and forward hind-stance shifts. Each row is reachable or
   the generator's refusal (leg, phase, joints at a stop).
3. **The same grid with the hind hip, knee and hock unlimited**, to read
   the joint range a plantigrade push-off would need.
4. **The hip height the static check stood at** (``foot_static.py``'s
   poses: trunk level, floor put under the paw), against standing.
"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(HERE))

import mujoco  # noqa: E402
import CadexGait  # noqa: E402

LEGS = {"LF": "c_paw_fl", "RF": "c_paw_fr", "LH": "c_paw_hl", "RH": "c_paw_hr"}
HEELS = {"LH": "c_qdd_hock_l", "RH": "c_qdd_hock_r"}
OFFSETS = {"LH": 0.0, "RH": 0.05, "RF": 0.5, "LF": 0.55}
HIND = ["j_hip_l", "j_knee_l", "j_hock_l", "j_hip_r", "j_knee_r", "j_hock_r"]


def clip(model, length, duty, **extra):
    return CadexGait.generate(model, LEGS, {"name": "rotary_gallop", "offsets": OFFSETS, "duty": duty},
                              length * 2.4, stride_length_m=length, spine_joint="j_spine",
                              home_qpos=list(model.key_qpos[0]), mujoco=mujoco, **extra)


def grid(model, label):
    print(f"\n  {label}")
    ok = 0
    rows = list(itertools.product([0.5, 0.7], [0.2, 0.25], [0.5], [0.03, 0.045, 0.06], [3, 6, 9],
                                  [0.0, 0.06, 0.12]))
    binds: dict[str, int] = {}
    for length, duty, hf, drop, pitch, shift in rows:
        try:
            c = clip(model, length, duty, swing_height_m=0.05, pitch_amplitude_deg=2.0, heels=HEELS,
                     heel_from=hf, body_drop_m=drop, body_pitch_deg=pitch,
                     stance_shift_m={"LH": shift, "RH": shift})
        except CadexGait.GaitError as error:
            d = error.detail
            key = f"{d.get('leg')} {'heel down' if 'heel' in str(error) else 'swing' if 'swing' in str(error) else 'stance' if 'stance' in str(error) else 'linkage'}" \
                  f" {','.join(d.get('joints_at_stop') or []) or 'no stop (full reach)'}"
            binds[key] = binds.get(key, 0) + 1
            continue
        ok += 1
        J = c["joints"]
        q = np.degrees(np.array(c["joint_angles_rad"]))
        span = {n: (round(float(q[:, J.index(n)].min())), round(float(q[:, J.index(n)].max()))) for n in HIND}
        print(f"   reachable: stride {length} m, duty {duty}, heel from {hf} of stance, drop {drop * 1000:.0f} mm,"
              f" pitch {pitch} deg, hind shift {shift * 1000:.0f} mm; hind spans {span}")
    print(f"   {ok} of {len(rows)} reachable; what binds the rest:")
    for key, n in sorted(binds.items(), key=lambda kv: -kv[1]):
        print(f"     {n:3d}  {key}")


def main(argv):
    path = argv[0]
    model = mujoco.MjModel.from_xml_path(path)
    print(path)
    base = clip(model, 0.7, 0.25, swing_height_m=0.06)
    J = base["joints"]
    q = np.degrees(np.array(base["joint_angles_rad"]))
    print("\n  1. the training clip with the rod held (ADR-776)")
    for foot, side in (("LH", "l"), ("RH", "r")):
        stance = [k for k, v in enumerate(base["contact"][foot]) if v]
        hock, pin = q[stance, J.index(f"j_hock_{side}")], q[stance, J.index(f"j_pawpin_{side}")]
        slope = float(np.polyfit(hock, pin, 1)[0]) if np.ptp(hock) > 0.5 else float("nan")
        print(f"   {foot}: stance hock {hock.min():+.1f}..{hock.max():+.1f} deg, pin {pin.min():+.1f}..{pin.max():+.1f}"
              f" (slope {slope:+.3f}); closure error {1000 * base['ik']['closures'][foot]['max_error']:.4f} mm")
    grid(model, "2. plantigrade clips inside the joint limits")
    for name in HIND:
        j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        model.jnt_range[j] = [-math.radians(120.0), math.radians(120.0)]
    grid(model, "3. the same with the hind hip, knee and hock unlimited")

    import foot_static  # noqa: PLC0415 - the static check's own poses
    model = mujoco.MjModel.from_xml_path(path)
    leg = foot_static.Leg(model, "l")
    hip = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "j_hip_l")
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0]
    mujoco.mj_kinematics(model, data)
    floor = min(data.geom_xpos[g][2] - model.geom_size[g, 0] for g in (leg.pad, leg.toe))
    print(f"\n  4. hip over the floor: standing (keyframe) {1000 * (data.xanchor[hip][2] - floor):.1f} mm;"
          " in the static check's poses:")
    for shin in (0.0, -6.0, -10.0, -14.0, -20.0):
        def pitch_error(k):
            leg.guess = np.zeros(len(leg.passive))
            leg.pose(0.0, k)
            return leg.pitch(leg.shin_body) - leg.shin0 - shin
        k = 0.0
        for _ in range(40):
            e = pitch_error(k)
            if abs(e) < 1e-6:
                break
            k -= e / ((pitch_error(k + 0.01) - e) / 0.01)
        leg.guess = np.zeros(len(leg.passive))
        for h in np.arange(0.0, -60.01, -0.25):
            leg.pose(h, k)
            if leg.case_height_mm() <= 0.0:
                break
        print(f"   shin {shin:+.0f}: hock {h:+.2f}, sole {leg.sole_pitch():+.1f} deg,"
              f" hip {1000 * leg.d.xanchor[hip][2] - leg.floor_mm():.1f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
