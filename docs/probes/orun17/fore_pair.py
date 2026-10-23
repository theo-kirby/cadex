"""orun17 RL (O3a, O8): the slow fore pair, in the clip and in judged traces.

usage: pixi run python docs/probes/orun17/fore_pair.py [--clip TASK_JSON] MODEL_XML EVALUATION_DIR [...]

Each EVALUATION_DIR is one ``sg_judge.py`` evaluation at a held command; its
``judged-task.json`` carries the ``gallop_sg`` schedule. The stride read is
the one the schedule's rule picks at that command when it sits on a stride's
speed (700 is stride 0); any other command is refused. Prints:

- **the clip:** each paw's contact row over the stride and its touchdown
  sample, and each pair's touchdown lag (ms) both ways round the stride;
- **per seed, from the engine's settle on** (``orun15/lag_term.py``'s clock
  and stance rule): each fore paw's touchdowns a clip stride (1.00 is one a
  stride; more is a tap or a double strike), its touchdown against the clip's own (ms,
  the median signed offset, positive late), the fore pair's touchdown lag
  (RF after LF, median), the share of fore touchdowns within 20 ms and 40 ms
  of each other, and the candidate ``fore_lag``
  ``|rlf - rrf| * (1 - |(clf - crf) - (rlf - rrf)|)`` per step with the
  clip's own score beside it;
- across seeds, ``fore_lag`` against the share within 40 ms (Pearson r).

``--clip TASK_JSON`` scores against another bundle's ``gallop_sg`` clip (its
schedule's stride at the same command) in place of the judged one: the
episode's start sample is still recovered from the judged task's reset rows
(the policy ran on that clock), and the two schedules must share the stride's
period and sample count. Beside ``fore_lag`` it then prints the fore half of
``track_contact`` (``(1 - |clf - rlf|) + (1 - |crf - rrf|)``, over 2) on that
clip, and the clip's own score of each. orun17 used it to price ``fore_lag``
on sgt-4's duty 0.35 slow stance before it is trained (``fore-lag-sgt4.md``).

Writes nothing.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "orun15"))

import lag_term as L  # noqa: E402
from lag_term import E, PAWS, mujoco  # noqa: E402


def wrap(x, period):
    return (x + period / 2) % period - period / 2


def main(argv):
    alt = None
    if argv[:1] == ["--clip"]:
        alt = json.loads(Path(argv[1]).read_text())["tracking"]
        argv = argv[2:]
    if len(argv) < 2:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    geoms = L.capsules(model)
    for arg in argv[1:]:
        out = Path(arg)
        ev = json.loads((out / "evaluation.json").read_text())
        task = json.loads((out / "judged-task.json").read_text())
        tracking = task["tracking"]
        sched = tracking["schedule"]
        cmd = float(ev["judged_command_mm_s"])
        if cmd not in sched["speeds_mm_s"]:
            print("%s: command %g is not a stride's speed %s" % (out.name, cmd, sched["speeds_mm_s"]))
            return 2
        k = sched["speeds_mm_s"].index(cmd)
        n = int(tracking["samples"])
        period = float(sched["periods_s"][k])
        dt = period / n
        stride = dict(tracking, table=sched["tables"][k], period_s=period,
                      reset_qpos=tracking["reset_qpos"][k * n:(k + 1) * n])
        clock = stride
        if alt is not None:
            asch = alt["schedule"]
            if (cmd not in asch["speeds_mm_s"] or int(alt["samples"]) != n
                    or abs(float(asch["periods_s"][asch["speeds_mm_s"].index(cmd)]) - period) > 1e-9):
                print("%s: --clip's stride at %g differs in period or samples" % (out.name, cmd))
                return 2
            ka = asch["speeds_mm_s"].index(cmd)
            stride = dict(alt, table=asch["tables"][ka], period_s=period,
                          reset_qpos=alt["reset_qpos"][ka * n:(ka + 1) * n])
        clip = {key: [L.ref_down(stride, s / n)[key] for s in range(n)] for key in PAWS}
        clip_td = {key: [s for s in range(n) if clip[key][s] and not clip[key][s - 1]][0] for key in PAWS}
        print("\n## %s (policy %s), %s\n" % (out.name, ev["policy_sha256"][:8], sched["labels"][k]))
        for key in ("lh", "lf", "rf", "rh"):
            print("    %s %s  touchdown sample %d" % (key.upper(), "".join("#" if v else "." for v in clip[key]),
                                                     clip_td[key]))
        for a, b in (("lf", "rf"), ("rh", "lh")):
            d = (clip_td[b] - clip_td[a]) % n
            print("- clip %s after %s: %.0f ms (the other way %.0f ms)" % (b.upper(), a.upper(), d * dt * 1000,
                                                                          (n - d) * dt * 1000))
        print("\n| seed | touchdowns a stride LF / RF | LF vs clip ms | RF vs clip ms | RF after LF ms "
              "| within 20 ms | within 40 ms | fore_lag | clip |")
        print("|---|---|---|---|---|---|---|---|---|")
        rows = []
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            joints = [c["joint"] for c in trace["actuator_channels"]]
            solver = [f for f in trace["frames"] if f.get("frame_kind") == "solver_output"]
            _, s0 = L.origin(model, clock, list(zip(joints, solver[0]["joint_positions"])))
            samples = [(f["nominal_time_s"], f["component_placements"]) for f in solver]
            times = [t for t, _ in samples]
            floor = ev["rig"]["floor_mm"]
            down = {key: [h <= E.STANCE_MM for h in E.foot_series(samples, body, geoms[body], floor)["height"]]
                    for key, body in PAWS.items()}
            score, clip_score, contact, clip_contact = [], [], [], []
            for i, t in enumerate(times):
                if t < E.SETTLE_S - 1e-9:
                    continue
                r = L.ref_down(stride, t / period + s0 / n)
                fr = r["lf"] - r["rf"]
                fc = (1.0 if down["lf"][i] else 0.0) - (1.0 if down["rf"][i] else 0.0)
                score.append(abs(fr) * (1 - abs(fc - fr)))
                clip_score.append(abs(fr))
                cl = 1.0 if down["lf"][i] else 0.0
                cr = 1.0 if down["rf"][i] else 0.0
                contact.append(((1 - abs(cl - r["lf"])) + (1 - abs(cr - r["rf"]))) / 2)
                clip_contact.append(1.0)
            tds = {key: [t for t in L.touchdowns(times, down[key]) if t >= E.SETTLE_S] for key in ("lf", "rf")}
            off = {}
            for key in ("lf", "rf"):
                # the clip's touchdown time nearest each policy touchdown
                ref_t = (clip_td[key] - s0) * dt
                off[key] = statistics.median([1000 * wrap(t - ref_t, period) for t in tds[key]]) if tds[key] else float("nan")
            lags = L.rh_after_lh(tds["lf"], tds["rf"], period)
            w20 = sum(1 for v in lags if abs(v) < 20) / len(lags) if lags else float("nan")
            w40 = sum(1 for v in lags if abs(v) < 40) / len(lags) if lags else float("nan")
            fl, cs = statistics.fmean(score), statistics.fmean(clip_score)
            rows.append((fl, w40, statistics.fmean(contact)))
            strides = (times[-1] - E.SETTLE_S) / period
            print("| %s | %.2f / %.2f | %+.0f | %+.0f | %+.0f | %.2f | %.2f | %+.3f | %.3f |" % (
                path.name.split("-")[1], len(tds["lf"]) / strides, len(tds["rf"]) / strides, off["lf"], off["rf"], statistics.median(lags) if lags else float("nan"),
                w20, w40, fl, cs))
        xs, ys = [r[0] for r in rows], [r[1] for r in rows]
        print("\nAll seeds: fore_lag %+.3f a step; within 40 ms %.2f." % (statistics.fmean(xs), statistics.fmean(ys)))
        if alt is not None:
            print("On the --clip stride: fore_lag %+.3f a step (clip %.3f); track_contact's fore half %.3f (clip 1)."
                  % (statistics.fmean(xs), cs, statistics.fmean(r[2] for r in rows)))
        if len(set(xs)) > 1 and len(set(ys)) > 1:
            print("Per seed, fore_lag against the share within 40 ms: r = %+.2f." % statistics.correlation(xs, ys))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
