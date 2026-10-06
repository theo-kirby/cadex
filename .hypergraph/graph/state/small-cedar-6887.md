---
node_id: 6b5c4bb4-cfff-5eaa-8787-a8fc467f9861
slug: small-cedar-6887
title: F1. Evaluation applies the command filter the policy was trained with
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **F1. Evaluation applies the command filter the policy was trained with.** The trainer writes `action_filter_alpha` into the `.cxpolicy`; the engine's rollout and evaluation read it from the policy and filter commands as the trainer does. A filtered policy is evaluated and replayed with the same filter; an unfiltered one behaves as before (alpha 1.0); old `.cxpolicy` files still load; checkpoint rollouts and the evaluation film use the same path; the packaged gate passes [rec: light-mist-9160]. The human owns the checkbox.

**Evidence complete, awaiting the owner's tick** [rec: loyal-path-4209] (code in commit `8724d1f9`, ADR-558). Reconcile judgement: status `working`, as earlier runs' met-pending-tick criteria.

- `CadexDynamics.rollout_policy` reads the header's `action_filter_alpha` / `command_slew_deg` (`recorded_command_filter`) and applies clamp → EMA → slew in the trainer's order, first step unfiltered. `evaluate_success`, the checkpoint runner and the worker's viewport replay all go through it, and the report and every trace carry a `command_filter` block [rec: loyal-path-4209].
- Measured on a real alpha-0.5 policy (10 frozen seeds): played unfiltered it tips 10/10 (median tilt 49.3°, which reproduces its recorded evaluation exactly). Played at 0.5 it reaches the horizon 10/10 (median tilt 3.1°) but still fails on heading and steps, so that verdict is now real. An unfiltered passing policy re-evaluates 10/10 with identical metrics [rec: loyal-path-4209].
- Gates: test-engine 2594 passed / 58 skipped; F1 test 9 passed, and 9 failed with the fix reverted; packaged lifecycle gate 24 passed on the staged payload; CLI suite 1178 passed / 1 skipped (GPU hidden) [rec: loyal-path-4209].

## Negative knowledge

- [scope: test_review_overlay.py::test_designing_turns_idle_once_the_window_passes | confidence: high | evidence: loyal-path-4209] It flakes across a minute boundary, because it compares a `since` minute prefix against a timestamp recomputed later. It predates F1, passes on rerun, and was left alone.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-f1-evaluation-applies-command-filter)
- loyal-path-4209 — ADR-558 recorded and measured end to end; evidence complete pending the owner's tick
