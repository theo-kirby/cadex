---
node_id: 733e69aa-6bee-5a5c-93b7-9c277923c4d8
slug: quiet-vine-3426
title: Fresh carriage completes the two-mechanism headless review rehearsal
created_at: '2026-09-08T00:24:54+00:00'
parents:
- first-branch-9614
summary: ''
artifacts:
- docs/probes/complete-review/linear-carriage/README.md
- docs/probes/complete-review/linear-carriage/audit.json
- docs/probes/complete-review/linear-carriage/PROGRESS.md
- docs/probes/complete-review/linear-carriage/runs/baseline/review.json
- docs/probes/complete-review/linear-carriage/cli-gate.log
- docs/probes/complete-review/linear-carriage/cli-monitor.log
- docs/probes/complete-review/hinged-arm/comparison-audit.json
- docs/probes/complete-review/hinged-arm/PROGRESS.md
---
## What

Rehearsed the fresh linear-carriage through the identical public lifecycle entry point, inspected all four named views and interior section, audited accepted identity and committed artifacts, and committed comparable numbers in both source projects' PROGRESS.md. Retained compact evidence under docs/probes/complete-review/linear-carriage plus the arm comparison update. Ticked the ROADMAP rehearsal item and appended ADR-240 evidence. No runtime change or removal.

## Why

Advances charter criterion **The agent can see its work without a screen** (damp-moon-9297), short rank 2 after first-branch-9614, and corroborates **The walk holds on a second mechanism**. Combined arm/carriage evidence now covers every review clause for maintainer judgement; no known missing headless-review leg remains. This is one evidence unit, not completion of the whole mission. Assumed the explicit contributor-only prohibition overrides the overseer's request to reconcile and re-plan in this dispatch: neither was run, no charter/state/plan edited. Later criteria remain parked.

## Method

Reproducible commands are in the carriage evidence README: fresh external project, `./cadex script --set examples/lifecycle/linear-carriage/script.py`, then public `walk --iterations 1 --envs 4 --seed 0 --timeout 600`, existing training venv and JAX_PLATFORMS=cpu. Existing process-tree monitor samples RSS at 0.2 s, terminates above 2.9 GB or 850 s. Same settings and measurement boundaries as the fresh arm; no mechanism-specific code change, GUI, SSH, GPU dispatch, provisioning or build.

Rasterized all five SVGs using inspection-only CairoSVG and existing pixi libcairo, then visually inspected them. Checked actual contour coordinates and shoelace areas; accepted script.json revision/digest against rollout leg, render and section; inventory/clearance revision; trace policy/task hashes, reward, seed and steps against review. Both projects' copied artifacts match git show HEAD byte for byte and both projects are clean. Source commits and hashes are in carriage audit.json and arm comparison-audit.json. The original arm audit remains tied to its previous commit. No checkpoints, policy bytes, rollout traces or machine paths are copied into product evidence. Existing example sensor notes were carried by the reviewing agent after script-only import, with comparison and rationale committed to project docs; no scaffold convention changed.

## Result

Design and walk exited 0. Carriage CPU training reward/step -82.31990814208984, witness error 5.41889473917867e-09; rollout seed 3, 50 steps, total reward -24159.19535630446, mean -483.1839071260892. Arm comparison: training -0.3801981508731842, witness 1.3841167412209642e-09, rollout -27.109384220927513, mean -0.5421876844185503. Both use the same weighted squared-height objective, but effort is N for carriage and N·mm for arm, so these do not rank policy improvements. Carriage falls under gravity; policy verification proves compatibility, not useful control.

Shared acquisition 0.6857212079921737 s; four-view rendering 0.6373496250016615 s; contour generation 0.00007579103112220764 s; walk_seconds 16.048740583006293 s; external whole command 16.39 s; sampled process-tree peak RSS 987,168,768 bytes. Acquisition counts once; contours exclude writes; walk_seconds excludes final commit; external timing includes it. Both runs overlapped their gate, so numbers are observations, not speed benchmarks.

Four legible views show the expected cube/plate placement. XZ Y=3.125 mm contours are base 360 mm² and slide 400 mm², with X/Z bounds 0..60/0..6 and 12..32/40..60 mm. No cavity in these examples; real-kernel cavity/rotation checks are in the CLI gate. Inventory truthfully names two uncatalogued synthetic components with catalogue fields. Clearance base–slide is 34 mm, 0 mm³ common volume: one checked pair, zero offending, zero unknowns. Arm retains base–swing contact: one offending pair, zero unknowns. Initial pose only, qualified tessellation sections, no swept safety claim.

Full built-engine CLI gate: **195 passed, zero skipped, 219.10 s**. Monitor exit 0 in 219.85 s, peak sampled RSS 1,173,487,616 bytes; logs retained. No payload/protocol changed and no packaged gate is claimed. git diff --check and hypergraph export/check pass.

Next: combined evidence is ready for maintainer assessment of damp-moon-9297, then planner selection from the authorized frontier. GUI remains documented-only, remote scripted-only with existing local CPU stand-in parity (copper-timber-8947), both intentionally unexecuted. This dispatch creates the third unreconciled record; separate maintainer owns reconciliation and planner owns re-planning. No additional work unit taken.

Dispatch closed: 1 unit — fresh carriage complete review inspected and compared with the arm; combined evidence handed off.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 2e935cd54e120e28e3aa79c0fcf526b1b829f111

## State Impact

- target: damp-moon-9297 — Fresh carriage and arm complete-review evidence now covers inspected named views, interior sections, truthful inventory and named pair checks, accepted identity and committed comparison bytes; ready for maintainer assessment, initial-pose and toy-policy limits retained.
- target: swift-dusk-2951 — Fresh carriage again passes unchanged public walk with same bounded CPU settings as arm; both projects commit comparable reward, witness and review measurements; 195 CLI tests pass without skips.
