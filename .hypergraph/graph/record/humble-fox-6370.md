---
node_id: b0d6f5ff-be0b-5177-90c0-b6d4ad4b1503
slug: humble-fox-6370
title: Merge ot7 and prepare ot8 follow-up charter
created_at: '2026-09-20T18:45:05+00:00'
parents:
- lone-bramble-2589
summary: ''
artifacts:
- .ouroboros/goal.md
---
## What

The owner asked to review and merge ot7 and start the next run. ot7 merged
with `fa75c531` after the ADR-398 retention correction. Prepared ot8's
charter and configuration (ADR-399).

## Why

The operator selected the stated conservative default follow-up after
offering the owner alternate scopes: purchased-part provenance on the arm,
accepted-artifact smoke on the biped, and a measured diagnosis of the
balancer's holding-smoke failure. Do not interpret a completed bounded
experiment as every design's success.

## Method

Preserved the previous charter in git history, refreshed ot7's archive after
merge, and retained Opus-only roles, no model fallback, a 48-hour limit and
two accepted done verdicts. The new charter freezes experiment prompts and
slot accounting before product work, bars actor edits to designs and
training, and makes old projects read-only. The runner seeds the new named
criteria at first launch. No state nodes were edited by the operator.

A no-tool availability probe reached `claude-opus-5`, answered successfully,
and reported an allowed five-hour window at 0 percent. The existing runner's
window gate returned room=true. Prior full-suite and payload verification
is in `docs/probes/ot7/MERGE-REVIEW.md`; only operator docs/config changed
after that product revision.

## Result

The merge is complete. ot8 is prepared for preflight and launch. G1-G6 cover
the frozen contract, arm, biped, balancer diagnosis, regression floor and
closing report. A reproduced need for feedback control is an explicit
negative result under the no-training constraint, not a reason for endless
retries. Launch liveness is verified separately after starting the runner.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: fa75c5318eb226da0e297dd9341a59e58ef8b669

## State Impact

- target: mild-ledge-7157 — ot7 merged with fa75c531 after the ADR-398 retention correction; supersede the completed experiment charter with the new ot8 follow-up while preserving failed F5/F6 bars and the accepted-artifact F7 caveat.
