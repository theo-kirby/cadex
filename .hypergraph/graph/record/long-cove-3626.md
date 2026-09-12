---
node_id: 08614861-04f2-5ec8-89d1-954a1d4dbd2e
slug: long-cove-3626
title: Final policy publication failures retain failed telemetry (ADR-288)
created_at: '2026-09-12T16:29:55+00:00'
parents:
- kind-fountain-5086
summary: ''
---
## What

Final policy publication failures now write failed telemetry instead of leaving
an apparently active training snapshot (ADR-288). Retain the last committed
metrics, histories, task/model identities and checkpoint references. Add four
headless browser fault-injection cases and update CLI/trainer/roadmap docs.

## Why

Advances D8 (cool-gate-3332), following the final-packaging failure limitation
explicitly recorded by parent kind-fountain-5086. No critic message was supplied.
Selected this unblocked defect within the current lifecycle charter instead of
the obsolete clearance/section plan. The previous product-agent attempts were
quota-refused; this unit does not retry authoring or substitute a hand-authored
biped. D3/D9 remain dependent on actual fresh-biped training evidence.

## Method

Read the actor and hypergraph-record skills and repository, loop, graph and
vision contracts. Reproduced the defect using HEAD's trainer in a temporary
module: a fixture train reported iteration 0 then final policy_header raised.
Observed state=training, error empty, iteration=0 after the exception.

Extend the existing failure handler through final header construction, policy
validation, witness comparison, atomic final save and done reporting. No
algorithm, training dependency, engine API, payload or shell change. No build
needed. Failure is still re-raised; the progress snapshot supplies observers
with its terminal outcome. Hard kills and failure to write progress remain
limitations, documented explicitly.

The new CLI browser test imports the actual offboard trainer orchestration,
substitutes fixture training/policy math and exercises real checkpoint and
progress atomic writes. Each of four cases first observes training in Chromium,
then injects failure at header/validation/witness/save and observes failed
without reloading. Assertions cover exact exception identity, missing final
policy, retained curves/iteration/task/model hashes, checkpoint bytes/digest,
retained checkpoint in the browser, historical revision identity, next CLI
action and another run record's byte-for-byte preservation. Training is fixture
math: neither the checkpoint nor the run is claimed as engine-verified or real
GPU evidence. No new dependency or machine-specific path is committed.

## Result

The known final-publication failure gap is fixed and browser-tested. D8 remains
open for a real interrupted biped training run followed by a successful new
attempt; no D criterion is ticked by this fixture. Checkpoint references and
existing run records survive the fault injection. No state/plan/charter edits
or reconciliation were performed. This adds a second unreconciled work record.

Pre-existing red gate: startup commit 372d68ba also contains video implementation
and tests absent from the supplied latest record. The full CLI suite fails
`test_browser_plays_downloads_and_keeps_playback_across_polls` at test_video.py:153:
`FileNotFoundError` reading the expected downloaded rollout-<digest>.webm after
its ten-second deadline. The unchanged video-only browser test fails separately
(1 failed, 7 deselected in 11.33s), and a clean `git archive HEAD cli` extracted
to a temporary directory under the pixi environment reproduces the same failure
(1 failed, 7 deselected in 11.28s). Thus this is a demonstrated baseline D4
regression, not a telemetry change. Leave its fix for the next single unit;
do not claim the full CLI gate is green. The first clean-baseline invocation
used the interpreter without the pixi environment and skipped; repeated under
pixi to obtain the real failure. No baseline files were edited.

Validation: `pixi run python -m pytest cli/tests/test_review_server.py -k publication -q`
passed all four new browser cases (4 passed, 18 deselected in 18.60s).
`pixi run test-engine`: 2103 passed, 54 skipped in 339.71s.
`pixi run python -m pytest cli/tests -q`: 351 passed, 1 skipped, the one
baseline video-download failure above in 348.48s. The new tests and existing
trainer tests pass. `git diff --check` and hypergraph export/check pass; repeat
export/check after minting. Full logs remain outside the repository under the
operator temporary directory; commands and failure location above are the
portable compact evidence. No build, no new dependency, no real training run.

Dispatch closed: 1 unit — report final policy publication failures with retained telemetry and browser evidence; record the pre-existing video-download gate failure.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 372d68ba1d16a00ce403ac941b647e435e6079a4

## State Impact

- target: cool-gate-3332 — Final policy header, validation, witness and save failures now publish failed telemetry while retaining metrics/checkpoints; four actual-writer browser fault cases pass. Real biped interruption remains untested.
- target: candid-harvest-2614 — Baseline video-download browser test fails at test_video.py:153 with missing downloaded WebM, reproduced against clean startup commit 372d68ba; D4 download regression requires the next unit.
