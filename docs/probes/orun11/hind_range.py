"""orun11 rung 7: how much hind hip and knee range a plantigrade clip needs (O3).

Usage: pixi run python docs/probes/orun11/hind_range.py MODEL.xml

Runs ``plantigrade_reach.py``'s grid (108 plantigrade clips: stride, duty,
trunk drop, nose-up pitch, hind-stance shift, the hock cases held down from
half the stance to toe-off) on the exported model with the hind hip and
knee stops widened by each candidate, everything else as exported. Hip
flexion (the knee forward) is negative on the left leg, knee flexion (the
shin folded back) negative on the left; the right leg mirrors both. Prints
the reachable count, each reachable row's hind joint spans, and what binds
the rest.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mujoco  # noqa: E402
import plantigrade_reach  # noqa: E402

# (hip flexion added, knee flexion added, knee extension added), degrees, against
# orun11-cat 4cd04aaf's stops: hip -30..+40, knee -40..+50 (left)
CANDIDATES = [(0, 0, 0), (15, 20, 0), (15, 20, 15), (20, 25, 15)]


def main(argv):
    for hip, knee, knee_ext in CANDIDATES:
        model = mujoco.MjModel.from_xml_path(argv[0])

        def stops(name, lo, hi):
            j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
            model.jnt_range[j] = [math.radians(lo), math.radians(hi)]

        stops("j_hip_l", -30 - hip, 40)
        stops("j_hip_r", -40, 30 + hip)
        stops("j_knee_l", -40 - knee, 50 + knee_ext)
        stops("j_knee_r", -50 - knee_ext, 40 + knee)
        plantigrade_reach.grid(model, f"hip flexion +{hip}, knee flexion +{knee}, knee extension +{knee_ext} deg")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
