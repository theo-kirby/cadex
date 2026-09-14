---
node_id: f2d3bc57-743b-5295-8114-e65854ed2df7
slug: eager-summit-3153
title: F9. Nothing regressed
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**Latest verification is green after the minimum-clearance correction (ADR-353): engine 2,142 passed/53 skipped, CLI 681 passed/1 skipped, fresh build and stage exited 0, and packaged lifecycle 18 passed.** Staged worker SHA-256 matches source. The corrected retained-input recheck leaves Finch at 44 failures and Robin at 39, and reduces Heron from 22 to 20 by removing only its two nominal-0.1 mm rounding flags. Accepted projects and retained input measurements were unchanged [rec: hidden-lodge-4550].

**Retained ot6 comparison now exists.** Fresh read-only Finch/Robin/Heron copies opened with `restore=False`; all measured pair distances/common volumes exactly equalled retained result tables, with unchanged script, metadata and result hashes and no unknown pairs. Initial counts were 406/44, 276/39 and 105/22 pairs/failures. Every difference against ot6 verdicts is explained: thread engagements, undeclared seatings, intended 0.05 mm gaps, and the two Heron rounding flags subsequently fixed. All three retained sweeps remain unavailable. Receipts and explanations are in `docs/probes/ot7/retained/` [rec: lucky-willow-8039] [rec: hidden-lodge-4550].

F8 added engine 2,127 passed/53 skipped, final CLI 666 passed/1 skipped and staged lifecycle plus smoke 43 passed. That unit changed no engine source or payload and needed no full build [rec: lean-fountain-9707]. Earlier F3 producer/consumer work also had fresh build/stage and green suites/gates [rec: misty-spark-6372] [rec: green-river-3790] [rec: curious-cedar-4881] [rec: kind-flint-2780]. F2's earlier full-CLI telemetry failure (636 passed/1 skipped/1 failed) and passing isolated retry remain part of the history; later green runs do not erase it or prove it pre-existing [rec: crisp-ember-0302].

Charter criterion: both suites and relevant packaged gate pass; retained ot6 Finch, Robin and Heron open, and checker differences against ot6 probes are explained [rec: kind-dusk-1609]. Reconcile judgement: retain `open`, as the latest impact explicitly directs. The previous missing-comparison claim is superseded: read-only opening and the comparison are evidenced. A rebuild/restore of all three retained designs is not newly claimed; all still fail fit and their retained sweeps are unavailable. This pass does not infer criterion closure beyond the declared impact [rec: lucky-willow-8039] [rec: hidden-lodge-4550].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
- happy-dawn-1960 — initial F1 suite results, focused licensing repair and packaged-gate scope
- steady-quartz-9854 — corrected CLI suite 636 passed/1 skipped; explicitly no fresh engine or F9 claim
- crisp-ember-0302 — F2 engine/packaged success, retained full-CLI telemetry failure and passing isolated retry
- misty-spark-6372 — fresh green engine/CLI/packaged producer runs; retained-design comparisons remain open
- green-river-3790 — ADR-350 consumer unit: engine 2,124/53, CLI 641/1, packaged 17 after one build and stage
- curious-cedar-4881 — ADR-351 backfill with iteration-13 gates: engine 2,127/53, CLI 641/1 to completion, packaged 18
- kind-flint-2780 — same green gates reaffirmed; Finch copy rebuilt under the product checker; retained-design comparison still open

- lean-fountain-9707 — green F8 engine/CLI and staged smoke verification without engine or payload changes
- lucky-willow-8039 — retained read-only ot6 comparison, exact pair-table equality and explained verdict differences
- hidden-lodge-4550 — corrected retained counts 44/39/20; latest green suites, fresh build/stage and packaged gate; F9 explicitly remains open
