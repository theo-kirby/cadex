"""Write leo v06's M1 task bundle: S1's speed-only task carrying the cheetah's strides (orun19 M1).

usage: pixi run python -I docs/probes/orun19/m1_bundle.py SPEED_BUNDLE OUT_DIR LABEL CLIP [CLIP ...]

``SPEED_BUNDLE`` is s1-v06's ``speed-task.json`` (leo v06, b1-s2's ten rows on 24
drives); each ``CLIP`` is a v06 clip from ``acino_retarget.py`` (this folder),
slowest first. This is orun18's ``c3_bundle.py`` run unchanged (the engine's own
``_tracking_records``, ``_schedule_record``, ``_reference_start_records`` and
``compile_reward``, the footfall-order refusal, the goal narrowed to the
strides' span), with its three tracking terms rewritten for v06's body (D6,
O4; no style term):

* ``track_pose`` drops the ``("wrist", "carpus")`` row, which v06 does not
  have, and adds the tail's two drives (``q_tail1``, ``q_tail2`` against the
  clip's mapped tail). That is 19 squared errors, as sgt-4's was, so its
  divisor stays 17100 (30 degrees RMS per joint at 1/e);
* ``track_lift`` reads each foot body's centre of mass (``pfl_z`` ...) less
  its height over the ball's lowest point at leo v06's keyframe: 20.9 mm fore
  (r 22 ball), 29.3 mm hind (r 30 ball), measured on the bundle's model,
  where v05's were 22 and 16 for its paws;
* ``track_contact`` is unchanged.

Weights are sgt-4's: 1.5, 1.5 and 10. The head drives are held in the speed
task, not actions, so the head is not tracked (``acino_retarget.measure_head``).
The bundle carries the clips, so it is AcinoSet-derived (D5a) and stays in
``~/mocap/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun18"))

import c3_bundle as C  # noqa: E402

C.JOINTS = [j for j in C.JOINTS if j[0] != "wrist"]
C.TRACK_POSE = "exp(-(" + " + ".join(
    [f"(q_{own}_{side} - q_{ref}_{side}_ref)**2" for side in "lr" for own, ref in C.JOINTS]
    + ["(q_spine - q_spine_ref)**2", "(q_tail1 - q_tail1_ref)**2", "(q_tail2 - q_tail2_ref)**2"]) + ") / 17100.0)"
C.TRACK_LIFT = ("exp(-(((pfl_z - 20.9 - ref_lf_lift) / 30)**2 + ((pfr_z - 20.9 - ref_rf_lift) / 30)**2"
                " + ((phl_z - 29.3 - ref_lh_lift) / 30)**2 + ((phr_z - 29.3 - ref_rh_lift) / 30)**2) / 4)")

if __name__ == "__main__":
    C.main(sys.argv[1:])
