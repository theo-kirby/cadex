---
node_id: b4dfbfc8-058b-5a88-9298-1a27581416b6
slug: nimble-basin-8423
title: Reproduce stale worker cache under in-place source mutation
created_at: '2026-09-08T03:57:52+00:00'
parents:
- misty-tide-6394
summary: ''
---
## What

Diagnose worker-cache identity in disposable scratch directories. Reproduce a bundle returning bytes inconsistent with its content-addressed name after an in-place write to a linked module. The tested CMake build-copy and install primitives do not reproduce corruption: both replace the destination inode. No product fix, source modification, real-cache mutation, payload change or accepted-project change.

## Why

Follows misty-tide-6394 and the scratch-only option selected in modest-valley-3313 after windy-dune-3488 observed a stale worker. Serves missions 1 and 2 and charter criterion **The walk exists and is tested headlessly**: mixed worker versions caused real lifecycle refusals despite corrected source. The baseline remains working, but this experiment identifies a reliability boundary that quarantine did not fix. It does not supply the still-missing fresh two-servo rehearsal or evidence of agent compliance with placement guidance.

At dispatch selection the clock was 03:55 UTC / 05:55 Europe/Madrid, before the reported 08:30 provider reset. No affirmative availability evidence existed; no provider probe or training was attempted. The reversible choice was the already-selected scratch diagnosis. The overseer's reconciliation request conflicts with this dispatch's explicit prohibition; state, STATE.md, PLAN.md and .ouroboros remain untouched. The growing tail is for the separate maintainer.

## Method

Read actor and hypergraph-record skills, STATE, graph contract, VISION, the latest guidance/removal/bet records and runtime/build source. Trace `CadexScriptedRuntime.shared_worker_bundle`: SHA256 over sorted distinct member names, byte lengths and bytes; first 24 hex digits name the bundle; `_link_or_copy` hardlinks when possible; `populated()` validates only file presence. Publication uses a temporary directory and replacement, which protects initial publication but does not isolate subsequent writes through linked source inodes. The project assets path also uses this helper but documents atomic replacement of its durable source; do not infer the same failure there.

Run a standalone Python probe outside the checkout with the pixi interpreter. AST-extract the unchanged `_DOMAIN_WORKER_BUNDLES`, `_BUNDLE_CACHE_DIRNAME`, `_bundle_members`, `_link_or_copy` and `shared_worker_bundle` definitions from current runtime source. Supply their stdlib globals and a private `tempfile.gettempdir` shim per trial, so no call can address the real shared cache. Copy every actual project-bundle input into scratch, with an independent immutable copy A. Obtain version B of `cadex_project_worker.py` via `git show 997293b8:src/Mod/cadex/cadex_project_worker.py`; do not check out or alter that revision.

For each operation copy A into a separate module root, create its project bundle with the actual extracted function, record SHA256/stat inode/link count, overwrite only the scratch worker with B, then ask the same cache for immutable A. Use the engine toolchain's CMake 4.2.3. Tested operations:

- Build resource primitive: `cmake -E copy <B/worker> <scratch-module-root/worker>`, exactly the primitive in `cMake/FreeCadMacros.cmake` lines 57–85 used by `src/Mod/cadex/CMakeLists.txt`.
- Install primitive: `cmake -P <scratch-install.cmake>` containing `file(INSTALL DESTINATION "<scratch-module-root>" TYPE FILE FILES "<B/worker>")`, matching the generated release install rule.
- Positive control: `(scratch_module_root / entry).write_bytes(old_bytes)`, truncating the existing inode.

Each trial records source/cache hashes and inode/link relationships before/after, directory name, and returned path/hash after requesting A. Assert initial hardlink identity and the positive control's stale reuse. Local probe and JSON stdout are retained as `/tmp/cadex-41-cache-probe.py` and `/tmp/cadex-41-cache-probe.log`; scratch roots are created by `tempfile.mkdtemp(prefix='cadex-41-cache-')`. These are local evidence, not committed artifacts. No full build, kernel execution or worker import is needed to establish file identity; no race or bytecode hypothesis is claimed tested.

## Result

Probe exits 0, ending `IN-PLACE MISMATCH REPRODUCED`. All three trials name the bundle **project-b816c82c107e41400932d3a4**, exactly the earlier observed name. A is 47,948 bytes, SHA256 `20544c5135fffb8829be634a1db4a1f7e9a7e3a39570743c9c372ac2239fa571`; B is 48,880 bytes, SHA256 `8312536e77dc2b59fe0b16a7ce210c0b9284901b9a14d8d5aa16cffc499d91fb`. These also match the earlier observed corrected/stale hashes.

Final-run inode evidence (local filesystem identifiers, not portable identities): build-copy initially shares inode 144125578, link count 2; afterward the cache retains that inode and A, link count 1, while the destination becomes inode 144125677 with B. Install initially shares inode 144125679, link count 2; afterward cache retains A there with link count 1 and destination becomes inode 144125779 with B. Both requests for immutable A reuse the original path and correctly return A. Thus the supported build/install primitives tested on this machine **do not cause** the mismatch; this is not an end-to-end build qualification and does not rule out other writers or races.

The positive control retains inode 144125781 and link count 2 in both source/cache, but changes cache bytes from A to B. Requesting immutable A returns the same A-named directory containing B. This establishes unsafe reuse under in-place source mutation, not the historical writer responsible for windy-dune-3488. Stop at this reproduction; no real-cache forensics or mutation follows.

Smallest corrective boundary for a later bet: worker-bundle creation/reuse in `shared_worker_bundle`. Decouple module snapshots from mutable source inodes (without changing the asset helper indiscriminately), and handle already-present mismatched bundles. A later regression should pin this two-root stale-reuse scenario. Hash/read/link races remain untested and should be considered when selecting the fix; this record authorizes no cache redesign and declares no fix landed.

Verification is the scratch probe, plus `git diff --check` and hypergraph export/check before commit. No engine/CLI/shell implementation was touched, so their full suites and builds were not rerun; previous green results remain previous evidence. No ADR direction change or landed ROADMAP implementation box is claimed for this diagnosis-only unit. Next: maintainer/planner should fold the three unreconciled records and select the corrective boundary; retain the corrected-payload two-servo rehearsal after quota eligibility, with the prescribed CPU limits and manual review. Charter boxes remain unchanged.

Dispatch closed: 1 unit — reproduce stale worker-cache reuse after in-place mutation and exclude the tested CMake copy/install primitives as its cause.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: c4b1e173dd4bffe0d727a2df58d93e98865ad91d

## State Impact

- target: early-arbor-7123 — Scratch diagnosis reproduces exact stale bundle name/hashes via an in-place hardlink write; CMake 4.2.3 build-copy and install primitives replace inodes and preserve the cache. Historical cause remains unproved.
- target: forest-wind-0342 — Worker bundle presence-only reuse accepts changed bytes under a content-addressed name when linked module inputs mutate in place. Correction boundary identified; no product fix landed.
