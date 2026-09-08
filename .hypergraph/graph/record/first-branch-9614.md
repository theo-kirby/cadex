---
node_id: 3a181266-9a74-5571-a962-dee868300558
slug: first-branch-9614
title: Fresh hinged-arm walk passes complete headless review rehearsal
created_at: '2026-09-08T00:18:10+00:00'
parents:
- sage-crow-3224
summary: ''
artifacts:
- docs/probes/complete-review/hinged-arm/README.md
- docs/probes/complete-review/hinged-arm/audit.json
- docs/probes/complete-review/hinged-arm/runs/baseline/review.json
- docs/probes/complete-review/hinged-arm/cli-gate.log
- docs/probes/complete-review/hinged-arm/cli-monitor.log
---
## What

Ran the separate fresh hinged-arm complete-review rehearsal through the documented public script/walk entry point. Retained compact inspected SVG/JSON and committed project-doc evidence under docs/probes/complete-review/hinged-arm, and ticked its ROADMAP work item. No runtime code change or removal.

## Why

Advances charter criterion **The agent can see its work without a screen**, damp-moon-9297, following sage-crow-3224 short rank 1. One mechanism is this dispatch's one unit; fresh carriage comparison remains required before criterion closure. Assumed the planner's explicit split governs the overseer's two-mechanism request. The overseer's reconciliation request cannot apply inside this explicitly contributor-only dispatch; no state, plan or charter was edited.

## Method

Used a fresh project outside the product checkout so automatic project commits remain separate. Commands and monitor invocation are in the evidence README: public `script --set examples/lifecycle/hinged-arm/script.py`, then `walk --iterations 1 --envs 4 --seed 0 --timeout 600` with the existing training venv and JAX_PLATFORMS=cpu. Existing monitor samples process-tree RSS every 0.2 s and cuts off at 2.9 GB or 850 s. Ran the full built-engine CLI suite under that same monitor. No GUI, SSH, provisioning, GPU dispatch or build.

Rasterized and visually inspected all four named SVGs plus the meaningful XZ Y=3.125 mm section with inspection-only CairoSVG and existing pixi libcairo. Checked actual contour coordinates/areas, revision/digest against rollout, trace reward/witness metadata, inventory catalogue fields, named clearance pair and unknown counts. Compared every retained project artifact's bytes with git show HEAD and verified clean project status. Audit hashes and source project commit are retained; checkpoints/policy bytes/rollout traces are not. The agent carried the existing example sensor notes after the script-only import and committed exact metrics, normalized project-path prose and the rationale in project ADR-002. No product behavior or scaffold convention changed.

## Result

Design and walk exited 0. CPU training reward/step -0.3801981508731842; witness error 1.3841167412209642e-09; rollout seed 3, 50 steps, reward -27.109384220927513 (mean -0.5421876844185503). Shared acquisition 0.7093497079913504 s; four-view rendering 0.5243987909634598 s; contour generation 0.00007558299694210291 s. Acquisition counts once; contour time excludes writes, walk_seconds 16.351018832996488 excludes final project commit, external whole command 16.61 s includes it. Peak sampled process-tree RSS 1,059,241,984 bytes. Gate overlap means these are observations, not benchmarks.

Visuals show blue base and orange arm in the accepted initial pose, legible captions and no missing components. Two closed section contours have areas 360 and 640 mm². Inventory: two components, zero catalogued, truthfully synthetic. Clearance: base–swing distance 0 mm, common volume 0 mm³, one offending/checked pair, zero unknowns. Initial contact is retained, never called clear. Render/section and rollout identity match; clearance revision matches. These are initial-pose reviews, tessellation sections and toy training, not swept safety or useful control. GUI and remote remain documented/scripted-only, with previous local CPU stand-in parity in copper-timber-8947.

Next: fresh carriage using identical settings and measurement boundaries, comparable committed PROGRESS.md, all views/section and pair checks, then assess combined evidence. Headless-review remains open. Separate maintainer owns reconciliation; this dispatch adds one unreconciled record.

Full built-engine CLI gate: **195 passed, zero skipped, 217.22 s**. Monitor exit 0, 217.87 s, peak sampled process-tree RSS 1,172,209,664 bytes. Logs retained; git diff --check passed. No packaged gate is claimed because no payload or protocol changed.

Dispatch closed: 1 unit — fresh hinged-arm complete review rehearsed and inspected; carriage comparison next.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 6e5b0c6ace216b6357fef4f3d29b29f83ab69c72

## State Impact

- target: damp-moon-9297 — Fresh arm public walk passed bounded CPU training, inspected four views and interior section, identity and committed-byte audit, inventory and contact checks; fresh carriage comparison remains.
