---
node_id: faff9f4e-d49d-59e6-bbb9-3c60b9c2128b
slug: dry-falcon-5463
title: A cart-pole with a passive joint walks through the unchanged entry point
created_at: '2026-09-09T05:38:22+00:00'
parents:
- square-crest-8869
summary: ''
---
## What

Took a **second mechanism** through the documented headless lifecycle entry
point on this machine, from nothing: `ot4-cart`, an **inverted-pendulum cart** —
grounded frame and rail, a cart on a **prismatic** joint driven by a bounded
**force motor**, and a slender pole on a **passive revolute** joint nothing
drives. Same `cadex walk --prompt`, same flags and bounds as the `ot4-mix55`
run, a fresh empty project, and **no code change of any kind**. It completed
every leg: exit 0 in 1222.22 s. The evidence landed in `docs/CLI.md` §2 as a
leg-for-leg table beside `ot4-mix55`, with a ticked `docs/ROADMAP.md` entry.

## Why

The overseer's explicit instruction for this dispatch, advancing charter
criterion **The walk holds on a second mechanism** (`swift-dusk-2951`) and, with
it, `calm-peak-5247` and `damp-moon-9297`. The mechanism was chosen to be one no
previous ot4 walk had: an **unactuated degree of freedom**. The three earlier
prompt walks on this machine used `(position, angular)`, `(motor, linear)` and
`(position, linear)` — every actuated pair the engine's action-source table has
— so a fourth distinct rig had to vary the topology, which `swift-dusk-2951`'s
negative knowledge already said in as many words. A passive joint also gives the
first task whose **termination** the rollout actually reaches.

Assumptions written down rather than asked: an early rollout termination is a
result, not a failure — a policy that holds a pendulum for 0.6 s after five PPO
iterations is pipeline evidence and is reported as such; and a section that
misses an object is a review finding for the next design turn, on the same terms
as ADR-271's clearance row.

## Method

The tree was clean and no source had changed since the last engine build, so the
installed engine was reused; the walk's own `engine_source_comparison` reported
`match` across 56 files before the first leg. Ran from `/home/theo/cadex` into
`~/cadex-projects/ot4-cart` (created empty), under the same 0.2 s process-tree
RSS monitor with a 2.9 GiB kill guard:

`JAX_PLATFORMS=cpu CADEX_MODEL=claude-opus-5 ./cadex walk --project "$P" --prompt "$PROMPT" --out "$P/runs/cart1" --name cart1.cxpolicy --iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800 --json`

The prompt described the rig, the actuator bound and the task, forbade
substituting disconnected parts for a joint, and asked for the project docs. It
gave no engine-internal guidance — no collision-shape advice, no joint-kind
hints — so the design turn's choices are its own. Then read the envelope, the
`review.json`, the trace and both projects' `PROGRESS.md`, and wrote the numbers
up. Nothing generated entered this repository.

## Result

**Walk: exit 0 in 1222.22 s; peak process-tree RSS 1,997,844,480 bytes; watchdog
did not intervene.** Legs, all exit 0: design 1196.04 s (revision `0aa617e2…`,
digest `b3b699e6…`), train 20.27 s, declare 0.65 s, rollout 1.21 s;
`walk_seconds` 1222.11 through review.

- **train** — CPU, 5 iterations x 16 envs, seed 0; reward/step **0.6936**, best
  0.7013 at iteration 0, 4,609 parameters, 3.95 s trainer wall time, 26,319-byte
  `cart1.cxpolicy` (`90c93807…`). Mean training episode 16.8 steps.
- **policy verify** — witness error **6.335e-09** against a 1e-04 tolerance over
  32 samples.
- **rollout** — total reward **28.756** at seed 7, terms `upright` +30.262,
  `pole_calm` -1.147, `stay_centred` -0.177, `cart_calm` -0.137, `effort`
  -0.046.
- **eyes** — render 4 views, 5,002 triangles, 3.19 s; section XZ at a derived
  **-15.0 mm**, **2 of 3** objects cut, status `ok`; inventory 3 components, 0
  catalogued; clearance 3 pairs, 0 unknown, **0 offending**, bounds check `pass`
  (6 comparisons); motion 6.328 mm and 35.75 deg, both on `pole_comp`, over 32
  solved frames; documentation 3 notes for 2 declared subjects, none missing.
- **project as codebase** — five commits (ending `fac73fc`), five `PROGRESS.md`
  rows, **seven** project ADRs and `docs/{actuators,rejected,sensors}.md` beside
  the CLI's own `inventory.md` and `clearance.md`.

**Two findings the run produced about itself, kept rather than smoothed.**
First, the verified rollout **ended on the task's own termination** —
`pole_fell` at step 30 — so `total_reward` sums **31 of 200** steps of a 4 s
episode. Five PPO iterations is a smoke test of the loop; nothing here claims
the policy balances a pendulum, and the docs say so. Second, the **derived
section offset cut 2 of 3 objects**: of the candidates
`[0.0, -2.0, 2.0, -8.5, 8.5, -15.0, 15.0]` the most-coverage rule (ADR-273,
ADR-275) chose -15.0 mm, the pole came back `empty`, and
`section.missed_objects` named it `moved: true` — the one object carrying all
35.75 deg of the mechanism's rotation. On a rig whose moving part is a slender
rod near the centre plane, maximum object coverage and maximum interest are not
the same plane. The eye reported that itself; the finding is a candidate unit,
not a defect fixed here.

Validation: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q` exited 0
— **289 passed in 222.16 s**, no skips. `git diff --check` clean. The commit
(`d7d1c227`) is documentation only — `docs/CLI.md` +55, `docs/ROADMAP.md` +20 —
so no engine suite or shell gate was required for the zone. Local run evidence
stays out of Git in `~/cadex-projects/ot4-cart/runs/cart1/`.

**What is still missing before `swift-dusk-2951` can be ticked** is unchanged
and is not a coverage question: control quality. Four mechanisms have now
completed the same entry point on this machine with no mechanism-specific
branch, and both projects' `PROGRESS.md` carry the same columns — but the reward
figures are different objectives in different units and rank nothing, and this
rig's policy holds its pole for 0.6 s. The tick stays a charter decision. The
tail is now two unreconciled records; the contributor did not reconcile.

Dispatch closed: 1 unit — a cart-pole with a passive joint completed the unchanged walk end to end, exit 0 in 1222.22 s, and the evidence is in `docs/CLI.md` §2 and `docs/ROADMAP.md`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: d7d1c22709a994b531b0605fbff1d4f054a9a27b

## State Impact

- target: swift-dusk-2951 — A fourth mechanism completed the unchanged cadex walk on this machine, and the first with a passive (unactuated) joint: ot4-cart, an inverted-pendulum cart (prismatic cart on a bounded force motor, pole on a passive revolute nobody drives), from one prompt into a fresh empty project with no code change of any kind. Exit 0 in 1222.22 s, peak tree RSS 1,997,844,480 bytes, no watchdog; design 1196.04 s (revision 0aa617e2, digest b3b699e6), train 20.27 s at reward/step 0.6936 with witness error 6.34e-09 against 1e-04, declare 0.65 s, rollout total_reward 28.756 at seed 7. Four eyes: 4 render views (5,002 triangles), XZ section at a derived -15.0 mm cutting 2 of 3 objects, 3-component inventory (0 catalogued), clearance 3 pairs with 0 offending and a passing bounds check. The project committed itself: five commits ending fac73fc, five PROGRESS.md rows, seven project ADRs, three domain notes. Both projects' PROGRESS.md carry the same columns; docs/CLI.md 2 now puts the two walks leg for leg. Control quality still holds the tick back: the rollout ended on the task's own pole_fell termination at step 30 of 200, so the reward sums 31 steps and claims nothing about learned balance.
- target: damp-moon-9297 — The section eye reported its own blind spot on a mechanism that exposes it. The most-coverage offset rule (ADR-273, ADR-275) picked XZ at -15.0 mm from candidates [0.0, -2.0, 2.0, -8.5, 8.5, -15.0, 15.0], cut 2 of 3 objects, and named the missed pole in section.missed_objects as moved: true - the one object carrying all 35.75 deg of the mechanism's rotation. On a rig whose moving part is a slender rod near the centre plane, maximum object coverage and maximum interest are not the same plane. Clearance on the same run was clean (3 pairs, 0 offending, bounds check pass over 6 comparisons), so the eyes disagreed with nothing; this is a candidate unit, not a defect fixed here.
- target: calm-peak-5247 — The project-as-codebase contract held unaided on a fourth rig: ot4-cart scaffolded and then maintained ARCHITECTURE.md, DECISIONS.md (seven ADRs), PROGRESS.md (five rows) and docs/{actuators,rejected,sensors}.md, with the CLI's own inventory.md and clearance.md beside them, across five automatic commits. The documentation eye reported 3 notes for 2 declared MJCF subjects, none missing.
