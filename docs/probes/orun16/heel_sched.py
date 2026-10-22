"""orun16 SG (O7): score a command-scheduled heel target per paw-down frame of judged gallop_sg traces, before it is built.

usage: CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/heel_sched.py \
           RUN/train/gallop-task.json EVALUATION_DIR [...]

heel_pitch and heel_tail pay the metatarsus towards its +6 deg flat (heel
down) and are gated by the command's share of 1.0-2.4 m/s, so at the slow end
they pay nothing either way and the heel drifts with the gait (sg-s3-25:
heel up at +23..+28 deg, down at +3..+6, the same at 1000 and 2400). The
candidate ties the target to the command and pays both ways, ungated:

    heel_sched = ref_h_down * tent(_META - T(cmd), W),
    T(cmd) = 6 + D (1 - g),  g = sat01((cmd - 1000) / 1400)

so at 1.0 m/s it pays a metatarsus D deg toes-down of flat (the heel up, on
the toes) and at 2.4 m/s the flat itself, sliding between. ``_META`` and its
calibration are ``orun14/heel_meta.py``'s (the first argument is a gallop
bundle on leo-v05's model, for the offset); paw-down frames stand in for the
clip's stance flags. Each evaluation is scored at its own judged command.
Per leg and candidate: the mean pay on heel-down and heel-up frames, the
contrast (heel-up minus heel-down: positive pushes the heel up, negative
down), and the slope per degree towards T at the heel-up median, all times
the candidate's weight. Writes nothing.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

import mujoco

_spec = importlib.util.spec_from_file_location(
    "heel_meta", Path(__file__).resolve().parents[1] / "orun14" / "heel_meta.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)
E = H.E

SG_LOW, SG_HIGH, FLAT = 1000.0, 2400.0, 6.0
# (D deg toes-down at the slow end, tent half-width W deg, weight)
CANDIDATES = [(24.0, 30.0, 6.0), (30.0, 30.0, 6.0), (30.0, 45.0, 6.0), (36.0, 45.0, 6.0)]


def target(cmd, d):
    g = min(1.0, max(0.0, (cmd - SG_LOW) / (SG_HIGH - SG_LOW)))
    return FLAT + d * (1.0 - g)


def tent(m, t, w):
    return max(0.0, 1.0 - abs(m - t) / w)


def frames(out, cal, paw_geoms):
    """_META per paw-down frame from the settle on, split heel down / heel up."""

    rig = json.loads((out / "evaluation.json").read_text())["rig"]
    acc = {side: {"heel": [], "up": []} for side in "lr"}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"])
                   for f in trace["frames"] if f.get("component_placements")]
        for side in "lr":
            paw = f"c_paw_h{side}"
            hb = rig["heels"][paw]
            heel = E.foot_series(samples, hb["body"], hb["geoms"], rig["floor_mm"])["height"]
            sole = E.foot_series(samples, paw, paw_geoms[paw], rig["floor_mm"])["height"]
            for i, (t, p) in enumerate(samples):
                if t < E.SETTLE_S - 1e-9 or sole[i] > E.STANCE_MM:
                    continue
                rot, _ = E._pose(p, f"c_meta_h{side}")
                m = H.pitch_from_x([rot[0][0], rot[1][0], rot[2][0]]) + cal[side][0]
                acc[side]["heel" if heel[i] <= E.STANCE_MM else "up"].append(m)
    return acc


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cal = H.calibrate(Path(argv[0]))
    task = json.loads(Path(argv[0]).read_text())
    paw_geoms = H.paw_capsules(mujoco.MjModel.from_xml_path(
        str(Path(argv[0]).parent / Path(task["model"]["path"]).name)))
    print("| evaluation | cmd | leg | heel-down share | _META heel down / heel up median "
          "| D W w: T; pay heel down / heel up; contrast; slope /deg at heel-up median |")
    print("|---|---|---|---|---|---|")
    for arg in argv[1:]:
        out = Path(arg)
        cmd = float(json.loads((out / "evaluation.json").read_text())["judged_command_mm_s"])
        acc = frames(out, cal, paw_geoms)
        for side, a in acc.items():
            n = len(a["heel"]) + len(a["up"])
            mu = H.med(a["up"])
            cells = []
            for d, w, wt in CANDIDATES:
                t = target(cmd, d)
                ph = wt * statistics.fmean(tent(m, t, w) for m in a["heel"]) if a["heel"] else float("nan")
                pu = wt * statistics.fmean(tent(m, t, w) for m in a["up"]) if a["up"] else float("nan")
                step = 0.5 if mu < t else -0.5
                sl = wt * (tent(mu + step, t, w) - tent(mu - step, t, w))
                cells.append(f"{d:g} {w:g} {wt:g}: {t:+.0f}; {ph:.2f} / {pu:.2f}; {pu - ph:+.2f}; {sl:.3f}")
            print(f"| {out.name} | {cmd:.0f} | {side.upper()}H | {len(a['heel']) / max(n, 1):.2f} "
                  f"| {H.med(a['heel']):+.1f} / {mu:+.1f} | " + "<br>".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
