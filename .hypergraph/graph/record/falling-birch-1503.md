---
node_id: 3c34d459-cfbb-5a04-8727-01682eb8ae0b
slug: falling-birch-1503
title: Headless clearance reports every assembly pair without a read-time rebuild
created_at: '2026-09-07T22:42:07+00:00'
parents:
- happy-dune-3481
summary: ''
---
## What

Add `cadex clearance`, writing docs/clearance.md from `inspect scope="clearance"`. The assembly worker publishes every component pair's exact minimum distance and common solid volume at the initial solved pose, before simulation. Inspection joins component names, labels and catalog ids; the CLI applies finite nonnegative thresholds without rebuilding and follows every inspection page/preview. Intersection, below-clearance, clear and unknown are separate verdicts. The table lives beside the hashed definition. ADR-237, CLI/process docs and the ROADMAP item describe the result. Walk wiring is deliberately deferred.

## Why

Iteration 9 advances charter criterion "The agent can see its work without a screen" (damp-moon-9297), missions 6 and 2, following happy-dune-3481 and the planned clearance unit in crimson-canyon-5993. Separated bounding boxes do not prove sufficient clearance: only common-volume work may be pruned by box separation. Missing or failed measurements and unsolved assemblies must never become clear; legacy accepted attempts get unknown pairs and an explicit rebuild instruction. No assembly is unavailable. The reversible implementation reuses inventory's complete reader and the existing inspect operation, with no new OP_ARG_SPECS or shell change. The explicit contributor prohibition overrides the overseer's reconcile instruction; the separate maintainer owns the three-record tail after this unit.

## Method

Benchmark before changing the worker: for each examples/lifecycle/{hinged-arm,linear-carriage}/script.py, start a ready development CadexdClient, open a fresh project, and send six write_script calls with distinct trailing comments and the previous accepted_revision. Record all wall times; predeclare the median of the five requests after the first as rebuild latency. Add measurement publication and repeat before continuing. The stop rule is either +2 seconds or +20 percent on either recipe. No training is needed for these rebuild measurements. Repeat with the final built engine and investigate its first-request spike with a quiet repeat. Raw samples and digests remain in ignored build/clearance-i9/{before,after,final,repeat}.json; benchmark.py alongside them specifies the exact request loop.

Real-engine regressions use three placed boxes: 100 mm³ overlap, disjoint 1 mm gap, and clear 10 mm gap. Reverse result-publication order to prove unordered pair identity. Change both thresholds without adding an attempt or moving script.json. Exercise real inspection pagination with 60 large-label rows; check legacy/no-assembly, failed measurements, unsolved poses, invalid thresholds and the content-digest exclusion. The first focused engine run failed two synthetic fixtures because their worker reports omitted ok=true; fix the fixtures before the green gates.

Run the full engine suite, one pixi run build-engine, then JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests under the external build/clearance-i9/monitor.py process-tree limits (2.9 GB RSS and 850 seconds). Stage only after those suites finish to avoid exposing a partly pruned payload. Then run packaged lifecycle and clearance tests. GUI and remote dispatch are not exercised; CLI training remains toy local CPU in the training venv. Use the public ./cadex clearance --project call on both final benchmark projects, landing docs/clearance.md under each root.

## Result

Warm medians, before → initial measurement implementation: arm 0.458872 → 0.444663 s (-3.10%); carriage 0.446007 → 0.449866 s (+0.87%). Final built-engine medians: 0.462742 s (+0.84%, +0.003870 s) and 0.443270 s (-0.61%). Both stay below the predeclared stop conditions. Final first requests: arm 2.219 s versus 1.071 s before, carriage 0.658 s versus 0.651 s before. That arm spike is retained rather than hidden; first-request latency is outside the predeclared warm-median metric. A quiet repeat after the CLI suite did not reproduce it: first requests 0.649 / 0.660 s and medians 0.446437 / 0.451253 s (arm/carriage). All before/after/final/repeat content digests match: arm 8b676fdca572d644aba62da1171f0765ba907924b60af21db30d7205a8a5a32e; carriage e9773d5cc1231056c65728da31a3231f0f46c8f2d0d7c04bd9ed46b42926cb54. These measure rebuilds, not the standing under-16-second whole-walk baseline. Quadratic all-pair cost is not qualified for large assemblies.

Full engine gate: 2074 passed, 52 skipped, 320.44 s. The usual Blender/trainer-dependency and packaged-only cases skipped; they are not claimed as exercised. Final focused engine/CLI run: 14 passed, including the unsolved-pose regression added after full-suite collection. One build-engine: exit 0. Full CLI gate: 159 passed, no skips, 165.32 s; external monitor 165.96 s, peak RSS 1,133,821,952 bytes, no cutoff. Logs remain in build/clearance-i9/{engine,combined-focused,build,cli}.log and cli.monitor.json. Stage-engine: exit 0, completed 2.4 GB local stage-only payload with the expected external-link audit warnings (not a relocatable release claim). With CADEX_ENGINE_ROOT naming build/engine/cadex-engine-0.0.0-macos-arm64, packaged test_cadexd_lifecycle.py plus cli/tests/test_clearance.py: 24 passed, no skips, 17.12 s (15 lifecycle and 9 clearance). Logs: build/clearance-i9/stage.log and packaged.log.

Public recipe reports: build/clearance-i9/final-hinged-arm/docs/clearance.md names base/swing at 0 mm / 0 mm³ as below clearance; build/clearance-i9/final-linear-carriage/docs/clearance.md names base/slide at 34 mm / 0 mm³ as clear, at defaults 0.1 mm and 1e-6 mm³. CLI exit 0 means report written, not an all-clear verdict. No benchmarks, checkpoints, rollouts or machine paths are committed.

The charter criterion remains open: wire clearance into walk review next, then named-angle rendering and section views with their walk wiring. The current check is initial-pose only, not swept motion. This record makes three unreconciled nodes; no state, plan or .ouroboros edits were made. Graph export/check and git diff --check must pass before the one commit.

Dispatch closed: 1 unit — headless clearance/intersection reports name every pair without rebuilding at read time.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 8b876ffc89c4e7018c87a5a9c08ed9392f402bb1

## State Impact

- target: damp-moon-9297 — clearance/intersection CLI and inspect scope now name every pair, including separated pairs; recipe rebuild cost and digest stillness verified; walk wiring, render and section remain open
- target: chilly-union-8972 — cadex clearance writes docs/clearance.md with catalog labels and read-time thresholds; full CLI and packaged clearance gates pass
