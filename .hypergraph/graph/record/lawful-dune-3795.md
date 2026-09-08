---
node_id: fbe57c4d-7ab5-542a-a030-af1e1bc742a2
slug: lawful-dune-3795
title: Repair and qualify worker-bundle snapshot integrity
created_at: '2026-09-08T04:11:05+00:00'
parents:
- amber-fjord-1560
summary: ''
---
## What

Repair shared worker-bundle snapshot integrity at creation and reuse. Stage detached bytes from the same read used for the content-addressed name; validate cached members, reject legacy hardlinks/symlinks, and validate the winner after a failed publication rename. Retain whole-directory replacement, missing-member recovery and warm-bytecode reuse. Add regressions, ADR-244, the architecture behavior contract/date and a landed ROADMAP checkbox. Project asset staging is unchanged.

## Why

Execute the first short-rung bet in amber-fjord-1560 after nimble-basin-8423 reproduced the two-root stale-reuse failure. Advances missions 1 and 2 and charter criterion **The walk exists and is tested headlessly** by removing the reproduced worker identity defect before further lifecycle evidence. This does not identify the historical writer that caused the earlier import failure, nor prove agent compliance with purchased-hardware placement guidance. The existing baseline walk and second-mechanism evidence remain prior evidence; a fresh two-servo rehearsal is still missing.

At selection the local clock was 06:03 Europe/Madrid, before the provider's reported 08:30 reset, with no affirmative availability evidence. No provider probe, training, paid fallback, remote dispatch or GUI launch. The overseer's older request to reconcile is already reflected in STATE's checkpoint through nimble-basin-8423 and the subsequent amber-fjord-1560 bet; in any case a work actor is explicitly forbidden to reconcile. Choose the recorded bounded repair, not a new direction. No state, PLAN or charter edits.

## Method

Read actor and hypergraph-record skills, STATE, graph contract, VISION, engine state and preceding diagnosis/bet, then inspect shared_worker_bundle and staging tests. Replace worker use of `_link_or_copy` with a dictionary of immutable bytes read once, hash those bytes and write them to the pending directory. Validate every expected cached member by bytes, link count and symlink exclusion. Reuse leaves matching files untouched; replacement retires stale bytecode as well as modules. Keep asset helper untouched and remove obsolete hardlink/mtime test expectations and a vacuous hash assertion.

Tests use isolated module roots and a private cache for two-root in-place A-to-B mutation, already-corrupt bytes, legacy hardlinks, symlinks, mutation immediately after the last source read, and valid/invalid publication-race winners. Existing missing-member recovery and content reuse tests remain. Execute the selected seven cases against the previous function AST from HEAD without changing product files: six fail and the valid race control passes; new code's focused file has 32 passed. Final mutation test triggers during read on both implementations, not only the new staging path.

Run the full engine suite; one full build through `pixi run build-engine`; finish `pixi run stage-engine` before launching `CADEX_ENGINE_ROOT=<fresh payload> pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`; run `pixi run python -m pytest cli/tests` against the built engine. No shell or protocol edit, so no shell gate. Use a standalone local probe to compare all payload bundle members by SHA256 and require detached files; measure 20 warm bundle lookups, then drive the real staged cadexd through open, box write and rebuild and require identical accepted digests. No accepted project is modified: the probe creates a disposable project outside the checkout.

Local evidence: /tmp/cadex-42-{old,target,engine,build,stage,payload,cli,probe}.log; old-function driver /tmp/cadex-42-old.py; actual-worker/timing driver /tmp/cadex-42-probe.py. These logs contain machine paths and remain uncommitted. Check `git diff --check` and hypergraph export/check before the single commit.

## Result

All required commands exit 0: full engine suite **2085 passed, 52 skipped in 333.21 s**; built-engine CLI **195 passed, no skips in 241.04 s**; fresh packaged lifecycle **15 passed in 17.33 s**. Build/install and completed staging both exit 0. Focused file **32 passed**; the final warm-reuse assertion was narrowed to inode/mtime (reads may legitimately change atime), and its targeted rerun is **1 passed, 31 deselected**. Previous-function regression control exits 1 as expected: **6 failed, 1 passed, 25 deselected**. No failed product gate or unfinished build remains.

Runtime SHA256 is identical in source, pixi-installed modules and the fresh staged payload: `602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df`. Payload is `build/engine/cadex-engine-0.0.0-macos-arm64`; worker bundle is `project-b816c82c107e41400932d3a4`, with entry SHA256 `20544c5135fffb8829be634a1db4a1f7e9a7e3a39570743c9c372ac2239fa571`. All bundle members match payload bytes and have link count 1. Twenty warm lookups: median 2.493 ms, maximum 6.130 ms. Real box acceptance: 1319.6 ms; rebuild: 204.4 ms, digest unchanged at `5c826efc078bb5f1c6ebefa74acd4a8a6474d3aaea03aaa7b266c1415b1c4169`. These are local observations under concurrent verification load, not latency guarantees or a before/after benchmark.

Limits: no general concurrent-writer safety or whole-install snapshot consistency is claimed. A later mutation can race validation; repairing a corrupt directory can disrupt existing readers. The controlled publication race is covered, not a multiprocess stress test. Stage-only output retains the known external LC_RPATH audit warnings and is local, not a relocatable release. The installed application remains stale and was neither rebuilt nor launched. No blanket cache purge or accepted-project mutation.

Next: retain the quota-gated two-servo rehearsal as the next unit, using the now-qualified payload and corrected CLI, prescribed CPU/process-tree limits and manual render/section/inventory review. No fresh design/training/review evidence or new charter completion is claimed by this repair. No criterion checkbox in the human charter is edited.

Dispatch closed: 1 unit — repair and qualify detached, identity-checked worker bundles.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: b20b4493c94845bf09cac1a5ed8b88e2d50cde3a

## State Impact

- target: forest-wind-0342 — Repair reproduced stale worker reuse with detached snapshots and verified cached identity; full engine, build/install, fresh payload lifecycle and CLI gates pass. General concurrent mutation remains outside the guarantee.
- target: crisp-reef-5607 — Worker integrity prerequisite qualified on a fresh local payload with real acceptance/rebuild and identical digest; two-servo lifecycle rehearsal remains pending quota eligibility.
