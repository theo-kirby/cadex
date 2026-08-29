# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One exported model, one digest -- and a stock MuJoCo that never saw Cadex.

The sibling of :mod:`dynamics_trace_digest`, and it carries the same two
jobs in one file for the same reason: a claim about *bytes across processes*
cannot be proved by two iterations of one loop, and a claim about "loads in
stock MuJoCo" cannot be proved by a process that has Cadex on its path.

Two modes, and the difference between them is the whole point:

``digest <fixture>``
    Builds a named fixture, exports it, prints the XML's sha256 and its
    size. Needs ``src/Mod/cadex`` on ``sys.path``, which it adds itself --
    *inside the function*, never at module scope, because the other mode
    must not have it.

``load <path.xml> [steps]``
    Imports **only** ``mujoco``, reads the file off disk, resets to the
    ``solved`` keyframe, steps, and prints the resulting ``qpos`` and body
    positions. It also reports whether ``CadexDynamics`` was importable at
    all, so a test can assert the negative rather than trust the invocation:
    run with ``python -P`` and a scrubbed ``PYTHONPATH`` this is ``false``,
    and if it ever comes back ``true`` the subprocess was not stock and the
    result proves nothing.

Floats are serialised with ``repr``, which round-trips exactly in Python 3,
so a difference between two runs is a *number* difference and never a
formatting one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

#: The fixtures a subprocess can be asked for by name. A closed set for the
#: same reason ``dynamics_trace_digest`` keeps one: the point is that both
#: sides of a comparison ran the same thing, and a name is checkable where
#: an arbitrary expression is not.
FIXTURE_NAMES = ("pendulum", "two_link_arm", "four_bar")


def _with_cadex_on_path() -> tuple[Any, Any]:
    """Import the pure module and the fixtures, adding the paths here.

    Deliberately not at module scope: ``load`` mode's entire claim is that
    this interpreter cannot reach Cadex, and an import at the top of the
    file would make that false before ``main`` ever ran.
    """

    here = Path(__file__).resolve().parent
    for path in (str(here.parent), str(here)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import CadexDynamics as dyn
    import dynamics_fixtures as fx

    return dyn, fx


def export_fixture(name: str) -> dict[str, Any]:
    """Build one named fixture and export it, returning the digest."""

    dyn, fx = _with_cadex_on_path()
    if name not in FIXTURE_NAMES:
        raise SystemExit(f"unknown fixture {name!r}")
    components, joints, _placements = getattr(fx, name)()
    built = dyn.build_model(components, joints)
    exported = dyn.export_mjcf(built)
    xml = exported["xml"]
    evidence = exported["evidence"]
    return {
        "fixture": name,
        "digest": hashlib.sha256(xml).hexdigest(),
        "bytes": len(xml),
        "body_count": int(evidence["body_count"]),
        "joint_count": int(evidence["joint_count"]),
        "keyframe_count": int(evidence["keyframe_count"]),
        "worst_inertia_rel_error": repr(
            float(evidence["worst_inertia_rel_error"])
        ),
        "worst_mass_rel_error": repr(float(evidence["worst_mass_rel_error"])),
        "worst_pose_error_mm": repr(float(evidence["worst_pose_error_mm"])),
        "mujoco_version": str(evidence["mujoco_version"]),
    }


def stock_load(path: str, steps: int) -> dict[str, Any]:
    """Load one MJCF in an interpreter that has never heard of Cadex.

    ``mj_resetDataKeyframe`` to the ``solved`` key rather than ``mj_resetData``
    is the difference between the mechanism this file describes and the same
    mechanism folded up at ``qpos=0``: MuJoCo's reference configuration is
    the one where each joint's connector frames coincide, which is not the
    pose the assembly was solved at.
    """

    import mujoco

    try:
        import CadexDynamics  # noqa: F401
    except Exception:
        cadex_importable = False
    else:
        cadex_importable = True

    model = mujoco.MjModel.from_xml_string(Path(path).read_text(encoding="utf-8"))
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    if key >= 0:
        mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    start_xpos = [repr(float(value)) for value in data.xpos.ravel().tolist()]
    for _ in range(steps):
        mujoco.mj_step(model, data)
    return {
        "cadex_importable": cadex_importable,
        "mujoco_version": str(getattr(mujoco, "__version__", "unknown")),
        "keyframe_id": int(key),
        "nbody": int(model.nbody),
        "nq": int(model.nq),
        "nv": int(model.nv),
        "ngeom": int(model.ngeom),
        "neq": int(model.neq),
        "nu": int(model.nu),
        "nmesh": int(model.nmesh),
        "nkey": int(model.nkey),
        "body_mass": [repr(float(value)) for value in model.body_mass.tolist()],
        "body_inertia": [
            repr(float(value)) for value in model.body_inertia.ravel().tolist()
        ],
        "start_xpos": start_xpos,
        "steps": steps,
        "qpos": [repr(float(value)) for value in data.qpos.tolist()],
        "xpos": [repr(float(value)) for value in data.xpos.ravel().tolist()],
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print("usage: dynamics_mjcf_digest.py digest <fixture> | load <xml> [steps]",
              file=sys.stderr)
        return 2
    mode = argv[1]
    if mode == "digest":
        name = argv[2] if len(argv) > 2 else "four_bar"
        print(json.dumps(export_fixture(name), sort_keys=True))
        return 0
    if mode == "load":
        if len(argv) < 3:
            print("load needs a path", file=sys.stderr)
            return 2
        steps = int(argv[3]) if len(argv) > 3 else 500
        print(json.dumps(stock_load(argv[2], steps), sort_keys=True))
        return 0
    print(f"unknown mode {mode!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
