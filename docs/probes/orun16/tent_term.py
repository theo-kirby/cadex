"""orun16 SG: score sg-s1's track_speed kernel against the tent that replaces it, per step, on judged traces (O7).

usage: python3 docs/probes/orun16/tent_term.py EVAL_DIR [EVAL_DIR ...]

The chest frame's forward speed from frame to frame (50 Hz, the first second
dropped), paid as the kernel exp(-|v - cmd| / (0.2 cmd)) and as the tent
(v - 0.75 (v - cmd + |v - cmd|)) / cmd, each as a share of the term's
weight; ``UP`` is left out (the policies judged stay upright).
"""
import json, glob, math, sys
for d in sys.argv[1:]:
    cmd = json.load(open(d + "/evaluation.json")).get("judged_command_mm_s")
    K = T = n = 0; vs = []
    for f in sorted(glob.glob(d + "/seed-*-trace.json")):
        fr = json.load(open(f))["frames"]
        dt = 1.0 / 50
        xs = [x["component_placements"]["c_chest_frame"]["position_mm"][0] for x in fr]
        for i in range(50 + 1, len(xs)):
            v = (xs[i] - xs[i - 1]) / dt
            vs.append(v)
            K += math.exp(-abs(v - cmd) / (0.2 * cmd)); T += (v - 0.75 * (v - cmd + abs(v - cmd))) / cmd; n += 1
    vs.sort()
    print(d, cmd, "median v %.0f" % vs[len(vs)//2], "kernel %.3f  tent %.3f  (share of weight per step)" % (K / n, T / n))
