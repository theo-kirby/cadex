"""The plantigrade clip's heel, eased or stepped: a bundle's clip against the generator's today (ADR-778).

Regenerates a training bundle's gait reference on the bundle's own exported
model, with the parameters the bundle records, through the current
``CadexGait.generate``, and prints for each hind leg the heel's height per
stance-and-after sample and the largest frame-to-frame step of the hip, knee
and hock, for the bundle's clip and the regenerated one. A model without
heels regenerates byte-equal to its bundle. Nothing is simulated.

    pixi run python docs/probes/orun11/heel_ease.py \
        ~/cadex-projects/orun11-cat/runs/hock80-s1/train/gallop-task.json [out.json]

With ``out.json`` it also writes the bundle with the regenerated clip in its
reference (for ``clip_static.py``).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexGait  # noqa: E402
import mujoco  # noqa: E402

HIND = {"LH": "l", "RH": "r"}


def regenerate(task_path: Path):
    task = json.loads(task_path.read_text())
    ref = task["reference"]
    p = ref["parameters"]
    model = mujoco.MjModel.from_xml_path(str(next(task_path.parent.glob("*-model.xml"))))
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, str(ref["reset_keyframe"]))
    extra = {}
    if ref.get("heels"):
        extra = dict(heels={f: h["body"] for f, h in ref["heels"].items()},
                     heel_from=next(iter(ref["heels"].values()))["from_stance_share"],
                     body_drop_m=p.get("body_drop_m", 0.0), body_pitch_deg=p.get("body_pitch_deg", 0.0),
                     stance_shift_m=p.get("stance_shift_m"))
    clip = CadexGait.generate(
        model, {f: leg["foot_body"] for f, leg in ref["legs"].items()},
        {"offsets": p["phase_offsets"], "duty": p["duty_factor"], "name": ref["gait"]}, p["speed_m_s"],
        stride_length_m=p["stride_length_m"], swing_height_m=p["swing_height_m"],
        pitch_amplitude_deg=p["pitch_amplitude_deg"], spine_joint=p.get("spine_joint"),
        spine_amplitude_deg=p.get("spine_amplitude_deg"), samples=ref["samples"],
        home_qpos=[float(v) for v in model.key_qpos[key]] if key >= 0 else None, mujoco=mujoco, **extra)
    return task, clip


def rows(clip):
    names, angles = clip["joints"], clip["joint_angles_rad"]
    out = {}
    for foot, side in HIND.items():
        heel = (clip.get("heels") or {}).get(foot)
        row = {"heel_mm": [round(1000 * h) for h in heel["height_m"]] if heel else None}
        for joint in ("hip", "knee", "hock"):
            c = names.index(f"j_{joint}_{side}")
            s = [math.degrees(a[c]) for a in angles]
            steps = [abs(s[(k + 1) % len(s)] - s[k]) for k in range(len(s))]
            row[joint] = {"max_step_deg": round(max(steps), 1), "at": steps.index(max(steps)),
                          "max_rate_deg_s": round(max(steps) / clip["sample_dt_s"])}
        out[foot] = row
    return out


def main(argv):
    task, clip = regenerate(Path(argv[1]))
    print("byte-equal to the bundle:", clip["qpos"] == task["reference"]["qpos"])
    for label, c in (("bundle", task["reference"]), ("generator", clip)):
        print(label, json.dumps(rows(c)))
    if len(argv) > 2:
        for k in ("label", "start", "reset_keyframe", "placements"):
            if k in task["reference"]:
                clip.setdefault(k, task["reference"][k])
        task["reference"].update(clip)
        Path(argv[2]).write_text(json.dumps(task))


if __name__ == "__main__":
    main(sys.argv)
