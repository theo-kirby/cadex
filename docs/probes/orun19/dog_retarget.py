"""Retarget one AI4Animation dog stride to leo v06 as a gait clip (orun19 M2, charter O4).

usage: pixi run python -I docs/probes/orun19/dog_retarget.py MODEL_XML BVH FIRST END LABEL OUT_DIR SAMPLES [paw|carpus]

``MODEL_XML`` is leo v06's MJCF as a task bundle carries it (``runs/s1-v06/train/
cat_model-model.xml``, sha256 ``f9b8ab82…``); ``BVH`` one of the dog's takes
(``~/mocap/ai4animation/extract/``, CC BY-NC 4.0, orun18 SOURCES.md). The stride is
read by orun18's ``retarget.dog_stride`` and solved by ``retarget.retarget``,
unchanged, as orun18 C2/C3 did on v05. The clip and its measure go to ``OUT_DIR``
beside the capture, never to the repository (D5); their sha256 is reported.

**O4 on v06.** The solve reads each leg's chain from the model, so on v06 the hind
target is the ball (r 30 mm) through hip, knee and hock, and the fore target is the
ball (r 22 mm) through abduction, scapula, shoulder and elbow. The dog's fore leg
has a carpus (``LeftHand``) and a paw end below it (``LeftHand_end``, 72 mm in the
capture). Which of the two the ball follows is the last argument:

- ``paw`` (orun18's target): the paw end, the point that meets the ground;
- ``carpus``: the carpus itself, as M1's cheetah (whose capture ends there). The
  digits' fold in swing is dropped with the carpus angle, and the carpus's track,
  held on leo's ground in stance, is the ball's.

Either way the floor, the scale and the contact rule are the stride's own (the
carpus track replaces only the fore targets, after ``dog_stride`` has read them). Spine as on
v05. M1's v06 measures are taken the same way (``acino_retarget.heel_and_miss``):
miss in stance and swing, the heel pad over the ground and the hock's angle in hind
stance.

**Tail and head.** The dog has a two-segment tail (``Tail``, ``Tail1``, an end) and
a neck and head (``Neck``, ``Head``, an end). The tail chord ``Tail`` to
``Tail1_end`` goes to ``j_tail1`` / ``j_tail2`` by M1's ``map_tail``; the head chord
``Neck`` to ``Head_end`` is measured by ``measure_head`` and not posed, because leo's
speed task holds the head drives.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "orun18"))
sys.path.insert(0, str(HERE))

import acino_retarget as M1  # noqa: E402  (orun19's, this folder)
import retarget as R  # noqa: E402

TAIL = ("Tail", "Tail1_end")
HEAD = ("Head_end", "Neck")


def main(argv: list[str]) -> None:
    model_path, bvh, first, end, label, out_dir = argv[:6]
    samples = int(argv[6])
    fore = argv[7] if len(argv) > 7 else "paw"
    stride = R.dog_stride(Path(bvh), int(first), int(end), samples)
    if fore == "carpus":
        names = stride["skeleton"]["names"]
        for f, joint in (("LF", "LeftHand"), ("RF", "RightHand")):
            stride["paw"][f] = stride["skeleton"]["points"][:, names.index(joint)].copy()
    elif fore != "paw":
        raise SystemExit(f"fore target is paw or carpus, not {fore!r}")
    clip, measure, _ = R.retarget(Path(model_path), Path(bvh), int(first), int(end), label, samples,
                                  stride=stride)
    clip["label"] = clip["label"].replace("retargeted to leo v05", "retargeted to leo v06")
    measure["fore_target"] = fore
    measure["model_sha256"] = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    measure["v06"] = M1.heel_and_miss(Path(model_path), clip, measure)
    measure["v06"]["tail"] = M1.map_tail(Path(model_path), stride, clip, points=TAIL)
    measure["v06"]["head"] = M1.measure_head(stride, int(clip["samples"]), points=HEAD)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(clip)
    (out / f"{label}.clip.json").write_text(text)
    measure["clip_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (out / f"{label}.measure.json").write_text(json.dumps(measure, indent=1))
    print(json.dumps({k: measure[k] for k in ("label", "leo", "v06", "clip_sha256")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
