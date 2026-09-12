---
node_id: 7f9a057c-dc7a-5bcf-997f-d48fae6e30fb
slug: forest-ledge-2219
title: Retain parameter-sweep tessellation before walk training
created_at: '2026-09-12T19:49:52+00:00'
parents:
- candid-forest-9800
summary: ''
---
## What

Fixed ordinary `cadex walk --set` training-model retention by requesting standard tessellation, without edges, in `cadex params`' existing acceptance transaction. Added a real-engine headless-browser regression and updated the behavior documentation, ADR-293 and the landed roadmap item.

## Why

Advances D2 and D5 by closing the missing accepted tessellation defect discovered in Reed foot90, following the critic's requested unit. The smallest fix is at parameter acceptance: no extra render command or rebuild and no new walk leg. Foot90's historical available:false snapshot remains untouched. Product-agent revision authorship and real D7 copy/edit/retraining remain open. This dispatch explicitly forbids reconciliation; the new record reaches the three-record threshold, so reconciliation is due in a separately authorized pass, not this work iteration.

## Method

The new `test_browser_walk_parameter_sweep_retains_model_before_training` runs a real script acceptance and the real `walk --set arm_len=100` sweep on an 80 mm parametric hinged-arm fixture. Only trainer dispatch is intercepted, at the point where the test examines the retained run and opens Chromium: status running, exact revision/digest, two placed assembly components, 100 mm value and 80 mm default, loaded WebGL model, real orbit/zoom and visible rendered pixels. It deliberately ends training with a named failure, then accepts 140 mm through real `cadex params`. The same browser document observes HISTORICAL, keeps the original revision/value/default, and retained marker/component/mesh bytes stay equal while the current arm mesh differs.

Negative control: temporarily restoring the previous `set_params` request makes the targeted regression fail at model.available before training (1 failed in 2.52 s). Restoring the fix passes; after adding displayed parameter assertions the targeted run reports 1 passed, 26 deselected in 4.87 s. Commands: `pixi run python -m pytest cli/tests/test_review_server.py -k parameter_sweep -q`, `pixi run python -m pytest cli/tests`, `pixi run test-engine`, and `git diff --check`. Full-suite results are recorded below.

## Result

The swept accepted attempt now includes the tessellation that the existing locked snapshot reader needs before training. Later parameter revisions preserve that run's recorded assembly and specs. No historical project artifacts were edited, no biped/GPU training was launched (the CLI suite includes real CPU toy training), no new dependency or engine/shell/protocol/payload implementation changed, and no full build was needed. Standard tessellation adds work to all CLI parameter edits; this is intentional and avoids a second acceptance transaction. This is toy-engine/browser regression evidence, not a new real-biped training or whole-goal completion claim.

Engine validation: `pixi run test-engine` passed, 2103 passed / 54 skipped in 279.84 s. The additional focused browser check with the final displayed-parameter assertions passed. No packaged or shell gate was required because neither payload/protocol nor shell changed.

CLI validation: `pixi run python -m pytest cli/tests` passed, 363 passed / 1 skipped in 322.00 s, including the real parameter-sweep browser regression, retained-artifact path/isolation tests and CPU walk lifecycle tests. `git diff --check` passed. The two broad suites ran concurrently; their durations are not isolated performance measurements. The final focused browser test also passed after the displayed-parameter assertions were added.

Reconciliation is now due at three unreconciled records. No state nodes, STATE.md, PLAN.md or charter were edited; this contributor dispatch does not reconcile. No deviation from the requested fix/test/docs unit.

Dispatch closed: 1 unit — retain accepted parameter-sweep tessellation before walk training and verify browser history

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 41c1b8efe76a9b236b72d806eaedf999fcf9c3ae

## State Impact

- target: shy-meadow-0959 — Ordinary walk --set now requests accepted tessellation before retention; real-engine browser regression verifies current assembled model, revision/digest, parameter values/specs and orbit/zoom at trainer dispatch. Foot90 missing snapshot remains historical evidence.
- target: sharp-union-6036 — Real-engine parameter-sweep browser regression preserves the prior run's mesh bytes, assembled components, identity and specs after a later physical parameter revision; no historical backfill.
