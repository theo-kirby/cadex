---
node_id: feb0fb0e-1bdf-531e-a926-0b4947930fc1
slug: steady-rain-3009
title: Audit remaining L3 coverage and evidence limits
created_at: '2026-09-06T22:51:21+00:00'
parents:
- true-fox-1464
summary: ''
artifacts:
- docs/L3-COVERAGE.md
---
## What

Audited remaining L3 coverage against ROADMAP Phase 17 at revision 333c805788e6. Added docs/L3-COVERAGE.md with a coverage/evidence matrix, historical gate ledger, reproducible baseline command and bounded follow-up prerequisites. Added ADR-212 and checked only the narrow ROADMAP audit item. No API, recipe, source contract or lifecycle scaffold changed.

## Why

Iteration 19 follows true-fox-1464 and its first short unit, serving mission 4 and frontier rising-banner-4325 / brave-stone-9609. Four one-SKU families are delivered, but the wider promise remains open. The reversible choice is to state evidence limits before selecting more implementation. The injected overseer reconciliation request is stale against the current STATE/PLAN marks and conflicts with this work dispatch's explicit prohibition; no reconciliation, state, plan or charter edits were performed. The existing plan already puts Phase 8 readiness after this audit.

## Method

Read STATE, PLAN, VISION, graph instructions/config and actor/record skills; compare ROADMAP, PROVENANCE 8b–8f, ADR-205–211 and delivery records idle-dawn-5426, floral-stone-2866, frosty-snow-9642, morning-field-8202 plus solenoid negative evidence against CadexCatalog, cadex_library_api and test_library.py. This is an audit of repository-recorded sources, not a new manufacturer search or hardware qualification.

Trace actual-worker probe functions and the shared cadexd publication test. Confirm all four canonical/placed values publish, with joint compounds distinguished from other solids; N20 lacks the independent interface probes present for BLDC/L12/joint. Distinguish spec ratings, approximate geometry, shaft coupling fit, S-switch powered reachability and physical inertia. Existing actuator helper belongs to ServoPart, not ordinary L3 LibraryPart values.

Run CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py against the completed existing payload. No build, staging, engine source, protocol or payload mutation. Run git diff --check and graph export/check before the single commit.

## Result

Packaged lifecycle/library baseline: 90 passed, no skips, 15.85 seconds, exit 0. Full engine suite was not rerun for this documentation-only audit; historical final engine counts are attributed in the matrix. Existing local payload relocation limitations remain, with no portable-release claim. No known regression introduced.

Full L3 remains open: one BLDC winding has kV but no torque contract or plural size coverage; the common-size acceptance set is undefined, so a second envelope alone would not close it. Solenoid mounting/travel prerequisites and ADR-209 restart conditions are unchanged. Joint delivery is not duplicated. N20 interface probes are the smallest evidence-only improvement; a named additional BLDC size/winding needs source qualification including qualified torque evidence before delivery. Improved geometry alone proves neither powered motion nor inertia.

Next: the existing short plan's Phase 8 dependency/deletion-readiness audit, not another unconstrained catalog expansion. This record adds one audit to the supplied one-record unreconciled tail; the separate maintainer owns reconciliation. No GUI, training, remote dispatch, provisioning or inherited-tree edit occurred.

Dispatch closed: 1 unit — audit residual L3 coverage and preserve exact implementation prerequisites without closing full L3.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 333c805788e612364cae117d3741931008ac7480

## State Impact

- target: rising-banner-4325 — Coverage audit documents four delivered single-SKU families; full L3 remains open for BLDC common-size and torque scope plus deferred solenoid delivery. Acceptance set and source prerequisites are explicit in docs/L3-COVERAGE.md; Phase 8 readiness audit is next per existing plan.
- target: brave-stone-9609 — Existing packaged lifecycle/library baseline passes 90 tests without skips. Audit distinguishes N20 publication-only kernel coverage from dedicated BLDC/L12/joint interface probes and preserves fit, powered-reachability and inertia limitations.
