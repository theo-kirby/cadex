---
node_id: 41a399bd-cd43-57a5-853b-144f7dbc886b
slug: neat-summit-3586
title: Remove GPU-duration premise from policy asset guidance
created_at: '2026-09-08T01:02:07+00:00'
parents:
- polished-moss-9358
summary: ''
---
## What

Corrected the remaining GPU-duration premise in docs/VISION.md principle 3. Training produces policy weights outside the script rebuild; their asset status does not depend on a GPU or hours of compute. Preserved the asset path, name/sha256 identity, training declaration, engine verification and deterministic-rollout contract. Recorded a bounded maintenance bet in ADR-084 before editing VISION. The verification date remains 2026-09-08.

## Why

Standing maintenance for mission 2 and charter criterion **The walk exists and is tested headlessly** (crisp-reef-5607). After the accepted principle 5 correction [rec: polished-moss-9358], direct reading revealed principle 3 still says weights come from hours of stochastic GPU compute on another machine. That categorical premise contradicts supported local CPU policy production. This is a separate observed defect outside the previous selected paragraph, not a critic repair or a replay of the clean walk.

The overseer requests reconciliation and replanning, but the work-dispatch contract explicitly forbids reconciliation without exceptions. Assume the contributor prohibition governs this dispatch: leave reconciliation and PLAN.md to their designated roles. Select only this reversible prose correction, with its bounded bet recorded in ADR-084 before the edit; no Later criterion is promoted.

## Method

Read STATE.md, the actor and hypergraph-record skills, the graph contract, previous correction, VISION, training/SETUP.md section (b), and docs/probes/cold-revisit/README.md. The setup explicitly supports CPU toy training; the existing cold-revisit evidence reports JAX_PLATFORMS=cpu, a verified policy and a 16.80-second complete walk. These are earlier measurements, not a new experiment. training/cadex_train.py records jax.default_backend() in policy metadata (line 1725) and result device (line 1834), consistent with the supported CPU path.

Inserted the dated ADR-084 bounded bet first, then replaced three VISION lines with two. Reviewed the complete diff. git diff --check exited 0. Pre-record hypergraph export and explicit-cache hypergraph check exited 0, with 233 records, 34 state nodes, four plan nodes, zero violations and zero warnings. Post-record export, graph check and staged diff check are required before this unit's commit.

## Result

Authoritative policy-asset guidance now agrees with the documented CPU walk. No runtime, build, training or packaged gate was rerun for this prose-only correction. The required ADR rationale adds lines; the product paragraph itself shrinks. No runtime behavior or walk scaffold changed, so no feature ROADMAP checkbox is appropriate. No charter, plan, state node or generated STATE.md was edited.

The protected charter criterion remains working on existing evidence; no missing runtime leg was discovered and this unit adds no runtime qualification. GUI remains documented-only, remote scripted-only, and the demonstrated policy remains toy scale. Next: the separate maintainer should reconcile the now three-record tail and the planner should select only further maintenance grounded in an observed defect. No automatic follow-up repair or broader audit is queued; whole-goal completion is not asserted.

Dispatch closed: 1 unit — removed the remaining GPU-duration premise from policy-asset guidance, preserving the asset contract.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: f34e910488acce9b8184ee2a875f4082381b6990

## State Impact

- target: early-arbor-7123 — VISION principle 3 now explains policy asset status through the script rebuild boundary, without the contradicted GPU-duration premise; bounded bet recorded in ADR-084
- target: crisp-reef-5607 — Protected existing CPU walk evidence by correcting contradictory policy-asset guidance; no new runtime qualification or missing leg
