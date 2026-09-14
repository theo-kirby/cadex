---
node_id: f4758b48-6e00-5c73-b2a1-ce91f03bd040
slug: kind-reef-3852
title: Robin restore isolated to nondeterministic shaft offsets; accepted identity preserved, D7 still blocked
created_at: '2026-09-14T02:17:48+00:00'
parents:
- salty-fox-4449
summary: ''
artifacts:
- docs/probes/ot6/robin/RESTORE.md
- docs/probes/ot6/robin/restore.json
- docs/probes/ot6/robin/restore_probe.py
---
## What

Isolated Robin's restore digest mismatch to the offset of each catalog D-shaft
segment. Added the read-only reproducer `docs/probes/ot6/robin/restore_probe.py`,
the measured receipt `restore.json`, and the user-facing diagnosis `RESTORE.md`.
Repointed ancient-field-7584's missing capture_before.py artifact to the actual
retained capture_page.py rename; no historical script was fabricated.

## Why

This advances D7 (`ready-sand-2621`) by turning the retained restore blocker into
an isolated kernel reproducibility failure. It follows salty-fox-4449 and the
critic's instruction, not the stale clearance plan. **Deviation:** the critic
asked for a corrective change and passing Robin reopen/section before training.
This unit establishes the failure but does not repair it: no correction that
reproduces the already accepted BREP bytes was established. The bounded unit is
therefore a completed diagnostic experiment, not a partial product patch or a
claimed passing regression. Training remains blocked. Re-accepting a new bore or
weakening digest validation would violate the explicit accepted-state constraint.

## Method

Ran `./cadex section --project "$HOME/cadex-projects/ot6-robin" --plane XY
--offset-mm 50 --json`; exit 1 on the restore digest check. Compared the fresh
attempt with the retained accepted attempt: all 75 output definitions and solved
placements match; only wheel_l and wheel_r artifact bytes differ. Replayed the
accepted wheel definitions in four fresh FreeCAD processes with PYTHONHASHSEED=0,
fingerprinting all 40 operation results. Then saved each stable upstream shaft
intersection as BREP and ran the worker's exact makeOffsetShape call on the same
loaded file in four more fresh processes. No project script or acceptance write
occurs in the reproducer; it asserts script.json is unchanged. The nine probe
children each have a 120-second timeout. Full logs and replay results stay under
cadex-projects/ot6-robin-src/restore-probe; the receipt hashes their manifest.

The missing artifact was a real rename in git commit 9a4ff012 (88% similarity).
Used `hypergraph artifacts mv` on ancient-field-7584, preserving its body and
pointing to the current script. Historical commit 1af3cb9c retains the original
script; the current file includes later changes. Existing before images and
receipt remain present.

Checked the persistent service active before reproduction. Fresh headless
browsers after the probes at 1400x900 and touch-emulated 400x850 loaded Robin's
accepted model: 24 components, 57044 triangles, zero horizontal overflow. No
initial browser identity measurement was made; the document says so. The server
remains on Robin and no training was started.

## Result

The accepted revision remains 71709063d6af7ee357d5bb5b409e3332730a1465e0caa62f92f93535ec04cd84,
digest 806ab1343b7c94789c986fe244d610b93bf4e8516e4bf0457408f31f081f6c4e.
The fresh restore digest was c14013df428ff40ad9eef90cf75fc2096727f7f18c31a539a929621b171170ec.
36/40 replay operations were byte-stable. Each offset produced four hashes in
four processes; downstream wheel cuts also varied. With frozen inputs, each
loaded input had one hash and each offset four. This isolates the offset call
independently of assembly and memoisation; equal volume and topology counts are
not geometric equivalence checks and are not proposed as acceptance criteria.

D7 remains open and Robin reopen remains broken; section cannot proceed past
restore. Strict digest checks and the accepted identity are preserved. A future
kernel fix must demonstrate agreement with that identity; future determinism
alone does not prove recovery of this accepted project. No product code changed,
no new dependency, no build, no training, no state edit or reconcile.

Verification: full engine suite 2,114 passed / 53 skipped in 283.06 seconds;
existing packaged lifecycle gate 16 passed in 18.07 seconds; evidence size/privacy
tests 73 passed / 16 deselected. Full logs are hashed in restore.json. Those
passing generic gates do not contradict the reproduced Robin failure. Hypergraph
export/check passed before minting and must pass again with this record.

Dispatch closed: 1 unit — isolate Robin's restore failure to nondeterministic shaft offsets, preserve acceptance, and retain a reproducible diagnosis.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: b551ac29678b7636570e545239a123b592a0c77a

## State Impact

- target: ready-sand-2621 — Restore blocker isolated: all 75 definitions/placements match; only wheel BREP artifacts differ. Four fresh-process replays and frozen identical input BREPs locate nondeterminism at each shaft offset. No accepted-byte-preserving correction established; Robin reopen and training remain blocked. Engine 2114 passed/53 skipped, packaged lifecycle 16 passed; dashboard remains on retained Robin.
