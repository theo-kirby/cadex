---
node_id: 8279436d-cd56-5bc6-8111-579c5f6ddeb1
slug: hidden-lodge-4550
title: 'F2/F9: tolerate numerical noise at clearance minima (ADR-353)'
created_at: '2026-09-14T21:07:11+00:00'
parents:
- lucky-willow-8039
summary: ''
---
## What

Fixed the measured minimum-clearance threshold comparison in engine fit annotations and CLI verdicts (ADR-353). An absolute 1e-9 mm deficit allowance applies to declared, default and CLI-overridden minima. Measurements remain unrounded, overlap/contact thresholds unchanged, and failing designs still accept. Added known-answer static and swept-minimum regressions and documented the rule in XSCRIPT, CLI and the retained comparison follow-up.

## Why

The critic selected the concrete F2/F9 defect found in parent lucky-willow-8039: nominal Heron 0.1 mm gaps falsely failed from floating-point noise. This unit follows that request. Source inspection found that swept reports contain raw extrema and no threshold verdicts; therefore swept coverage here is real-kernel extrema regression plus unchanged report serialization, not a new swept verdict implementation. The documented same minimum-comparison rule can be applied to those extrema. F4's earlier provider refusal remains distinct from a completed repair attempt: no product-agent invocation occurred this unit.

## Method

Changed both strict minimum comparisons to minimum minus measured distance greater than 1e-9 mm. Used an absolute allowance, six orders below the existing contact tolerance, with no relative growth at large minima. Tests cover exact equality, both retained Heron numbers (0.09999999999999952 and 0.09999999999999039), a 5e-10 mm deficit that passes, a 2e-9 mm deficit that fails, and 0.0999/0.05 mm gaps that fail. Declared minima and defaults get identical fixtures; the CLI override and large-minimum case also run.

A real OCCT slider moves two boxes over 0 to 1 mm in 0.5 mm steps with fixed lateral gaps of 0.1, 0.0999 and 0.05 mm. Static measurements and swept minima give the expected classifications under both declared and default minima. Raw extrema, zero common volume and absent contact remain pinned. Applying _check_fit to mapped extrema is a test of the comparison, not a claim that production sweeps call it. CLI tests preserve the complete swept report exactly.

Restoring only the old comparison expressions made the targeted tests fail: 13 failed, 16 passed, 31 deselected. Restored the fix before building; the initial focused run passed 60 tests. Full suites below include the subsequently added override/relative-tolerance regression.

Re-evaluated the prior retained *.clearance.json inputs through corrected fit_summary, asserting the inputs unchanged and exact expected counts. Finch remains 44 failures, Robin 39; Heron drops from 22 to 20. Only comp_upper_arm/comp_bearing_shoulder and comp_forearm/comp_bearing_elbow disappear from the failing set, each with nominal 0.1 mm distance and zero common volume. Existing receipts and accepted projects were not edited.

## Result

F2's rounding defect is fixed, with real static/swept-minimum evidence and CLI report regressions. F9 gains the corrected retained comparison and the verification results below, but the three retained designs still fail and their sweeps remain unavailable. F4 remains open: the prior session-limit refusal produced zero completed design turns; no repair is claimed. No design, parameter, accepted state, dashboard, prompt or dependency changed. No new roadmap checkbox was warranted by this correction to the already-landed static fit item.

The record is the third unreconciled work record. The critic requested the scheduled reconcile after it, but this dispatch explicitly forbids reconciliation, state nodes and generated-view edits and budgets exactly one work unit. Those stronger dispatch constraints were followed; the separate scheduled reconcile remains due.

Verification: pixi run test-engine: 2142 passed, 53 skipped in 315.52 s; pixi run python -m pytest cli/tests: 681 passed, 1 skipped in 554.44 s. One pixi run build-engine and one pixi run stage-engine both exited 0. CADEX_ENGINE_ROOT=<staged payload> pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py: 18 passed in 14.73 s. Staged worker sha256 equals source: b4a46025c6b8a07269fee04724e598c8b2bda5ae0ebc5ca6182b753c3379d5b7. git diff --check passed. No failing gate or unfinished implementation is left.

Logs and the retained recheck live outside the checkout in cadex-projects/ot7-threshold-check/evidence, with sha256 digests:

- build.log: 6c2a42ca42f21c50b6716a7beaf165da68a9b285dead1efdeb288988b45ea11c
- cli.log: 30981d11911db08f86d789095239a535b951344ffc75697bc4748045d01eb8aa
- engine.log: e55d0af426bf4c3291e51214f7a9066acb05e3823456b77d30b9ea5b09f1f59d
- focused.log: 6d7d173244a4166cce18df6a7b80d1fd93649886202cd86a01dde412845e7e62
- gate.log: e46d2e2c44db90f66353a4d85197e2d494cdd717db2c406971b08d35d04ae515
- old.log: d0c0e435546ccdd439ee1688a39bc9eb61733df2208ea9e02ce78a989e1d9b69
- retained-recheck.json: cacc749dbdd0a6a917d24917e5a80dc4a662432b3adefffbce048082ddd28764
- stage.log: e6af0d4a960027d867cb0e194a8a09df882aefc2f7dbf9884d1a805a1a059d1c

Dispatch closed: 1 unit — minimum-clearance numerical tolerance fixed and verified without changing measurements or acceptance.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 0258c7248fea57202ad3cde38aba78037383640e

## State Impact

- target: winter-key-1482 — Strict-minimum rounding defect fixed with absolute 1e-9 mm slack for engine and CLI declared/default minima; raw static and swept measurements preserved; known-answer regressions fail on old comparisons.
- target: eager-summit-3153 — Corrected retained verdicts are Finch 44, Robin 39, Heron 20; only two Heron rounding flags removed. Engine 2142 passed/53 skipped, CLI 681 passed/1 skipped, fresh build/stage and packaged gate 18 passed; F9 remains open.
