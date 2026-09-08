---
node_id: 4511c38b-74ea-5e06-b87b-0b41eb41dadd
slug: lean-union-6426
title: Remove obsolete frontier snapshots from agent orientation
created_at: '2026-09-08T00:51:46+00:00'
parents:
- first-wing-3387
summary: ''
---
## What

Correct the two obsolete live-state snapshots in .hypergraph/AGENTS.md: orientation now points to generated STATE.md and its cited state nodes, and the small-state convention no longer asserts a fixed node count. Add the verification date and a dated ADR-137 maintenance note. Preserve the historical adoption snapshot in the ADR.

## Why

Implement the concrete finding selected by [rec: first-wing-3387], serving mission 1 standing file-lifecycle maintenance. This explicitly addresses the critic rejection of [rec: careful-sand-9714]: the separate maintainer reconciliation and planner selection already landed (2f480de0, 593d5629, 6e5d46dc), so this actor fixes the selected defect instead of repeating its administrative handoff or writing state. Charter criterion advanced through accurate agent guidance: file lifecycle opening, re-acceptance and Save-As remain shipped; the supporting lifecycle-walk criterion remains working. The documentation gap was a false instruction to treat repaired lifecycle failures as current blockers. No missing runtime implementation is asserted before those criteria can be ticked; the remaining action is independent review of this correction, and charter edits remain human-owned. Later criteria stay parked. Assume the checked-in maintainer/planner evidence supersedes the repeated dispatch request, as the smallest reversible interpretation consistent with the actor prohibition.

## Method

Read the actor and hypergraph-record skills, STATE.md, the graph contract/config, VISION, ROADMAP convention, ADR-137, current lifecycle/RL state nodes and the causal records. Confirm clean starting tree and completed maintainer/planner commits. Replace transient frontier assertions with the existing generated-state reference and remove the obsolete count. No graph protocol changes, state writes, generated snapshot edits or .ouroboros edits. No applicable ROADMAP feature item landed, so no checkbox is invented. No runtime behavior or project-doc scaffold changes.

## Result

The selected prose finding is corrected. git diff --check passed. hypergraph export succeeded (229 records, 34 state nodes, 4 plan nodes before this record); hypergraph check with explicit record/state cache paths exited 0 with zero violations and zero warnings. Post-record export/check and staged diff validation run before the single commit. No runtime tests or build rerun for this prose-only unit, as the selected plan requires. No GUI, training, remote dispatch or provisioning. Next: review this bounded correction; absent a concrete review finding, the selected direction is exhausted and the planner must choose any further authorized standing work. Existing lifecycle and review evidence is preserved, not replayed or newly certified.

Dispatch closed: 1 unit — replaced stale orientation snapshots with generated-state guidance and recorded the critic-directed concrete fix.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 6e5d46dc86a74b138047b7ac659027f65d4cf808

## State Impact

- target: early-arbor-7123 — Agent onboarding now points to generated STATE.md and cited nodes instead of obsolete lifecycle/RL statuses and a fixed state count; ADR-137 records prose-only verification and the critic-directed concrete fix
