---
node_id: 93186d66-96b8-53f8-bdde-361ca8531283
slug: polished-moss-9358
title: Clarify offboard training and supported CPU toy runs in VISION
created_at: '2026-09-08T00:59:44+00:00'
parents:
- civic-snow-4700
summary: ''
---
## What

Corrected docs/VISION.md guiding principle 5: offboard training keeps the trainer and JAX/MJX outside the engine payload, while toy tasks can train locally on CPU and larger runs can use a GPU. Removed the GPU-only rationale and obsolete dispatch-history digression. Preserved agent-driven task/run/result handling, put_asset policy ingestion, engine verification and human judgement. Added a dated ADR-084 maintenance note. VISION's verification date was already 2026-09-08 and remains accurate.

## Why

Implements the selected scope in [rec: lucky-canyon-6724] and dispatch [rec: civic-snow-4700], serving mission 2 and charter criterion **The walk exists and is tested headlessly** (crisp-reef-5607). Authoritative guidance should not imply that the proven local CPU rehearsal needs a GPU. This protects the working criterion; no runtime leg is missing before it can remain working. Assume the selected paragraph boundary is intentional: surrounding historical prose is outside this correction. No Later criterion is promoted and no clean walk is replayed.

## Method

Read STATE.md, the graph contract, actor and hypergraph-record skills, selected bets and docs/VISION.md. Compared training/SETUP.md section (b), which explicitly supports CPU toy tasks, with training/cadex_train.py backend metadata (jax.default_backend at lines 1725 and 1834), training/README.md's packaging contract and source guardrails in test_engine_purity_guardrails.py and test_dynamics_policy_trainer.py. Reviewed existing docs/probes/cold-revisit/README.md and [rec: fair-cedar-7455]: JAX_PLATFORMS=cpu, one iteration/four environments, exit 0, 16.80 s whole walk and verified policy. These are prior evidence, not new measurements.

Only edited the principle 5 paragraph and inserted the ADR-084 note. Reviewed the full two-file diff and ran git diff --check (exit 0). Pre-record hypergraph export succeeded (232 records, 34 state nodes, four plan nodes); explicit-cache hypergraph check exited 0 with zero violations and zero warnings. Post-record export/check and staged diff checks run before committing this unit.

## Result

The selected prose finding is corrected. VISION's replacement paragraph is shorter (13 lines replaced by 10); the ADR note adds the required removal rationale and evidence reference. No runtime gate, build or training rerun was performed for prose alone. No runtime, lifecycle scaffold, payload, shell, charter, plan or state changes; no ROADMAP feature checkbox invented for maintenance of existing guidance. Existing lifecycle evidence retains its toy-scale limits, GUI documented-only and remote scripted-only qualifications.

Next: review this bounded correction; only a concrete critic finding warrants a repair. Otherwise this selected direction is exhausted and the planner must select further authorized standing work. No new missing condition for the protected headless criterion was found, and whole-goal completion is not asserted. This record makes the unreconciled tail two nodes; the separate maintainer owns reconciliation.

Dispatch closed: 1 unit — corrected VISION's offboard-training rationale with CPU evidence and an ADR-084 maintenance note.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: eef0991872581349f72c5741608edaec9a336737

## State Impact

- target: early-arbor-7123 — VISION principle 5 now explains the offboard dependency/payload boundary and links supported CPU toy and GPU paths; obsolete dispatch-history prose removed with ADR-084 maintenance evidence
- target: crisp-reef-5607 — Removed conflicting GPU-only guidance using existing successful CPU walk evidence; criterion remains working with no runtime rerun or newly missing leg
