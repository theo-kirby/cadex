"""orun12 P2: which pair lags the plantigrade gallop clip can take on feline v07.

Regenerates a bundle's clip offline with the engine's own generator
(``CadexGait.generate``, through ``clip_heel.clip``) on the bundle's
exported MJCF, at its heel_from, with the offsets LH 0, RH ``hind``, RF
0.5, LF 0.5 + ``fore`` (the script's ``gallop_ref``) and the stride and
swing given, and prints for each whether the clip is reachable, each
foot's stance samples, the heel-down samples per hind paw, the airborne
samples and the footfall order. The bundle's own clip is regenerated
first and checked equal to it.

    pixi run python docs/probes/orun12/clip_lag.py RUN/train/gallop-task.json \
        RUN/train/cat_model-model.xml STRIDE_M:SWING_M:HIND:FORE [...]

A lag may be written as a fraction, ``2/21``: the clip has 21 samples a
cycle at 2.4 Hz, and an offset off that grid gives the two feet of a pair
different stance sample counts.
"""

import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_heel  # noqa: E402
import mujoco  # noqa: E402

import CadexGait  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ref = json.loads(Path(argv[0]).read_text())["reference"]
    model = mujoco.MjModel.from_xml_path(argv[1])
    heel_from = next(iter(ref["heels"].values()))["from_stance_share"]
    same = clip_heel.clip(model, ref, heel_from)["qpos"] == ref["qpos"]
    print(f"bundle clip regenerated equal: {same}")
    print("stride m | swing m | hind lag | fore lag | reachable | stance samples LH RH LF RF "
          "| heel-down / stance | airborne / cycle | order")
    for case in argv[2:]:
        stride, swing, hind, fore = (float(Fraction(x)) for x in case.split(":"))
        r = json.loads(json.dumps(ref))
        p = r["parameters"]
        p["phase_offsets"] = {"LH": 0.0, "RH": hind, "RF": 0.5, "LF": 0.5 + fore}
        p["stride_length_m"], p["swing_height_m"] = stride, swing
        p["speed_m_s"] = stride * p["stride_frequency_hz"]
        head = f"{stride:g} | {swing:g} | {hind:.3f} | {fore:.3f}"
        try:
            c = clip_heel.clip(model, r, heel_from)
        except CadexGait.GaitError as exc:
            print(f"{head} | no: {exc} |")
            continue
        ct = c["contact"]
        n = len(ct["LH"])
        heel = ", ".join(f"{k} {sum(v['down'])}/{sum(ct[k])}" for k, v in sorted(c["heels"].items()))
        air = sum(1 for i in range(n) if not any(ct[k][i] for k in ct))
        order = " ".join(sorted(ct, key=lambda k: p["phase_offsets"][k]))
        stance = " ".join(str(sum(ct[k])) for k in ("LH", "RH", "LF", "RF"))
        print(f"{head} | yes | {stance} | {heel} | {air}/{n} | {order}")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
