# SPDX-License-Identifier: LGPL-2.1-or-later

"""One trace, one digest -- and a way to compute it in a fresh interpreter.

Determinism *within* one process is what M2 proved. What M3 has to prove is
that the same script produces the same bytes in a process that has never
seen the first one, because that is the claim a project digest would rest
on: two people open the same project on two machines and the trace they get
is the same trace.

So this is importable *and* runnable. As a module it gives the digest
function; as a script it builds a named fixture, simulates it, and prints
one line, which is what lets a test compare two interpreters rather than
two loop iterations. The pure module imports no FreeCAD, so the subprocess
needs no stubs, no kernel and no build -- it needs ``src/Mod/cadex`` and
this directory on ``sys.path`` and nothing else.

Floats are serialised with ``repr``, which round-trips exactly in Python 3,
so a digest difference is a *number* difference and never a formatting one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
for _path in (str(_HERE.parent), str(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import CadexDynamics as dyn  # noqa: E402
import dynamics_fixtures as fx  # noqa: E402

#: The fixtures a subprocess can be asked for by name. Deliberately a
#: closed set: the point is that both sides of the comparison ran the same
#: thing, and a name is checkable where an arbitrary expression is not.
FIXTURES = {
    "pendulum": fx.pendulum,
    "four_bar": fx.four_bar,
}


def trace_digest(frames: Sequence[Mapping[str, Any]]) -> str:
    """A trace's frames, hashed exactly as written."""

    return hashlib.sha256(
        json.dumps(
            list(frames), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def run_fixture(
    name: str, *, end_time_s: float = 0.5, frames_per_second: int = 60
) -> dict[str, Any]:
    """Simulate one named fixture and return its trace and digest."""

    components, joints, _placements = FIXTURES[name]()
    run = dyn.simulate(
        components,
        joints,
        start_time_s=0.0,
        end_time_s=end_time_s,
        frames_per_second=frames_per_second,
    )
    return {
        "fixture": name,
        "digest": trace_digest(run["frames"]),
        "frame_count": len(run["frames"]),
        "solver_step_s": float(run["solver_step_s"]),
        "worst_closure_residual_mm": float(run["worst_closure_residual_mm"]),
        "disableflags": int(run["evidence"]["solver_disableflags"]),
        "enableflags": int(run["evidence"]["solver_enableflags"]),
    }


def main(argv: Sequence[str]) -> int:
    name = argv[1] if len(argv) > 1 else "four_bar"
    if name not in FIXTURES:
        print(f"unknown fixture {name!r}", file=sys.stderr)
        return 2
    end_time = float(argv[2]) if len(argv) > 2 else 0.5
    print(json.dumps(run_fixture(name, end_time_s=end_time), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
