---
node_id: f52b3d8b-98e9-5c58-af07-1fa769872f5e
slug: dawn-sky-3891
title: Failed retraining preserves policies and lifecycle comparison history
created_at: '2026-09-08T15:39:59+00:00'
parents:
- careful-union-7585
summary: ''
---
## What

Extend the real-engine lifecycle iterate regression with a failed third retraining attempt after two successful local toy runs. Update the CLI guide, new-project architecture scaffold and ROADMAP to describe preservation and the accepted sweep that remains after failure.

## Why

Answers the critic rejection of iteration 10 recorded in careful-union-7585: a record-only handoff was not a unit. The overseer explicitly selected this bounded failure-path regression. It advances the charter's “The walk exists and is tested headlessly” criterion and preserves “Iterate works” under the robot lifecycle node calm-peak-5247. The reversible choice is a fresh output directory and an injected trainer subprocess failure, with no live model turn, remote dispatch or new production behavior.

## Method

Extend cli/tests/test_walk.py::test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates: real engine and real local trainer, one iteration by four environments for each successful run. Snapshot SHA-256 for every file in both successful run directories and assets, plus script bytes, PROGRESS.md and git HEAD. A third walk accepts lift_weight=0.0003 with policy_on=0, warm-start arguments and the existing job2.cxpolicy asset name. Its executable trainer stand-in writes a partial policy into the fresh output directory, prints an injected failure, and exits 7. Assert CLI exit 1, sweep/train only, no declaration or review, all snapshot hashes and script bytes unchanged, prior progress preserved, exactly one additional sweep row/commit, and a public CLI revisit retaining the accepted sweep.

## Result

`pixi run python -m pytest cli/tests`: **223 passed, no skips, 231.54 s**, exit 0 (local log `/tmp/cadex-iteration11-cli-final.log`). The real-engine failed retry and subsequent export both passed. Successful toy trainer rewards per step in the initial focused run were -0.380211 and -0.61513; these are pipeline fixtures, not a quality improvement claim. Initial regression authoring exposed two incorrect test assumptions (commit-message ordering, and calling `params` without a required `--set`); both were corrected. The first full gate was 222 passed / 1 failed solely on that invalid test call; the corrected full gate above is green. `git diff --check` passed. Generated policies, traces and reports remain only in pytest temporary directories and no dumps are committed.

No production failure was demonstrated; the coverage gap and failure-state documentation are closed. This is a regression addition outside bookkeeping, not another successful-walk rehearsal as the sole deliverable. No build or engine/payload change was needed. GUI and actual remote execution remain unexercised per charter; no claim of gait quality or whole-goal completion. No further repair is evidenced by this unit, and no parked criterion is promoted. The two previously unreconciled records plus this one remain for the separate maintainer; no state or plan file was edited.
Dispatch closed: 1 unit — pin preservation of policies and comparison history after failed retraining.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: fa49ab103f596b250e463ef7f26170da0196ba4a

## State Impact

- target: crisp-reef-5607 — Real-engine iterate regression now exercises a trainer exit after partial output; both successful runs, stored policies and comparison history survive, with no failed-run declaration or review.
- target: calm-peak-5247 — Failed retries in a fresh output directory preserve prior artifacts and history while retaining the accepted sweep with policy_on=0; guide and project scaffold document this verified behavior.
