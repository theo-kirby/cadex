---
node_id: ef9dbd9f-1809-58ec-ba59-4399d854d811
slug: mild-river-8224
title: Repair Wren's fresh-project probe and record persistent review evidence
created_at: '2026-09-12T23:22:45+00:00'
parents:
- soft-aspen-5095
summary: ''
artifacts:
- docs/probes/wren-fresh/evidence.json
- docs/probes/wren-fresh/README.md
---
## What

Repair and execute the second-fresh-project Wren lifecycle probe, publish its receipt and current operator status, and restore the missing causal handoff from iteration 45. The persistent port 8765 now serves ot5-wren, accepted revision 5309bebc6597f7f792edea73265591480228f0ffb7e0b756b8fb755d9aa28f46, digest dbd02d7c12a0553b9ffadb3466e73da4055521264dd52e0bea40b2cc16588714, with no runs.

## Why

The critic rejected iteration 45 (commit 8bfa07c6, no record): its probe inventoried its own screenshot writes and never produced the committed evidence required by its tests. This unit follows soft-aspen-5095 and repairs that handoff, advancing D2/D10 and the second fresh lifecycle rung. Wren creation reached an accepted product-agent script but the CLI exited 1 at a provider session limit; a finished agent decision narrative and training are not claimed.

The requested exclusion alone was insufficient in the real run. In-place engine restore replaces attempt metadata and artifacts, so its byte-equality assertion failed before the browser and the served accepted model lost tessellation. Rather than weaken retained-input checking, the corrected probe performs two reopens on a disposable full copy and strictly hashes the served project. This is an explicit deviation from in-place reopen, not D6 completion evidence.

## Method

The inventory excludes only the invocation's evidence directory plus the existing .git exclusion; earlier evidence remains included. Added a regression that detects changed prior evidence while allowing a new screenshot. Corrected the nonexistent /api/review route to /api/project, asserted declared-default columns separately from explicit parameter overrides, and corrected the expected solid count from seven to eight (seven biped solids plus ground).

Switched the existing cadex-operator-review user service to Wren at the same private address and port. Snapshot both Reed projects during this iteration before the successful probe (after the switch); these snapshots do not prove isolation during the preceding creation turn. Early in-place restore attempts modified Wren attempt artifacts; a public rebuild with standard display restored its tessellation, with accepted revision and digest asserted unchanged. No historical run exists in Wren or was substituted.

Executed the command in docs/probes/wren-fresh/README.md against the persistent service. The receipt is docs/probes/wren-fresh/evidence.json; project-local evidence/lifecycle46 holds screenshots and the full receipt. Headless Chromium loaded in 0.84 s, drew eight solids, showed twelve declared defaults, exercised pointer orbit and wheel zoom, and preserved the empty accepted view across a poll. Two distinct engine processes matched accepted identity on the disposable full copy. All 66 served files outside this invocation's output directory remained identical; Reed original 582 and Reed copy 1017 files matched their snapshots. Inspected the saved viewport image. This is a same-machine private-network check, not a second-device visit or a D11 visual acceptance comparison.

## Result

The completed receipt and documentation restore the missing handoff. The persistent service remains running on Wren; no training is active. No new dependency or product behavior change. The delivered probe is complete for copy reopen and read-only inspection; a separate demonstrated D6 defect remains: in-place restore drops retained tessellation. The next unit should address that before claiming another complete fresh lifecycle. Wren still needs training, videos, design revision and retraining. The unreconciled tail is now three records; this contributor did not reconcile or edit state.

Validation: the final `pixi run python -m pytest cli/tests` passed 395 tests with 1 skip in 373.52 s. `pixi run test-engine` passed 2103 tests with 54 skips in 291.70 s. The initial full CLI process, launched before the corrected component-count test, reported 393 passed, 1 skipped and one stale seven-component assertion failure; the fresh full rerun above is green. The focused seven-test receipt/inventory suite passed. `git diff --check` passed. No build was needed for this probe/test/documentation unit.

Dispatch closed: 1 unit — repair and prove Wren's persistent review probe, retaining the in-place restore defect as an explicit handoff.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 8bfa07c6b9be385ab864df26344046331d2d7d42

## State Impact

- target: deep-clover-6012 — Persistent port 8765 now serves fresh ot5-wren at accepted revision 5309bebc6597 with no runs; real private-address browser checks pass and the service remains running.
- target: shy-meadow-0959 — Wren's eight solids and twelve declared parameter defaults pass pointer orbit, zoom, accepted identity and empty-run polling checks; compact evidence committed.
- target: clever-field-7845 — A demonstrated D6 gap remains: in-place restore republishes attempt artifacts without retained tessellation. Wren display was repaired with a public rebuild at unchanged accepted identity; successful evidence proves disposable-copy reopen plus strict read-only served-project preservation, not in-place display preservation.
- target: silent-river-6649 — Second fresh lifecycle begins with agent-authored Wren accepted and browser-reviewed, but creation CLI hit a provider session limit and no Wren training or video is claimed; missing iteration-45 handoff is restored.
