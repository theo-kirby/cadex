"""orun16 SG: check a built schedule bundle's strides against sg_clip.py's, stride by stride.

usage: pixi run python docs/probes/orun16/sg_bundle.py SG_TASK.json MODEL.xml PARENT_TASK.json STRIDES.json

SG_TASK.json is the built ``gallop_sg`` bundle; PARENT_TASK.json the single-
speed gallop bundle sg_clip.py generated the strides from (its reference's
settings), STRIDES.json the strides sg_clip.py judged. Each stride is
generated again with sg_clip.py's ``generate`` on the schedule's common grid
and compared with the bundle's ``reference_schedule`` entry: qpos (largest
difference), contact and heel flags (equal), phase offsets, speed and
period. Then the schedule's own records: ``tracking.schedule`` speeds and
labels, ``tracking.table`` equal to stride 0's table, the bundle's
``reference`` equal to stride 0, the speed goal, and the reward terms. Exit
0 only if every stride matches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sg_clip  # noqa: E402


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    sg, model_path, parent, strides = (json.loads(Path(a).read_text()) if a.endswith(".json") else a for a in argv)
    model = sg_clip.mujoco.MjModel.from_xml_path(model_path)
    ref = parent["reference"]
    built = sg["reference_schedule"]
    rows = int(built[0]["samples"])
    ok = len(built) == len(strides) and all(int(b["samples"]) == rows for b in built)
    print(f"strides: {len(built)} built, {len(strides)} judged; grid {rows} samples")
    print("\n| stride | qpos max diff | contact equal | heels equal | offsets equal | m/s built / judged | period s |")
    print("|---|---|---|---|---|---|---|")
    for k, (b, s) in enumerate(zip(built, strides)):
        c = sg_clip.generate(model, ref, s, samples=rows)
        dq = float(np.max(np.abs(np.array(b["qpos"]) - np.array(c["qpos"]))))
        ce = b["contact"] == c["contact"]
        he = all(b["heels"][leg]["down"] == c["heels"][leg]["down"] for leg in c["heels"])
        oe = all(abs(b["parameters"]["phase_offsets"][f] - c["parameters"]["phase_offsets"][f]) < 1e-12
                 for f in c["parameters"]["phase_offsets"])
        bs, cs = b["parameters"]["speed_m_s"], c["parameters"]["speed_m_s"]
        good = dq < 1e-9 and ce and he and oe and abs(bs - cs) < 1e-9
        ok = ok and good
        print(f"| {b['label']} | {dq:.2e} | {ce} | {he} | {oe} | {bs:.3f} / {cs:.3f} | "
              f"{b['parameters']['period_s']:.4f} |")
    tr = sg["tracking"]
    sch = tr["schedule"]
    same_table = tr["table"] == sch["tables"][0]
    same_ref = sg["reference"]["qpos"] == built[0]["qpos"]
    ok = ok and same_table and same_ref
    print(f"\nschedule speeds mm/s {sch['speeds_mm_s']}, periods s {[round(x, 4) for x in sch['periods_s']]}")
    print(f"tracking.table is stride 0's: {same_table}; bundle reference is stride 0: {same_ref}")
    print(f"goal: {[(g['name'], g['kind'], g['low'], g['high'], g['resample_steps'], g.get('ramp_steps')) for g in sg['goal']]}")
    print(f"reward terms: {len(sg['reward'])}")
    for r in sg["reward"]:
        if "cmd" in r["expression"]:
            print(f"- {r['label']} (w {r['weight']:g}) reads cmd")
    print("\nverdict:", "match" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
