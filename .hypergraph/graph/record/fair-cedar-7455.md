---
node_id: 3d83f6fa-ac80-51c0-aea7-fa071018e20c
slug: fair-cedar-7455
title: Fresh walk preserves policy and review across a cold project revisit
created_at: '2026-09-08T00:36:14+00:00'
parents:
- modest-grotto-1192
summary: ''
artifacts:
- docs/probes/cold-revisit/README.md
- docs/probes/cold-revisit/audit.json
- docs/probes/cold-revisit/PROGRESS.md
- docs/probes/cold-revisit/cli-gate.log
---
## What

Ran one fresh hinged-arm public lifecycle walk followed by a cold revisit of the same project using script, asset, inventory, clearance, render and section in separate public CLI processes. Retained compact audit, committed project documents, actual SVGs/JSON and CLI gate output under docs/probes/cold-revisit; ticked the ROADMAP maintenance item. No runtime change, removal or new feature.

## Why

Follows modest-grotto-1192 short rank 1, protecting charter criteria **The walk exists and is tested headlessly** and **The agent can see its work without a screen**, plus project/file persistence (missions 1, 2 and 6). Those criteria are reconciled working; no missing headless leg was found and no new criterion is promoted. The explicit work-iteration reconciliation prohibition overrides the stale overseer message: existing STATE already reflects the two fresh rehearsals, and this dispatch neither reconciles nor edits state, plan or charter. Conditional repair requires a demonstrated defect; none was found.

## Method

Fresh external project, documented script import and public walk with existing training venv, JAX_PLATFORMS=cpu, iterations 1, envs 4, seed 0, timeout 600. Existing monitor samples process-tree RSS every 0.2 s, stops above 2.9 GB or 850 s. Waited for producing process exit before issuing each cold command. No cache/asset deletion or recovery, GUI, SSH, remote training, provisioning or build. Reproduction commands and comparison procedure are in the evidence README.

Compared accepted revision/digest after each command; hashed assets and compared the public script read; compared restored policy receipt and trace with baseline; compared actual review SVG bytes with git show of the baseline commit, object geometry and named pair reports. Rasterized all five SVGs with inspection-only CairoSVG and inspected them. Copied existing example sensor notes and committed measured PROGRESS/ADR-002 into the source project; normalized machine paths in prose. Every retained project file equals final git show HEAD bytes and source project is clean. No checkpoint, policy or rollout bytes retained. No lifecycle behavior/scaffold changed, so no behavior-doc/scaffold edit or ADR direction change is needed.

## Result

Design and walk exited 0. Training reward/step -0.3801981508731842; witness error 1.3841167412209642e-09. Rollout seed 3, 50 steps, total reward -27.109384220927513, mean -0.5421876844185503. Whole walk 16.80 s, peak sampled process-tree RSS 1,056,636,928 bytes. Gate overlapped the walk; timings are observations, not benchmarks.

All six cold commands exited 0 and preserved revision 61cf81142adf36939673e39d02a78112657e6f85b668af9d8405c26407121062 and digest 663209866d7c8697992c7188fd138e9705c6418fa72ab22ac16bfc8207d4e477. Policy assets unchanged, receipt SHA matches review, restored trace byte-identical to baseline. Four named SVGs and interior section SVG equal committed baseline bytes; geometry objects equal. Inventory/clearance bytes unchanged: two synthetic uncatalogued components, base–swing contact 0 mm / 0 mm³, one offending pair, zero unknowns. Inspected section contours have areas 360 and 640 mm². Initial pose/tessellation and toy-policy limitations remain explicit; GUI documented-only, remote scripted-only.

Restore legitimately re-stages attempts; public review commands append/commit progress rows. Standalone section refreshes the same revision-addressed summary's timing fields; original measurements survive in committed baseline and review.json. These are expected behavior, not persistence defects. Architecture/decisions/script survived unchanged until the agent's final evidence note. No recovery needed. Audit retains baseline/final project commits and artifact hashes.

Full built-engine CLI gate **195 passed, zero skipped, 218.91 s**, exit 0; retained cli-gate.log. git diff --check and hypergraph export/check pass. No payload/protocol/shell changed; no packaged gate is claimed. This adds one unreconciled record to the one-node tail; separate maintainer owns reconciliation.

Next: no missing requirement was found before either protected criterion can remain working. The clean outcome exhausts this selected maintenance direction; conditional repair is not actionable. Planner should re-plan from authorized standing work without repeating the delivered walk or promoting Later criteria. Whole mission completion is not asserted.

Dispatch closed: 1 unit — fresh walk and cold public revisit preserve accepted identity, policy and review artifacts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: e24afc3b4bd2e3c87605122172b1a2eabedf9efc

## State Impact

- target: crisp-reef-5607 — Fresh bounded CPU walk followed by six cold public commands preserves accepted revision/digest, policy assets and byte-identical restored trace; 195 CLI tests pass without skips.
- target: damp-moon-9297 — Cold standalone inventory, clearance, four views and interior section match committed baseline identity and geometry; contact and unknown counts remain truthful, no persistence defect found.
