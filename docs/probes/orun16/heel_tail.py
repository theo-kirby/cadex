"""orun16 SG (O7): score heel_pitch's shape, and a wide tail on it, per paw-down frame of judged gallop_sg traces.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/heel_tail.py \
           RUN/train/gallop-task.json EVALUATION_DIR [...]

``orun14/heel_meta.py`` with its shapes swapped for sg-s3's candidates. The
first argument is a *gallop* bundle on the same model (v05-s1's): the
calibration reads the clip's ``reset_qpos`` through the trainer's
``tracking_vector``, which a speed-scheduled bundle cannot be read through
without a command. The offset is the model's geometry, so any bundle on
leo-v05's model gives the same one.

heel_pitch (w 10, gated by the command's share of 1.0-2.4 m/s) pays a cubic
of half-width 16 deg about a metatarsus angle of +6 deg (``_META``). A policy
on its toes holds ``_META`` 20-60 deg off it, where the cubic pays nothing
and has no slope, so a larger weight multiplies zero. The candidates add a
tent of half-width 60 or 90 deg at 0.3 of the weight, which pays a slope
towards the heel wherever the paw is down. Per leg: the mean pay on
paw-down frames, on heel-down frames, and the pay and slope (per deg
towards +6) at the heel-up median. Writes nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "heel_meta", Path(__file__).resolve().parents[1] / "orun14" / "heel_meta.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def _tent(centre, half):
    return lambda m: max(0.0, 1.0 - abs(m - centre) / half)


def _sum(*parts):
    return lambda m: sum(w * f(m) for w, f in parts)


H.SHAPES = {
    "cubic 16 @6 (now, sg-s2)": (6.0, H._cubic(6.0, 16.0)),
    "3 x cubic 16 @6 (weight 30)": (6.0, _sum((3.0, H._cubic(6.0, 16.0)))),
    "cubic 16 + 0.3 tent 60 @6": (6.0, _sum((1.0, H._cubic(6.0, 16.0)), (0.3, _tent(6.0, 60.0)))),
    "cubic 16 + 0.3 tent 90 @6": (6.0, _sum((1.0, H._cubic(6.0, 16.0)), (0.3, _tent(6.0, 90.0)))),
}

if __name__ == "__main__":
    raise SystemExit(H.main(sys.argv[1:]))
