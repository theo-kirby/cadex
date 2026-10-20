"""How a hind heel leaves the floor before toe-off (orun12 P1, O2a).

usage: python3 docs/probes/orun12/toeoff.py MODEL_XML EVALUATION_DIR [EVALUATION_DIR ...]

MODEL_XML is the run's compiled ``train/cat_model-model.xml``; each
EVALUATION_DIR holds ``docs/probes/orun11/judge.py``'s ``seed-*-trace.json``
and ``evaluation.json``.

``hock_at_toeoff`` (``CadexEvaluation.heel_metrics``) passes a toe-off --
the last settled stance frame before the paw lifts -- when the heel is down
in some stance frame of its last ``HEEL_TOEOFF_S`` (40 ms, three 20 ms
frames). This reads each toe-off the engine counts, per hind leg, and
prints:

- the toe-offs, and the share that pass (checked against the engine's
  ``heel_down_at_toeoff_share`` per seed: ``engine``);
- of the failing ones, the **lead**: ms from the heel's last down frame in
  that stance to the toe-off frame, as a histogram, and how many never had
  the heel down in that stance at all;
- the stance length (ms) of passing and failing stances (medians);
- the metatarsus pitch (deg, ``stance_pose.pose``) at the toe-off frame,
  and the hock drive's angle there (deg, the right leg folded onto the
  left's), for passing and failing toe-offs (medians);
- the heel's height (mm) at the toe-off frame of a failing toe-off (median).

Standard library only, plus the engine's ``CadexEvaluation`` helpers and
``stance_pose.py``'s model reader, as ``stance_pose.py`` uses them.
"""

from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stance_pose as S  # noqa: E402

E = S.E
LEGS = S.LEGS


def toeoffs(samples, sole, heel):
    """(stance start, toe-off frame, last heel-down frame or None) per settled toe-off, as the engine counts them."""

    times = [t for t, _ in samples]
    stance = [h <= E.STANCE_MM for h in sole]
    down = [h <= E.STANCE_MM for h in heel]
    out = []
    for e in range(len(stance) - 1):
        if not (stance[e] and not stance[e + 1]) or times[e] < E.SETTLE_S - 1e-9:
            continue
        s = e
        while s > 0 and stance[s - 1]:
            s -= 1
        last = next((j for j in range(e, s - 1, -1) if down[j]), None)
        out.append((s, e, last))
    return out


def med(values):
    return statistics.median(values) if values else float("nan")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    paws, pins = S.model(Path(argv[0]))
    window_ms = 1000 * E.HEEL_TOEOFF_S
    for out in map(Path, argv[1:]):
        evaluation = json.loads((out / "evaluation.json").read_text())
        heels = evaluation["rig"]["heels"]
        floor = evaluation["rig"]["floor_mm"]
        engine = {s["seed"]: s["detail"]["heels"] for s in evaluation["seeds"]}
        rows = {leg: {"n": 0, "pass": 0, "lead": collections.Counter(), "never": 0, "check": [],
                      "len": ([], []), "meta": ([], []), "hock": ([], []), "fail_heel": []}
                for leg, *_ in LEGS}
        for path in sorted(out.glob("seed-*-trace.json")):
            trace = json.loads(path.read_text())
            seed = int(path.name.split("-")[1])
            names = [c["joint"] if isinstance(c, dict) else c for c in trace["actuator_channels"]]
            frames = [f for f in trace["frames"] if f.get("joint_positions")]
            samples = [(f.get("nominal_time_s") or 0.0, f["component_placements"]) for f in frames]
            times = [t for t, _ in samples]
            for leg, side, foot, sign in LEGS:
                paw = "c_paw_" + foot
                sole = E.foot_series(samples, paw, paws[paw], floor)["height"]
                heel = E.foot_series(samples, heels[paw]["body"], heels[paw]["geoms"], floor)["height"]
                row = rows[leg]
                n = ok = 0
                for s, e, last in toeoffs(samples, sole, heel):
                    lead = None if last is None else round(1000 * (times[e] - times[last]))
                    passed = lead is not None and lead <= window_ms + 1e-6
                    n += 1
                    ok += passed
                    k = 0 if passed else 1
                    row["len"][k].append(1000 * (times[e] - times[s]))
                    row["meta"][k].append(S.pose(samples[e][1], side, foot, pins, paws[paw])["meta"])
                    row["hock"][k].append(sign * frames[e]["joint_positions"][names.index(f"j_hock_{side}")])
                    if not passed:
                        row["fail_heel"].append(heel[e])
                        if lead is None:
                            row["never"] += 1
                        else:
                            row["lead"][lead] += 1
                row["n"] += n
                row["pass"] += ok
                share = engine[seed][paw]["heel_down_at_toeoff_share"]
                row["check"].append(abs((ok / n if n else 0.0) - (share or 0.0)) < 1e-9)
        print(f"## {out.name}\n")
        print("| leg | toe-offs | pass | engine | fail lead ms (count) | never down | stance ms pass / fail "
              "| metatarsus deg at toe-off pass / fail | hock deg pass / fail | heel mm at failing toe-off |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for leg, *_ in LEGS:
            r = rows[leg]
            lead = ", ".join(f"{k} ({v})" for k, v in sorted(r["lead"].items()))
            print(f"| {leg} | {r['n']} | {r['pass'] / r['n']:.2f} | {'ok' if all(r['check']) else 'MISMATCH'} "
                  f"| {lead or '–'} | {r['never']} | {med(r['len'][0]):.0f} / {med(r['len'][1]):.0f} "
                  f"| {med(r['meta'][0]):.1f} / {med(r['meta'][1]):.1f} "
                  f"| {med(r['hock'][0]):.1f} / {med(r['hock'][1]):.1f} | {med(r['fail_heel']):.1f} |")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
