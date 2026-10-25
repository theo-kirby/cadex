"""ADR-825: a student distilled by command band, against real teachers.

usage: PYTHONPATH=training python docs/probes/l3r1/distill.py BUNDLE LOW:HIGH:POLICY...

l3r1 runs it with leon III's U1 bundle and two teachers: the stand specialist at
0-250 mm/s and the gallop policy at 2000-4500 mm/s. Checks, one line each:

- the teachers fit the bundle (``check_teachers``: same model, actor channels and
  action table; bands apart and inside the goal's range);
- each teacher, read by ``load_teacher`` and played by ``teacher_actions``, gives back
  the actions its own container recorded for its witness observations (the engine's
  witness test: tanh of the location times the action box's scale plus its bias), to
  the engine's relative tolerance;
- on one teacher's witness observations with the goal rewritten into each band, every
  step is taught by the teacher whose band holds it, and a step in no band is not
  taught;
- ``distillation_loss`` reads 0 when the student is a teacher, on that teacher's band.

Exits non-zero on the first failure.
"""

from __future__ import annotations

import sys

import numpy as np

import cadex_train as T


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        raise SystemExit(1)


def main(argv: list[str]) -> int:
    import jax.numpy as jnp

    bundle = T.load_bundle(argv[1], T.globals_for(jnp))
    teachers = [T.load_teacher(np, *T.parse_teacher(spec)) for spec in argv[2:]]
    index = T.check_teachers(teachers, bundle, "cmd")
    check(index == T.actor_channels(bundle["task"]).index("cmd"),
          f"{len(teachers)} teachers fit {bundle['task'].get('label')}; cmd is actor "
          f"channel {index}")

    for teacher in teachers:
        header = teacher["header"]
        network = header["network"]
        observation = np.asarray(header["evaluation"]["observations"], dtype=np.float32)
        recorded = np.asarray(header["evaluation"]["actions"], dtype=np.float64)
        whole = [{**teacher, "low": 0.0, "high": 4500.0}]
        target, mask = T.teacher_actions(np, whole, observation, index)
        played = (target.astype(np.float64) * np.asarray(network["output_scale"])
                  + np.asarray(network["output_bias"]))
        ranges = np.asarray([float(a["high"]) - float(a["low"]) for a in header["actions"]])
        worst = float(np.max(np.abs(played - recorded) / ranges))
        check(mask.all() and worst < T.POLICY_WITNESS_TOLERANCE,
              f"{teacher['name']} ({teacher['sha256'][:8]}) replays its "
              f"{len(observation)} witness actions to {worst:.2e} "
              f"(tolerance {T.POLICY_WITNESS_TOLERANCE:g})")

    base = np.asarray(teachers[-1]["header"]["evaluation"]["observations"][:8],
                      dtype=np.float32)
    goals = [t["low"] for t in teachers] + [t["high"] - 1.0 for t in teachers]
    gaps = [g for g in np.linspace(0.0, 4500.0, 46)
            if not any(t["low"] <= g < t["high"] or g == t["high"] == 4500.0
                       for t in teachers)]
    for goal in goals + gaps[:4]:
        observation = base.copy()
        observation[:, index] = goal
        target, mask = T.teacher_actions(np, teachers, observation, index)
        owner = [t for t in teachers if t["low"] <= goal < t["high"]]
        if owner:
            own, _ = T.teacher_actions(np, [{**owner[0], "low": 0.0, "high": 4500.0}],
                                       observation, index)
            check(mask.all() and np.array_equal(target, own),
                  f"cmd {goal:g} is taught by {owner[0]['name']}")
            location = np.arctanh(np.clip(own, -1 + 1e-7, 1 - 1e-7))
            loss = float(T.distillation_loss(np, location, target, mask))
            check(loss < 1e-10, f"cmd {goal:g}: the teacher as student scores {loss:.1e}")
        else:
            check(not mask.any() and not target.any(), f"cmd {goal:g} has no teacher")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
