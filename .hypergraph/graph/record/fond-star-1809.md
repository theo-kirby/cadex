---
node_id: 948130f8-db23-533f-9c8a-bda80d370656
slug: fond-star-1809
title: The documented walk runs clean in a durable project and the design turn writes the domain notes
created_at: '2026-09-08T07:17:24+00:00'
parents:
- lucid-pebble-4000
summary: ''
---
## What

Ran the documented `cadex walk` end to end, headless, on a two-MG90S servo leg
in a **durable** project (basename `nt3-leg` under a `cadex-projects` directory
in the operator's home, outside this repository and outside `~/arch`), with a
prompt that names the three review findings the previous rehearsal produced.
All four legs completed: design, train+store, declare, verify/rollout, plus
review. **The design turn left `docs/actuators.md` and `docs/sensors.md`
behind** — the ADR-245 note convention works on a live turn, not only in tests.
The four positive-volume intersections the earlier leg had are gone, and the
5 mm servo-to-driven-link gap is closed by a printed shaft boss.

## Why

Advances charter criterion **The walk exists and is tested headlessly**
(`crisp-reef-5607`) and **The agent can see its work without a screen**
(`damp-moon-9297`), missions 2 and 6. It is the overseer's redispatch verbatim
and the short bet's unit 1 [rec: weathered-hill-5955], merged with the
compliance question ADR-245 opened [rec: lucid-pebble-4000]: does a real design
turn now write the domain notes?

Two assumptions, written down because nobody was here to ask.

1. The bet asked to iterate the *existing* leg project with `--resume`. That
   project was under the system temporary directory and has been reaped
   [rec: lucid-pebble-4000], so there was no conversation to resume. The
   closest faithful reading — and what the overseer asked for — is a fresh
   conversation in a durable project whose prompt states the findings verbatim,
   with their measured volumes. The findings therefore act as design inputs
   rather than as a second turn's correction. A repair-turn on a live project is
   still unexercised; this run leaves a durable project to do it on.
2. No operator edit to the generated script, and no source repair. What the
   agent produced is the measurement.

## Method

Same qualified payload as [rec: lawful-dune-3795] and [rec: proud-beacon-8002]:
`build/engine/cadex-engine-0.0.0-macos-arm64`, whose `CadexScriptedRuntime.py`
SHA256 was re-checked as `602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df`
before dispatch. Repository HEAD `88f7b732`, clean, so the CLI under test carries
ADR-245.

```sh
env -u PYTHONPATH -u CADEX_ENGINE_ROOT -u CADEX_MODULE_DIR JAX_PLATFORMS=cpu \
  <repo>/.venv/bin/python <existing-monitor> <log> \
  ./cadex walk --engine <qualified-payload> --project <durable-project> \
  --out <durable-project>/runs/baseline --prompt "$(cat <prompt>)" \
  --trainer-python <repo>/.venv/bin/python \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

The monitor is the existing one: process-tree RSS every 0.25 s, 2.9 GiB / 850 s
cutoffs, TERM then KILL. Training is the repo's `.venv` per `training/SETUP.md`,
CPU, toy scale; no remote dispatch, no GUI. Model `claude-fable-5` (the default).

The prompt asked for the same leg as the earlier rehearsal, then named the three
findings with their numbers — shin/foot-bolt 5.8373525743 mm³ each, bolt/nyloc-nut
9.2781252741 mm³ each, and the 5 mm servo-to-link gap — required the six catalog
instances to stay separately placed `assembly.component`s, and asked for
`DECISION:`, `NOTE actuators:` and `NOTE sensors:` closing lines.

Review by eye: extracted the lossless PNGs embedded in the four saved view SVGs
and rasterised the section SVG with `qlmanage`. Re-implemented the
`morning-summit-7848` bound-agreement checker (the earlier one was ad hoc and
not kept): every clearance row's reported distance must not fall below the
AABB gap taken from the render and section summaries, and no positive common
volume may come with separated AABBs.

Local ignored evidence: `build/lifecycle/nt3-i185-leg.json`,
`.err`, `.monitor.json`.

## Result

**Every leg clean; no leg needed a person or a guess; no leg was unreached.**
Monitor exit 0 in **630.22 s**, peak process-tree RSS **1,115,717,632 bytes**,
no cutoff — inside the 15 min / 3 GB bound. Legs: design **599.74 s**, train
(rebuild, export, train, store) **20.03 s**, declare **2.33 s**, verify/rollout
**2.69 s**; review completed. Accepted revision `417d0fdf3286…`, digest
`e6395e3e49c4…`. One `inspect` error inside the design turn
(`/library/catalog/servo` is not a JSON Pointer path) was the agent's own probe
and it recovered; no engine error and no source repair.

**The domain-doc convention works on a live turn.** `docs/actuators.md` records
the torque-limited position-servo model — 176.52 N·mm limit, 600 °/s no-load
speed from the MG90S 4.8 V datasheet, 30 N·mm/deg stiffness, damping
0.294 N·mm·s/deg chosen so torque saturates exactly at no-load speed, plus the
passive damping and armature. `docs/sensors.md` records six channels: hip/knee
angle in degrees (the per-axis angle sensors asked for), joint velocity, and
actuator effort in N·mm feeding the effort cost. Five project ADRs landed from
the same closing paragraph, including the two that answer the findings directly.
This is the first live evidence for ADR-245; the earlier run produced no such
notes.

**The findings are answered in geometry, not only in prose.** Clearance:
**45 pairs checked, 9 offending (was 11), 0 unknown** at 0.1 mm / 1e-6 mm³ —
and **every offending pair is a zero-volume face contact**. The four
positive-volume intersections are gone: the shin and pad now carry real Ø3.4
`lib.clearance_hole("m3")` through-holes with a 45° countersink void, and the
bolt grip is held at 10 mm so the shank ends exactly at the nyloc base plane.
The servo/driven-link distance is now **6.1e-16 mm** for both hip-servo/thigh
and knee-servo/shin, where it was 5 mm: each driven link carries a printed Ø9
boss with a Ø5.5 bore over the Ø4.9 spline, face-coincident with the servo case
top. The remaining nine contacts are the declared mating faces (boss/case-top,
flange tabs/plate, nut/flange, flange/pad). **A face contact at 0.0 mm is still
below the 0.1 mm criterion and is still reported** — this is a changed geometry
with a stated intent, not a waived check, and no print-fit or assembly-tolerance
claim follows from it.

**Catalog placement holds.** 10 components, **6 catalogued instances**
(`servo/mg90s` ×2, `bolt/m3x10-countersunk` ×2, `nut/m3-nyloc` ×2). Manual
script tally agrees: the only `lib.*` calls are the six placements plus the
scalar `lib.clearance_hole("m3")`; every `part.fuse`/`part.cut` takes
`part.*` primitives only, so no catalog body enters a printed solid and none is
discarded. The agent chose *not* to place a catalog horn, modelling the boss
itself, and said so in a project ADR.

**Eyes.** Four views (front/top/right/iso) and the world XZ section at
Y = 3.125 mm, all at the accepted revision. Front shows the hanging chain
support→thigh→shin→pad; right shows each servo case seated through its plate
cutout with the boss meeting the case top; iso shows the two servos on opposite
sides and the foot hardware; top shows the lateral offsets. The section shows
the thigh hip boss as an annulus, the thigh bridge, **the knee servo spline
inside the shin boss bore** — the attachment, in cut — and the pad/flange. These
are initial-solved-pose tessellation views, not a swept check.

Bound-agreement checker: **PASS, 90 comparisons, 0 failures**, at a stated
1e-3 mm tolerance; worst discrepancy **3.05e-6 mm**, which is float32
tessellation resolution at ~100 mm, not a disagreement. 39 of the 45 pairs
involve a catalog instance. This is AABB consistency between three independent
outputs, not independent validation of each OCCT volume.

**Training and rollout, toy scale.** 4,738 parameters, 1 iteration × 4
environments, seed 0, CPU; trainer wall **2.3 s**, final batch reward/step
**0.0025930453557521105**; policy sha256 `c172882864ad…`. Verified rollout
total_reward **0.8530453495479725** (crouch_tracking 0.8530939220340145, effort
−4.857e-5). This leg's reward expression is positively shaped, so it is **not
comparable** with the earlier leg's −5144.79 or with the arm and carriage rows:
different objective, weights and horizon. One PPO iteration supports no claim
about learned control.

The project has **five commits**, HEAD `b244f26`, clean status, 72 tracked
files: script and history, `ARCHITECTURE.md`, five ADRs, `PROGRESS.md`, the two
agent-authored domain notes, the generated inventory and clearance reports, the
four views, the section and `review.json`. The stored policy asset is committed
by the product lifecycle as designed; trainer checkpoints, traces and the 12 MB
`runs/` tree are ignored. **This repository's status is clean and carries no
project artefact, checkpoint or machine path.**

**One new finding, not fixed here.** The walk's `PROGRESS.md` row and the
project's own commit subject both record `--out` as an absolute path, so a
version-controlled project carries the operator's home directory in its history.
`review.json` already relativises paths under `--out`; the row and the commit
subject do not. That is a small CLI defect in the LGPL zone with an obvious
smallest fix, and it is the next unit — this one was the walk.

No repository product edit, build, removal or ADR was warranted: the engine,
CLI and shell suites were not re-run because nothing in this repository changed,
and the walk itself is the runtime verification. The tail now carries three
unreconciled records including this one; reconciling is the maintainer's.

Next: fix the absolute `--out` path in the walk's PROGRESS row and commit
subject, with a test. Then use this durable project for the thing that is still
unexercised — a *second* design turn on a live conversation (`--resume`),
iterating from the run's own review rather than from a prompt that was told the
answers. `crisp-reef-5607`'s remaining gap is that repair turn, not the walk.

Dispatch closed: 1 unit — the documented walk runs clean end to end in a durable project, the design turn writes docs/actuators.md and docs/sensors.md, and the leg's four positive-volume intersections and 5 mm drive gap are gone.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 88f7b73290b1f971d802846b11710ef580fb4c72

## State Impact

- target: crisp-reef-5607 — Documented walk completes all four legs plus review headlessly in 630 s on a durable project; the design turn now leaves docs/actuators.md and docs/sensors.md, first live evidence for ADR-245; the unexercised leg is a repair turn on a live conversation.
- target: damp-moon-9297 — Four views and the XZ section inspected by eye at the accepted revision; 45 clearance pairs, 9 offending all zero-volume face contacts, 0 unknown; bound-agreement checker passes 90 comparisons at 1e-3 mm with a 3.05e-6 mm worst discrepancy.
- target: calm-peak-5247 — Review findings stated as design inputs removed all four positive-volume intersections and closed the 5 mm servo-to-link gap with a printed shaft boss, with six catalog instances still separately placed.
