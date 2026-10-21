"""orun13 P1 (O2, O5): each hind foot's ground frames in one seed's trace, frame by frame, left and right.

usage: pixi run python docs/probes/orun13/foot_frames.py MODEL_XML EVALUATION_DIR SEED [FROM_S TO_S]

Reads the seed's trace the way ``spine_foot.py`` does (the engine's
``foot_series`` on the paw's and the heel's collision geoms, from the 1 s
settle on) and gives every frame each hind foot touches the floor one
letter:

- ``F`` flat: heel and toes both down;
- ``U`` toes-up: heel down, toes off the floor (the orun12 fault);
- ``T`` toe stance: toes down, heel up;
- ``.`` the foot is off the floor.

Prints, per leg, the frame counts and shares of the on-ground frames, the
timeline between FROM_S and TO_S (default 1.0 to 2.5 s) one letter per
frame, and per stance the frame times of its first flat frame and its
heel and toe heights there, which are the frames a still is rendered from
(``docs/probes/orun12/render_frame.py``). Writes nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
from spine_foot import LEGS, paw_capsules  # noqa: E402


def letters(sole, heel):
    out = []
    for s, h in zip(sole, heel):
        toes, down = s <= E.STANCE_MM, h <= E.STANCE_MM
        out.append("F" if toes and down else "U" if down else "T" if toes else ".")
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    out, seed = Path(argv[1]), int(argv[2])
    lo, hi = (float(argv[3]), float(argv[4])) if len(argv) > 4 else (1.0, 2.5)
    evaluation = json.loads((out / "evaluation.json").read_text())
    rig = evaluation["rig"]
    trace = json.loads((out / f"seed-{seed}-trace.json").read_text())
    frames = [f for f in trace["frames"] if f.get("joint_positions")]
    samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
    late = [i for i, (t, _) in enumerate(samples) if t >= E.SETTLE_S - 1e-9]
    geoms = paw_capsules(model)
    print(f"## {out.name}, seed {seed}\n")
    for leg, paw in LEGS:
        sole = E.foot_series(samples, paw, geoms[paw], rig["floor_mm"])["height"]
        h = rig["heels"][paw]
        heel = E.foot_series(samples, h["body"], h["geoms"], rig["floor_mm"])["height"]
        mark = letters(sole, heel)
        ground = [mark[i] for i in late if mark[i] != "."]
        counts = {c: ground.count(c) for c in "FUT"}
        n = max(len(ground), 1)
        print(f"**{leg}** on-ground frames {len(ground)}: flat {counts['F']} ({counts['F'] / n:.2f}), "
              f"toes-up {counts['U']} ({counts['U'] / n:.2f}), toe stance {counts['T']} ({counts['T'] / n:.2f})\n")
        span = [i for i in late if lo <= samples[i][0] <= hi]
        if span:
            print(f"    {samples[span[0]][0]:.2f}-{samples[span[-1]][0]:.2f} s  "
                  + "".join(mark[i] for i in span) + "\n")
        print("| stance from s | frames | letters | first flat s | heel / toe mm there |")
        print("|---|---|---|---|---|")
        k = 0
        while k < len(late):
            if mark[late[k]] == ".":
                k += 1
                continue
            run = []
            while k < len(late) and mark[late[k]] != ".":
                run.append(late[k])
                k += 1
            if not lo <= samples[run[0]][0] <= hi:
                continue
            flat = next((i for i in run if mark[i] == "F"), None)
            where = ("–", "–") if flat is None else (f"{samples[flat][0]:.2f}", f"{heel[flat]:.1f} / {sole[flat]:.1f}")
            print(f"| {samples[run[0]][0]:.2f} | {len(run)} | {''.join(mark[i] for i in run)} | {where[0]} | {where[1]} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
