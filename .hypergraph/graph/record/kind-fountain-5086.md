---
node_id: 1a91ea00-7085-5da3-ba6f-f26fd42eec0f
slug: kind-fountain-5086
title: Retained training histories and live dashboard telemetry (ADR-287)
created_at: '2026-09-12T16:12:51+00:00'
parents:
- zesty-star-7710
summary: ''
---
## What

Retain loss and episode-length histories in the offboard trainer's existing
atomic progress snapshot and show run-local telemetry in the inspection
dashboard (ADR-287). Add checkpoint integrity checks and explicit missing,
invalid, stale, failed and terminal states with headless browser coverage.

## Why

Advances D3 (dawn-delta-4361), following the critic's request. Retried fresh
biped creation exactly once through the product agent; quota still refused
before authoring, so continued with telemetry rather than waiting. No synthetic
result is treated as real biped training or as completion of D3. The obsolete
clearance/section bets were not followed because this charter governs. This
is one telemetry unit with its prerequisite retry, not a second design unit.

## Method

Read actor and hypergraph-record skills, STATE and repository/loop/graph
contracts, VISION and training documentation. Product-agent retry:
`timeout --signal=TERM --kill-after=20s 1200 ./cadex --project "$PROJECT" --json -p <fresh Reed biped prompt>`.
Prompt requested a compact torso, two hip/knee legs, broad feet, analytic
geometry, parameters/specs, free root/ground, dynamics/actuators and forward
task; prohibited old imports and training. Output remains project-local in
`cadex-projects/ot5-biped/evidence/retry-7.json` and `retry-7.stderr`.

The trainer adds update time, task/model digests and two bounded histories
under the existing progress schema. First/last samples survive the 512-point
cap. Caught training failure keeps the last reported iteration and histories.
The dashboard reads only each run's fixed train/progress.json, including when
the initial run record has no progress reference yet. Two-second polling shows
metrics and SVG histories without page reload. Starting/training snapshots
older than 30 seconds are stale, including slow compilation; this is not a
process-death claim. Terminal done/failed snapshots do not expire. Checkpoint
references are contained within the run and bytes checked against sha256;
retained means integrity, not engine policy verification. No dependency added,
no engine/protocol/payload/shell product changes and no build required.

The browser fixture observes three separate atomic telemetry commits within
five seconds each, preserves historical model identity and page identity,
checks loss/episode histories, checkpoint creation and digest mismatch,
missing/partial output, stale-but-reachable server, failed and terminal states,
and switching away/back without borrowing another run's curves. Reader tests
refuse traversal/symlink escapes, wrong task identities, nonfinite and oversized
histories. A stubbed failing train call exercises the real snapshot writer and
proves 600 rows retain 512 samples with both endpoints after failure, even
when the training loop subsequently appends a nonfinite row. The saved report
copies the mutable curve/best containers so that later mutations cannot alter
its last committed identity. This aliasing refinement landed while the full
suites were running; the final focused trainer suite was rerun afterward. The
existing dependency-gated real toy trainer test also asserts both new histories.

## Result

The implementation and fixture behavior advance D3; real GPU/biped evidence
remains absent. Product creation exited 1 again with claude-fable-5 reporting
its session limit (reset message 2:30pm America/New_York). Accepted revision
and digest remain empty, outputs empty, no biped or training started. Do not
assume the reported reset guarantees the next attempt succeeds.

Retain/copy each run's train directory with its progress and checkpoint files.
Histories are sampled, not full-resolution logs. Remote training-progress.json
mirrors are outside this local telemetry path. Hard kills and final policy
packaging failures can leave stale telemetry rather than a failed snapshot;
this is documented and not represented as success. Checkpoint hashing occurs
on each poll; long-history overhead is not measured by this fixture. D3 still
needs actual GPU updates; video/lifecycle criteria remain open.

Validation: `pixi run python -m pytest cli/tests -q`: 340 passed, 1 skipped
in 310.56s; `pixi run test-engine`: 2103 passed, 54 skipped in 324.50s.
These are the previous baseline plus two CLI tests and one trainer test.
Final dashboard suite: 17 passed, 1 skipped in 26.91s (optional private-address
smoke not enabled). Final trainer suite: 30 passed, 8 dependency-gated skips
in 0.37s. Initial combined focused suite: 47 passed, 9 skipped in 24.92s.
No new gate failure. `git diff --check` passed. Hypergraph export/check passed
before minting and are repeated after the record. docs/CLI.md, training/README,
ADR-287 and docs/ROADMAP.md document this implementation; no charter/state/plan
edits. D3 is not ticked. No reconciliation performed.

Dispatch closed: 1 unit — retained training telemetry and live dashboard polling with browser evidence; real biped training remains blocked on provider quota.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 5afb109ea7943743da4b2bf7882addc739fa8e4c

## State Impact

- target: dawn-delta-4361 — Retained bounded loss/episode histories, checkpoint integrity and live polling pass browser/writer tests; D3 remains open pending actual fresh-biped GPU observation.
- target: silent-river-6649 — One product-agent biped retry again refused on session quota before authoring; no accepted biped or training produced.
