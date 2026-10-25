"""ADR-823: an episode commanded to stand (a command of 0) is measured, its speed ratios None.

usage: pixi run python docs/probes/l3r1/stand_command.py [EVALUATION_DIR]

``gait_metrics`` divided the measured speeds by the command, so an evaluation at a held
command of 0 (U1's stand) failed with a division by zero and wrote nothing. Here the
base series and each foot's gait are stubbed (a base drifting 100 mm/s forward and
20 mm/s sideways, every foot planted), and ``gait_metrics`` is read at commands None,
0, 0.0, 1000 and -500. At None and 0 the speeds must be measured and both ratios None;
at 1000 and -500 the ratios must be the speeds over the command, as before.

``EVALUATION_DIR``, optional, is a real evaluation judged at command 0 (l3r1:
``evaluations/u1s-dog-50-0``): every seed must carry measured speeds and a ``None``
``speed_ratio``. Prints one line per check and exits non-zero on the first failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexEvaluation as E  # noqa: E402

ALONG, ACROSS = 100.0, 20.0


def check(ok: bool, text: str) -> None:
    print(("ok   " if ok else "FAIL ") + text, flush=True)
    if not ok:
        raise SystemExit(1)


def stub() -> None:
    times = [i * 0.02 for i in range(300)]

    def base_series(samples, rig, **_):
        return {"time": times, "point": [(ALONG * t, ACROSS * t) for t in times],
                "tilt": [0.0] * len(times), "heading": [0.0] * len(times),
                "forward": [(1.0, 0.0)] * len(times),
                "velocity": [(ALONG, ACROSS)] * len(times), "dt": 0.02}

    class Foot(dict):
        """A planted foot: no steps, duty 1, every other figure unmeasured."""

        def __missing__(self, key):
            return None

    def gait(*_, **__):
        return Foot(steps=0, duty_factor=1.0)

    E.base_series, E.gait = base_series, gait
    E.posture = lambda base, com: {}


def main() -> None:
    stub()
    rig = {"hip_height_mm": 366.0, "com_height_mm": 300.0, "floor_mm": 0.0,
           "feet": {name: () for name in ("LF", "RF", "LH", "RH")}}
    for command in (None, 0, 0.0):
        read = E.gait_metrics([], rig, command)
        check(read["speed_ratio"] is None and read["lateral_ratio"] is None,
              f"command {command!r}: speed_ratio and lateral_ratio are None")
        check(abs(read["mean_forward_speed_mm_s"] - ALONG) < 1e-9
              and abs(read["mean_lateral_speed_mm_s"] - ACROSS) < 1e-9,
              f"command {command!r}: the speeds are still measured")
    for command in (1000.0, -500.0):
        read = E.gait_metrics([], rig, command)
        check(abs(read["speed_ratio"] - ALONG / command) < 1e-12
              and abs(read["lateral_ratio"] - ACROSS / command) < 1e-12,
              f"command {command!r}: ratios are speed / command, as before")
    if len(sys.argv) > 1:
        report = json.loads((Path(sys.argv[1]) / "evaluation.json").read_text())
        check(report["judged_command_mm_s"] == 0, f"{sys.argv[1]} was judged at command 0")
        for row in report["seeds"]:
            m = row["metrics"]
            check(m["speed_ratio"] is None and m["mean_forward_speed_mm_s"] is not None,
                  f"seed {row['seed']}: speed measured "
                  f"({m['mean_forward_speed_mm_s']:.1f} mm/s), speed_ratio None")


if __name__ == "__main__":
    main()
