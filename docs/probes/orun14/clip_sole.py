"""orun14 P1 (ADR-784): the gallop clip regenerated with flat_feet="sole".

usage: pixi run python docs/probes/orun14/clip_sole.py RUN/train/gallop-task.json RUN/train/cat_model-model.xml [OUT.json]

Regenerates the bundle's clip offline with the engine's generator on the
bundle's MJCF: first at the bundle's own settings (checked equal to the
bundled clip, qpos exactly), then with ``flat_feet="sole"``. Prints each hind
paw's sole pitch and the clip's metatarsus pitch range while the heel is held.
With OUT, writes a copy of the task with the sole clip as its reference, for
``clip_pad.py`` to read the pad's height in stance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun12"))

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from clip_flat import clip, report  # noqa: E402


def main(argv: list[str]) -> int:
    task = json.loads(Path(argv[1]).read_text())
    ref = task["reference"]
    model = mujoco.MjModel.from_xml_path(argv[2])
    own = clip(model, ref, False)
    same = float(np.max(np.abs(np.array(own["qpos"]) - np.array(ref["qpos"])))) == 0.0
    print(f"regenerated clip equals the bundle's: {same}")
    sole = clip(model, ref, "sole")
    for leg, h in sole["heels"].items():
        print(f"{leg}: sole pitch {h['flat_pitch_deg']:+.2f} deg; max IK miss {1000 * sole['ik']['max_miss_m'][leg]:.2f} mm")
    print("clip | leg | heel-down samples | metatarsus pitch deg | paw pin deg | largest step deg")
    report(model, own, "bundle")
    report(model, sole, "sole")
    if len(argv) > 3:
        task["reference"] = {**ref, **{k: v for k, v in sole.items() if k in ref}}
        Path(argv[3]).write_text(json.dumps(task))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
