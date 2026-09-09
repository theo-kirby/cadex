---
node_id: 61704324-020a-55dd-a2cb-7e6c31ec8ab8
slug: mellow-quartz-8093
title: Model-free carriage iterate preserves the baseline and records the reward decrease
created_at: '2026-09-08T15:04:03+00:00'
parents:
- narrow-wing-0418
summary: ''
---
## What

Ran one model-free iterate comparison on the durable external ot4-carriage project through the unchanged public cadex walk entry point. Added the actual command, review findings and limitations to docs/CLI.md, a landed ROADMAP checkbox, and end-to-end evidence to ADR-251. Corrected the old CLI warning that still said the walk made no source comparison.

## Why

This follows narrow-wing-0418 and the overseer's explicit selection of plan short unit 2. It advances maintenance evidence for the charter's “The walk exists and is tested headlessly”, “The walk holds on a second mechanism” and headless-review criteria, while exercising the shipped Iterate criterion. Assumption: increase carriage_wid 70 to 80 mm, which changes geometry/mass without changing travel or the reward denominator; changing force_limit_n instead would change the reward expression. Train cold to preserve the baseline's initialization regime. No parked criterion is promoted.

## Method

Read script.py and stored parameter values first. Preserve the baseline output and policy; select a fresh runs/iterate-1 directory and lift_iterate1.cxpolicy. Add project ignore entries for new generated artifacts and a project DECISIONS rationale before the run. Run JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/iterate-1" --set carriage_wid=80 --name lift_iterate1.cxpolicy --iterations 5 --envs 16 --seed 0 --timeout 600 --json, with PYTHONPATH, CADEX_ENGINE_ROOT, CADEX_MODULE_DIR and CADEX_TRAIN_PYTHON unset. No trainer-python flag; the documented venv fallback resolved. Measure with /usr/bin/time -v. Envelope and stderr remain outside git at /tmp/ot4-iterate-1.json and /tmp/ot4-iterate-1.stderr. Hash all 21 baseline files including the stored baseline policy before and after. Compare task bundle fields and read both verified traces. Inspect the four rendered images, section contours, inventory and clearance reports and their revision/digest agreement.

## Result

Exit 0, 20.89 s whole command, peak RSS 1,760,116 KiB; sweep/train/declare/rollout 1.01/16.54/0.87/1.00 s. CPU trainer 2.96 s, 4,673 parameters, witness error 3.058e-9 against tolerance 1e-4. Training-batch reward/step 0.02347 to 0.0084295. Both rollouts seed 7, 200 steps, 4 seconds, identical randomisation factors and no early termination; task bundles differ only in model. Reward total 3.2962976534 to 2.7601867887 (delta -0.5361108646), height 2.7717764068 and effort -0.0115896180. The walk itself wrote total_reward 2.8 (delta -0.5 vs 5a021bed at 3.3) into PROGRESS.md. Five automatic project commits end at dcef1a0. All baseline bytes unchanged; no new policy/checkpoint/trace/render dump enters this repository.

Render: front/top/right/iso show the carriage around its rail, 60 triangles, Y bounds +/-40 mm. Section: XZ at Y=3.125 mm, one base contour and two carriage contours, status ok. Inventory: two uncatalogued components, carriage volume 231950 mm3. Clearance: base/carriage 0.5 mm, common volume 0, one pair, zero offending/unknown, bounds check pass (two comparisons). Report matches 56 top-level Python files in JSON and stderr, zero changed/missing/extra. This does not prove binary or loaded-module provenance; review is initial pose, not motion coverage. One cold training seed is not general design qualification.

Gate: JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests — 223 passed, no skips, 183.98 s, exit 0. Log /tmp/ot4-iterate-cli.log. git diff --check passed.

No code, protocol, payload or scaffold behavior changed; no build, GUI or remote work. No remaining defect was exposed before the cited criteria can be considered met at their stated toy scale; charter boxes remain human-owned. Next: the conditional prompt slot has no new prompt-specific reporting path to exercise (comparison is before the design loop), so this end-to-end verification spends that slot per the plan; return the evidence to planning without repeating a green walk or starting parked work. The tail reaches three records with this unit; reconciliation remains the separate maintainer's work.

Dispatch closed: 1 unit — model-free carriage iterate compared and reviewed with baseline preserved.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 8c9f5431c583a9d8aa55b04cdbc81dfb80ff39d6

## State Impact

- target: calm-peak-5247 — Model-free carriage width change 70 to 80 mm completed all walk legs and automatically committed the same-objective reward comparison, 3.296298 to 2.760187 over 200 steps; baseline unchanged and CLI gate 223 passed.
- target: swift-dusk-2951 — Durable second mechanism now has baseline and model-free iterate evidence at CPU 5x16 seed 0, with identical task fields except model and all four eyes reviewed.
- target: damp-moon-9297 — Wider-carriage review agrees at the accepted revision: four renders, closed XZ section, two-component inventory, 0.5 mm clearance and zero intersection; initial-pose limitation retained.
