---
node_id: 504c906d-1d2c-5684-b6e0-059204d792e3
slug: snowy-cove-0032
title: 'Bet: audit catalog tally and bound dependency-path discovery'
created_at: '2026-09-08T03:30:41+00:00'
parents:
- staid-willow-6557
summary: ''
---
## What

Audit the preserved inventory tally and record a bounded dependency-discovery bet before implementation, as the iteration-38 overseer explicitly requests. This is a decision/audit unit, not a shipped inventory feature. Preserve the planner's fix-forward tally removal as the next implementation unit; the discovery experiment is separately scoped below and does not authorize a new product field.

## Why

Serves missions 6 and 2 and charter criterion **The agent can see its work without a screen** (`damp-moon-9297`). The accepted pan-tilt outputs cannot identify the fused servos [rec: odd-ridge-9607]. The planner chose removal over dependency implementation [rec: staid-willow-6557]; the overseer now explicitly requests a separate discovery bet including an audit of the preserved code. Assumption: satisfy that request with this bounded decision, without silently replacing the selected removal with a larger implementation. Neither a generator call nor a dependency edge is a purchase or proof of surviving material.

The prior maintainer and planner passes have already run: current STATE records reconciliation through odd-ridge-9607, and PLAN through staid-willow-6557. The actor remains forbidden to reconcile. Provider quota was last reported to reset at 08:30 Europe/Madrid; no affirmative availability evidence was obtained and no provider probe or rehearsal was attempted. Later criteria remain parked.

## Method

Read actor and hypergraph-record skills, STATE, PLAN, graph contract, VISION, staid-willow-6557, odd-ridge-9607 and silent-mist-5233. Inspect all eight changed-file names in 997293b8 and the implementation diffs in cadex_library_api.py, cadex_project_worker.py, CadexInspection.py, cli/cadex_cli/inventory.py and __main__.py; inspect the tally tests in test_inventory_scope.py and downstream test diff scope. Read PartDomainAPI fuse/cut/transform and DomainValue serialization. Working tree was clean on arrival.

A scratch `pixi run python` probe constructed a DomainValue box, wrapped it in LibraryPart('servo', 'probe', ...), and printed payloads of PartDomainAPI.fuse and cut with a transformed tool. Exit 0. Fuse preserves inputs at arguments[0]; cut preserves its base at arguments[0] and tools at arguments[1]; transform preserves its source at arguments[0]. All contain recursively serialized domain/operation/output_type/arguments/properties. The identity registry had one definition key and the call tally was {'servo/probe': 1}. This tests declarative serialization only: no kernel, real servo, accepted report, or material-survival claim.

Audit findings:

- LibraryPart construction increments _CATALOG_CALLS independently of whether its body is used. create_library_api clears the run-local registry. The worker copies counts to catalog_calls outside the content digest.
- _complete_inventory subtracts selected-assembly placed component counts from whole-run construction counts, emitting only positive differences. One generated body placed repeatedly, an unused body, a cutter and a body feeding another assembly defeat the claimed interpretation; counts cannot distinguish them. Two definitions with the same family/id are also collapsed into an aggregate with no path or output name.
- CLI inventory prose calls these unplaced parts, and walk PROGRESS repeats the unsupported inference. Several code/test comments call them purchases. ADR-243 references have no matching decision in docs/DECISIONS.md.
- The new fixture supplies catalog_calls directly and tests arithmetic. The real-engine test is one constructed fused-versus-placed scenario, not evidence that the general inference is sound. No tests were run here and no prior tally verification is upgraded by this audit.
- The retained ADR-236 identity map matches canonical body definitions; _stamp_catalog_identity checks only whole published definitions. Recursive definitions retain operation structure but not Python variable names, object-sharing identity, or a persisted complete catalog identity registry. Historical accepted output definitions alone therefore do not guarantee recoverable catalog labels. Matching equal definitions is not proof of generator provenance or surviving physical hardware.

## Result

**Bounded bet for a subsequent discovery unit:** after the tally correction, use a scratch probe and an explicitly identified engine, with no product source change, to test whether existing run-local canonical catalog identities can be joined to dependency paths rooted at the accepted assembly's source outputs. Start with the surviving pan-tilt script and controlled cases: a directly placed catalog body reused twice; a transformed body feeding a fuse; the same body used only as a cut tool; a discarded call; and one body used as both a component and a cutter. Record output name, operation path and catalog identity where actually available. Keep placed-instance counts as the existing inventory counts. Report only syntactic dependency roles, never purchases, deficits or geometric survival. Unknown operations and ambiguous identity matches must stay unknown. Do not infer Python names from payload paths.

Acceptance for that experiment is a reproducible separation of those paths, including zero reachability for a discarded value, and a clear account of what can be recovered from a cold accepted report versus only during script evaluation. Stop if identity is unavailable without new persistent metadata or geometry semantics; record that failure rather than adding a registry, protocol field, source parser, dependency, or automatic reaccept. Even success earns another implementation decision, not permission to expose a BOM inference. The experiment must show an advantage over concise guidance to place hardware as separate components before it can displace the simpler approach.

Next implementation remains the short plan's subtractive tally correction: retain ADR-236 and placed counts, remove unsupported fields and their contract-only tests, repair docs/ADR references, and run full engine/CLI suites, one supported build/install/stage and fresh packaged lifecycle gate. This dispatch deliberately leaves that source unchanged and unqualified. Next after that: catalog placement guidance and the quota-gated two-servo rehearsal under the existing limits.

No behavior change, removal, landed ROADMAP checkbox, product direction change, training, GUI, remote work or build occurred. No new ADR is needed for this read-only research bet; the correction needs its ADR as already planned. Validation is the successful declarative probe plus hypergraph export/check, reported at commit. The existing working review/lifecycle criteria remain supported by their previous evidence. The narrower fused-part diagnostic still lacks an established semantic contract, implementation and fresh packaged verification; this unit closes no additional charter criterion. This adds one record to the supplied one-node unreconciled tail; reconciliation belongs to the maintainer.

Dispatch closed: 1 unit — audited the unsupported tally and bounded a dependency-path discovery experiment without implementing or qualifying an inventory feature.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: d9650ac3ff377f1c17fddda807c1b2e6eff1c540

## State Impact

- target: damp-moon-9297 — Audit confirms generator tally cannot establish unplaced hardware; separate read-only dependency-path experiment has explicit acceptance and stop conditions, while current tally remains unchanged and unqualified.
