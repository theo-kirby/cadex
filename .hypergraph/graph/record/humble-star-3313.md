---
node_id: 2667a177-aba7-5b1a-a391-86e244a69522
slug: humble-star-3313
title: The live iterate read the history and closed the finding
created_at: '2026-09-08T23:10:58+00:00'
parents:
- candid-fern-3092
summary: ''
---
## What

Ran the plan's exclusive short unit #1 — the **live project-history iterate** —
to completion on `ot4-quill`, and the answer to the question it was posed is
**yes**: a real provider turn read the project's own recorded history, disputed
the project's own ADR about it, changed the geometry, and the review eye that
had reported the finding on every walk row now reports it gone.

Then landed the one code gap the run exposed: the walk's `PROGRESS.md` row
compared its reward and travel figures against the previous walk but wrote the
clearance finding count bare, so the number the iterate actually turned —
offending 1 → 0 — read as if there had never been a finding (ADR-271).

## Why

Charter criterion **"The walk exists and is tested headlessly"**
(`crisp-reef-5607`) and, behind it, **"Iterate works"** on the lifecycle-walk
node `calm-peak-5247`. The plan and the overseer both named this unit and made
it exclusive; `candid-fern-3092` is the bet.

The design turn itself had **already run and committed** in `ot4-quill` at
22:57:54Z (`0741643`), from an earlier iteration that was killed during the
train leg — two half-built run directories (`live-iterate-42`, `42b`, each
containing only `train/`) and a stale advisory lock were all it left, and
nothing was recorded on the cadex side. Rather than spend tokens re-asking a
question already answered, this iteration finished the walk the provider turn
had started, token-free, and reported what the turn read and changed.

Assumption taken without asking: finishing a killed walk on an already-landed
design turn *is* the live iterate, because the evidence the criterion wants is
the closed loop — history read → geometry changed → review re-measured — not a
second provider call. The stale lock needed no fix: `session.py`'s lock is an
advisory `flock`, released by the kernel when the holder dies, so the leftover
pid file is inert by design.

## Method

1. Confirmed the killed run's state: lock holder pid 2021869 dead, project
   `script.json` re-staged at the design turn's revision `839ff9fd…`, geometry
   change committed.
2. Read what the turn had actually done (`git show 0741643`): it quoted the
   repeated `clearance offending 1 … 960 mm³` row out of `PROGRESS.md`, checked
   the arithmetic against the accepted values (head block y −32.2…−10.2 against
   column y −42.2…−30.2 is 2.0 × 30 × 16 = 960 mm³ exactly), **contradicted the
   project's ADR-005** attribution to shaft-in-solid-bore modelling, and wrote
   project ADR-007: the bore axis stands off the column face by the head's full
   swept radius (25.50 mm) plus a declared `spin_clearance`, with a web tying
   the boss back in, under the invariant
   `stand_off = max(head_sweep_r + spin_clearance, housing_od/2 − embed)`.
3. Ran the reference command token-free — no `--prompt`, no `--set`, seed 0,
   rollout seed 7, CPU 5 iterations × 16 environments, trainer timeout 600 s,
   leg timeout 120 s — into `runs/live-iterate-43`.
4. Read `review.json` and compared every eye against `runs/derived-section-41b`.
5. `cli/cadex_cli/project_docs.py`: `clearance offending` joins
   `COMPARED_NUMBERS`; `cli/cadex_cli/__main__.py`: new `_clearance_cell`
   builds the walk row's clearance half through `compared_number`, mirroring
   `_motion_cell`. No re-spelling — the label already sat in front of the
   count, so every row ever written reads back.
6. Two test changes: a new `test_project_docs.py` regression (old-spelling row
   reads back, first new row carries `Δ -1`, a repeat finding says `±0`), and
   the existing `test_walk.py` two-walk assertion strengthened to require the
   delta.
7. Wrote the narrative and the comparison table into the project's
   `PROGRESS.md` and committed it in the project repo (`f8f65ff`).

## Result

**The live iterate closed the finding it read.** `runs/live-iterate-43`, exit 0,
walk 23.618845950928517 s (23.67 s external, peak RSS 1,945,824 KB), all three
legs exit 0 (train 19.59, declare 0.97, rollout 1.07 s).

| | `derived-section-41b` (before) | `live-iterate-43` (after) |
|---|---|---|
| clearance offending pairs | **1** (960 mm³ `housing`/`quill`) | **0** |
| unknown / checked | 0 / 1 | 0 / 1 |
| `bounds_check` | pass | pass, 2 comparisons, 0 failures |
| section | derived, XZ −15.7, housing 3 loops, quill 1 | derived, XZ 0.0, housing 2 loops, quill 1 |
| inventory | 2 components, 0 catalogued | unchanged |
| motion mm / deg over 201 frames | 30.078469436328 / 0 | 30.088980188884396 / 0 |
| exported task sha256 | 89e911f824d1… | **42958f923436…** |
| total reward | 175.487211145051 | 175.3771498711709 |

**The reward numbers are not a comparison**: the task digest changed with the
moved masses, so the new policy trained on a different rig — the row's standing
disclaimer applies with more force here, not less. The clearance row is the
result, and it is the eye's own verdict at the initial solved pose at the
unchanged 0.1 mm / 1e-06 mm³ thresholds. Both parts are still cut by the
section; the chosen plane moved because the geometry did.

Gate: `pixi run python -m pytest cli/tests` — **262 passed in 228.80 s** (was
261). No engine, protocol, payload or `shell/` diff, so no other gate applies.
`git diff --check` clean.

Criterion advanced: **"The walk exists and is tested headlessly"** — the
last unmeasured leg, a provider reading the project's own history and choosing
an iterate from the review's own findings, is now exercised end to end with the
numbers on both sides. Still missing before it can be ticked: this was a walk
whose design turn and measurement legs ran in two pieces after a kill, so a
single uninterrupted `walk --prompt … --resume` invocation start-to-review has
still not been observed; and the same closure has not been shown on the second
mechanism (`swift-dusk-2951`).

The unreconciled tail is 2 nodes after this one — small; no action needed.

Dispatch closed: 1 unit — the live project-history iterate ran to completion,
the clearance finding it read went 1 → 0, and the walk row now says so.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 4b5306a243b84d0f269a11053fa39c17a6fbc4c5

## State Impact

- target: crisp-reef-5607 — a live design turn on --resume read this project's own PROGRESS.md/DECISIONS.md, disputed its ADR-005, changed the geometry, and the walk that followed drove the review's clearance eye from 1 offending pair (960 mm³) to 0; the walk's PROGRESS row now carries that count as a delta (ADR-271)
- target: calm-peak-5247 — the iterate leg is exercised with a real provider turn end to end on ot4-quill: history read, project ADR-007 written by the turn, runs/live-iterate-43 exit 0 in 23.62 s, task digest changed so reward is explicitly not a comparison
- target: chilly-union-8972 — clearance offending joins COMPARED_NUMBERS and _clearance_cell builds the walk row's clearance half through compared_number; unknown and pairs checked stay plain by decision; cli/tests 262 passed
