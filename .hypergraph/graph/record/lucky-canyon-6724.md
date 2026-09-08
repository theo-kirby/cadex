---
node_id: fdf443f1-3f9a-5466-8ec2-8641402c0d64
slug: lucky-canyon-6724
title: 'Bet: distinguish offboard training from GPU requirements'
created_at: '2026-09-08T00:53:51+00:00'
parents:
- lean-union-6426
summary: ''
---
## What

Bet: correct the GPU-only rationale in docs/VISION.md guiding principle 5. This iteration is one evidence-backed scope decision, recorded before any implementation. Select a narrow prose correction distinguishing offboard training (an architectural boundary) from GPU availability (a scale choice). No runtime change is selected.

## Why

The overseer accepted [rec: lean-union-6426] and explicitly requested a concrete standing-maintenance finding and a bet before editing. Its orientation correction is exhausted. While reading the mandatory VISION document, found principle 5 saying training cannot run in the engine because it "needs JAX on a GPU" and describing a trainer copied to a GPU machine. That contradicts the deliberately supported CPU path and the already exercised local walk. This serves mission 2 and protects charter criterion **The walk exists and is tested headlessly** (crisp-reef-5607): authoritative agent guidance must not send a toy local rehearsal to a GPU machine. The criterion remains working; no missing runtime leg is alleged. What remains for this finding is the prose correction and its review, not another training run. Assume the overseer's explicit request authorizes this bounded decision unit without writing the planner's view. Later criteria remain parked.

## Method

Read STATE.md, the graph contract, VISION, actor and hypergraph-record skills, the two unreconciled records, training/SETUP.md section (b), docs/MUJOCO.md's live-gate qualification, and trainer backend metadata. SETUP explicitly supports CPU toy tasks; MUJOCO says GPU changes speed rather than semantics. training/cadex_train.py records jax.default_backend() at policy emission and receipt rather than requiring a GPU there. Existing [rec: fair-cedar-7455] reports a CPU walk with one iteration/four environments, 16.80 seconds, and a verified policy; this is cited evidence, not a new run.

Choose only VISION principle 5's rationale, plus a dated ADR-084 maintenance note when it is implemented. Replace the hardware necessity argument with the actual offboard dependency boundary and a short reference to training/SETUP.md for local CPU and GPU paths; retain agent-driven training, policy ingestion and human judgement. Remove the paragraph's obsolete dispatch-history digression rather than expanding it into a setup guide. Historical ADR decisions stay historical. Do not audit or rewrite the surrounding vision, trainer, MUJOCO history, protocol, project scaffold or runtime. No new ROADMAP feature checkbox is warranted for a correction to existing guidance. The next implementation must report diff/source-document checks and graph checks; no build or runtime gate rerun is selected for prose alone.

## Result

Concrete contradiction verified and one subtractive correction selected; no product file edited and no correction claimed landed. Pre-record hypergraph export succeeded (230 records, 34 state nodes, four plan nodes); explicit-cache hypergraph check exited 0 with zero violations/warnings. git diff --check passed. Post-record export/check and staged diff validation are required before this decision's single commit. Runtime tests, training and builds were not run for this record-only decision. No GUI, remote dispatch, provisioning, state/plan writes or charter edits.

Next: the separate maintainer/planner can incorporate this bet; its addition reaches the three-record reconciliation threshold. The actor does not reconcile. Implement only the selected VISION rationale correction if carried forward, preserving the already accepted lifecycle/review evidence. This is a new concrete finding, not a repeated administrative handoff or invented runtime repair.

Dispatch closed: 1 unit — selected an evidence-backed correction to VISION's obsolete GPU-only training rationale before editing.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: dffe23e96226ba1acce4955accf53f27456ae600

## State Impact

- target: early-arbor-7123 — Verified VISION principle 5 incorrectly makes a GPU necessary for training; select a bounded prose correction using the supported local CPU path, with no runtime repair or wider audit
- target: crisp-reef-5607 — Existing CPU walk remains working; selected documentation maintenance removes conflicting GPU-only guidance without replaying or recertifying the walk
