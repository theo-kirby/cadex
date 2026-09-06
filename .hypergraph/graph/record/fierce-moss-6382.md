---
node_id: 1a79efa0-d9ff-5a51-9eab-fcefda4fd996
slug: fierce-moss-6382
title: 'The INSPECTION_FAILED frame is the one tool-failure envelope (ADR-195): §7c item 5 closes, the engine node''s broken reason removed'
created_at: '2026-09-06T06:39:44+00:00'
parents:
- sunny-fern-8059
summary: ''
---
## What

Fixed the engine's one contract-violating refusal frame. `CadexInspection.complete_inspection` built its `INSPECTION_FAILED` frame by hand — `tool`, `failure_code`, `failure_stage`, `error`, plus `scope`, `target` and a size-accounted `result_json_bytes` — so it lacked eight `FAILURE_RESPONSE_SPEC` keys and carried three forbidden ones. It now calls `CadexTools.tool_failure("core.inspect", "INSPECTION_FAILED", "precondition", …)` like every other refusal, with `scope`/`target`/`path` under `requested` and the captured `kind` under `observed`; `result_json_bytes` is dropped, because a refusal has no page. ADR-195. A validator test and a recorded `inspect.failure` golden pin it. `docs/INTEGRATION.md` names the inspect refusal under the failure envelope; `docs/MUJOCO.md` §7c item 5 and the ROADMAP checkbox close.

## Why

Target: `forest-wind-0342` (the engine), `broken` on exactly this frame since the lifecycle audit (`sweet-light-3396`), and item 5 of the lifecycle frontier on `calm-peak-5247` — the last open item there. Mission item 2 (the robot lifecycle loop) with the smallest open unit; the file-lifecycle criteria the overseer named are already met (ADR-186/187/188, `simple-willow-8989` at `working`), so that suggestion was stale against STATE.md. The CLI validates every reply, so this frame was a hard `CadexdError` where the agent should have read a refusal. Assumption written here: `failure_stage` stays `precondition` (unchanged), and the size field is not added to the failure spec's optional set — a per-op failure shape by another name is what the spec forbids.

## Method

Read `FAILURE_RESPONSE_SPEC`, `validate_response`, `tool_failure` and the two existing tool-level failure goldens. Replaced the hand-built dict and its fixed-point size loop with one `tool_failure` call (CadexTools does not import CadexInspection, so no cycle; the import is local to the exception path). Added `test_an_inspection_exception_is_a_contract_failure_frame` (provokes the exception with an unknown captured kind, asserts the keys, runs `validate_response("inspect", …)`) and `response_schemas/inspect.failure.json`, which `test_failure_envelope_is_one_shape_for_every_op` now iterates. A second assertion — that an over-limit scalar refuses the same way — was wrong and dropped: the pager stubs large scalars instead of throwing. Docs: INTEGRATION (envelope paragraph, date), MUJOCO (§7c audit paragraph and item 5), ROADMAP checkbox, ADR-195. Gates: `pixi run test-engine` (full engine suite) and `pixi run python -m pytest cli/tests` with the built engine.

## Result

Commit `06a2748b`. `pixi run test-engine`: **1967 passed, 52 skipped** in 264 s (the new validator test and the `inspect.failure` golden included; the golden is now iterated by `test_failure_envelope_is_one_shape_for_every_op`). `pixi run python -m pytest cli/tests`: **117 passed** in 89 s with the built engine. `validate_response("inspect", …)` over the new frame returns no problems; the old frame returned eleven.

No protocol op changed, no `shell/` diff, no build needed. Housekeeping found on the way: `.git/sequencer` still held an unfinished `revert cda98460` from iteration 5 (00:35), so `git status` said "Revert currently in progress" while the tree was clean and HEAD was 50 commits past it; cleared with `git revert --quit`, which touches neither the tree nor HEAD. The shell still does not validate replies; that stays a decision of its own. Unreconciled tail after this node: one.

Dispatch closed: 1 unit — the INSPECTION_FAILED frame is the one tool-failure envelope (ADR-195); §7c item 5 closes; the engine node's broken reason is removed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 06a2748bf648b5713c5ad8744722da8036e6a92d

## State Impact

- target: forest-wind-0342 — broken → working: the INSPECTION_FAILED frame is now built by tool_failure and passes validate_response (ADR-195), pinned by a unit test and the inspect.failure golden; the one reason the node was broken is removed
- target: calm-peak-5247 — §7c item 5 (the INSPECTION_FAILED frame) closed 2026-09-06 (ADR-195); the lifecycle audit's ordered frontier is fully closed; what remains is the remote leg's GPU box on the RL node and the two documented-not-exercised modes
- target: chilly-union-8972 — the CLI's strict validator no longer turns an inspect exception into a hard CadexdError; it is a refusal frame the agent reads like every other tool failure
