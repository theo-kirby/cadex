"""orun16 SG: score sg-s4's overrun penalty per step on judged traces (O7), before it is built.

usage: python3 docs/probes/orun16/overrun_term.py EVAL_DIR[:CMD] [EVAL_DIR[:CMD] ...]

sg-s2's track_speed (w 20) is a tent, (v - 0.75 (v - cmd + |v - cmd|)) / cmd:
1 at the command, falling at half its rising slope past it, so a policy that
runs 2.06 m/s at a 1.0 m/s command is still paid 0.47 of it. The candidate is
a separate term, weight -W:

    overrun = (o + |o|) / 2,  o = (comv_x - (1 + B) cmd) / cmd

nothing inside a dead band B over the command, then linear. Speed is the
chest frame's forward speed from frame to frame (50 Hz, the first second
dropped), as ``tent_term.py``; the trainer's ``comv_x`` is the COM's, per
control step, so it swings more within a stride than this does. ``:CMD``
judges a trace against a command it was not run at (a single-speed gallop
at its own speed: how much the term fires on in-stride surges alone).
Per evaluation: the median speed, the tent's pay (x 20), and for each
candidate the mean penalty per step and the net speed pay (tent x 20 -
W x overrun), with the share of steps the penalty fires. Writes nothing.
"""
import glob
import json
import math
import sys

CANDIDATES = [(10.0, 0.15), (10.0, 0.25), (20.0, 0.15), (20.0, 0.25)]


def speeds(d):
    vs = []
    for f in sorted(glob.glob(d + "/seed-*-trace.json")):
        xs = [x["component_placements"]["c_chest_frame"]["position_mm"][0] for x in json.load(open(f))["frames"]]
        vs += [(xs[i] - xs[i - 1]) * 50.0 for i in range(51, len(xs))]
    return vs


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    head = "| evaluation | cmd | median v | tent x 20 | " + " | ".join(
        "W %g B %g: pen / net / fires" % c for c in CANDIDATES) + " |"
    print(head)
    print("|" + "---|" * (4 + len(CANDIDATES)))
    for arg in argv:
        d, _, c = arg.partition(":")
        cmd = float(c) if c else float(json.load(open(d + "/evaluation.json"))["judged_command_mm_s"])
        vs = speeds(d)
        n = len(vs)
        tent = 20.0 * sum((v - 0.75 * (v - cmd + abs(v - cmd))) / cmd for v in vs) / n
        cells = []
        for w, b in CANDIDATES:
            o = [max(0.0, (v - (1 + b) * cmd) / cmd) for v in vs]
            pen = w * sum(o) / n
            cells.append("%.2f / %.2f / %.2f" % (pen, tent - pen, sum(1 for x in o if x > 0) / n))
        name = d.rstrip("/").split("/")[-1]
        print("| %s | %.0f | %.0f | %.2f | %s |" % (name, cmd, sorted(vs)[n // 2], tent, " | ".join(cells)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
