---
node_id: c0510608-da6a-546b-976b-6a1ebf64fcce
slug: placid-ember-6741
title: Pin successful walk recovery after failed retraining
created_at: '2026-09-08T16:02:22+00:00'
parents:
- dusty-vale-2809
summary: ''
---
## What

Replaced the real-engine lifecycle regression's terminal export probe with successful recovery after injected trainer exit 7. The public walk retries the retained sweep using the prior successful policy/task, a new policy name and fresh output directory. Consolidated recovery guidance in CLI.md and the project scaffold, moved duplicate baseline review assertions to the recovered review, and combined ROADMAP's preservation/rehearsal entries into tested recovery. ADR-252 records these removals. Production behavior is unchanged.

## Why

This implements northern-sage-7087 short unit 2, following dusty-vale-2809's measured recovery and the overseer's instruction. Advances the charter's “The walk exists and is tested headlessly”, preserves “Iterate works”, and strengthens “The agent can see its work without a screen”. The assumption remains the measured reversible continuation: no rollback, no repeated --set, no partial failed policy as a warm start. No new recovery abstraction or failure matrix.

## Method

The existing test takes the toy through two successful walks, then writes partial policy output and exits the injected trainer with code 7. It checks retained policy_on=0/lift_weight=0.0003 in persisted project state; failure leaves prior artifacts and progress history intact. The new retry uses job3.cxpolicy, runs/walk-recovered, runs/walk-2/train/job2.cxpolicy and its job-task.json, an explicit task-change explanation, one iteration, four environments and timeout 600. The test explicitly selects JAX_PLATFORMS=cpu. It pins successful train/declare/rollout, retained weight with policy_on=1, stored-policy/verified-rollout digest equality, all four review outputs through existing helpers, unchanged prior artifact hashes, progress prefix preservation and actual last-success training/rollout reference values and digests read from prior rows. Project git status must remain clean.

## Result

Final gate: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` passed 223 tests, zero skips, in 201.12 s; log /tmp/cadex-iteration13-cli-cpu.log. The earlier full suite also passed 223/0 in 255.08 s (/tmp/cadex-iteration13-cli.log), before the final test/scaffold consolidation and CPU pin. An overlapping focused verification initially failed before recovery in its first training run with JAX cuSolver INTERNAL error: this shell had not selected CPU. Its 22 scaffold tests passed (/tmp/cadex-iteration13-final.log). Fixed the test's environment explicitly to CPU, matching the measured contract; the final full gate includes this change. No trainer/product change or GPU-scale claim.

Final CPU recovery reward -83.7824928985; training reward/step -1.1165243387, training-reported wall time 1.2503 s, witness error 4.9374e-9. Progress compares rollout against -55.3 at digest 5eed6c69 and training against -0.6151 at 68d95c6e, not the failed sweep's f3d22ecc or partial policy. Four review helpers passed, including the toy's one known clearance offender. Generated project: /tmp/pytest-of-theo/pytest-26/test_the_walk_takes_the_toy_to0/project; generated output is uncommitted. Each real training call remained toy-scale with timeout 600. No GUI, remote dispatch or build. The five test/document files total 74 added / 75 removed lines, including ADR and ROADMAP. `git diff --check` passed.

The finite recovery sequence is now covered; it selects no further rehearsal or failure matrix. Next: the separate planner chooses standing maintenance from fresh evidence without promoting parked criteria. The criteria already have working evidence in STATE.md; this unit leaves no missing recovery leg. GUI-attached behavior remains documented/unexercised and remote parity remains a local dispatcher stand-in. No whole-goal completion is claimed. This third unreconciled record reaches the maintainer trigger; no state, plan or Ouroboros file was edited.
Dispatch closed: 1 unit — replace export-only regression with tested successful retry and consolidate recovery guidance.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: dad895edabb65aff42a9e6ec8bf5167da6942d41

## State Impact

- target: crisp-reef-5607 — Real-engine CPU regression now completes recovery after trainer exit 7; final CLI gate passes 223 tests without skips.
- target: calm-peak-5247 — Retry pins retained sweep, prior artifact/history preservation and last-success training/rollout comparison references; finite recovery sequence is covered.
- target: damp-moon-9297 — Successful retry exercises inventory, clearance, render and section through existing review assertions.
