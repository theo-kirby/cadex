---
node_id: 8a275731-e595-5150-897c-6d4b41c8732a
slug: twilight-key-7506
title: Correct obsolete solver-change recovery guidance
created_at: '2026-09-08T00:44:46+00:00'
parents:
- green-wolf-7549
summary: ''
---
## What

Correct VISION's obsolete solver-migration recovery question to the shipped ADR-187 behavior. Update its source-verification date to 2026-09-08, append an ADR-187 correction note and annotate the existing completed ROADMAP recovery item. Runtime is unchanged.

## Why

Selected short-rung documentation maintenance follows [rec: green-wolf-7549] and the overseer's explicit dispatch. It preserves mission 1 and the shipped file-lifecycle charter criterion: a digest-moving change exposes the re-accept box and write_script recovers the project. Target is simple-willow-8989. The criterion is already shipped; this unit removes contradictory guidance, with no missing implementation claimed and no additional charter box ticked. Assume the existing recovery action is the intended resolution, as the source and ADR agree. No broader migration framework or audit is authorized.

## Method

Read STATE.md, the graph contract, actor and record skills, VISION, ADR-187 and the existing ROADMAP item. Inspect shell/scripts/startup/mesh_agent/cadex_backend.py: locked_out_project and reaccept_stored_script; shell/scripts/startup/mesh_agent/ui.py: MESH_AGENT_OT_reaccept_script and the chat-panel lockout branch; shell/tests/python/bl_mesh_agent_cadex.py: test_a_locked_out_project_is_reaccepted_from_the_chat. The backend opens with unrestored_ok=True and writes state.source; the action description explicitly accepts external edits. The existing regression asserts restore refusal, unchanged digest after refused Rebuild Model, successful re-accept, cleared failure state and a subsequent matching restore. This was source inspection, not execution of that regression.

## Result

VISION now states that restore refuses a changed accepted digest and the user explicitly re-accepts the engine-stored script through the shipped action. It no longer implies every solver upgrade necessarily changes a digest or that recovery is absent. Diff review confines changes to three documentation files. git diff --check passed; hypergraph export and hypergraph check passed before recording, with post-record export/check required before commit. No runtime suite, build, GUI, training or walk replay was run for this prose-only correction. Existing runtime evidence is preserved, not newly claimed.

Next: hand off for reconciliation and planning, as the overseer reports three records already unreconciled; this contributor does not reconcile or edit the plan/state. A critic finding is the only selected conditional follow-up. No parked criterion is promoted and the whole goal is not declared complete.

Dispatch closed: 1 unit — corrected obsolete solver-change recovery guidance against shipped ADR-187 behavior.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: ec0eb2747f589af11c04b002808283be73aa5fec

## State Impact

- target: simple-willow-8989 — VISION now documents shipped ADR-187 explicit re-accept recovery; source-inspected documentation correction only, runtime evidence unchanged
