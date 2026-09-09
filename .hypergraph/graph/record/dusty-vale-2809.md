---
node_id: be130b17-b312-53dd-a6e6-4e474a52e303
slug: dusty-vale-2809
title: Public walk recovers from failed retraining using the preserved policy
created_at: '2026-09-08T15:51:51+00:00'
parents:
- northern-sage-7087
summary: ''
---
## What

Rehearsed recovery after failed retraining through the public `./cadex walk`, reusing the existing real-engine fixture's isolated project. Added the measured retry command and results to docs/CLI.md, a recovery pointer to the project architecture scaffold, and the completed rehearsal checkbox to ROADMAP. No production behavior changed.

## Why

Follows northern-sage-7087 short unit 1 and the overseer's selected file-lifecycle recovery boundary. Advances the charter criterion “The walk exists and is tested headlessly” and protects “Iterate works”: preservation alone did not prove that the retained sweep could complete another walk. Assumption: retry under a new policy name in a fresh directory, using the last successful policy/task and an explicit task-change explanation, is the reversible continuation. The overseer's earlier reconcile request was already superseded by the supplied reconciled state and plan; contributors remain forbidden to reconcile. No parked criterion is promoted.

## Method

Ran `pixi run python -m pytest cli/tests --basetemp /tmp/cadex-iteration12-recovery`, whose existing test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates creates two successful CPU runs and injects trainer exit 7 after partial output. Its public export proves the retained policy_on=0, lift_weight=0.0003 sweep. Reused that isolated test project, snapshotting SHA-256 of every file under runs/walk-1, runs/walk-2 and assets (46 files), PROGRESS.md and its last compared numbers.

Ran the public command printed in docs/CLI.md with P set to that project: JAX_PLATFORMS=cpu, walk-recovered output, job3.cxpolicy name, init-from runs/walk-2/train/job2.cxpolicy, parent task runs/walk-2/train/job-task.json, task-change “lift weight increased from 0.0002 to retained 0.0003”, iterations 1, envs 4, timeout 600. No --set was passed. The external experiment script reused the existing inventory, clearance, render and section assertion helpers; checked train/declare/rollout legs, retained lift weight with policy_on=1, asset/verified-policy hash agreement, all prior hashes, progress prefix and both comparison-reference digests. `/usr/bin/time -v` measured the command and descendants. No model, GUI, remote dispatch, build or training beyond toy scale.

## Result

Recovery exited 0 without a product intervention. Prior rollout rewards were -27.1093774589 and -55.3476404085; recovered reward was -83.7819245968. PROGRESS compares -83.8 against the second successful rollout at -55.3, digest 746a9f53, delta -28.5. Trainer reward/step compares -1.116 against the second successful training row at -0.6151, digest 68d95c6e. It does not compare against partial failed output. All 46 old hashes and the progress prefix survived. The new policy witness error was 4.8792e-9; all four review outputs passed existing assertions, with one known offending clearance pair and two independent bounds comparisons passing. This proves continuation, not policy improvement under changed reward weights.

Training reported CPU, 1.386 s; the full retry took 16.45 s and maximum RSS 1,521,004 KiB, within the 15-minute/3-GB bound. The real CLI suite passed 223 tests without skips in 232.44 s; after the scaffold prose edit, its 22 tests passed in 1.32 s. git diff --check passed. Logs: /tmp/cadex-iteration12-cli.log, /tmp/cadex-iteration12-docs-final.log, /tmp/cadex-iteration12-retry.{json,stdout,stderr,time}; isolated project: /tmp/cadex-iteration12-recovery/test_the_walk_takes_the_toy_to0/project. Generated evidence remains outside the repository. Initial experiment harness glob incorrectly included an underscore before pytest's numeric suffix and failed before invoking Cadex; corrected the glob. An initial edit command used unavailable unqualified python; applied the edit with apply_patch instead. Neither required a product fix.

Next: short unit 2 replaces the existing regression's export-only ending with this successful retry and consolidates recovery documentation. The newly measured recovery path still needs durable regression coverage; existing criterion evidence retains its GUI-unexercised and remote-local-stand-in limits. No whole-goal completion is claimed, no state/plan file edited, no removals or direction change requiring an ADR. This record joins the one pending planner record for the separate maintainer.
Dispatch closed: 1 unit — prove public walk recovery from retained failed-retraining sweep and document the measured command.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 39ac2e4b8a33985fca7198f3a5981c70d6f96a9c

## State Impact

- target: crisp-reef-5607 — Public CPU retry from the retained failed-retraining sweep completes verification, rollout and all four reviews; durable retry regression remains next.
- target: calm-peak-5247 — Recovery preserves 46 prior artifact hashes and progress history; new comparisons reference the last successful training and rollout rows, not failed partial output.
