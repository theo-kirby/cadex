---
node_id: 4eea3cfb-09d7-56c6-a111-16d3bcf9475b
slug: crisp-ember-0302
title: 'F2: declared contact and clearance checked against published geometry, with Heron defect fixtures (ADR-347)'
created_at: '2026-09-14T18:36:32+00:00'
parents:
- steady-quartz-9854
summary: ''
artifacts:
- docs/probes/ot7/FIT-INTENT.md
---
## What

Implemented advisory static fit intent (ADR-347): assembly contact pairs and minimum-clearance triples annotate published exact-solid measurements. Every pair reports overlap, missed contact, insufficient declared/default gap and unknown measurement as applicable; collision planes, planar CAD faces and explicitly marked world components report separate world-geometry findings. The CLI build reply and clearance report expose the findings. The API description exposes the declarations to the product agent.

## Why

This is the critic-selected F2 unit, targeting winter-key-1482 under the ot7 charter. It follows F1's complete measured replies (steady-quartz-9854). The older section-view plan is out of scope and was not followed. The actual first accepted Heron source declares a collision plane on its base, so detecting only visible floor solids would miss the charter's original defect. No product-agent design was edited or authored by the actor.

## Method

Added contacts and clearances keyword arguments to assembly.assembly and an optional world marker to assembly.component, including the project wrapper. Validate declaration structure and membership, not whether geometry satisfies it. Default calls omit the new definition keys to preserve legacy hashes. Reused _measure_clearance; the worker attaches intent and all fit_failures beside the definition, and the existing clearance inspection joins those published rows without rebuilding. World detection walks body declarations, including nested graph values, and checks placed CAD faces. No new op or OP_ARG_SPECS change, no shell code and no new dependency.

Known-answer real-OCCT fixtures report cheek/servo_tab common volume 248.2 mm³ even with contact intent, horn/link missed contact at 0.2 mm, the base's collision plane, a rotated planar CAD face, a passing touching pair, an undeclared 0.05 mm gap against 0.1 mm and a declared 0.4 mm gap against 0.5 mm. Malformed declarations are covered. A real CLI transaction accepts failing fit and preserves the accepted revision, digest and attempt on reopen; the same transaction passes against the staged engine. The API-description test pins discoverability. Updated XSCRIPT, CLI, INTEGRATION, ROADMAP and ADR-347. The receipt docs/probes/ot7/FIT-INTENT.md contains commands, results and retained-log digests under cadex-projects/ot7-fit-intent/evidence, expressed portably without machine paths.

## Result

F2's implementation and known-answer fixtures are present. One full build succeeded; installation and staging succeeded. Full engine suite: 2117 passed, 53 skipped in 332.10 s, exit 0. The API-description test was added after full-suite collection and passed in the focused engine/API run (15 passed); the final rotated-plane module passed 2 tests. Packaged lifecycle gate: 16 passed in 18.22 s. Packaged fit-intent transaction: 1 passed in 0.65 s. Final focused CLI clearance suite: 25 passed in 2.07 s.

Full CLI suite: 636 passed, 1 skipped, 1 failed in 542.34 s. The unchanged dashboard restart test at test_review_lifecycle.py:266 read history points 15, then iteration 18 and expected 19 points. Isolated retry passed in 7.98 s. Separate reads of changing telemetry suggest a timing race, but this does not prove it was pre-existing; the previous full-CLI baseline in steady-quartz-9854 was green. No owner-owned dashboard source or test was edited. The final clearance-report detail change occurred after full-CLI collection and is covered by the final focused suite. F9 stays open: this is not a full-CLI green claim, nor retained-ot6 regression evidence. The failure is retained with its output and digest for the next iteration rather than silently fixed outside scope.

Assumptions: contact tolerance is 0.001 mm, default gap 0.1 mm and overlap tolerance 1e-6 mm³. A solid bench has no shape-only distinction from a printable base, so environment solids require world=True; grounded alone is never world geometry. Collision planes reproduce the actual Heron failure without guessing from names. No question, new dependency, policy training, design turn or actor design edit. No state nodes or generated views were changed. F3 swept fit is the next charter rung, subject to the critic's regression assessment. Graph export/check and the commit close this unit.

Dispatch closed: 1 unit — implement and measure advisory static fit intent, with the CLI telemetry failure explicitly retained.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: f11ad78e641043f0dc122d1321ba823bd69e7def

## State Impact

- target: winter-key-1482 — Static fit intent implemented with known-answer real-kernel fixtures for Heron's buried tab, missed horn contact and collision plane; advisory acceptance and reopen identity pinned. Engine and packaged gates pass; full CLI has a retained telemetry failure and isolated retry pass. See docs/probes/ot7/FIT-INTENT.md.
- target: eager-summit-3153 — F2 engine suite 2117 passed/53 skipped, packaged gate 16 passed; full CLI 636 passed/1 skipped/1 failed at unchanged review-lifecycle telemetry assertion, isolated retry passed. No dashboard edits; full-CLI green and retained-ot6 comparison remain open.
