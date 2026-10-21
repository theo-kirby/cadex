"""orun13 P1 (O2, O7): do the hind feet stand outside the clip's stance, where heel_pitch stops paying?

usage: pixi run python docs/probes/orun13/stance_gate.py EVALUATION_DIR [EVALUATION_DIR ...]

``heel_pitch`` (and ``plantigrade``) pay only while the clip has the hind
paw in stance (``ref_lh_down``). The gallop clip stands each hind paw for
a duty of 0.2 (5 of 21 samples, about 100 ms); a foot that stands
outside the clip's stance (early, late, or a tap off the clock) is paid
nothing for being flat there, so ``hock_at_toeoff``'s window at such a
toe-off is unpriced.

The traces carry no clip clock, and an episode starts at a random clip
sample. Per seed, the clip's offset is fitted: the sample shift
(0..20) whose clip contact best matches the paw's measured ground contact
over the settled frames, both legs shifted together (one clock). Then, per
leg, over the settled on-ground frames (paw or heel down):

- the share inside the clip's stance and outside it;
- the toe-stance frames (paw down, heel up) inside and outside;
- each toe-off's last 40 ms (the ``hock_at_toeoff`` window): the share of
  toe-offs whose window lies wholly outside the clip's stance;
- the median measured stance in frames, against the clip's.

Writes nothing. Left and right apart (O5).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))
import CadexEvaluation as E  # noqa: E402
import mujoco  # noqa: E402
from spine_foot import paw_capsules  # noqa: E402

LEGS = (("LH", "c_paw_hl"), ("RH", "c_paw_hr"))


def model_for(out: Path):
    """The run's trained model: evaluations/NAME-IT judges runs/NAME/train."""
    run = out.parents[1] / "runs" / out.name.rsplit("-", 1)[0] / "train" / "cat_model-model.xml"
    return mujoco.MjModel.from_xml_string(run.read_text())


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    print("| evaluation | leg | stance frames med (clip) | on-ground in clip / outside | "
          "toe frames in clip / outside | toe-offs | window wholly outside clip stance | fit match |")
    print("|---|---|---|---|---|---|---|---|")
    for arg in argv:
        out = Path(arg).expanduser()
        task = json.loads((out / "judged-task.json").read_text())
        ref = task["reference"]
        n = int(ref["samples"])
        clip = {leg: ref["contact"][leg] for leg, _ in LEGS}
        evaluation = json.loads((out / "evaluation.json").read_text())
        rig = evaluation["rig"]
        acc = {leg: {"in": 0, "out": 0, "toe_in": 0, "toe_out": 0, "pushes": 0,
                     "outside": 0, "runs": [], "match": []} for leg, _ in LEGS}
        geoms = paw_capsules(model_for(out))
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            frames = [f for f in trace["frames"] if f.get("joint_positions")]
            samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
            times = [t for t, _ in samples]
            settled = [k for k, t in enumerate(times) if t >= E.SETTLE_S - 1e-9]
            series = {}
            for leg, paw in LEGS:
                sole = E.foot_series(samples, paw, geoms[paw], rig["floor_mm"])["height"]
                h = rig["heels"][paw]
                heel = E.foot_series(samples, h["body"], h["geoms"], rig["floor_mm"])["height"]
                series[leg] = ([s <= E.STANCE_MM for s in sole], [x <= E.STANCE_MM for x in heel])
            period = float(ref["parameters"]["period_s"])

            def phase_idx(k, shift):
                return (int(round((times[k] / period) * n)) + shift) % n

            best = max(range(n), key=lambda sh: sum(
                (series[leg][0][k] or series[leg][1][k]) == bool(clip[leg][phase_idx(k, sh)])
                for leg, _ in LEGS for k in settled))
            for leg, _ in LEGS:
                toes, down = series[leg]
                ground = [a or b for a, b in zip(toes, down)]
                a = acc[leg]
                a["match"].append(sum(ground[k] == bool(clip[leg][phase_idx(k, best)]) for k in settled)
                                  / max(len(settled), 1))
                for k in settled:
                    if not ground[k]:
                        continue
                    ins = bool(clip[leg][phase_idx(k, best)])
                    a["in" if ins else "out"] += 1
                    if toes[k] and not down[k]:
                        a["toe_in" if ins else "toe_out"] += 1
                i = 0
                while i < len(ground):
                    if not ground[i]:
                        i += 1
                        continue
                    run = []
                    while i < len(ground) and ground[i]:
                        run.append(i)
                        i += 1
                    if times[run[0]] < E.SETTLE_S - 1e-9 or i >= len(ground):
                        continue
                    a["runs"].append(len(run))
                    a["pushes"] += 1
                    e = run[-1]
                    window = [k for k in run if times[e] - times[k] <= E.HEEL_TOEOFF_S + 1e-9]
                    if not any(clip[leg][phase_idx(k, best)] for k in window):
                        a["outside"] += 1
        for leg, _ in LEGS:
            a = acc[leg]
            g = max(a["in"] + a["out"], 1)
            t = max(a["toe_in"] + a["toe_out"], 1)
            print(f"| {out.name} | {leg} | {statistics.median(a['runs']) if a['runs'] else 0:.0f} "
                  f"({sum(clip[leg])}) | {a['in'] / g:.2f} / {a['out'] / g:.2f} "
                  f"| {a['toe_in'] / t:.2f} / {a['toe_out'] / t:.2f} | {a['pushes']} "
                  f"| {a['outside'] / max(a['pushes'], 1):.2f} | {statistics.mean(a['match']):.2f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
