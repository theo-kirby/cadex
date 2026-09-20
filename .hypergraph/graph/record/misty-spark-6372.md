---
node_id: 3b4cd6fc-f8a8-5d6c-9887-5f5a0dc2af3d
slug: misty-spark-6372
title: 'F3: publish bounded exact-solid hinge sweeps with explicit incomplete coverage (ADR-349)'
created_at: '2026-09-14T19:07:15+00:00'
parents:
- amber-lantern-9712
summary: ''
---
## What

Implemented the F3 product producer: `assembly.assembly(..., sweep_step_degrees=5)` publishes advisory `clearance_sweep` on the assembly output. Limited rigid-tree hinges move real descendant solids independently from the solved pose. Reports carry per-pair minimum distance, maximum common volume, first sampled contact in degrees, per-joint timing, sampling and budget limits, and explicit incomplete coverage. ADR-349 and docs/XSCRIPT.md document the behavior.

## Why

This follows amber-lantern-9712 and the critic's requested producer/publication unit, advancing curious-quill-9036 (F3). Finch's measured negative result is preserved; no contact angle is invented and no retained design is edited. Agent and CLI exposure remain the next product work, as the critic requested. This unit does not claim all of F3 or the overall goal.

## Method

The declaration is optional and omitted from legacy definitions. The worker captures static clearance, then sweeps before simulation can move components. Copied world BREPs and solved connector data reach a fresh FreeCAD subprocess; the parent never moves live components. Each joint first remeasures the solved pose and requires agreement within 0.0001 mm and 0.001 mm³. Endpoint-inclusive samples have at most the declared step. Each subprocess has 90 seconds, sharing 180 seconds across the assembly; 73 poses and 2,000 pairs cap each joint. Serialization and process cleanup add overhead to native-query timeouts. Unsupported joints, flexible components, closed/coupled/static-joint graphs, budget exhaustion, unsolved assemblies or unavailable geometry explicitly report incomplete. Joint ranges without limits are outside coverage. Findings do not reject acceptance.

A fork-only prototype stalled on a native futex after FreeCAD initialized. It was discarded in this unit in favor of a fresh executable inheriting the worker sandbox. The known-angle fixture uses two unit spheres on a radius-10 circle, a source with translation/rotation, and a 20-degree solved angle. Tests also deliberately corrupt the baseline, exceed pose/pair/total budgets, time out a real child, and supply a closed graph and a limited slider. The lifecycle test builds through the real sandbox, reads the published result, restarts, and checks byte-identical retained result plus identical accepted identity. An initial assertion comparing the whole script.json was corrected because access timestamps legitimately change; no acceptance behavior was changed to satisfy it. An engine suite collected before that test correction was interrupted and restarted.

Validation: `pixi run test-engine`: 2,121 passed, 53 skipped, 317.93 seconds. `pixi run python -m pytest cli/tests -q`: 637 passed, 1 skipped, 541.45 seconds. One `pixi run build-engine` succeeded; `pixi run stage-engine` succeeded. The staged payload's `test_cadexd_lifecycle.py` gate passed all 17 tests in 10.84 seconds, including sweep publication/restoration. The final focused sweep tests passed 2 tests in 1.10 seconds, with the additional closed-graph and pair-cap cases. No protocol operation or agent tool surface changed.

Receipts remain project-local at `cadex-projects/ot7-finch-sweep/evidence/producer/` (relative to the operator's projects parent):

- `ot7-sweep-build.log`: `f1120b15e6bc3830cdea1799909780a4ab6f5fbaeaec5a580942a1b14ddcc495`
- `ot7-sweep-cli.log`: `115f00a4493c3f49e32a51f1594e41ae3526077e24e435d2b6aec61b6fd45585`
- `ot7-sweep-engine.log`: `d355817ab43bcd0966ee616c1e25bad9a996d4cce883b67ccf79631db6ee7983`
- `ot7-sweep-fixture.json`: `3dac29cd9abb7d86200f66dfe9811dc5aa2157916609876ccdbdaea3bc0fec75`
- `ot7-sweep-packaged.log`: `ab81f5b7f6560defad6a8baf38bf687311f4d34c16b9723cf11af363620514ef`
- `ot7-sweep-stage.log`: `e6af0d4a960027d867cb0e194a8a09df882aefc2f7dbf9884d1a805a1a059d1c`

## Result

The real producer fixture measured first contact at 79 degrees, within one 1-degree sample of the analytic 90 - 2 asin(0.1) degrees (about 78.522). It swept 71 poses, measured minimum distance zero and maximum common volume 4.1887902047863905 mm³, with solved-pose agreement. Measured joint time was 1.017529861 seconds, total 1.023235607 seconds. Unchanged parent placements and baseline measurements are test-pinned. Stored sweep results survive reopen unchanged. The tested shipped payload has the producer, not just the experiment.

F3 remains open: the agent and `cadex clearance --sweep` cannot yet read these results, no product sweep has been requested on Finch, and non-hinge limited-joint support remains explicitly incomplete. Sampling is not continuous collision proof; native-query deadlines exclude serialization/cleanup overhead, and the existing enclosing script timeout still applies. F9 gains green engine/CLI/packaged runs, but retained-design comparison and other charter evidence remain outstanding. No new dependency, actor design edit, policy training, dashboard change or generated-state edit. ROADMAP was left untouched under the unattended-run contract. The tail reaches three records; the next dispatch is due for reconcile, but this contributor dispatch did not reconcile.

Dispatch closed: 1 unit — publish bounded exact-solid hinge sweeps with known-angle, coverage and restoration evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 4330f5b6033bd4887cf66119fdd7f348e38c37c2

## State Impact

- target: curious-quill-9036 — Product opt-in sweep declaration and published limited-tree-hinge measurements now exist, with analytic contact, solved-pose agreement, runtime budgets and restoration tests; agent/CLI exposure and other limited joints remain open.
- target: eager-summit-3153 — Producer unit passes engine 2121/53 skipped, CLI 637/1 skipped and staged packaged gate 17; retained-design comparisons remain open.
