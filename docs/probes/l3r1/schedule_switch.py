"""ADR-822: a speed schedule switches between gait families, in the engine and the trainer alike.

usage: PYTHONPATH=training pixi run python docs/probes/l3r1/schedule_switch.py SWITCHED [BLENDED]

``SWITCHED`` is a task bundle whose ``tracking.schedule`` states ``switches_mm_s`` (l3r1:
leon III's U1 bundle, walk10 and trot23 blended, then a switch, then three gallops
blended); ``BLENDED`` optionally a bundle without switches (l3r1: B1's dog bundle), on
which the ADR-773 reading must be what it always was.

On ``SWITCHED`` it reads the reference over a sweep of commands (both signs, the clamped
ends, every stride's speed, and each switch less 1 mm/s, at it and 1 mm/s past it) and
of clock origins and turns, with the engine (``schedule_blend``, ``schedule_nearest``,
``tracking_turn``, ``tracking_values``) and the trainer (the same four in numpy). The two
must agree to 1e-6, a switched pair must read the slower stride's own table below its
switch and the faster one's from it up, never a blend, and a pair inside a family must
blend linearly as ADR-773 says. The start stride must be of the family in force.

Then the refusals: the same strides with no switch, and with the switch moved to a pair
that leaves a crossing inside a family, are refused ``schedule_footfall_order``; a switch
outside its strides' speeds, a wrong count and an all-``None`` list are refused, by the
engine (``check_schedule_order``) and by the script API (``_reference_switches``).
Prints one line per check and exits non-zero on the first failure.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
import cadex_assembly_api as API  # noqa: E402
import cadex_train as T  # noqa: E402

TOLERANCE = 1e-6


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def told_row(task: dict, command: float) -> np.ndarray:
    channels = T.goal_channels(task)
    row = np.zeros(len(channels), dtype=np.float64)
    row[channels.index(str(task["tracking"]["schedule"]["channel"]))] = command
    return row


def commands(schedule: dict) -> list[float]:
    speeds = [float(v) for v in schedule["speeds_mm_s"]]
    out = [0.0, speeds[0] - 500.0, speeds[-1] + 500.0, *speeds]
    for a, b in zip(speeds, speeds[1:]):
        out += [a + 0.25 * (b - a), 0.5 * (a + b), a + 0.75 * (b - a)]
    for switch in schedule.get("switches_mm_s") or []:
        if switch is not None:
            out += [switch - 1.0, switch, switch + 1.0]
    return sorted(set(out + [-v for v in out]))


def agreement(task: dict, name: str) -> None:
    """Engine and trainer read the schedule the same way at every command and phase."""

    schedule = task["tracking"]["schedule"]
    channel = str(schedule["channel"])
    names = [str(c) for c in task["tracking"]["channels"]]
    rows = int(task["tracking"]["samples"])
    worst = 0.0
    picks = []
    for command in commands(schedule):
        told = told_row(task, command)
        index, weight = D.schedule_blend(schedule, command)
        t_index, t_weight = T.schedule_blend(np, task, told)
        if int(t_index) != index or abs(float(t_weight) - weight) > TOLERANCE:
            check(False, f"{name}: blend at {command:g} mm/s, engine ({index}, {weight}) "
                         f"trainer ({int(t_index)}, {float(t_weight)})")
        nearest = D.schedule_nearest(schedule, command)
        if int(T.schedule_nearest(np, task, told)) != nearest:
            check(False, f"{name}: start stride at {command:g} mm/s differs")
        picks.append((command, index, weight, nearest))
        turn = D.tracking_turn(task["tracking"], {channel: command})
        worst = max(worst, abs(float(T.tracking_turn(np, task, told)) - turn))
        for origin in (0, 7, rows + 3, 3 * rows + 25):
            for turned in (0.0, 0.31, 1.77, 4.5):
                engine = D.tracking_values(task, 0, origin, turned, {channel: command})
                trainer = T.tracking_vector(np, task, np.asarray(0), np.asarray(origin),
                                            np.asarray(turned), told)
                worst = max(worst, max(abs(engine[n] - float(trainer[i]))
                                       for i, n in enumerate(names)))
    check(worst <= TOLERANCE, f"{name}: engine and trainer agree on the clock turn and all "
                              f"{len(names)} tracking channels at {len(picks)} commands x 16 "
                              f"phases (worst {worst:.2e})")
    return picks


def main() -> None:
    switched = json.loads(Path(sys.argv[1]).read_text())
    schedule = switched["tracking"]["schedule"]
    speeds = [float(v) for v in schedule["speeds_mm_s"]]
    switches = schedule.get("switches_mm_s")
    check(bool(switches) and len(switches) == len(speeds) - 1,
          f"switched bundle states {switches} over strides {schedule['labels']}")
    check(schedule["rule"] == D.SCHEDULE_RULE + D.SCHEDULE_SWITCH_RULE,
          "its rule is ADR-773's with ADR-822's clause")
    picks = agreement(switched, "switched")

    for command, index, weight, nearest in picks:
        v = min(max(abs(command), speeds[0]), speeds[-1])
        switch = switches[index]
        if switch is not None:
            want = 0.0 if v < switch else 1.0
            if weight != want or nearest != index + int(want):
                check(False, f"at {command:g} mm/s across switch {switch:g}: weight {weight}, "
                             f"start stride {nearest}")
        else:
            want = (v - speeds[index]) / (speeds[index + 1] - speeds[index])
            if abs(weight - want) > 1e-12:
                check(False, f"at {command:g} mm/s inside a family: weight {weight} not {want}")
    check(True, "across each switch the weight is 0 below it and 1 from it up, the start "
                "stride is that family's; inside a family it is ADR-773's linear blend")

    channel = str(schedule["channel"])
    names = [str(c) for c in switched["tracking"]["channels"]][2:]
    tables = schedule["tables"]
    for index, switch in enumerate(switches):
        if switch is None:
            continue
        for command, stride in ((switch - 1.0, index), (switch, index + 1)):
            values = D.tracking_values(switched, 0, 0, 0.0, {channel: command})
            own = [float(v) for v in tables[stride][0]]
            held = switched["tracking"]["held"]
            want = [(1.0 if v >= 0.5 else 0.0) if h else v for v, h in zip(own, held)]
            check(all(abs(values[n] - w) <= 1e-12 for n, w in zip(names, want)),
                  f"at {command:g} mm/s the reference is {schedule['labels'][stride]}'s own row")

    clips = switched["reference_schedule"]
    found = next(i for i, s in enumerate(switches) if s is not None)
    # The switch moved to the pair before, so the pair it separated must blend.
    early = [None] * len(switches)
    early[found - 1] = 0.5 * (speeds[found - 1] + speeds[found])
    for label, bad in (("no switch", None),
                       (f"the switch moved to pair {found - 1}", early if found else None)):
        try:
            D.check_schedule_order(clips, bad, context="probe")
            check(False, f"{label}: refused schedule_footfall_order")
        except D.DynamicsError as error:
            check(error.reason == "schedule_footfall_order", f"{label}: refused {error.reason}")
    for label, bad, reason in (
            ("a switch at the slower stride's speed",
             [speeds[found] if i == found else s for i, s in enumerate(switches)],
             "schedule_switch_outside_strides"),
            ("a switch past the faster stride's speed",
             [speeds[found + 1] + 1.0 if i == found else s for i, s in enumerate(switches)],
             "schedule_switch_outside_strides"),
            ("one switch too few", switches[:-1], "schedule_switches_count"),
            ("every entry None", [None] * len(switches), "schedule_switches_empty")):
        try:
            D.check_schedule_order(clips, bad, context="probe")
            check(False, f"engine: {label} refused {reason}")
        except D.DynamicsError as error:
            check(error.reason == reason, f"engine: {label} refused {error.reason}")
        try:
            API._reference_switches("task", bad, speeds)
            check(False, f"script API: {label} refused")
        except Exception as error:  # noqa: BLE001 - the API's own error type
            check("reference_switches" in str(error), f"script API: {label} refused: {error}")
    check(API._reference_switches("task", switches, speeds) == switches,
          "script API: the bundle's switches are accepted as stated")

    unswitched = copy.deepcopy(switched)
    del unswitched["tracking"]["schedule"]["switches_mm_s"]
    rows = agreement(unswitched, "switched bundle with its switches removed")
    check(all(abs(w - (min(max(abs(c), speeds[0]), speeds[-1]) - speeds[i])
                  / (speeds[i + 1] - speeds[i])) <= 1e-12 for c, i, w, _ in rows),
          "without switches every pair blends linearly (ADR-773)")

    if len(sys.argv) > 2:
        blended = json.loads(Path(sys.argv[2]).read_text())
        check("switches_mm_s" not in blended["tracking"]["schedule"]
              and blended["tracking"]["schedule"]["rule"] == D.SCHEDULE_RULE,
              "blended bundle states no switch and ADR-773's rule unchanged")
        agreement(blended, "blended")


if __name__ == "__main__":
    main()
