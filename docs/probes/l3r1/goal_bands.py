"""ADR-824: a goal drawn by weighted bands, in the script API, the engine and the trainer alike.

usage: PYTHONPATH=training pixi run python docs/probes/l3r1/goal_bands.py

A speed goal ``between=[0, 4500]`` with ``bands=[[0, 2500, 0.11], [2500, 4500, 0.89]]``
(l3r1: leon III's U1 command, about 0.89 of episodes in the gallops' band) goes from
``api.goal`` through the worker's ``_goal_input`` to the engine's ``_goal_records``, and
must arrive with its bands intact. Held for the episode and resampled every 150 steps,
the engine (``draw_episode_goals``) and the trainer (``draw_goals``) must draw the same
numbers from the same seed, and the trainer's ``goal_pool`` the same as the engine's
stream; 20,000 held episodes must put 0.89 +- 0.01 of their commands in 2500-4500 and be
uniform inside each band. A goal without bands must draw exactly what ``uniform(low,
high)`` draws, so every earlier bundle trains on the numbers it always did.

Then the refusals: bands that leave a gap, overlap, miss an end, weigh 0, are empty or
are on a phase or a waypoint goal are refused by the engine (``goal_bands_malformed``)
and by the script API. Prints one line per check and exits non-zero on the first
failure.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
import cadex_assembly_api as API  # noqa: E402
import cadex_assembly_worker as W  # noqa: E402
import cadex_train as T  # noqa: E402
import mujoco  # noqa: E402

BANDS = [[0.0, 2500.0, 0.11], [2500.0, 4500.0, 0.89]]
SCHEDULE = {"control_interval_s": 0.02, "max_steps": 600}


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def api() -> API.AssemblyDomainAPI:
    return object.__new__(API.AssemblyDomainAPI)


def records(**goal) -> list[dict]:
    entry = W._goal_input(api().goal("cmd", kind="speed", between=[0.0, 4500.0], **goal), {})
    return D._goal_records(None, None, [entry], {"bodies": []}, SCHEDULE,
                           actions=[], taken=[], context="probe")


def refused_by_engine(bands, kind: str = "speed", low: float = 0.0, high: float = 4500.0) -> bool:
    entry = {"name": "cmd", "kind": kind, "low": low, "high": high, "bands": bands,
             "period_seconds": 1.0, "bearing_deg": 0.0}
    try:
        D._goal_records(None, None, [entry], {"bodies": []}, SCHEDULE,
                        actions=[], taken=[], context="probe")
    except D.DynamicsError as error:
        return error.reason == "goal_bands_malformed"
    return False


def refused_by_api(bands, kind: str = "speed") -> bool:
    between = None if kind == "phase" else [100.0 if kind == "waypoint" else 0.0, 4500.0]
    try:
        api().goal("cmd", kind=kind, between=between, bands=bands,
                   **({"period_seconds": 1.0} if kind == "phase" else {}))
    except Exception as error:  # the API's own error type, whatever its class
        return "bands" in str(error)
    return False


def main() -> None:
    (held,) = records(bands=BANDS)
    check(held["bands"] == BANDS and held["low"] == 0.0 and held["high"] == 4500.0
          and held["segments"] == 1, f"api -> worker -> engine keeps the bands: {held['bands']}")
    (resampled,) = records(bands=BANDS, resample_seconds=3.0)
    check(resampled["segments"] == 4, "resampled every 150 steps: 4 segments, each banded")
    (plain,) = records()
    check("bands" not in plain, "a goal without bands records none")

    for entry, name in ((held, "held"), (resampled, "resampled")):
        task = {"goal": [entry], "episode": {}}
        for seed in range(200):
            engine = D.draw_episode_goals(None, None, task, random.Random(seed))
            trainer = T.draw_goals(None, None, task, random.Random(seed))
            if engine != trainer:
                check(False, f"{name}: engine and trainer differ at seed {seed}")
        check(True, f"{name}: engine and trainer draw the same numbers at 200 seeds")
        (pool,) = T.goal_pool(mujoco, b"<mujoco/>", task, base_seed=7, count=500)
        rng = random.Random(7)
        want = [D.draw_episode_goals(None, None, task, rng)[0]["segments"] for _ in range(500)]
        check(want == pool, f"{name}: the trainer's goal_pool (500 episodes) is the engine's stream")

    rng = random.Random(0)
    values = [D.draw_episode_goals(None, None, {"goal": [held]}, rng)[0]["segments"][0][0]
              for _ in range(20000)]
    fast = sum(v >= 2500.0 for v in values) / len(values)
    check(abs(fast - 0.89) < 0.01, f"share of 20,000 held commands at 2500-4500: {fast:.4f}")
    slow = [v for v in values if v < 2500.0]
    fast_v = [v for v in values if v >= 2500.0]
    check(min(values) >= 0.0 and max(values) <= 4500.0, "every command inside between")
    halves = (sum(v < 1250.0 for v in slow) / len(slow), sum(v < 3500.0 for v in fast_v) / len(fast_v))
    check(all(abs(h - 0.5) < 0.03 for h in halves),
          f"uniform inside each band: lower half {halves[0]:.3f} and {halves[1]:.3f}")

    rng, raw = random.Random(3), random.Random(3)
    drawn = [D.draw_episode_goals(None, None, {"goal": [plain]}, rng)[0]["segments"][0][0]
             for _ in range(100)]
    check(drawn == [raw.uniform(0.0, 4500.0) for _ in range(100)],
          "a goal without bands draws uniform(low, high), number for number")

    bad = {
        "gap": [[0.0, 2000.0, 1.0], [2500.0, 4500.0, 1.0]],
        "overlap": [[0.0, 3000.0, 1.0], [2500.0, 4500.0, 1.0]],
        "short of high": [[0.0, 2500.0, 1.0], [2500.0, 4000.0, 1.0]],
        "past low": [[100.0, 4500.0, 1.0]],
        "zero weight": [[0.0, 2500.0, 0.0], [2500.0, 4500.0, 1.0]],
        "empty band": [[0.0, 0.0, 1.0], [0.0, 4500.0, 1.0]],
        "no bands": [],
        "two numbers": [[0.0, 4500.0]],
    }
    for what, bands in bad.items():
        check(refused_by_engine(bands), f"engine refuses {what}: goal_bands_malformed")
        check(refused_by_api(bands), f"script API refuses {what}")
    for kind in ("phase", "waypoint"):
        check(refused_by_engine(BANDS, kind, 100.0), f"engine refuses bands on a {kind}: goal_bands_malformed")
        check(refused_by_api(BANDS, kind), f"script API refuses bands on a {kind}")
    check(D.GOAL_BAND_ALGORITHM.startswith("; on a goal with bands"),
          "GOAL_BAND_ALGORITHM is a clause appended to GOAL_ALGORITHM")


if __name__ == "__main__":
    main()
