"""orun16 RL (O3a, O7): score a speed schedule's pair lag per step on judged gallop_sg traces, at the judged command.

usage: pixi run python docs/probes/orun16/sg_lag.py RUN/train/gallop_sg-task.json RUN/train/cat_model-model.xml \
           EVALUATION_DIR [...]

orun15's ``lag_term.py`` reads one clip; a gallop_sg bundle carries a
schedule of strides (ADR-773), and a judged evaluation holds one command, so
the clip is the schedule's blend at that command (``tracking.schedule.rule``):
stride ``i`` and weight ``w`` from ``speeds_mm_s``, the clock turning
``(1 - w) turns[i] + w turns[i + 1]`` a control step from the episode's start
sample, the down columns blended and held at one half. The start sample is
recovered from the first solver frame against ``reset_qpos`` (every stride's
samples in stride order; the sample is the row mod ``samples``).

Per step from the settle (1 s) on, with each paw's contact the evaluator's
stance rule (``CadexEvaluation.STANCE_MM``), as ``lag_term.py``:

- ``track_contact`` (w10) split into its hind and fore halves, and
  ``hind_lag`` (w10, in the bundle) and the same form on the fore pair
  (``fore_lag``, not in the bundle), against the clip as built;
- **the candidates:** the same terms against the clip with each pair's lag
  replaced by ``L``, the trailing paw's down column being the leading paw's
  shifted by ``L`` of the stride (the script's offsets: LH 0, RH 1 - lag,
  RF 0.5, LF 0.5 - lag). The shift is first checked against the clip's own
  trailing columns at its own lag (the mismatched share is printed);
- the policy's own lag: each pair's median touchdown lag in ms, and as a
  share of its own median touchdown period, with the tied share (< 20 ms).

A candidate whose contact pay is higher on the policy's own contacts is a
clip nearer what the policy does; ``hind_lag`` and ``fore_lag``'s pay show
how much of that each pair term would see. Writes nothing.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import mujoco

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "probes" / "orun15"))
import lag_term as LT  # noqa: E402

E = LT.E
PAWS = LT.PAWS
CANDIDATES = (0.35, 0.30, 0.25, 0.20, 0.15, 0.10)


def blend(schedule, cmd):
    speeds = [float(v) for v in schedule["speeds_mm_s"]]
    v = min(max(abs(cmd), speeds[0]), speeds[-1])
    i = max(k for k in range(len(speeds) - 1) if speeds[k] <= v)
    return i, (v - speeds[i]) / (speeds[i + 1] - speeds[i])


def column(schedule, names, i, w, key, phase, rows):
    at = (phase - math.floor(phase)) * rows
    lo = int(math.floor(at)) % rows
    hi = (lo + 1) % rows
    f = at - math.floor(at)
    c = names.index("ref_%s_down" % key)
    out = 0.0
    for k, share in ((i, 1.0 - w), (i + 1, w)):
        if share <= 0.0:
            continue
        tab = schedule["tables"][k]
        out += share * (tab[lo][c] + f * (tab[hi][c] - tab[lo][c]))
    return 1.0 if out >= 0.5 else 0.0


def lag_label(schedule, i, w):
    lags = []
    for label in schedule["labels"]:
        lags.append(float(label.split("lag ")[1].split(",")[0]))
    return (1.0 - w) * lags[i] + w * lags[min(i + 1, len(lags) - 1)]


def own_lag(times, a, b, period):
    """b's touchdowns after a's, ms, and a's median touchdown period, s."""

    ta, tb = LT.touchdowns(times, a), LT.touchdowns(times, b)
    lags = LT.rh_after_lh(ta, tb, period)
    gaps = [y - x for x, y in zip(ta, ta[1:])]
    return lags, (statistics.median(gaps) if gaps else float("nan"))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    task = json.loads(Path(argv[0]).read_text())
    tracking = task["tracking"]
    schedule = tracking["schedule"]
    rows = int(tracking["samples"])
    names = tracking["channels"][2:]
    model = mujoco.MjModel.from_xml_path(argv[1])
    geoms = LT.capsules(model)
    dt = 1.0 / float(task.get("episode", {}).get("control_hz") or 50)
    for arg in argv[2:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        cmd = float(ev["judged_command_mm_s"])
        i, w = blend(schedule, cmd)
        turns = (1 - w) * float(schedule["turns_per_step"][i]) + w * float(schedule["turns_per_step"][i + 1])
        period = dt / turns
        lag0 = lag_label(schedule, i, w)
        floor = ev["rig"]["floor_mm"]
        print("\n## %s at %.0f mm/s (policy %s): stride %d w %.2f, clip period %.0f ms, clip lag %.3f (%.0f ms)\n"
              % (out.name, cmd, ev["policy_sha256"][:8], i, w, 1000 * period, lag0, 1000 * lag0 * period))
        pay = {L: {"hc": [], "fc": [], "hl": [], "fl": []} for L in ("clip",) + CANDIDATES}
        check = {"rh": [], "lf": []}
        own = {"hind": [], "fore": [], "hp": [], "fp": []}
        steps = 0
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, row = LT.origin(model, tracking, list(zip(joints, solver[0]["joint_positions"])))
            s0 = (row % rows) / float(rows)
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            down = {k: [h <= E.STANCE_MM for h in E.foot_series(samples, body, geoms[body], floor)["height"]]
                    for k, body in PAWS.items()}
            for i_, t in enumerate(times):
                if t < E.SETTLE_S - 1e-9:
                    continue
                steps += 1
                ph = s0 + turns * round(t / dt)
                c = {k: 1.0 if down[k][i_] else 0.0 for k in PAWS}
                r = {k: column(schedule, names, i, w, k, ph, rows) for k in PAWS}
                lead_h, lead_f = r["lh"], r["rf"]
                check["rh"].append(r["rh"] != column(schedule, names, i, w, "lh", ph + lag0, rows))
                check["lf"].append(r["lf"] != column(schedule, names, i, w, "rf", ph + lag0, rows))
                for L in pay:
                    if L == "clip":
                        rr = r
                    else:
                        rr = {"lh": lead_h, "rf": lead_f,
                              "rh": column(schedule, names, i, w, "lh", ph + L, rows),
                              "lf": column(schedule, names, i, w, "rf", ph + L, rows)}
                    pay[L]["hc"].append(10 * ((1 - abs(c["lh"] - rr["lh"])) + (1 - abs(c["rh"] - rr["rh"]))) / 4)
                    pay[L]["fc"].append(10 * ((1 - abs(c["lf"] - rr["lf"])) + (1 - abs(c["rf"] - rr["rf"]))) / 4)
                    dr, dc = rr["lh"] - rr["rh"], c["lh"] - c["rh"]
                    pay[L]["hl"].append(10 * abs(dr) * (1 - abs(dc - dr)))
                    fr, fc = rr["lf"] - rr["rf"], c["lf"] - c["rf"]
                    pay[L]["fl"].append(10 * abs(fr) * (1 - abs(fc - fr)))
            hl, hp = own_lag(times, down["lh"], down["rh"], period)
            fl, fp = own_lag(times, down["rf"], down["lf"], period)
            own["hind"].extend(hl)
            own["fore"].extend(fl)
            own["hp"].append(hp)
            own["fp"].append(fp)
        print("Shifted lead against the clip's own trail at lag %.3f: RH mismatched %.3f, LF %.3f of %d steps."
              % (lag0, statistics.fmean(check["rh"]), statistics.fmean(check["lf"]), steps))
        print("\n| clip lag | track_contact hind (w10) | track_contact fore | sum | hind_lag (w10) | fore_lag (w10) |")
        print("|---|---|---|---|---|---|")
        for L, a in pay.items():
            m = {k: statistics.fmean(v) for k, v in a.items()}
            print("| %s | %.2f | %.2f | %.2f | %+.2f | %+.2f |" % (
                "as built %.3f" % lag0 if L == "clip" else "%.2f" % L, m["hc"], m["fc"], m["hc"] + m["fc"],
                m["hl"], m["fl"]))
        for pair, key, pk in (("hind (RH after LH)", "hind", "hp"), ("fore (LF after RF)", "fore", "fp")):
            v = own[key]
            per = statistics.median([p for p in own[pk] if not math.isnan(p)] or [float("nan")])
            if v:
                med = statistics.median(v)
                print("Policy %s: median %+.0f ms over %d touchdowns, |lag| median %.0f ms, tied %.2f; "
                      "own period %.0f ms, |lag| share %.3f." % (
                          pair, med, len(v), statistics.median(abs(x) for x in v),
                          sum(1 for x in v if abs(x) < 20) / len(v), 1000 * per,
                          statistics.median(abs(x) for x in v) / (1000 * per) if per == per else float("nan")))
            else:
                print("Policy %s: no paired touchdowns." % pair)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
