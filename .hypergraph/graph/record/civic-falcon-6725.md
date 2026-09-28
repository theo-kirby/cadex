---
node_id: 30ee97aa-467c-527a-848d-4cdaaa8aa574
slug: civic-falcon-6725
title: 'ot10: a refused project publish rolls back, and argument values in result are refused at validation (ADR-434)'
created_at: '2026-09-28T21:11:18+00:00'
parents:
- chilly-willow-8488
summary: ''
---
## What

I fixed the engine defect that ended `ot10-biped-2`.
- A project publish that raised part-way through left its objects in the live document and wedged every publish after it. It now rolls back completely.
- An argument value returned in `result`, such as an actuator, is now refused at validation, with an error that names the fix.
- ADR-434 amends ADR-429. The regression runs under the real FreeCADCmd and fails on the previous source.

## Why

This is what the critic asked for, in the order it asked: fix the engine defect before any prompt change. That meant a real-kernel regression that fails on the current source, a fix (roll back what was created, or set UndoMode), an ADR amending ADR-429, a validation refusal for unpublishable output types with its own test, then test-engine, the CLI suite and the packaged lifecycle gate. I did all of it.

The critic's first line says "fold them in the next reconcile pass". I did not reconcile, because this dispatch forbids it in a work iteration. The tail is now 3 unreconciled records, which is the charter's trigger for a reconcile pass. No new biped turn was registered: per the critic, that comes after this unit. Target: A5 (`loyal-fountain-8709`) through the engine (`forest-wind-0342`).

## Method

**Reproduction.** Under `build/release/bin/FreeCADCmd` with the `project_xscript_api_integration` harness:
- Accept a parts-only revision.
- Publish an assembly script whose `result` includes `motor = assembly.actuator(...)`.
- Result: refused with `No native publisher exists for output type 'actuator'`, and 16 objects were left behind: the assembly, its dependencies, the components, `Joints`, and the origins.
- The next, valid publish was refused with `PUBLICATION_UNTAGGED_OBJECT` naming 15 of them. That is the biped's wedge.
- The same script with `doc.UndoMode = 1` left the one accepted object, and the next publish succeeded.

**Fix.**
- **Rollback.** `publish_project_candidate` (`CadexScriptedDomainPublication.py`) sets `UndoMode = 1` for its own transaction. In a `finally` it calls `clearUndos()` and restores the prior mode, so no undo history outlives a publish. I chose this over tracking and deleting created objects because deletion cannot restore a shape edited in place, or an object that was retired.
- **Validation.** A new `publishable_output_type()` is used by `validate_project_result` (`CadexScriptedRuntime.py`). Any other type is refused with `PROJECT_OUTPUT_UNPUBLISHABLE`: "Project output 'motor' is a `assembly.actuator` value, which is an argument to another call and cannot be published on its own. Remove 'motor' from `result` and pass it to the call that uses it (assembly.mjcf(..., actuators=[...]) and assembly.task(..., actions=[...]))."

**Regression.** `cadex_tests/test_publication_refused_rollback_live.py` has four real-kernel tests and one kernel-free test:
- A publish poisoned with an unpublishable output, last in the assembly pass, leaves the parts-only state exactly, and the next publish succeeds. The poison is appended after validation, so the test does not depend on the new refusal.
- A refused in-place edit (arm 80 to 70) restores the shape volumes, and undo mode and undo count are back to 0.
- An actuator in `result` is refused at validation with the code and the fix, and the document is unchanged.
- A kernel-free unit test calls `validate_project_result` directly.

I stashed the two source files and ran it again: all 4 kernel tests fail on the previous source.

**Docs.**
- ADR-434 is new, and ADR-429's "Not taken" bullet now points to it.
- `docs/XSCRIPT.md` publisher section: the rollback and the refusal. It no longer claims "one undo step".
- `docs/ARCHITECTURE.md` publisher entry, with its verified date bumped to 2026-09-28.
- `docs/probes/ot10/REPORT.md` defect 9 is marked fixed by ADR-434. biped-2's score stands.

## Result

**True now:**
- A refused project publish leaves the live document as accepted, whether it was refused by the lint or by a pass that raised half-way. The next publish succeeds.
- `accepted_live_state_preserved: true` is now actually true for the project path.
- An argument value in `result` never reaches the document.

**Verification:**
- New test file: 5 passed.
- `pixi run test-engine`: 2247 passed, 53 skipped, 0 failed (303 s).
- `pixi run build-engine` and `stage-engine` succeeded, and the staged payload carries the change.
- Packaged lifecycle gate (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64`, `test_cadexd_lifecycle.py`): 23 passed, 0 skipped.
- CLI suite (`pixi run python -m pytest cli/tests`): 1064 passed, 1 skipped, 0 failed (736 s).
- No protocol op, result shape, `OP_ARG_SPECS` or shell change.

**Not changed, and still open:**
- The cadexd document still starts at `UndoMode 0`. Only the project publish transaction turns undo on.
- The per-domain `publish_candidate(manage_transaction=True)` path is untouched. cadexd does not use it for projects.
- ADR-429's retire-linked refusal ("Cannot retire XScript output … foreign document objects still reference it") is a separate defect and is still open.

**A5 is still not met:** the confirmation round closed 2 of 3, and this fix re-scores nothing. The next unit is a new, registered biped turn on a new `ot10-*` project, with the prompt frozen and unchanged. Registering it is a recorded decision, not part of the closed round.

**The tail is now 3 unreconciled records** (`tidy-pebble-6206`, `chilly-willow-8488`, this one). That meets the charter's reconcile trigger.

Dispatch closed: 1 unit — the refused-publish leak that ended ot10-biped-2 is fixed (transaction-scoped UndoMode + clearUndos) and argument values in `result` are refused at validation with the fix named (ADR-434, amends ADR-429); real-kernel regression fails on old source; engine suite, packaged gate and CLI suite green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 45636b04b24f7249e218a68c0bcdd197d488d905

## State Impact

- target: forest-wind-0342 — A refused project publish now rolls back completely: publish_project_candidate enables UndoMode for its own transaction and clears the undo history after commit or abort, so created objects, retired objects and edited shapes return to the accepted revision and the next publish succeeds; validate_project_result refuses output types with no publisher (PROJECT_OUTPUT_UNPUBLISHABLE, fix named, actuator -> mjcf actuators/task actions). ADR-434 amends ADR-429; real-kernel regression test_publication_refused_rollback_live.py fails on the old source; engine 2247 passed/53 skipped, CLI 1064/1 skipped, packaged gate 23 passed (commit 45636b04). Still open: ADR-429's retire-linked refusal
- target: loyal-fountain-8709 — The engine defect that ended ot10-biped-2 is fixed (ADR-434); no score changes. A5 stays not met at 2 of 3; the next unit is a newly registered biped turn on a new ot10-* project with the frozen prompt
