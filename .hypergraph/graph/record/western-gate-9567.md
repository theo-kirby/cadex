---
node_id: 3f5ebbf6-ac06-560d-b0ef-c205bda8c7cd
slug: western-gate-9567
title: Both documented lifecycle example walks reproduce on this machine
created_at: '2026-09-08T17:36:26+00:00'
parents:
- sleepy-hollow-9498
summary: ''
---
## What

Ran both repository-owned lifecycle examples — the hinged arm (revolute, torque
motor) and the vertical linear carriage (prismatic, force motor) — through the
**documented** headless entry point in `examples/lifecycle/README.md` on this
machine, unchanged and with no mechanism-specific option. Then landed the two
defects the run exposed: a reproduction command that could not run here, and
two example projects that did not keep the domain note their own review asks
for. Commit `f152798a`; ADR-257 and a ROADMAP bullet.

## Why

The overseer's iteration-19 steer named this unit: run the linear carriage
through the same documented headless entry point, end to end, no
mechanism-specific code change, comparable `PROGRESS.md` rows, bounded CPU
training, nothing generated committed. Criterion: **The walk holds on a second
mechanism** (`swift-dusk-2951`), mission 2.

The criterion's state node already records a prompt-walk pair on this machine
(`rare-cliff-9595`, `mellow-quartz-8093`), so a re-roll of that would be
re-evidence. What had *not* been done here is the repository's own documented
example path — the commands a reader is told to run — which was last measured on
a different machine on 2026-09-06, before the ADR-256 documentation eye existed.
Running that is the same unit and is new evidence: it tests the entry point *as
documented*, on the machine of record, costs no model call and no network, and
finishes in 13–15 s per mechanism. Assumption written here rather than asked:
reproducing the documented path serves the overseer's instruction better than
re-rolling an already-recorded prompt walk.

Question-policy call: the reproduced projects have no domain notes because
`script --set` installs the recipe alone. The reversible fix is a documented
convention, not a CLI change that would copy sibling files into a project — and
a CLI change was barred by the standing order against review-surface polish.

## Method

Fresh `build/lifecycle/<name>` projects (gitignored) per walk. Each: `./cadex
script --project P --set examples/lifecycle/<name>/script.py --json`, then
`JAX_PLATFORMS=cpu ./cadex walk --project P --out P/runs/baseline --iterations 1
--envs 4 --seed 0 --timeout 600 --json`, at the documented toy scale. A parent
watchdog sampled summed descendant RSS every 0.2 s and would have killed above
2.9 GB or 850 s; the trainer separately had `--timeout 600`. Neither fired.

Three walks: arm and carriage each with `--trainer-python "$TRAINER_PYTHON"`,
where `$TRAINER_PYTHON` is this machine's trainer venv interpreter (the
home-directory `cadex-train-venv`, the last entry in the CLI's discovery order);
then a third carriage walk written exactly as the corrected README block — no
`--trainer-python` at all — to verify that the discovery order resolves the same
interpreter on its own. So the two measured rows were produced with the
interpreter configured explicitly, and the flagless documented form is evidenced
by the third walk alone. Read each
run's `review.json`, the exported `train/<name>-model.xml` `<actuator>` and
`<sensor>` sections, and both example scripts, so the notes state what the model
declares rather than what the prose assumed.

## Result

All three walks exit 0. No code change of any kind was needed to run either
mechanism; the diff is documentation and example-project files only.

| Mechanism | rollout `total_reward` | trainer reward/step | `walk_seconds` | wall s | peak tree RSS | witness err |
|---|---:|---:|---:|---:|---:|---:|
| hinged-arm | -27.109384220904474 | -0.3801981508731842 | 14.40 | 14.61 | 1,539,432,448 | 2.069844824703626e-09 |
| linear-carriage | -24159.195371510654 | -82.31990814208984 | 13.10 | 13.18 | 1,467,621,376 | 3.736925650865697e-09 |

Legs: arm train 11.38 s / declare 0.75 / rollout 0.93; carriage 10.08 / 0.75 /
0.88 — all exit 0. Clearance: arm 1 offending pair of 1 checked, carriage 0 of 1,
bounds check pass on both. Inventory: 2 components, 0 catalogued, on both.

**Reproduction is exact where the seed fixes it and not where it does not.**
Trainer reward/step is bit-identical to the 2026-09-06 rows on the first
machine; the rollout totals agree to 1e-11 (arm) and 1.5e-05 (carriage) and the
stored policy digests differ (`186faa6e7aad`, `bcf9617aba52`), because the two
JAX builds sum the gradient update in a different order while the first
exploratory batch is fixed by the seed. Task sha256 is unchanged on both
(`c4315071`, `d71677f3`), so the same objective was scored. Peak RSS is ~1.5×
the first machine's at the same wall time. Both `PROGRESS.md` files gained a
two-column comparison; the earlier machine's numbers are not withdrawn.

**Two defects found and fixed.** (1) The README's command hard-coded
`--trainer-python "$PWD/.venv/bin/python"`, which does not exist on this machine
— it is now flagless, relying on the documented discovery order, verified by the
third walk. (2) The ADR-256 documentation eye reported `0 domain note(s) for 2
declared subject(s); no note for actuators, sensors` for both reproduced
projects. Correct for a recipe walk, which runs no design turn, and the README
now says so — but the example *directories* carried only `docs/sensors.md`, so
the convention their own review declares was half kept. Both gain
`docs/actuators.md` written from the exported MJCF (`j/motor`, `forcerange
-0.4 0.4` = 400 N·mm on the arm, `-4 4` = 4 N on the carriage) and naming what
is assumed rather than selected: no damping, friction, gearing or end stops, no
manufacturer part, and the N·mm-versus-N effort difference that is why the two
control-cost terms do not compare.

`JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q`: **227 passed in
201.50 s**, 0 skipped, exit 0 — unchanged from the last recorded count, as
expected for a docs-only diff. `git diff --check` exit 0. No engine build,
engine suite, packaged gate or `shell/` gate was run, and none was implicated.
Nothing generated is committed: the three project trees live under gitignored
`build/lifecycle/`.

**Still missing before the criterion ticks:** nothing in the walk itself, on the
evidence here — the same entry point took two mechanisms with different joint and
actuator types end to end, twice over, on two machines. What the criterion's
state node still qualifies is control quality, not pipeline coverage: one PPO
iteration is a smoke test, and the carriage still falls to z = -4699 mm at 1 s on
an ideal unlimited guide. The human owns the charter checkbox.

Dispatch closed: 1 unit — both documented lifecycle example walks reproduced on this machine (exit 0, comparable PROGRESS rows), the dead `--trainer-python` path in the reproduction command replaced by the CLI's discovery order, and the `docs/actuators.md` the ADR-256 review asks for written for both examples; cli/tests 227 passed, 0 skipped.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: f152798af126f6e8203704f9b7348ab3a702e596

## State Impact

- target: swift-dusk-2951 — the repository's documented example entry point, not just the prompt walk, takes both mechanisms end to end on this machine: exit 0, trainer means bit-identical to the first machine, rollout totals differing only by JAX summation order, comparable two-column PROGRESS rows
- target: crisp-reef-5607 — the documented reproduction command was unrunnable as written (dead --trainer-python path); it is now flagless and verified against the CLI's documented venv discovery order
- target: calm-peak-5247 — the walk's ADR-256 documentation eye correctly reports both subjects missing for a recipe walk, which runs no design turn; the README says so and both example projects now keep docs/actuators.md
