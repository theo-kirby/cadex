---
node_id: ddf7a0df-00c3-5d10-99a5-bd3e62992125
slug: stormy-quill-5350
title: 'L2 boards: sourced ESP32, Pi Zero and PCA9685 interfaces with placed wiring terminals'
created_at: '2026-09-06T20:32:13+00:00'
parents:
- humble-bell-9017
summary: ''
---
## What

L2 boards now compose through `lib.board`: ESP32-DevKitC V4 (WROOM-32E),
Pi Zero 2 W and Adafruit 815 PCA9685 revision C. Catalog rows carry
mounting interfaces, source links, explicit approximation lists and 38,
40 and 62 solder-pad terminals respectively. `BoardPart.terminals()`
feeds the existing `boards(...)` table and follows origin/direction/roll.
No new protocol op, dependency, payload rule or shell implementation.
ADR-202, XSCRIPT examples, PROVENANCE §8a, the catalog response golden,
INTEGRATION and the L2 ROADMAP checkbox accompany the feature.

## Why

One unit from short-horizon bet humble-bell-9017, targeting ready-falcon-6286
and brave-stone-9609 (mission 4). The overseer's maintainer/planner request
is already fulfilled by the checkpoint and commits ce0ba4b5, 6d3590fb and
7f79f1a7 on arrival. This actor did not reconcile or edit state, PLAN or
the charter. The GUI stale-revision replay risk remains open.

Reversible assumptions: choose specific manufacturer variants, never a
generic ESP32/PCA9685 outline. ESP32 V4 has no mounting holes. Use simple
PCB/chip geometry and identify nominal interfaces in the spec instead of
inventing an exact populated-board model. Pi terminal origins and hole
diameters remain nominal. Connector bodies, rounded corners and measured
populated-board mass are outside this slice and explicitly documented.

## Method

Read the actor, record and PDF skills, STATE/PLAN, VISION, the existing L0/L1
catalog/generator/test shape and the board declaration contract. Read the
manufacturer sources cited individually in ADR-202 and PROVENANCE §8a;
rendered the Espressif and Pi drawings headlessly to inspect their datums
and pin labels. Read Adafruit's rev C board at commit
32578c83a5ba2946249b80b1aa1fb18ae4e61e7d as data: its board coordinates
translate by (+1.905, +6.477) into the catalog frame. An independent XML
pad-coordinate audit matched all 62 catalog terminal XY/drill triples.
No vendor file, drawing, layout or software is committed.

Extended the library tests with dimension and pinout pins, nested-copy
isolation, transformed terminal coordinates and canonical board declarations.
The real-kernel script publishes all three boards (including translated
and rotated variants) and declares all their wiring tables through `boards`.

## Result

- `pixi run build-engine`: exit 0; one full build in this unit.
- Source `test_library.py`: 32 passed, including the real-kernel test.
- `pixi run stage-engine`: exit 0; local stage-only 2.4 GB payload. Its
  expected external-link audit warnings are not a relocatable release claim.
- Packaged `test_cadexd_lifecycle.py` plus `test_library.py`, with
  `CADEX_ENGINE_ROOT` naming that completed payload: 47 passed in 19.24 s.
- The first `pixi run test-engine`: 1972 passed, 52 skipped, 1 failed in
  265.17 s. This was my sequencing error, not a pre-existing baseline:
  staging ran concurrently, so the analysis exclusion test saw `bin/ccx`
  after the environment copy and before the normal payload prune. After
  staging completed, that exact test passed (1 passed in 2.28 s) and ccx
  was absent. Run staging before suites that inspect the payload.
- Final `pixi run test-engine`, after staging: 1973 passed, 52 skipped
  in 253.59 s, exit 0. No residual failures.
- `git diff --check`, hypergraph export and check: exit 0;
  no violations or warnings.

Next: the unchanged lifecycle entry point on a second repository-owned
mechanism, per the short plan. L3 stays open; GUI foreign-revision mutation
safety remains a runtime follow-up and is not closed by this catalog work.
This record adds one unreconciled unit; reconciliation belongs to the separate
maintainer dispatch.

Dispatch closed: 1 unit — L2 board variants with sourced interfaces, wiring terminals and real-kernel/packaged verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 7f79f1a7f8c95b45e6c84a9e1e83d422a07ac27f

## State Impact

- target: ready-falcon-6286 — L2 working: three explicit board variants over CadexCatalog, mounting patterns, placed solder-pad pinouts, approximation ledger, real-kernel coverage and packaged lifecycle/library gate (47 passed); final engine suite 1973 passed, 52 skipped. Connector bodies and measured populated-board mass remain outside the model.
- target: brave-stone-9609 — L2 joins L0/L1 through lib.board and existing boards/term declarations; ADR-202 and ROADMAP updated. L3, broad catalog and manufacturer-source horn/pigtail gaps remain open.
- target: early-arbor-7123 — Stage the payload before running suites that inspect it: concurrent stage-engine temporarily exposes copied ccx before pruning, causing a transient analysis exclusion failure. Completed payload and sequential final suite passed.
