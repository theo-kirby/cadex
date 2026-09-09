---
node_id: 0bfe8f9e-4e83-5682-a7e4-c7e0cb6e7688
slug: falling-willow-7995
title: The walk's mechanism-blindness is pinned by a test, and documented
created_at: '2026-09-08T18:14:36+00:00'
parents:
- square-bay-3436
summary: ''
---
## What

Turned the second-mechanism claim from narrative into something a critic can
check, in three parts, all in `cli/` and `docs/`:

- `cli/tests/test_walk.py::test_the_two_example_mechanisms_dispatch_the_identical_legs`
  — installs both repository-owned recipes, walks each through `command_walk`
  with identical flags against the existing fake `cadex`, and requires the
  child argv to be **equal** once the project path is substituted out.
- `cli/tests/test_walk.py::test_the_digest_edit_treats_both_example_mechanisms_alike`
  — `declare_policy`, the one leg that reads a script the walk did not write,
  rewrites the same two literals on both recipes and leaves every other byte
  alone.
- `examples/lifecycle/README.md` §"One entry point, and no branch that knows
  which mechanism" — names the entry point (`cadex walk` → `command_walk` in
  `cli/cadex_cli/__main__.py`, legs spawned as child commands by `run_leg`),
  names both regressions, and puts the two projects' comparable `PROGRESS.md`
  numbers side by side with the joint and actuator each uses.

ADR-260 and a ROADMAP bullet. No implementation changed.

## Why

The overseer's explicit instruction for this iteration: do the
second-mechanism evidencing before plan unit 2, because the frontier has been
unmoved for 16 iterations and only a criterion closing moves it. Target:
`swift-dusk-2951` — charter criterion "the walk holds on a second mechanism",
mission 2.

The criterion's first half — "no code change specific to the mechanism" — was
supported only by records saying no workaround was needed (`sage-peak-2689`,
`western-gate-9567`, and five prompt walks from the previous machine). That is
a statement about the past, not a property of the tree. The way it decays is
not a rewrite; it is one `if` on the joint kind, and nothing would have
noticed. Assumption taken without asking: the two real example recipes are the
right pair to test against, rather than a synthetic mechanism pair — they
differ where the claim needs them to (revolute/torque-N·mm against
slider/force-N) and are the same files the documented reproduction and the
real CPU walk already use, so a synthetic script would pin the test against
itself.

Rejected on the way: a lexical net over the dispatch's identifiers for
mechanism nouns. It would have had to exempt `swing`, which is the motion
block's own word for the rotation channel — an arbitrary guard whose first act
is an exemption is worse than no guard. The two behavioural tests replaced it.

## Method

Read `command_walk` and `walk.py` end to end to find where a mechanism-specific
path could live: the dispatch decides only which legs run and with which
flags, and the only place it opens a script it did not write is
`declare_policy`. Both are covered.

The first test reuses the existing `fake_cadex` argv-log fixture, slicing the
log per mechanism (the log does not exist before the first walk, so the offset
starts at 0). It asserts the four legs really ran — `train`, `script`,
`script`, `params` — so equality is not two empty lists agreeing.

Mutation check, to prove the test can fail: added
`if "slider" in (project/"script.py").read_text(): argv += ["--label",
"slider-rig"]` before the train leg. The test failed with both argv lists
printed. Restored `cli/cadex_cli/__main__.py` from a copy taken before the
mutation and confirmed `git diff --stat cli/cadex_cli/` empty before
continuing.

No engine, protocol, payload or `shell/` diff. No build. No model call, GUI or
remote dispatch. Both new tests are offline and need neither engine nor
trainer.

## Result

`JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`: **233 passed, 0
skipped, 202.58 s, exit 0** — the whole CLI suite including the real CPU walk
and iterate legs. `git diff --check` clean. Commit `9e888610`, four files,
+175/-1: the two tests, the README section, ADR-260, the ROADMAP bullet.

The side-by-side numbers the doc now carries, from the two `PROGRESS.md` files
unchanged (1 PPO iteration × 4 envs, training seed 0, rollout seed 3, 1 s at
50 Hz, CPU):

| Mechanism | Joint, actuator | `total_reward` | reward/step | trainer reward/step | walk s | peak RSS |
|---|---|---:|---:|---:|---:|---:|
| hinged-arm | revolute, torque motor (N·mm) | -27.1093842209 | -0.542187684419 | -0.380198150873 | 15.22 | 986,218,496 |
| linear-carriage | slider, force motor (N) | -24159.1953563 | -483.183907126 | -82.3199081421 | 13.52 | 979,582,976 |

**What is still missing before `swift-dusk-2951` ticks.** Both halves the
criterion literally names now hold and are checkable: the same entry point
(pinned by test, not by memory) and both projects carrying comparable
`PROGRESS.md` numbers. What the criterion's recorded *qualification* still
names is unchanged by this unit and is not something a test can supply —
control quality. The carriage's policy lets it fall to -4699 mm in one second
on an ideal unlimited guide, one PPO iteration is a smoke test of the loop, and
the two `total_reward` columns are different objectives in different units, so
they compare runs of one project and never rank the designs. The README section
says exactly this so a reader cannot take the new evidence for more than it is.
Judgement for the maintainer, not taken here: this unit closes the
"evidence a critic can check" gap the overseer named; whether the criterion
ticks depends on whether its working-level qualification is read as pipeline
coverage (met) or learned control (not met, and not this unit's target).

Dispatch closed: 1 unit — the walk's mechanism-blindness is pinned by two
offline regressions and documented with both projects' numbers side by side;
CLI suite 233 passed 0 skipped; ADR-260.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 9e888610f8958e2ea1eb2575de0036d270477e17

## State Impact

- target: swift-dusk-2951 — the criterion's 'no mechanism-specific code change' half is now a behavioural regression (two example recipes dispatch byte-identical child argv; the digest edit treats both alike), not a narrative claim; examples/lifecycle/README.md names the entry point, the regressions and both projects' comparable numbers side by side. Control quality remains the open qualification.
