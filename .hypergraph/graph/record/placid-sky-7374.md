---
node_id: 6c9420ce-3871-56e9-a86c-090f5034e4e7
slug: placid-sky-7374
title: A second prompt walk, a second mechanism, clean end to end
created_at: '2026-09-07T21:29:33+00:00'
parents:
- rustic-loom-0992
summary: ''
---
## What

Ran a second, independent `cadex walk --prompt` on a fresh project, with a
different mechanism, a different prompt and a different seed from
`cool-fountain-2483`, and changed nothing in the repository. The unit is the
run; the tree is unchanged at `dfeccc9f`.

**It ran clean, all four legs exit 0.**

| leg | exit | seconds |
|---|---|---|
| design | 0 | 172.59 |
| train | 0 | 13.06 |
| declare (the digest edit) | 0 | 1.25 |
| rollout | 0 | 1.50 |

Whole walk: **189.4 s wall, 1.115 GB peak process-tree RSS**, inside the
charter's 15-minute and 3 GB guards. Review: `total_reward` **0.0035556**
(`lift` +0.0035706, `effort_cost` -1.4984e-05), policy sha256 `dad19e92…`,
weights `lift_task.cxpolicy`, task sha256 `cbffdf6c…`, 4481 parameters
trained on CPU in 1.47 s, witness error 3.679e-09 against a 1e-4 tolerance.
`review.json` (`cadex-walk-review-v1`) landed in the project beside
`ARCHITECTURE.md`, `DECISIONS.md` and `PROGRESS.md`.

The design turn wrote a mechanism the walk had never seen: base plate, an
upright rail column, a carriage on a **prismatic** joint, a bounded force
`motor` (not a position servo), a height sensor, a lift-minus-effort task,
`policy_on` and one `assembly.policy(...)` with both strings as inline
literals — so the digest edit rewrote it with no refusal. It also landed
three of its own `DECISION:` lines in the project's `DECISIONS.md`
(ADR-002..004: no collision geom on the rail because the carriage bore
surrounds it; a raw force motor rather than a position servo, so the action
space is the force range; termination at `carriage_z < 3` mm so a dropped
carriage fails the episode instead of resting on the joint limit).

## Why

Two frontier nodes at once, and the overseer's dispatch for this iteration:
a second independent prompt walk, different seed, different prompt, headless,
no leg fixed in the same iteration.

- **`crisp-reef-5607` — the walk exists and is tested headlessly.** The plan
  (`rustic-loom-0992`) set the tick rule: a clean run makes it two clean of
  three attempts, with the one failure predating both fixes, and the record
  may then declare the criterion met. This run satisfies that rule and is
  stronger than the repeat the rule asked for, because it changed the prompt,
  the mechanism, the joint type, the actuator type and the seed.
- **`swift-dusk-2951` — the walk holds on a second mechanism.** This is the
  same entry point taking a second mechanism through the whole loop with no
  code change of any kind, and both prompt-designed projects' `PROGRESS.md`
  files carry the same rows with the same definitions.

Assumption written down (nobody to ask): the overseer's dispatch said "plan
rank 3" but described rank 2's unit — a different prompt and a different
seed. The described unit was taken, because the description is unambiguous
and rank 2's run is also rank 1's reliability evidence; taking it serves both
frontier nodes in one dispatch, which the plan itself anticipated.

## Method

- Prerequisites already present, nothing built: release engine at
  `build/release/bin/FreeCADCmd`, training venv at `.venv`.
- Guard harness (`/tmp`, not committed), same discipline as `misty-rain-9048`
  and `cool-fountain-2483`: spawn the walk in its own process group, sample
  process-tree RSS every 0.2 s, SIGKILL at 2.9 GB or 850 s.
- One command, fresh gitignored project under `build/lifecycle/`:

```
JAX_PLATFORMS=cpu ./cadex walk --project build/lifecycle/prompt-walk-nt3c \
  --out build/lifecycle/prompt-walk-nt3c/runs/baseline \
  --prompt "A vertical linear carriage test rig: a fixed base plate with an
  upright rail column, and a carriage block that slides up and down that rail
  on a prismatic joint. Give the bodies masses, a force motor on the sliding
  joint, a sensor that reads the carriage height, and a task that rewards
  lifting the carriage while penalising actuator effort. Follow the policy
  switch convention so the lifecycle walk can install a trained policy." \
  --model claude-fable-5 --trainer-python "$PWD/.venv/bin/python" \
  --iterations 1 --envs 4 --seed 1 --timeout 600 --json
```

- Zone gate, after the run, on an unchanged tree: `JAX_PLATFORMS=cpu pixi run
  python -m pytest cli/tests -q` — **142 passed in 127.95 s** (142 is the
  count after `ancient-wind-0117`; the engine is built, so `test_walk.py`'s
  two real end-to-end walks ran).
- No GUI, no `pixi run app`, no remote dispatch, no retry, no hand edit of
  either project's script or documents. `git status` is clean.

## Result

**Yes — `crisp-reef-5607` can be ticked.** Ideation → design → assembly →
MJCF → task → local CPU training → policy verify → rollout → review completed
with no human step, from one documented entry point, on this machine, for the
second time in a row and on a mechanism designed inside the walk from a
prompt the walk had never seen. Three prompt-walk attempts across this run:
one failure (`misty-rain-9048`, before both fixes), then two clean
(`cool-fountain-2483`'s pendulum rig, this run's carriage). Both fixes the
failure named are in the tree and pinned by tests.

**Yes — `swift-dusk-2951` can be ticked, with one honest caveat.** Same
entry point, no mechanism-specific code, second mechanism through the whole
loop, and both `PROGRESS.md` files carry comparable rows:

| project | mechanism, joint, actuator | design | train | declare | rollout | wall | peak RSS | `total_reward` |
|---|---|---|---|---|---|---|---|---|
| `prompt-walk-nt3b` | pendulum rig, revolute, position servo | 262.03 s | 14.50 s | 1.43 s | 1.76 s | 280.7 s | 1.23 GB | 425.997 (`lift_height` +427.193, `effort_cost` -1.194, `speed_cost` -0.001) |
| `prompt-walk-nt3c` | vertical carriage, prismatic, force motor | 172.59 s | 13.06 s | 1.25 s | 1.50 s | 189.4 s | 1.115 GB | 0.0035556 (`lift` +0.0035706, `effort_cost` -1.4984e-05) |

Both at 1 iteration × 4 environments (seeds 0 and 1), both `--timeout 600`,
both verified against the engine witness (4.48e-09 and 3.679e-09). The
caveat is the one `examples/lifecycle/README.md` already records for the two
example mechanisms and it applies unchanged here: the columns and their
definitions are the same, but the two reward expressions are different
objectives in different units, so the totals compare *runs of the same
project*, never designs against each other. Neither number is a claim about
learned control — one PPO iteration is a smoke test of the loop, which is
what the criterion asks for.

Two attempts, two mechanisms, two clean walks, no code touched between them.
The remaining frontier work on the walk is not its shape: `witty-spark-2613`
still needs the GUI-attached and remote modes documented-not-exercised
evidence, and `damp-moon-9297` (the headless review calls) is untouched.

The unreconciled tail is now 2 nodes; that is the maintainer's to fold.

Dispatch closed: 1 unit — ran a second independent `cadex walk --prompt` (vertical carriage, prismatic joint, force motor, seed 1) clean end to end on a fresh project, four legs exit 0, 189.4 s, 1.115 GB, total_reward 0.0035556, with the tree unchanged and `cli/tests` 142 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: dfeccc9f4198dc2bcec78f2c8409252bcc9bccbd

## State Impact

- target: crisp-reef-5607 — MET. The walk from --prompt completed unattended a second time, on a mechanism designed inside the walk (vertical carriage, prismatic joint, bounded force motor): design 172.59 s, train 13.06 s, declare 1.25 s, rollout 1.50 s, all exit 0; 189.4 s wall, 1.115 GB peak, total_reward 0.0035556, witness error 3.679e-09, review.json in the project. Three attempts this run: one failure predating both fixes, then two clean on two different prompts and seeds. The design leg's reliability doubt that held the criterion open is answered by evidence, and both named causes are fixed and test-pinned (cli/tests 142 passed on the unchanged tree).
- target: swift-dusk-2951 — MET. The same documented entry point took a second, prompt-designed mechanism through the whole loop with no code change of any kind (git status clean at dfeccc9f), and both prompt-walk projects' PROGRESS.md files carry the same rows with the same metric definitions: nt3b pendulum/revolute/position-servo 280.7 s, 1.23 GB, total_reward 425.997; nt3c carriage/prismatic/force-motor 189.4 s, 1.115 GB, total_reward 0.0035556, both at 1 it x 4 envs. Caveat, same as examples/lifecycle/README.md: the two reward expressions are different objectives in different units, so the totals compare runs of one project and never rank designs.
- target: witty-spark-2613 — Headless mode exercised again on this machine under the charter's guards (0.2 s process-tree RSS sampling, 2.9 GB and 850 s cutoffs; observed 1.115 GB peak, 189.4 s wall). GUI-attached and remote modes remain documented-not-exercised, unchanged by this unit.
