---
node_id: 98768f6e-abd6-5956-9599-027ddafdcd2d
slug: dusty-oak-7376
title: Share cold retained-video verification across browser clients
created_at: '2026-09-12T20:53:22+00:00'
parents:
- neat-vine-2517
summary: ''
---
## What

Prevented duplicate retained-video hashing across concurrent browser clients with one bounded process-local verification lock (ADR-298). Added two-client browser corruption coverage and a 257-file cache eviction regression; documented serialization and its latency limits.

## Why

Advances D3 bounded dashboard operation and D8 retained-output integrity, following neat-vine-2517 and the critic's explicit fallback. First retried product-agent review-informed physical revision on the independent Reed copy. Session quota again refused authorship, so no actor-authored substitute geometry or retraining was performed. D9 remains open. This is one demonstrated review defect, not a reconcile pass.

## Method

Ran timeout --signal=TERM --kill-after=10s 240 ./cadex --project "$COPY" --out "$COPY/evidence/revision34" --json -p <read review/decisions/comparison and author, document and save one physical revision; no training>. Project-local evidence/revision34-agent.json and .stderr retain the receipt. claude-sonnet-5 returned session-limit refusal, an empty accepted_revision and no outputs; retained revision 25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc.

Ran pixi run python -m pytest cli/tests/test_review_server.py -k two_browser_clients -q before changing product code: failed in 1.19 seconds because two headless Chromium pages caused two reads of one cold video. The regression blocks the first hash, opens the second page and waits for its request to enter verification before release. Both pages must remain loading with no playable video, then refuse the intentionally corrupt bytes. Changed bytes require one fresh verification. This is deterministic concurrency fault injection, not real storage throughput or GPU training evidence.

The lock covers stat, LRU lookup and hashing, avoiding concurrent duplicate misses without a per-file lock registry. Exceptions release it. Existing containment, file-stamp and current-record digest checks remain. The 257-file test verifies 256-entry capacity, a cache hit without reading, and rehashing after eviction. Commands and scope are documented in docs/probes/video-history/README.md.

## Result

Two concurrent browser requests now hash shared unchanged bytes once rather than twice. Corruption remains refused in both clients, changed bytes are revalidated, and the cache remains bounded. Unrelated video checks can wait behind cold hashing, including cached lookups; separate processes do not share the lock/cache. No claim of a universal five-second latency bound, second-device observation or new D9 evidence. No new dependency, engine/shell/protocol/payload change, build, charter edit or generated/state/plan edit.

Validation so far: focused reader/server suite 54 passed, 1 skipped in 76.51 seconds; subsequent group including eviction 55 passed, 1 skipped in 75.81 seconds. Full engine suite 2103 passed, 54 skipped in 291.60 seconds. Initial full CLI run: 368 passed, 1 skipped, one new-test failure in 345.02 seconds. Its in-place write exposed an intermediate truncated file to polling and correctly caused a third hash; corrected the fixture to publish one atomic file replacement. This was test nondeterminism, not a reason to weaken changed-file verification. Corrected full CLI suite: 369 passed, 1 skipped in 324.08 seconds. Both required suites are green.

Real Reed copy recovery passed via PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/video_recovery.py "$COPY": missing and partial output refused, restored video plays/downloads, prior completed video remains available, all 418 protected files unchanged. SHA-256 remains 2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24. This uses the same machine's private address, not a second device. git diff --check passes. No build or packaged/shell gate required for the CLI-only change.

Dispatch closed: 1 unit — share cold retained-video verification across browser clients after product-agent quota refusal

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 3449fecf3b8a5796b2cd16a1152ce8dc214aefc6

## State Impact

- target: dawn-delta-4361 — Concurrent browser cold verification now hashes shared unchanged video once, with bounded process-local serialization and explicit latency limits.
- target: cool-gate-3332 — Two-client corruption refusal and changed-byte revalidation pass; 256-entry eviction proven; real Reed copy recovery preserves 418 protected files.
- target: silent-river-6649 — Product-agent revision34 request refused on session quota before authorship; no substitute geometry or training, D9 remains open.
