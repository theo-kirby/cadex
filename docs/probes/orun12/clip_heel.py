"""orun12 P1: which heel_from the plantigrade gallop clip can take on feline v07.

Regenerates a training bundle's gait clip offline with the engine's own
generator (CadexGait.generate) on the bundle's exported MJCF, at the
bundle's clip parameters, for each heel_from given, and prints whether the
clip is reachable and on how many of each hind paw's stance samples the
heel is held down. The bundle's own heel_from is regenerated first and
checked against the bundle's clip (heel schedule and qpos), so the scan is
known to be the engine's clip and not an approximation.

    pixi run python docs/probes/orun12/clip_heel.py \
        RUN/train/gallop-task.json RUN/train/cat_model-model.xml 0.5 0.3 0.2 0
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import CadexGait  # noqa: E402


def clip(model, ref, heel_from):
    p = ref["parameters"]
    return CadexGait.generate(
        model, {k: v["foot_body"] for k, v in ref["legs"].items()},
        {"duty": p["duty_factor"], "offsets": p["phase_offsets"], "spine_deg": p["spine_amplitude_deg"]},
        p["speed_m_s"], stride_length_m=p["stride_length_m"], swing_height_m=p["swing_height_m"],
        pitch_amplitude_deg=p["pitch_amplitude_deg"], spine_joint=p["spine_joint"],
        spine_amplitude_deg=p["spine_amplitude_deg"],
        heels={k: v["body"] for k, v in ref["heels"].items()}, body_drop_m=p["body_drop_m"],
        body_pitch_deg=p["body_pitch_deg"], stance_shift_m=p["stance_shift_m"],
        heel_from=heel_from, mujoco=mujoco)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    ref = json.loads(Path(argv[0]).read_text())["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    own = next(iter(ref["heels"].values()))["from_stance_share"]
    c = clip(model, ref, own)
    same = (all(c["heels"][k]["down"] == ref["heels"][k]["down"] for k in ref["heels"])
            and float(np.max(np.abs(np.array(c["qpos"]) - np.array(ref["qpos"])))) == 0.0)
    print(f"bundle heel_from {own}: regenerated clip equals the bundle's: {same}")
    print("heel_from | reachable | heel-down samples / stance samples per hind paw")
    for hf in [float(a) for a in argv[2:]]:
        try:
            c = clip(model, ref, hf)
        except CadexGait.GaitError as exc:
            print(f"{hf:g} | no | {exc}")
            continue
        legs = ", ".join(f"{k} {sum(v['down'])}/{sum(c['contact'][k])}" for k, v in sorted(c["heels"].items()))
        print(f"{hf:g} | yes | {legs}")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
