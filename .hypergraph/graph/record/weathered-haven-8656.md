---
node_id: 77a7378b-6103-5b12-ba09-992dfb0d2c82
slug: weathered-haven-8656
title: 'Bet: correct obsolete solver-migration recovery guidance'
created_at: '2026-09-08T00:38:35+00:00'
parents:
- fair-cedar-7455
summary: ''
---
## What

Selected one bounded standing-maintenance decision: correct the obsolete solver-migration paragraph in docs/VISION.md in the next work unit. Accepted the clean cold-revisit evidence [rec: fair-cedar-7455]; its conditional persistence repair is unnecessary. This is the bet before any code or documentation correction, not another walk rehearsal.

## Why

Concrete finding during required orientation: docs/VISION.md, Open questions, says a solver upgrade leaves a project refusing to open and that the migration path is missing. Current shell source and ADR-187 provide the explicit Re-accept Stored Script recovery. This contradicts the shipped charter file-lifecycle criterion about the re-accept box and can misdirect subsequent agents toward rebuilding an existing feature. It serves mission 1 and standing work to keep docs true. The shipped runtime criterion remains working; the missing work is correction of this current-status claim, not a new runtime leg or a Later criterion.

Assumption: the work-dispatch prohibition on reconciliation remains controlling despite the overseer's request for a maintainer/planner pass. Those roles own the generated views. This contributor records the finding and bounded bet without changing state, plan, charter or .ouroboros.

## Method

Read STATE.md, PLAN.md, docs/VISION.md, the actor and record skills, .hypergraph/AGENTS.md and the prior cold-revisit record. Compared the migration paragraph with shell/scripts/startup/mesh_agent/cadex_backend.py: locked_out_project caches the restore failure and reaccept_stored_script opens unrestored, checks the engine-stored source and invokes write_script. Read the chat panel's locked-out branch in ui.py and ADR-187, including its description of the existing regression test. Located test_a_locked_out_project_is_reaccepted_from_the_chat in shell/tests/python/bl_mesh_agent_cadex.py. These are source observations; no GUI test was executed and no new runtime result is claimed.

Bet: replace only the obsolete VISION open-question paragraph with the resolved ADR-187 behavior and retain the distinction between refusing changed accepted output and explicitly accepting the engine-stored script. Update that document's verification date, add an ADR-187 documentation-correction note for the removed stale claim, and follow the repository's documentation/ROADMAP conventions. Validate wording against the cited source and existing regression, run diff and graph checks, and commit one documentation correction. No shell or engine change, new migration framework, walk rerun, or broad documentation audit is selected. If source inspection during that unit reveals a different runtime defect, record it rather than expanding this bet silently.

## Result

One demonstrated documentation defect supplies an actionable next unit after the exhausted cold-revisit direction. No product files were changed, so no build, CLI suite or shell gate was run; the prior 195-pass CLI result belongs to fair-cedar-7455 and is not a new verification. This record-only decision requires graph validation and a clean diff. No ADR or ROADMAP completion checkbox is changed because the correction has not landed and this is no product direction change.

Next: separate maintainer should reconcile the now-three-record tail; planner should retire the clean revisit and its unneeded repair, then consider this bounded documentation correction. The active lifecycle/review criteria are reconciled working; no whole-goal completion is asserted and no Later criterion is promoted. Keep GUI unlaunched and training/remote machinery idle.

Dispatch closed: 1 unit — source-verified bet to correct stale file-lifecycle recovery guidance.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: d34fc75287c6af39e510eb5462d39a6eb2ae61f6

## State Impact

- target: simple-willow-8989 — Runtime remains working; VISION Open questions incorrectly says solver-migration recovery is missing despite ADR-187 and the reaccept_stored_script/chat-panel implementation. Selected a bounded documentation correction, not a persistence repair.
